import os
import re
from typing import Dict, Any, List, Tuple, Set

class EngineConfig:
    BASE_TOP_LINE_BOOST: float = 50.0
    ISOLATION_BOOST: float = 35.0
    TITLE_CASE_BOOST: float = 25.0
    ALL_CAPS_BOOST: float = 15.0
    EMAIL_PROXIMITY_BOOST: float = 40.0
    PHONE_PROXIMITY_BOOST: float = 30.0
    SINGLE_WORD_PENALTY: float = -20.0
    BELOW_CONTACT_PENALTY: float = -45.0
    MIXED_CASE_PENALTY: float = -30.0
    SCAN_LINE_LIMIT: int = 40
    PROXIMITY_WINDOW: int = 5
    MIN_ACCEPTABLE_SCORE: float = 45.0

_EMAIL_RE = re.compile(r'[\w\.-]+@[\w\.-]+\.[a-zA-Z]{2,4}')
_PHONE_RE = re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}')
_FUZZY_HEADER_RE = re.compile(
    r'^\s*(?:summary|objective|profile|exper[ie]ence|employment|work|history|edu[ca]tion|skills|projects|certifications)\b[:\-]*\s*$',
    re.IGNORECASE
)
_NAME_LABEL_RE = re.compile(r'^\s*(?:full\s+)?name\s*[:\-=]\s*', re.IGNORECASE)
_PREFIX_RE = re.compile(r'^(?:dr|mr|mrs|ms|prof|sir|madam|engr)\.?\s+', re.IGNORECASE)
_SUFFIX_RE = re.compile(r'\b(?:jr|sr|iii|ii|iv|phd|md)\.?$', re.IGNORECASE)
_ADDRESS_INDICATORS = re.compile(r'\b(?:road|rd|street|st|lane|nagar|colony|building|bldg|floor|suite|apt|apartment|box|po)\b', re.IGNORECASE)
_COMPANY_SUFFIX_RE = re.compile(r'\b(?:pvt|pivate|ltd|limited|inc|corp|corporation|llc|llp)\b', re.IGNORECASE)

_REDUCED_STOP_WORDS: Set[str] = {
    "resume", "cv", "curriculum", "vitae", "page", "details", "contact",
    "phone", "email", "address", "gender", "linkedin", "github", "zipcode"
}

def clean_candidate(raw: str) -> str:
    if not raw:
        return ""
    for delimiter in ('|', '•', '::', '–', '—'):
        raw = raw.split(delimiter)[0]
    return raw.strip(" .,-:_–—\t\"'")
def is_valid_name(candidate: str, is_isolated: bool = False) -> bool:

    cleaned = candidate.strip()

    if not cleaned:
        return False

    if len(cleaned) < 3 or len(cleaned) > 50:
        return False

    # Reject emails, addresses and company names
    if (
        _EMAIL_RE.search(cleaned)
        or _ADDRESS_INDICATORS.search(cleaned)
        or _COMPANY_SUFFIX_RE.search(cleaned)
    ):
        return False

    # Reject common resume section headings
    blocked = {
        "communication",
        "skills",
        "technical",
        "summary",
        "objective",
        "education",
        "experience",
        "contact",
        "phone",
        "email",
        "windows",
        "unix",
        "operating",
        "systems",
        "language",
        "languages",
        "certification",
        "certifications",
        "project",
        "projects",
        "good",
        "analytical",
        "learning",
        "management",
        "statistical",
        "programmer",
        "other"
    }

    words = [
        re.sub(r'^[.\-,\'’‘]+|[.\-,\'’‘]+$', '', w)
        for w in cleaned.split()
    ]
    # Reject if any blocked word appears
    for word in words:
        if word.lower() in blocked:
            return False

    if len(words) == 0:
        return False

    # Reject one-word names unless isolated
    if len(words) == 1:
        if not is_isolated:
            return False

    # Reject 4+ word candidates
    if len(words) > 3:
        return False

    for word in words:

        if word.lower() in blocked:
            return False

        if word.lower() in _REDUCED_STOP_WORDS:
            return False

        is_initials = bool(
            re.fullmatch(r'[A-Za-z](?:\.[A-Za-z])*\.?', word)
        )

        if not (
            word.isalpha()
            or "-" in word
            or "'" in word
            or "’" in word
            or is_initials
        ):
            return False

    return True

