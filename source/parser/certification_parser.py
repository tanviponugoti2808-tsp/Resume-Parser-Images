"""
certification_parser.py

State-machine based certification extractor for Qwen-normalized resume text.

Handles:
  - Multiple section heading aliases
  - Multi-line certificate names
  - Issuing organization detection
  - Year extraction
  - Deduplication across summary + certification sections
  - No hardcoded certificate lists — structural regex only

Output:
  [
    {
      "Certification": "AWS Certified Solutions Architect",
      "Issuing_Organization": "Amazon Web Services",
      "Year": "2022"
    },
    ...
  ]
"""

import re
from typing import List, Dict, Optional


# ─── Section boundary detection ───────────────────────────────────────────────

_CERT_SECTION_START = re.compile(
    r'^\s*(?:certifications?|certificates?|professional\s+certifications?|'
    r'licenses?\s+(?:and\s+)?certifications?|credentials?|'
    r'professional\s+credentials?|courses?\s+(?:and\s+)?certifications?|'
    r'training\s+(?:and\s+)?certifications?|achievements?\s+(?:and\s+)?certifications?|'
    r'awards?\s+(?:and\s+)?certifications?)\s*[:\-]?\s*$',
    re.IGNORECASE,
)

_CERT_SECTION_STOP = re.compile(
    r'^\s*(?:experience|professional\s+experience|work\s+experience|employment|'
    r'education|academic|skills?|technical\s+skills?|projects?|languages?|'
    r'personal\s+(?:details?|information)|declaration|references?|hobbies|'
    r'interests?|publications?|patents?|summary|objective|profile)\s*[:\-]?\s*$',
    re.IGNORECASE,
)

# ─── Line classification regexes ──────────────────────────────────────────────

# Year: standalone 4-digit year in range 1990–2035
_YEAR_RE = re.compile(r'\b((?:19[9]\d|20[0-3]\d))\b')

# Issuing org indicators — structural signals, not hardcoded names
_ORG_INDICATORS = re.compile(
    r'\b(?:issued?\s+by|certified?\s+by|accredited?\s+by|authorized?\s+by|'
    r'provided?\s+by|offered?\s+by|from|by)\b',
    re.IGNORECASE,
)

# Known org patterns — used to infer org from cert text itself
_ORG_SUFFIX_RE = re.compile(
    r'\b(?:institute|university|college|academy|association|board|council|'
    r'foundation|society|organization|centre|center|school|corporation|'
    r'inc\.?|ltd\.?|llc\.?|corp\.?|pvt\.?)\b',
    re.IGNORECASE,
)

# Bullet/list prefix
_BULLET_RE = re.compile(r'^\s*[•▪▸◦➢\-\*>→]\s*')

# Lines that are clearly NOT certification entries
_NOISE_RE = re.compile(
    r'^\s*(?:page\s+\d+|\d+\s+of\s+\d+|references?\s+available|'
    r'declaration|i\s+hereby|place\s*:|date\s*:|signature\s*:)\s*$',
    re.IGNORECASE,
)

# Lines that look like section headings mid-text (short, all-caps or title-case)
_HEADING_LIKE_RE = re.compile(
    r'^\s*[A-Z][A-Z\s&/]{3,40}[A-Z]\s*[:\-]?\s*$'
)

# Continuation line indicators (line is part of previous cert, not new one)
_CONTINUATION_WORDS = re.compile(
    r'^\s*(?:professional|certificate|certification|associate|foundation|'
    r'practitioner|architect|developer|analyst|expert|specialist|'
    r'fundamentals|level\s+\d+|advanced|intermediate|basic|'
    r'track|series|bootcamp|workshop|training|course|program)\b',
    re.IGNORECASE,
)

# Strong cert signal — structural indicator that this line is a certification
_CERT_SIGNAL = re.compile(
    r'\b(?:certif(?:ied|icate|ication)|certified|diploma|accreditation|'
    r'credential|licence|license|fellowship|designation|examination|exam|'
    r'assessment|badge|program|course|workshop|bootcamp|training)\b',
    re.IGNORECASE,
)

