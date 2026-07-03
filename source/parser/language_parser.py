import re

# Closes out language lists if common unindexed footer sections appear
_NOISE_END_PATTERNS = re.compile(r"\b(hobby|hobbies|interest|declaration|reference|signature)\b", re.I)

def parse_languages(section_text: str) -> list:
    if not section_text.strip():
        return []
        
    lines = []
    for line in section_text.splitlines():
        line_clean = line.strip()
        if not line_clean:
            continue
        if _NOISE_END_PATTERNS.search(line_clean):
            break
        lines.append(line_clean)
        
    return lines