def generate_candidates(raw_lines: List[str]) -> List[Tuple[int, str, bool]]:
    candidates_pool: List[Tuple[int, str, bool]] = []
    processed_lines: List[Tuple[int, str, bool]] = []

    for idx, raw_line in enumerate(raw_lines[:EngineConfig.SCAN_LINE_LIMIT]):
        stripped = raw_line.strip()
        if not stripped:
            continue
        prev_blank = (idx == 0 or raw_lines[idx - 1].strip() == "")
        next_blank = (idx == len(raw_lines) - 1 or raw_lines[idx + 1].strip() == "")
        processed_lines.append((idx, stripped, prev_blank and next_blank))

    for i, (orig_idx, current_str, is_isolated) in enumerate(processed_lines):
        if _FUZZY_HEADER_RE.match(current_str):
            break
        candidates_pool.append((orig_idx, current_str, is_isolated))
        if i < len(processed_lines) - 1:
            _, next_str, next_isolated = processed_lines[i + 1]
            if current_str[0].isupper() and next_str[0].isupper():
                if len(current_str.split()) <= 2 and len(next_str.split()) <= 2:
                    if not _FUZZY_HEADER_RE.match(next_str) and not _NAME_LABEL_RE.match(next_str):
                        candidates_pool.append((orig_idx, f"{current_str} {next_str}", is_isolated or next_isolated))
    return candidates_pool

def score_candidate(candidate: str, line_idx: int, email_idx: int, phone_idx: int, is_isolated: bool) -> float:

    score = 0.0

    if line_idx <= 2:
        score += EngineConfig.BASE_TOP_LINE_BOOST
    elif line_idx <= 10:
        score += max(0.0, EngineConfig.BASE_TOP_LINE_BOOST - (line_idx - 2) * 5.0)
    else:
        score += max(0.0, 15.0 - (line_idx - 10) * 1.0)

    if is_isolated:
        score += EngineConfig.ISOLATION_BOOST

    if email_idx != -1:
        dist = email_idx - line_idx
        if 0 < dist <= EngineConfig.PROXIMITY_WINDOW:
            score += max(0.0, EngineConfig.EMAIL_PROXIMITY_BOOST - (dist * 6.0))
        elif dist <= 0:
            score += EngineConfig.BELOW_CONTACT_PENALTY

    if phone_idx != -1:
        dist_p = phone_idx - line_idx
        if 0 < dist_p <= EngineConfig.PROXIMITY_WINDOW:
            score += max(0.0, EngineConfig.PHONE_PROXIMITY_BOOST - (dist_p * 5.0))

    words = candidate.split()

    # Strongly prefer complete names
    if len(words) == 1:
        score -= 50
    elif len(words) == 2:
        score += 30
    elif len(words) == 3:
        score += 20
    elif len(words) >= 4:
        score -= 20

    # Strong bonus for likely person names
    if len(words) == 2:
        score += 40
    elif len(words) == 3:
        score += 50

    # Bonus if all words are uppercase (common in resumes)
    if all(w.isupper() for w in words):
        score += 30

    is_title = all(w[0].isupper() for w in words if w.isalpha())
    is_caps = all(w.isupper() for w in words if w.isalpha())

    if is_title and not is_caps:
        score += EngineConfig.TITLE_CASE_BOOST
    elif is_caps:
        score += EngineConfig.ALL_CAPS_BOOST
    else:
        score += EngineConfig.MIXED_CASE_PENALTY

    return score

    is_title = all(w[0].isupper() for w in words if w.isalpha())
    is_caps = all(w.isupper() for w in words if w.isalpha())