# Weak cert signal — may be a cert but needs context
_WEAK_CERT_SIGNAL = re.compile(
    r'\b(?:pmp|csm|aws|gcp|azure|cissp|ceh|ccna|ccnp|itil|prince2|'
    r'scrum|agile|six\s+sigma|lean|iso|iec|sas|spss|tableau|'
    r'google|microsoft|oracle|cisco|comptia|redhat|ibm|salesforce)\b',
    re.IGNORECASE,
)

# Deny list — lines that mention certs but are clearly job responsibilities
_RESPONSIBILITY_VERBS = re.compile(
    r'^\s*(?:responsible|managed?|performed?|developed?|created?|reviewed?|'
    r'led|supported?|coordinated?|implemented?|analysed?|analyzed?|worked?\s+on|'
    r'handled?|checked?|monitored?|maintained?|prepared?|ensured?|conducted?)\b',
    re.IGNORECASE,
)


# ─── State machine ────────────────────────────────────────────────────────────

class _State:
    OUTSIDE   = "OUTSIDE"
    IN_CERT   = "IN_CERT"
    IN_SECTION = "IN_SECTION"


def _clean_line(line: str) -> str:
    """Strip bullets, leading symbols, and trailing punctuation."""
    line = _BULLET_RE.sub("", line)
    line = re.sub(r'^[\s\d]+[\.\)]\s+', '', line)  # numbered lists
    return line.strip(" .,-:;|")


def _extract_year(text: str) -> str:
    m = _YEAR_RE.search(text)
    return m.group(1) if m else ""


def _extract_org(text: str) -> str:
    """
    Try to extract issuing organization from a line.
    Looks for 'by X', 'from X', or org-suffix words.
    """
    # Pattern: "issued by Amazon Web Services" or "from Coursera"
    m = re.search(
        r'\b(?:issued?\s+by|certified?\s+by|from|by)\s+([A-Z][A-Za-z\s\.&,]+)',
        text, re.IGNORECASE
    )
    if m:
        org = m.group(1).strip().strip(".,;:")
        if 2 < len(org) < 60:
            return org

    # Pattern: look for known org-suffix words and grab surrounding words
    m = _ORG_SUFFIX_RE.search(text)
    if m:
        start = max(0, m.start() - 40)
        snippet = text[start:m.end()]
        # Take last 1-5 capitalized words before and including the match
        words = re.findall(r'[A-Z][a-zA-Z\.&]+', snippet)
        if words:
            return " ".join(words[-4:]).strip()

    return ""


def _remove_year_and_org_phrases(text: str) -> str:
    """Strip year and org-attribution phrases from a cert name."""
    text = _YEAR_RE.sub("", text)
    text = re.sub(
        r'\s*[-–—|]\s*(?:issued?\s+by|from|by)\s+.+$', "", text, flags=re.IGNORECASE
    )
    text = re.sub(r'\s*\(\s*\)', "", text)
    return re.sub(r'\s+', ' ', text).strip(" .,-:;|")


def _is_cert_line(line: str) -> bool:
    """Determine if a cleaned line looks like a certification entry."""
    if len(line) < 5 or len(line) > 200:
        return False
    if _NOISE_RE.match(line):
        return False
    if _RESPONSIBILITY_VERBS.match(line):
        return False
    if _CERT_SIGNAL.search(line):
        return True
    if _WEAK_CERT_SIGNAL.search(line):
        return True
    return False


def _is_continuation(line: str) -> bool:
    """Return True if this line looks like the second line of a multi-line cert."""
    return bool(_CONTINUATION_WORDS.match(line))


def _fingerprint(cert: str) -> str:
    """Normalized key for deduplication."""
    return re.sub(r'[^a-z0-9]', '', cert.lower())


# ─── Main extraction function ─────────────────────────────────────────────────

