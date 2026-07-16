import re
from typing import List, Dict, Any

# --- Structural Patterns (Non-Hardcoded) ---

# Broader section boundaries (word-boundary, case-insensitive, singular/plural safe)
# --- Structural Patterns (Non-Hardcoded) ---

# Added 'academics' to prevent empty-returns on Nidhi's format
_EDU_START = re.compile(
    r'(?i)\b(education|educational\s+(?:qualifications?|background|details?|profile)|'
    r'academia|academic\s+qualifications?|academic\s+profile|'
    r'qualifications?|scholastics?|academics)\b'
)

# Added 'personal\s+information' to act as a definitive boundary guard
_EDU_STOP = re.compile(
    r'(?i)\b(experience|work\s+experience|professional\s+experience|employment|'
    r'skills?|projects?|certifications?|certificates?(\s*&\s*training)?|training|'
    r'publications?|research\s+work|languages?\s+known|personal\s+details|'
    r'personal\s+information|declaration|awards?|achievements?|references?)\b'
)

# Degree keywords - broadened to cover more formats, dots/spaces optional
_DEGREE_KEYWORDS = (
    r'doctor\s+of\s+pharmacy|pharm\.?\s?d\.?|'
    r'masters?\s+of\s+computer\s+applications?|bachelors?\s+of\s+computer\s+(?:science|applications?)|'
    r'masters?\s+(?:of|in)\s+(?:science|technology|engineering|pharmacy)|bachelors?\s+(?:of|in)\s+(?:science|technology|engineering|pharmacy)|'
    r'm\.?\s?pharm(?:acy)?|b\.?\s?pharm(?:acy)?|'
    r'm\.?\s?sc\.?|b\.?\s?sc\.?|m\.?\s?tech|b\.?\s?tech|m\.?\s?e\.?\b|b\.?\s?e\.?\b|'
    r'm\.?\s?eng(?:g)?\.?|b\.?\s?eng(?:g)?\.?|'
    r'mba|mca|bca|bba|ph\.?\s?d\.?|'
    r'bachelors?|masters?|'
    r'diploma|intermediate|s\.?s\.?c\.?|h\.?s\.?c\.?|matriculation'
)
_DEGREE_PATTERN = re.compile(r'(?i)\b(' + _DEGREE_KEYWORDS + r')\b')
# Anchored version: only counts as a NEW entry if the line STARTS with a degree keyword
_DEGREE_START_PATTERN = re.compile(r'(?i)^\s*(' + _DEGREE_KEYWORDS + r')\b')

_INST_KEYWORD = r'(?:University|College|Institute|School|Academy|Board|Polytechnic|Vidyalaya|Vidhya\s?Nilam)'
# Prefix: only consecutive Title-Case tokens directly before the keyword (stops
# at lowercase filler words like "from"/"of"/"Completed" mid-sentence, which
# previously caused the match to swallow unrelated sentence text).
# Suffix: optional formal-name continuation like " of Health and Science" —
# allow lowercase connector words (and/of/&) so the full name isn't truncated.
_SUFFIX_STOPWORDS = (
    r'with|during|having|aggregate|percentage|average|score|cgpa|grade|'
    r'in\s+the|from\s+\d|batch|year|years|session|and\s+studied'
)
_INST_PATTERN = re.compile(
    r"(?:[A-Z][\w\.']*\s+){0,6}(?i:" + _INST_KEYWORD + r")"
    r"(?:\s+of\s+(?:(?!(?i:" + _SUFFIX_STOPWORDS + r")\b)[A-Za-z][\w\.']*\s*){1,6})?"
)

# Leading OCR bullet artifacts to strip before checking if a line starts a new
# degree entry (e.g. "e Bachelor of Pharmacy...", "- B. Pharmacy...",
# "¢ Intermediate...", "> M.Sc..."). Without this, bulleted education lists
# fail the start-of-line anchor entirely and produce zero entries.
_BULLET_PREFIX = re.compile(r'^\s*[\-\*\u2022\u00b7¢e>»]+\s*')


def _strip_bullet(line: str) -> str:
    return _BULLET_PREFIX.sub('', line, count=1)
# Fallback: standalone acronym institutions (RGUHS, JNTUH, VIPS, IKG etc.) — 3-6 caps
_INST_ACRONYM_PATTERN = re.compile(r'\b[A-Z]{4,6}\b')
_COMMON_NON_INST_ACRONYMS = {"CGPA", "SSC", "HSC", "GPA", "CDM", "GCP", "ICH"}

_YEAR_PATTERN = re.compile(r'\b(19\d{2}|20[0-2]\d)\b')
_PERCENT_PATTERN = re.compile(r'(?i)\b(\d{1,3}(?:\.\d+)?\s?%|CGPA[:\s]*\d(?:\.\d+)?|first\s+class|distinction)\b')
_TRAINING_CONTEXT_RE = re.compile(r'\b(?:certif(?:icate|ication)|course|training|workshop)\b', re.IGNORECASE)


