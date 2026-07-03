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
for section, aliases in SECTION_ALIASES.items():
    for alias in aliases:
        _ALIAS_MAP[alias.upper()] = section

def _normalize(line: str) -> str:
    line = line.strip()
    line = re.sub(r'^[^a-zA-Z0-9]+', '', line)
    line = re.sub(r'[^a-zA-Z0-9\s]+$', '', line)
    line = re.sub(r'\s+', ' ', line)
    return line.upper().strip()

def _is_section_heading(line: str):
    normalized = _normalize(line)
    if not normalized or len(normalized) > 50:
        return None
        
    if normalized in _ALIAS_MAP:
        return _ALIAS_MAP[normalized]
        
    # Check if a line starts with a known header keyword combo
    for alias, section in _ALIAS_MAP.items():
        if normalized.startswith(alias) and len(normalized) <= len(alias) + 4:
            return section
            
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