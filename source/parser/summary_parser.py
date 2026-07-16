import re
from typing import Dict, List, Optional

from .section_parser import split_sections

# Minimum word count for something to count as a usable summary paragraph.
# Relaxed slightly to catch concise, punchy summaries.
_MIN_SUMMARY_WORDS = 10

# Max words we'll keep even if the section itself is very long (protects
# against a summary section that never hit a recognized boundary at all
# and just absorbed the whole rest of the resume).
_MAX_SUMMARY_WORDS = 120

# A job-history line almost always contains a date range like
# "01/2022 – Current" or "Aug 2015 - Aug 2018". If summary content
# matches this, real Summary prose has ended and Experience content has started.
_JOB_DATE_RANGE_RE = re.compile(
    r'\b(?:0?[1-9]|1[0-2])[\/\-]\d{4}\b.{0,20}(?:-|–|—|to)\s*'
    r'(?:present|current|\d{4}|(?:0?[1-9]|1[0-2])[\/\-]\d{4})'
    r'|\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\'?\d{2,4}\b'
    r'.{0,20}(?:-|–|—|to)\s*'
    r'(?:present|current|(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\'?\d{2,4})',
    re.IGNORECASE,
)

# OCR resumes frequently use dates such as "21-Apr-2022 — Current".
_DAY_MONTH_YEAR_RANGE_RE = re.compile(
    r'\b\d{1,2}[\s/\-](?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)'
    r'[a-z]*[\s,\-]+\d{2,4}\b.{0,25}(?:\W+|to)\s*'
    r'(?:present|current|\d{1,2}[\s/\-](?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*[\s,\-]+\d{2,4})',
    re.IGNORECASE,
)

# A dense list of short comma-separated fragments (4+) reads as a
# skills/competencies block, not a prose sentence.
_DENSE_COMMA_LIST_RE = re.compile(r'^(?:[\w&/\'\.\s]{2,30},\s*){3,}[\w&/\'\.\s]{2,30}\.?$')

# OCR often mangles bullet characters when a bulleted skills list gets flattened.
# Three or more of these acting as separators within a chunk of text is a strong signal 
# that a bullet list has begun.
_BULLET_MARKER_RE = re.compile(r'[•«»*+·‣▪§]')

# Section-heading phrases distinctive enough to safely detect even when
# embedded mid-paragraph with no preceding newline.
_EMBEDDED_HEADING_RE = re.compile(
    r'\b(?:'
    r'OTHER\s+SKILLS|OPERATING\s+SYSTEMS|CORE\s+COMPETENC(?:Y|IES)|'
    r'TECHNICAL\s+SKILLS|KEY\s+SKILLS|SKILL\s+SET|SOFTWARE\s+SKILLS|'
    r'ADD[\s\-]+ON\s+(?:DOMAIN\s+)?SKILLS|KEY\s+(?:COMPETENC\w*|SK\w{2,8})|'
    r'CERTIFICATIONS?(?:\s*&\s*TRAINING)?|PROFESSIONAL\s+EXPERIENCE|'
    r'WORK\s+EXPERIENCE|EMPLOYMENT\s+HISTORY|CAREER\s+HISTORY|'
    r'ACADEMIC\s+QUALIFICATIONS?|EDUCATIONAL?\s+QUALIFICATIONS?|'
    r'PROJECT\s+EXPERIENCE|KEY\s+PROJECTS|ACHIEVEMENTS|LANGUAGES\s+KNOWN'
    r')\b',
    re.IGNORECASE,
)

# A short title-like line containing one of these terms is a reliable section boundary.
_FUZZY_BOUNDARY_RE = re.compile(
    r'^(?:[A-Z][A-Za-z&/\-]*\s+){0,4}(?:skill|skills|experience|employment|'
    r'education|qualification|certification|achievement|project|language)\w*'
    r'(?:\s+[A-Z][A-Za-z&/\-]*){0,3}:?$',
    re.IGNORECASE,
)

_LIKELY_SKILLS_HEADING_RE = re.compile(
    r'^(?:key|core|technical|add[\s\-]*on)\s+[a-z]{3,12}:?$',
    re.IGNORECASE,
)

# Regexes for surgically stripping contact info out of the summary text
_EMAIL_RE = re.compile(r'[\w.\-]+@[\w.\-]+\.[A-Za-z]{2,}')
_PHONE_RE = re.compile(r'(?:\+?\d{1,3}[\s\-]?)?\(?\d{3,4}\)?[\s\-]?\d{3,4}[\s\-]?\d{3,4}')
_URL_RE = re.compile(r'https?://[^\s]+|linkedin\.com[^\s]+|github\.com[^\s]+', re.IGNORECASE)