def _extract_institution(block_text: str) -> str:
    matches = _INST_PATTERN.findall(block_text) if False else _INST_PATTERN.finditer(block_text)
    candidates = [m.group(0).strip() for m in matches]
    if candidates:
        # A sentence can mention a short-form name earlier and the full formal
        # name later (e.g. "...K.L.E's College... Rajiv Gandhi University of
        # Health and Science..."). Prefer the longest / most complete match
        # rather than the first (leftmost) one.
        return max(candidates, key=len)
    # Fallback to acronym form (e.g. "RGUHS", "JNTUH", "IKG Punjab...")
    for candidate in _INST_ACRONYM_PATTERN.findall(block_text):
        if candidate not in _COMMON_NON_INST_ACRONYMS:
            return candidate
    return ""


def extract_education(text: str) -> List[Dict[str, Any]]:
    lines = text.splitlines()
    records: List[Dict[str, Any]] = []

    in_section = False
    current_lines: List[str] = []  # raw lines belonging to the active entry block

    def flush_block():
        """Turn accumulated lines for one degree block into a record."""
        if not current_lines:
            return
        block_text = " ".join(l.strip() for l in current_lines if l.strip())
        deg_match = _DEGREE_PATTERN.search(block_text)
        years = _YEAR_PATTERN.findall(block_text)
        pct_match = _PERCENT_PATTERN.search(block_text)

        # Search for institution AFTER the degree keyword ends where possible —
        # prevents the degree word itself (and connectors like "at"/"in"/"from"
        # sitting between degree and institution) from leaking into the match.
        search_text = block_text[deg_match.end():] if deg_match else block_text
        institution = _extract_institution(search_text) or _extract_institution(block_text)

        # An institution or a year by itself is not an education record.  This
        # filters false positives such as "SAS Institute" and work-history
        # dates that happen to be captured inside a loose education section.
        if not deg_match:
            return

        # A short diploma may be a training certificate rather than an academic
        # qualification.  Keep diplomas only when the block also contains an
        # academic institution signal.
        if (
            deg_match.group(0).strip().lower() == "diploma"
            and _TRAINING_CONTEXT_RE.search(block_text)
            and not _INST_PATTERN.search(block_text)
        ):
            return

        year_values = sorted({int(year) for year in years})
        entry = {
            "Degree": deg_match.group(0).strip() if deg_match else "",
            "Institution": institution,
            "Start Year": str(year_values[0]) if year_values else "",
            "End Year": str(year_values[-1]) if year_values else "",
        }
        if pct_match:
            entry["Additional_Info"] = pct_match.group(0).strip()

        # Only keep entries that actually carry some signal (avoid empty stub rows)
        records.append(entry)

    for line in lines:
        stripped = line.strip()

        # 1. Section boundary checks
        if not in_section:
            if _EDU_START.search(line):
                in_section = True
            continue

        if in_section and _EDU_STOP.search(line):
            # Two-column OCR can interleave a skills-column line between an
            # education degree and its dates/institution.  If the active
            # education entry is still incomplete, ignore that stray boundary
            # line and keep gathering its supporting lines.
            active_text = " ".join(current_lines)
            has_degree = bool(_DEGREE_PATTERN.search(active_text))
            has_year = bool(_YEAR_PATTERN.search(active_text))
            has_institution = bool(_extract_institution(active_text))
            if has_degree and (not has_year or not has_institution):
                continue
            if not current_lines and re.search(r'\bskills?\b', line, re.IGNORECASE):
                continue
            flush_block()
            current_lines = []
            in_section = False
            continue

        if not stripped:
            continue  # skip blank lines, don't break the block

        # 2. Decide whether this line STARTS a new degree entry.
        #    A bullet marker itself signals "one entry per line" (e.g.
        #    "> Graduated in M. Pharm..."), even when the degree word isn't
        #    literally the first token. Non-bulleted lines fall back to the
        #    degree-at-start anchor (e.g. "Bachelor of Pharmacy, RGUHS...").
        bullet_match = _BULLET_PREFIX.match(stripped)
        had_bullet = bool(bullet_match)
        clean_line = stripped[bullet_match.end():] if bullet_match else stripped

        if had_bullet or _DEGREE_START_PATTERN.match(clean_line):
            # Some layouts put the institution/date on the line before the
            # degree.  Join that incomplete fragment to its degree instead of
            # emitting two partial records.
            existing_text = " ".join(current_lines)
            if current_lines and not _DEGREE_PATTERN.search(existing_text):
                current_lines.append(clean_line)
            else:
                flush_block()               # close out the previous block, if any
                current_lines = [clean_line]  # start a fresh block (bullet-free)
        else:
            if current_lines:
                current_lines.append(clean_line)
            elif _DEGREE_PATTERN.search(clean_line) or _YEAR_PATTERN.search(clean_line) or _INST_PATTERN.search(clean_line):
                # Institution/date-first layout: no line ever starts with a
                # degree keyword, but this line clearly carries education
                # signal (degree word anywhere, a year, or an institution
                # name). Seed a block instead of silently dropping the
                # section's content.
                current_lines = [clean_line]
            # else: stray sub-header/noise line before any real signal — ignore

    # Catch trailing block at end of section/document
    flush_block()

    return records