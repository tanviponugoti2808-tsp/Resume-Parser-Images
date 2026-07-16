import re

SECTION_ALIASES = {
    "OBJECTIVE": ["OBJECTIVE", "CAREER OBJECTIVE", "CARRER OBJECTIVES"],
    "SUMMARY": [
        "SUMMARY", "PROFILE", "PROFILE SUMMARY", "CAREER SUMMARY",
        "PROFESSIONAL SUMMARY", "ABOUT ME", "PROFESSIONAL PROFILE",
        "EXECUTIVE SUMMARY", "SUMMARY OF EXPERIENCE"
    ],
    "CONTACT": [
        "CONTACT", "CONTACT DETAILS", "CONTACT INFORMATION",
        "PERSONAL DETAILS", "PERSONAL INFORMATION"
    ],
    "EDUCATION": [
        "EDUCATION", "ACADEMICS", "ACADEMIC CREDENTIALS",
        "EDUCATIONAL QUALIFICATION", "EDUCATIONAL QUALIFICATIONS",
        "ACADEMIC QUALIFICATIONS", "ACADEMIC BACKGROUND",
        "QUALIFICATION", "QUALIFICATIONS"
    ],
    "EXPERIENCE": [
        "WORK EXPERIENCE", "WORK HISTORY", "EXPERIENCE",
        "PROFESSIONAL EXPERIENCE", "EMPLOYMENT HISTORY",
        "CAREER HISTORY", "WORK SUMMARY", "EMPLOYMENT",
        "JOB HISTORY", "PROFESSIONAL BACKGROUND",
        "EXPERIENCE SUMMARY", "CAREER DETAILS"
    ],
    "TECHNICAL_SKILLS": [
        "TECHNICAL SKILLS", "SKILLS", "CORE SKILLS", "ADD-ON DOMAIN SKILLS",
        "TECHNICAL EXPERTISE", "TECHNOLOGY SUMMARY", "ADD-ON SKILLS",
        "SKILLS SUMMARY", "KEY SKILLS", "SKILL SET", "CORE COMPETENCIES",
        "TOOLS", "TECHNOLOGIES", "SOFTWARE SKILLS", "COMPETENCIES"
    ],
    "LANGUAGES": [
        "LANGUAGES", "LANGUAGE", "LANGUAGES KNOWN",
        "LANGUAGE SKILLS", "LANGUAGE PROFICIENCY"
    ],
    "CERTIFICATION": [
        "CERTIFICATION", "CERTIFICATIONS", "LICENSES",
        "CERTIFICATES", "TRAINING", "COURSES",
        "PROFESSIONAL CERTIFICATIONS", "CERTIFICATES AND TRAINING"
    ],
    "PROJECTS": [
        "PROJECT", "PROJECTS", "KEY PROJECTS",
        "PROJECT EXPERIENCE", "PROJECT DETAILS"
    ],
    "ACHIEVEMENTS": [
        "ACHIEVEMENTS", "HONORS", "AWARDS",
        "ACCOMPLISHMENTS", "RECOGNITION"
    ]
}

_ALIAS_MAP = {}
_ALIAS_WORDS_MAP = {}
for section, aliases in SECTION_ALIASES.items():
    for alias in aliases:
        alias_upper = alias.upper()
        _ALIAS_MAP[alias_upper] = section
        _ALIAS_WORDS_MAP[alias_upper] = alias_upper.split()

# Sort aliases longest-first (by word count) so that a more specific alias
# (e.g. "PROFESSIONAL CERTIFICATIONS") is checked before a shorter one that
# could otherwise shadow it via prefix matching.
_SORTED_ALIASES = sorted(
    _ALIAS_WORDS_MAP.items(), key=lambda kv: len(kv[1]), reverse=True
)

# Max number of *extra* trailing words a heading line may have beyond the
# matched alias (covers things like "CERTIFICATIONS & TRAINING",
# "SKILLS AND TOOLS", "EDUCATION DETAILS") without being so loose that
# ordinary sentences get misread as headings.
_MAX_EXTRA_WORDS = 2

def _normalize(line: str) -> str:
    line = line.strip()
    # Strip ALL non-alphanumeric characters (not just leading/trailing),
    # replacing them with spaces so words don't get glued together
    # (e.g. "SKILLS/TOOLS" -> "SKILLS TOOLS", "CERTIFICATIONS & TRAINING"
    # -> "CERTIFICATIONS TRAINING").
    line = re.sub(r'[^a-zA-Z0-9\s]+', ' ', line)
    line = re.sub(r'\s+', ' ', line)
    return line.upper().strip()

def _is_section_heading(line: str):
    normalized = _normalize(line)
    if not normalized or len(normalized) > 50:
        return None

    if normalized in _ALIAS_MAP:
        return _ALIAS_MAP[normalized]

    heading_words = normalized.split()

    # Word-level prefix match: the heading's words must start with the
    # alias's words exactly, with only a small number of extra trailing
    # words allowed. This is far more reliable than a character-count
    # tolerance, since it correctly handles compound headings like
    # "CERTIFICATIONS & TRAINING" or "SKILLS AND TOOLS" while still
    # rejecting ordinary sentences that merely start with a keyword.
    for alias, alias_words in _SORTED_ALIASES:
        n = len(alias_words)
        if heading_words[:n] == alias_words:
            extra_words = len(heading_words) - n
            if 0 <= extra_words <= _MAX_EXTRA_WORDS:
                return _ALIAS_MAP[alias]

    return None

def split_sections(text: str) -> dict:
    sections = {"HEADER": []}
    current = "HEADER"

    for line in text.splitlines():
        line_str = line.strip()
        if not line_str:
            continue

        detected = _is_section_heading(line_str)
        if detected:
            current = detected
            sections.setdefault(current, [])
        else:
            sections[current].append(line_str)

    return sections