def select_best_candidate(candidates_pool: List[Tuple[float, str]]) -> Dict[str, Any]:
    if not candidates_pool:
        return {"name": ""}
    unique_candidates: Dict[str, float] = {}
    for score, name in candidates_pool:
        normalized_key = name.lower().strip()
        if normalized_key not in unique_candidates or score > unique_candidates[normalized_key]:
            unique_candidates[normalized_key] = score

    sorted_items = sorted(unique_candidates.items(), key=lambda x: x[1], reverse=True)
    best_name_key, best_score = sorted_items[0]
    target_name = next(name for score, name in candidates_pool if name.lower() == best_name_key)

    if best_score >= EngineConfig.MIN_ACCEPTABLE_SCORE:
        return {"name": normalize_name(target_name)}
    return {"name": ""}

def normalize_name(name: str) -> str:
    words = name.split()
    normalized_tokens = []
    lowercase_particles = {"de", "van", "von", "der", "al", "bin"}

    for word in words:
        clean_token = re.sub(r'[^A-Za-z\-’\']', '', word)
        if not clean_token:
            continue
        lower_token = clean_token.lower()
        if lower_token in lowercase_particles:
            normalized_tokens.append(lower_token)
        elif lower_token.startswith("mc") and len(lower_token) > 2:
            normalized_tokens.append("Mc" + lower_token[2:].capitalize())
        elif lower_token.startswith("mac") and len(lower_token) > 3:
            normalized_tokens.append("Mac" + lower_token[3:].capitalize())
        elif (lower_token.startswith("o'") or lower_token.startswith("o’")) and len(lower_token) > 2:
            char = "’" if "’" in lower_token else "'"
            normalized_tokens.append("O" + char + lower_token[2:].capitalize())
        elif '-' in clean_token:
            normalized_tokens.append("-".join([part.capitalize() for part in clean_token.split('-')]))
        elif re.match(r'^[A-Z]\.?$', word, re.IGNORECASE):
            normalized_tokens.append(clean_token.upper() + ".")
        else:
            normalized_tokens.append(clean_token.capitalize())
    return " ".join(normalized_tokens)

def extract_name(text: str, filename: str = "") -> Dict[str, Any]:
    raw_lines = text.splitlines()
    for line in raw_lines[:20]:
        if _NAME_LABEL_RE.match(line):
            extracted_val = _NAME_LABEL_RE.sub('', line)
            cleaned_val = clean_candidate(_PREFIX_RE.sub('', extracted_val))
            if is_valid_name(cleaned_val, is_isolated=True):
                return {"name": normalize_name(cleaned_val)}

    email_line_idx, phone_line_idx = -1, -1
    for idx, raw_line in enumerate(raw_lines[:EngineConfig.SCAN_LINE_LIMIT]):
        stripped = raw_line.strip()
        if email_line_idx == -1 and _EMAIL_RE.search(stripped):
            email_line_idx = idx
        if phone_line_idx == -1 and _PHONE_RE.search(stripped):
            phone_line_idx = idx

    
    generated_pool = generate_candidates(raw_lines)

    evaluated_candidates: List[Tuple[float, str]] = []

    for orig_idx, text_candidate, is_isolated in generated_pool:
        stripped_candidate = _PREFIX_RE.sub('', text_candidate).strip()
        stripped_candidate = _SUFFIX_RE.sub('', stripped_candidate).strip()
        final_candidate = clean_candidate(stripped_candidate)

        if not is_valid_name(final_candidate, is_isolated=is_isolated):
            continue

        calculated_score = score_candidate(final_candidate, orig_idx, email_line_idx, phone_line_idx, is_isolated)
        evaluated_candidates.append((calculated_score, final_candidate))

    output = select_best_candidate(evaluated_candidates)
    if output["name"] != "":
        return output

    if filename:
        fn_cand = _extract_name_from_filename(os.path.basename(filename))
        if fn_cand:
            return {"name": normalize_name(fn_cand)}
    return {"name": ""}

def _extract_name_from_filename(filename: str) -> str:
    stem, _ = os.path.splitext(filename)
    stem = re.sub(r'\[.*?\]|\(.*?\)', '', stem)
    stem = stem.replace('_', ' ').replace('-', ' ').replace('.', ' ')
    stem = re.sub(r'([a-z])([A-Z])', r'\1 \2', stem)
    tokens = [w for w in stem.split() if w.lower() not in _REDUCED_STOP_WORDS and w.isalpha()]
    return " ".join(tokens[:3]) if tokens else ""