def _earliest_bleed_cutoff(text: str) -> Optional[int]:
    """
    Find the earliest character index in `text` where content stops
    being Summary prose (checking embedded headings, dates, and bullets).
    Returns None if no cutoff is found.
    """
    candidates = []

    m = _EMBEDDED_HEADING_RE.search(text)
    if m and m.start() > 0:
        candidates.append(m.start())

    m = _JOB_DATE_RANGE_RE.search(text) or _DAY_MONTH_YEAR_RANGE_RE.search(text)
    if m and m.start() > 0:
        candidates.append(m.start())

    bullet_positions = [mm.start() for mm in _BULLET_MARKER_RE.finditer(text)]
    if len(bullet_positions) >= 3 and bullet_positions[0] > 0:
        candidates.append(bullet_positions[0])

    return min(candidates) if candidates else None


def _looks_like_bleed(line: str) -> bool:
    """True if this whole line looks like it belongs to Experience/Skills rather than Summary."""
    stripped = line.strip()
    if not stripped:
        return False
    if _JOB_DATE_RANGE_RE.search(stripped) or _DAY_MONTH_YEAR_RANGE_RE.search(stripped):
        return True
    if _EMBEDDED_HEADING_RE.search(stripped):
        return True
    if len(stripped.split()) <= 8 and _FUZZY_BOUNDARY_RE.match(stripped):
        return True
    if len(stripped.split()) <= 5 and _LIKELY_SKILLS_HEADING_RE.match(stripped):
        return True
    if _DENSE_COMMA_LIST_RE.match(stripped) and len(stripped.split()) > 8:
        return True
    if len(_BULLET_MARKER_RE.findall(stripped)) >= 3:
        return True
    return False


def _looks_like_header_field(line: str) -> bool:
    """True if this line is a name/email/phone/address/URL header field rather than prose."""
    stripped = line.strip()
    if not stripped:
        return True
    if _EMAIL_RE.search(stripped) or _PHONE_RE.search(stripped) or _URL_RE.search(stripped):
        return True
    # Short lines (<= 4 words) at the top of a resume are almost always name/title/location
    if len(stripped.split()) <= 4:
        return True
    return False


def _clean_summary_text(raw: str) -> str:
    text = raw.strip()
    # Strip stray leading/trailing quote marks and punctuation left over from OCR.
    text = text.strip(' "\'\u201c\u201d\u2018\u2019.,-')
    text = re.sub(r'\s+', ' ', text)
    return text


def _strip_contact_info(text: str) -> str:
    """Surgically removes emails, phones, and URLs from the text instead of rejecting the whole string."""
    text = _EMAIL_RE.sub('', text)
    text = _PHONE_RE.sub('', text)
    text = _URL_RE.sub('', text)
    return _clean_summary_text(text)


def _collect_until_bleed(lines: List[str]) -> str:
    kept: List[str] = []
    for line in lines:
        if kept and _looks_like_bleed(line):
            break

        # Check if a boundary occurs mid-line
        cutoff = _earliest_bleed_cutoff(line)
        if cutoff is not None:
            truncated = line[:cutoff].rstrip()
            if truncated:
                kept.append(truncated)
            break

        remaining_words = _MAX_SUMMARY_WORDS - sum(len(l.split()) for l in kept)
        if remaining_words <= 0:
            break
        
        words = line.split()
        kept.append(' '.join(words[:remaining_words]))
        if len(words) > remaining_words:
            break

    joined = ' '.join(kept)
    
    # Surgically remove any contact info that might have been flattened into the paragraph
    joined = _strip_contact_info(joined)
    
    # Final safety net check on the assembled string
    cutoff = _earliest_bleed_cutoff(joined)
    if cutoff is not None:
        joined = joined[:cutoff]

    return _clean_summary_text(joined)


def extract_summary(text: str, sections: Optional[Dict[str, List[str]]] = None) -> str:
    """
    Extract a clean professional-summary paragraph from normalized resume text.
    """
    if sections is None:
        sections = split_sections(text)

    # 1. First choice: The explicitly parsed SUMMARY section
    summary = _collect_until_bleed(sections.get("SUMMARY", []))
    if len(summary.split()) >= _MIN_SUMMARY_WORDS:
        return summary

    # 2. Fallback: Scan the HEADER block for the first prose-like paragraph
    # (Many resumes put the summary directly under their name without a heading).
    header_lines = sections.get("HEADER", [])
    prose_start = len(header_lines)
    for i, line in enumerate(header_lines):
        if not _looks_like_header_field(line):
            prose_start = i
            break

    fallback_lines = header_lines[prose_start:]
    fallback = _collect_until_bleed(fallback_lines)
    
    if len(fallback.split()) >= _MIN_SUMMARY_WORDS:
        return fallback

    # 3. Return whatever we found that is longest.
    best = summary if len(summary.split()) >= len(fallback.split()) else fallback
    
    # Absolute minimum threshold: If it's less than 4 words, it's just noise, return empty string.
    if len(best.split()) < 4:
        return ""
        
    return best