def extract_certifications(text: str) -> List[Dict[str, str]]:
    """
    Extract certifications from normalized resume text.

    Args:
        text: Full normalized resume text (may contain multiple sections).

    Returns:
        List of dicts: [{"Certification": ..., "Issuing_Organization": ..., "Year": ...}]
    """
    lines = [l.rstrip() for l in text.splitlines()]
    results: List[Dict[str, str]] = []
    seen: set = set()

    # ── Pass 1: Extract from the dedicated certification section ──────────────
    state = _State.OUTSIDE
    section_lines: List[str] = []

    for line in lines:
        stripped = line.strip()

        if state == _State.OUTSIDE:
            if _CERT_SECTION_START.match(stripped):
                state = _State.IN_SECTION
            continue

        if state == _State.IN_SECTION:
            if _CERT_SECTION_STOP.match(stripped) and stripped:
                break
            if stripped:
                section_lines.append(stripped)

    # Parse collected section lines with the state machine
    _parse_cert_lines(section_lines, results, seen)

    # ── Pass 2: Scan entire text for inline cert mentions (e.g. in summary) ──
    # Only add if not already found in Pass 1
    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue
        # Skip if this line is inside what we already parsed
        cleaned = _clean_line(stripped)
        if not cleaned or not _is_cert_line(cleaned):
            continue
        name = _remove_year_and_org_phrases(cleaned)
        if not name or len(name) < 5:
            continue
        fp = _fingerprint(name)
        if fp not in seen:
            year = _extract_year(cleaned)
            org  = _extract_org(cleaned)
            results.append({
                "Certification":       name,
                "Issuing_Organization": org,
                "Year":                year,
            })
            seen.add(fp)

    return results


def _parse_cert_lines(
    lines: List[str],
    results: List[Dict[str, str]],
    seen: set,
) -> None:
    """
    State machine parser for a block of certification section lines.
    Handles multi-line cert names and org/year on separate lines.
    """
    state        = _State.OUTSIDE
    current_name = ""
    current_org  = ""
    current_year = ""

    def flush():
        nonlocal current_name, current_org, current_year
        name = _remove_year_and_org_phrases(current_name).strip()
        if name and len(name) >= 5:
            fp = _fingerprint(name)
            if fp not in seen:
                results.append({
                    "Certification":        name,
                    "Issuing_Organization": current_org.strip(),
                    "Year":                 current_year.strip(),
                })
                seen.add(fp)
        current_name = ""
        current_org  = ""
        current_year = ""

    for line in lines:
        cleaned = _clean_line(line)
        if not cleaned:
            continue
        if _NOISE_RE.match(cleaned):
            continue

        year = _extract_year(cleaned)
        org  = _extract_org(cleaned)

        if state == _State.OUTSIDE:
            if _is_cert_line(cleaned):
                state        = _State.IN_CERT
                current_name = cleaned
                current_year = year
                current_org  = org
            # else: skip non-cert lines outside a cert entry

        elif state == _State.IN_CERT:
            # Check if this is the start of a NEW cert entry
            if _is_cert_line(cleaned) and not _is_continuation(cleaned):
                flush()
                current_name = cleaned
                current_year = year
                current_org  = org
                state        = _State.IN_CERT
            # Check if this is a continuation of the current cert name
            elif _is_continuation(cleaned):
                current_name += " " + cleaned
                if not current_year and year:
                    current_year = year
                if not current_org and org:
                    current_org = org
            # Check if this line is just a year (standalone date line)
            elif re.fullmatch(r'\s*\d{4}\s*', cleaned):
                if not current_year:
                    current_year = cleaned.strip()
            # Check if this line looks like an org attribution
            elif _ORG_INDICATORS.search(cleaned) or _ORG_SUFFIX_RE.search(cleaned):
                if not current_org:
                    current_org = org or cleaned
            # Otherwise this is a non-cert line — flush current and go outside
            else:
                flush()
                state = _State.OUTSIDE

    # Flush any remaining entry
    if state == _State.IN_CERT:
        flush()