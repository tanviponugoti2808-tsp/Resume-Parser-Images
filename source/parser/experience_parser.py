import re
import datetime
from typing import List, Dict, Any, Tuple, Optional

# Bare 4-digit years (no month attached) are the most OCR-fragile date token
# -- a single misread digit turns "2015" into garbage like "3155". Reject
# such tokens via a plausibility check rather than trying to over-constrain
# the regex itself (which stays permissive; validation happens downstream).
_CURRENT_YEAR = datetime.date.today().year
_MIN_PLAUSIBLE_YEAR = 1980
_MAX_PLAUSIBLE_YEAR = _CURRENT_YEAR + 1

_MONTH_PAT = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
PARTIAL_DATE = rf'(?:\d{{1,2}}(?:st|nd|rd|th)?\s+)?{_MONTH_PAT}[,\s\'’\-]+\d{{2,4}}|\d{{1,2}}[/-]{_MONTH_PAT}[/-]\d{{4}}|\d{{1,2}}/\d{{4}}|Q[1-4]\s*\d{{4}}|\d{{4}}'


def _extract_years(s: str) -> List[int]:
    return [int(y) for y in re.findall(r'\b(\d{4})\b', s)]


def _has_implausible_year(s: str) -> bool:
    """True if any 4-digit year token in `s` falls outside a sane calendar
    range. Catches OCR digit-corruption (e.g. '3155') that would otherwise
    slip through as a 'valid' 4-digit year -- and also catches accidental
    year-like matches (a 4-digit id, a percentage, etc.)."""
    return any(y < _MIN_PLAUSIBLE_YEAR or y > _MAX_PLAUSIBLE_YEAR for y in _extract_years(s))
PRESENT_WORDS = r'(?:Present|Current|Till\s+Date|Till\s+Now|Ongoing|Now|Continuing|To\s+Date|Still\s+working)'
DATE_TOKEN = rf'(?:{PARTIAL_DATE}|{PRESENT_WORDS})'

DATE_RANGE_RE = re.compile(
    rf'({PARTIAL_DATE})\s*(?:to|-|–|—|~|till|thru|through)\s*({DATE_TOKEN})',
    re.IGNORECASE
)
DATE_RANGE_SPACED_RE = re.compile(rf'({PARTIAL_DATE})\s+({DATE_TOKEN})', re.IGNORECASE)

# OCR may turn an en/em dash into several non-word characters.  Use a
# separator pattern that accepts those artifacts as well as normal dashes.
_DATE_SEPARATOR = r'(?:to|till|thru|through|[-~\u2013\u2014]+|[^\w\s]{1,4})'
_ROBUST_PARTIAL_DATE = rf'(?:\d{{1,2}}(?:st|nd|rd|th)?\s+)?{_MONTH_PAT}[,\s\'\u2019\-]+\d{{2,4}}|\d{{1,2}}[/-]{_MONTH_PAT}[/-]\d{{4}}|\d{{1,2}}/\d{{4}}|Q[1-4]\s*\d{{4}}|\d{{4}}'
_ROBUST_DATE_TOKEN = rf'(?:{_ROBUST_PARTIAL_DATE}|{PRESENT_WORDS})'
DATE_RANGE_RE = re.compile(
    rf'({_ROBUST_PARTIAL_DATE})\s*{_DATE_SEPARATOR}\s*({_ROBUST_DATE_TOKEN})',
    re.IGNORECASE,
)
DATE_RANGE_SPACED_RE = re.compile(
    rf'({_ROBUST_PARTIAL_DATE})\s+({_ROBUST_DATE_TOKEN})', re.IGNORECASE
)
SECTION_HEADER_RE = re.compile(
    r'^\s*(?:work(?:ing)?\s+experience|professional\s+experience|employment\s+history|'
    r'experience|career\s+(?:history|summary|profile)|employment\s+details|'
    r'professional\s+background|work\s+history|work\s+profile|job\s+history|'
    r'experience\s+(?:summary|details|profile)|relevant\s+experience|'
    r'employment\s+record|occupational\s+history)\b',
    re.IGNORECASE
)
SUMMARY_HEADER_RE = re.compile(r'^\s*(?:professional\s+summary|career\s+objective|profile\s+summary|about\s+me|summary|profile)\s*[:\-]?\s*$', re.IGNORECASE)

_COMPANY_NOISE_WORDS = ['responsibilities','summary','objective','profile','skills','education','certification','project','achievements','awards','publications','references','languages','hobbies','interests','declaration','personal details','personal information','regional team','cross functional','client',
    # Embedded section-heading phrases. These normally get stripped out as
    # section headers, but OCR/layout can collapse a heading onto the same
    # line as the first job's dates (e.g. "PROFESSIONAL EXPERIENCE (June'24 -
    # till now)"), which previously slipped through as a "company" name.
    'professional experience','work experience','employment history','career history',
    'relevant experience','experience summary','career summary','professional background',
    'work history','professional summary','academic profile','academic qualification']
DESIGNATION_KEYWORDS = sorted(['chief','head of','vice president','vp ','director','president','ceo','cto','coo','cfo','senior','lead','principal','staff','manager','associate','specialist','consultant','analyst','executive','officer','coordinator','administrator','engineer','developer','scientist','researcher','technician','intern','trainee','assistant','fellow','architect','programmer','designer','writer','recruiter','accountant','instructor','professor','teacher','clinical data manager','statistical programmer','data manager','study coordinator','regulatory affairs','pharmacovigilance','drug safety','bioinformatics','backend','frontend','full stack','devops','cloud','qa','automation','network','system','coder','reviewer','processor','validator','tester','biller','auditor','pharmacist'], key=len, reverse=True)

RESPONSIBILITY_VERBS_RE = re.compile(r'\b(?:responsible|managed?|performed?|developed?|created?|reviewed?|led|supported?|coordinated?|implemented?|analy[sz]ed?|worked?\s+on|handled?|checked?|monitored?|maintained?|prepared?|ensured?|conducted?|collected?|reported?|assisted?|processed?|validated?|reconciled?|designed?|built?|established?|generated?|tracked?|trained?|mentored?|collaborated?|communicated?|contributed?|participated?|provided?|spearheaded?|oversaw|overseen|identified?|resolved?|initiated?|prioritized?|streamlined?|automated?|documented?|submitted?|started?|set[\s\-]?up|gained?\s+knowledge|used?\s+efficient|leading|mentoring|auditing|writing|reviewing|cleaning|managing|coordinating|investigating|evaluating|assessing|archived?)\b', re.IGNORECASE)
_RESP_STOP_WORDS = ["education","academic","qualification","skills","certifications","projects","languages","personal information","personal details","awards","references","declaration","key skills","technical skills","patents","publications"]
_RESP_HEADER_RE = re.compile(r'^\s*(?:key\s+)?(?:roles?\s+(?:and|&)\s+)?(?:responsibilities?|duties?|tasks?|deliverables|accountabilities)\s*[:\-]?\s*$', re.IGNORECASE)
_NEW_EXP_DATE_RE = re.compile(r'^\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\w]*\s+\d{4}|\d{4}\s*[-–—])', re.IGNORECASE)
_RESP_LINE_RE = re.compile(r'^(?:[•➢▪■♦\-\*▸◦]|\d+[\)\.]\s+)?')
_PAGE_NOISE_RE = re.compile(r'^(?:page\s+\d+(?:\s+of\s+\d+)?|\d+\s+of\s+\d+|\s*)$', re.IGNORECASE)

def _clean(t: str) -> str: return t.strip()

# Decorative bullet/marker characters that OCR/copy-paste commonly leaves
# in front of a job entry's company line (e.g. "• Novo Nordisk",
# "➢ Google Inc"). None of these are stripped by the narrower
# (">", "-", "*", "+", "=") check inside _is_valid_company, so a bullet
# was slipping through and staying attached to the company name. Strip
# them from every line up front instead of trying to special-case them
# in every downstream check.
_LEADING_BULLET_RE = re.compile(r'^\s*[•➢▪■♦▸◦‣·§→]+\s*')

def _strip_leading_bullet(line: str) -> str:
    return _LEADING_BULLET_RE.sub('', line)

# A line like "Role : Statistical Programmer" or "Organization: ClinicaMapletree"
# carries a form-field label that should never end up embedded in the stored
# Company/Designation text. Strip it once, at the point of use, rather than
# only rejecting lines that start with it (which left cases like "Role :
# Statistical Programmer - PROFESSIONAL EXPERIENCE" storing the label verbatim).
_FIELD_LABEL_PREFIX_RE = re.compile(
    r'^\s*(?:role|designation|position|title|company|organi[sz]ation|employer)\s*[:\-]\s*',
    re.IGNORECASE,
)


def _strip_field_label(t: str) -> str:
    return _FIELD_LABEL_PREFIX_RE.sub('', t, count=1).strip()

def _is_noise(t: str) -> bool: return any(w in t.lower() for w in _COMPANY_NOISE_WORDS)
def _looks_like_designation(t: str) -> bool: return any(kw in t.lower() for kw in DESIGNATION_KEYWORDS)
def _looks_like_date_line(t: str) -> bool: return bool(DATE_RANGE_RE.search(t) or DATE_RANGE_SPACED_RE.search(t))

def _extract_date_range(t: str) -> Optional[Tuple[str, str]]:
    m = DATE_RANGE_RE.search(t)
    if m:
        start, end = m.group(1).strip(), m.group(2).strip()
        if not _has_implausible_year(start) and not _has_implausible_year(end):
            return start, end
    m = DATE_RANGE_SPACED_RE.search(t)
    if m:
        start, end = m.group(1).strip(), m.group(2).strip()
        if not _has_implausible_year(start) and not _has_implausible_year(end):
            return start, end
    return None

def _strip_dates_from(t: str) -> str:
    t = DATE_RANGE_RE.sub('', t)
    t = re.sub(rf'\b{PARTIAL_DATE}\b', '', t, flags=re.IGNORECASE)
    t = re.sub(rf'\b{PRESENT_WORDS}\b', '', t, flags=re.IGNORECASE)
    return t.strip().strip(',-–—\u2013\u2014 ')

def _is_valid_company(t: str) -> bool:

    if not t:
        return False

    t = t.strip()

    if len(t) < 2 or len(t.split()) > 14:
        return False

    if _PAGE_NOISE_RE.match(t):
        return False

    if _is_noise(t):
        return False

    if '@' in t:
        return False

    lower = t.lower()

    if lower.startswith((
        "company:", "job title:", "designation:", "areas worked",
        "tools:", "compliance:", "responsibilities:", "key responsibilities"
    )):
        return False

    if RESPONSIBILITY_VERBS_RE.match(lower):
        return False

    # Resume responsibility fragments commonly begin with a lowercase word;
    # organisation names normally preserve an uppercase initial even in noisy
    # OCR.  Ignore leading punctuation before applying this check.
    first_letter = next((char for char in t if char.isalpha()), "")
    if first_letter and first_letter.islower():
        return False

    # ----------------------------------------
    # Reject bullets
    # ----------------------------------------
    if lower.startswith((">", "-", "*", "+", "=")):
        return False

    # ----------------------------------------
    # Reject locations
    # ----------------------------------------
    if lower.startswith(("location", "address", "city", "country")):
        return False

    # ----------------------------------------
    # Reject designation labels
    # ----------------------------------------
    if lower.startswith((
        "designation",
        "role",
        "position",
        "title"
    )):
        return False

    # ----------------------------------------
    # Reject responsibility sentences
    # ----------------------------------------
    if re.match(
        r'^(to|responsible|handled|handling|created|create|developed|performed|managed|managing|validated|preparing|preparation|appending|reading|accessing|working|provided|providing|reviewing|review|ensuring|ensure|coordinating|coordinate|maintaining|maintain|participating|participate|supporting|support|implementing|implement|conducting|conduct|tracking|track|monitoring|monitor|generating|generate|resolving|resolve)',
        lower
    ):
        return False

    # ----------------------------------------
    # Reject common responsibility words
    # ----------------------------------------
    if re.match(
        r'^(?:who|which|that|for|to|of|and|or|with|by|from|in|on|under|between|during|at|before|after)\b',
        lower
    ):
        return False

    # ----------------------------------------
    # Reject obvious section headings
    # ----------------------------------------
    if re.search(
        r'(summary|objective|education|skills|certification|certifications|references|declaration|projects|languages|profile|professional summary)',
        lower
    ):
        return False

    # ----------------------------------------
    # Reject pure numbers
    # ----------------------------------------
    if re.fullmatch(r'[\d\s\-/,\.]+', lower):
        return False

    return True
def _is_valid_designation(t: str) -> bool:
    if not t or len(t.split()) > 12 or len(t) < 3 or _is_noise(t):
        return False
    # Enforce structural rule: a designation line shouldn't solely consist of date strings
    if _looks_like_date_line(t) and len(_strip_dates_from(t).split()) == 0:
        return False
    return _looks_like_designation(t)

def score_experience_block(exp: Dict[Any, Any]) -> float:
    score = 0.0
    if exp.get("Company") and _is_valid_company(exp["Company"]): score += 2.5
    if exp.get("Designation") and _is_valid_designation(exp["Designation"]): score += 2.5
    if exp.get("Start Date"): score += 1.0
    if exp.get("End Date"): score += 1.0
    if exp.get("Responsibilities"): score += min(len(exp["Responsibilities"]) * 0.5, 3.0)
    return score


_ORG_HINT_RE = re.compile(
    r'\b(?:pvt\.?|private|limited|ltd\.?|llp|inc\.?|corp(?:oration)?|'
    r'company|solutions|services|technologies|research|pharma|healthcare|'
    r'hospital|university|institute)\b',
    re.IGNORECASE,
)


_PROPER_NOUN_COMPANY_RE = re.compile(r"^(?:[A-Z][\w&.'\-]*\s*){2,6}$")


def _is_credible_experience(exp: Dict[str, Any]) -> bool:
    """Require enough evidence that a candidate is a job, not OCR prose."""
    company = exp.get("Company", "").strip()
    designation = exp.get("Designation", "").strip()
    has_dates = bool(exp.get("Start Date") and exp.get("End Date"))
    if not has_dates or not _is_valid_company(company):
        return False
    if _has_implausible_year(exp.get("Start Date", "")) or _has_implausible_year(exp.get("End Date", "")):
        return False
    valid_designation = _is_valid_designation(designation)
    # A company field that itself reads as a job title is almost never a real
    # organization name -- e.g. two consecutive title-like lines ("Research
    # Associate 2" / "Research Associate 1") previously got paired as
    # company+designation just because the second one validated fine as a
    # designation. Require an org-hint word (Ltd/Pvt/Inc/...) to accept a
    # designation-shaped company in that situation.
    if _looks_like_designation(company) and not bool(_ORG_HINT_RE.search(company)):
        return False
    if valid_designation or bool(_ORG_HINT_RE.search(company)):
        return True
    # No designation and no generic corp-suffix word (Ltd/Inc/Pvt/...) --
    # still accept if the company reads as a clean multi-word proper
    # noun (e.g. "Novo Nordisk", "Tata Consultancy Services"), since
    # plenty of real, well-known companies don't carry a corp suffix at
    # all. _is_valid_company has already rejected responsibility
    # sentences, section headings, and lowercase-led prose, so this is
    # just an extra shape check, not the only line of defense.
    return bool(_PROPER_NOUN_COMPANY_RE.match(company))


def _filter_experience_pool(pool: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Discard weak candidates and collapse duplicate matches for one job."""
    best_by_job: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    for exp in pool:
        if not _is_credible_experience(exp):
            continue
        key = (
            exp.get("Start Date", "").strip().lower(),
            exp.get("End Date", "").strip().lower(),
            exp.get("Company", "").strip().lower(),
        )
        existing = best_by_job.get(key)
        if existing is None or score_experience_block(exp) > score_experience_block(existing):
            best_by_job[key] = exp
    return list(best_by_job.values())

_EDU_SECTION_HEADER_RE = re.compile(
    r'^\s*(?:education|academic\s+(?:profile|qualifications?|background)|'
    r'qualifications?|academics|scholastics?)\b',
    re.IGNORECASE
)
# Stop words that legitimately close an Education (or Summary) block once
# we're inside one -- excludes the education-signal words themselves so the
# range-open check doesn't immediately close on its own header line.
_NON_EDU_RESP_STOP_WORDS = [w for w in _RESP_STOP_WORDS if w not in ('education', 'academic', 'qualification')]


def detect_experience_section(lines: List[str]) -> Tuple[List[str], int]:
    start_idx, end_idx = -1, len(lines)
    summary_ranges, current_summary_start = [], -1
    edu_ranges, current_edu_start = [], -1

    for idx, line in enumerate(lines):
        if SUMMARY_HEADER_RE.match(line): current_summary_start = idx
        elif current_summary_start != -1 and (SECTION_HEADER_RE.match(line) or any(w in line.lower() for w in _RESP_STOP_WORDS)):
            summary_ranges.append((current_summary_start, idx)); current_summary_start = -1
    if current_summary_start != -1: summary_ranges.append((current_summary_start, len(lines)))

    # Education sections commonly hold their own date ranges (degree years),
    # which otherwise look identical to a job's date range to every
    # date-based heuristic below. Track Education blocks the same way
    # Summary blocks are tracked so they can be excluded everywhere.
    for idx, line in enumerate(lines):
        if _EDU_SECTION_HEADER_RE.match(line): current_edu_start = idx
        elif current_edu_start != -1 and (SECTION_HEADER_RE.match(line) or any(w in line.lower() for w in _NON_EDU_RESP_STOP_WORDS)):
            edu_ranges.append((current_edu_start, idx)); current_edu_start = -1
    if current_edu_start != -1: edu_ranges.append((current_edu_start, len(lines)))

    excluded_ranges = summary_ranges + edu_ranges

    for idx, line in enumerate(lines):
        if SECTION_HEADER_RE.match(line) and not any(s <= idx < e for s, e in excluded_ranges):
            start_idx = idx + 1; break
    if start_idx == -1:
        for idx, line in enumerate(lines):
            if _looks_like_date_line(line) and _looks_like_designation(line) and not any(s <= idx < e for s, e in excluded_ranges):
                start_idx = idx; break
    if start_idx == -1:
        # Last resort: never start scanning from the very first lines of the
        # document — those are almost always the name/contact header, not
        # experience content. Require an actual date on the line (a bare
        # designation-keyword substring match is too easy for a long prose
        # sentence, e.g. a Summary paragraph mentioning "Programmer", to
        # satisfy — which previously let unheaded Summary text get swept in
        # as "experience"). Education-section dates are also excluded here --
        # without this, a degree line like "B. Pharmacy (2015 - 2019)" was
        # the only "date line" in some resumes and got treated as the start
        # of Experience content.
        for idx, line in enumerate(lines):
            if _looks_like_date_line(line) and not any(s <= idx < e for s, e in excluded_ranges):
                start_idx = idx
                break
        if start_idx == -1:
            _CONTACT_LINE_RE = re.compile(r'[\w.+-]+@[\w.-]+\.\w+|(?:\+?\d[\d\s\-]{8,}\d)')
            header_end = 0
            for idx, line in enumerate(lines[:10]):
                if _CONTACT_LINE_RE.search(line):
                    header_end = idx + 1
            start_idx = header_end

    # An Education block reached later in the same scan (e.g. Education
    # appears after Experience in the resume) should also close the
    # Experience range at its start, even on phrasings not covered by the
    # exact-word forms in _RESP_STOP_WORDS.
    edu_starts_after = [s for s, _e in edu_ranges if s >= start_idx]
    if edu_starts_after:
        end_idx = min(end_idx, min(edu_starts_after))

    for j in range(start_idx, end_idx):
        line_lower = lines[j].lower()
        if any(w == line_lower.strip() or line_lower.startswith(w + " ") for w in _RESP_STOP_WORDS):
            end_idx = j; break

    return [lines[idx] for idx in range(start_idx, end_idx) if not any(s <= idx < e for s, e in excluded_ranges)], start_idx

def split_into_experience_blocks(lines: List[str]) -> List[List[str]]:
    blocks, current_block = [], []
    for line in lines:
        cleaned = line.strip()
        if not cleaned: continue
        if ((_looks_like_date_line(cleaned) and _looks_like_designation(cleaned)) or _NEW_EXP_DATE_RE.match(cleaned) or re.match(r'^Experience\s*#\d*', cleaned, re.I)) and current_block:
            blocks.append(current_block); current_block = [line]
        else: current_block.append(line)
    if current_block: blocks.append(current_block)
    return blocks


def _looks_like_responsibility(line: str) -> bool:
    if _PAGE_NOISE_RE.match(line) or len(line) < 10 or _RESP_HEADER_RE.match(line): return False
    return True if (RESPONSIBILITY_VERBS_RE.search(line) or (_RESP_LINE_RE.match(line) and len(line.split()) >= 5)) else len(line.split()) >= 8

def extract_responsibilities(lines: List[str], start: int, end: int) -> List[str]:
    result = []
    HARD_STOP_SECTIONS = re.compile(r'^\s*(?:certification|certifications|certification\s+details|awards?|achievements?|personal\s+growth|education|academic|qualification|skills|technical\s+skills|key\s+skills|projects?|publications?|languages?|declaration|personal\s+details|references)\b[:\-]?\s*$', re.IGNORECASE)

    for j in range(start, min(end, len(lines))):
        line = lines[j].strip();
        lower = line.lower()
        if _extract_date_range(line):
            continue
        if HARD_STOP_SECTIONS.match(line):
            break
        # The loose substring stop-word check only makes sense for a short,
        # heading-shaped line (a stray section title that HARD_STOP_SECTIONS'
        # exact full-line regex didn't happen to match). Applying it to every
        # line let an ordinary long responsibility sentence that merely
        # mentions "skills"/"academic"/"qualification"/etc anywhere in its
        # text ("coordinated cross-functional skills training") wrongly end
        # the block and silently drop every responsibility after it.
        if len(line.split()) <= 6 and any(w in lower for w in _RESP_STOP_WORDS):
            break
        if _PAGE_NOISE_RE.match(line) or _RESP_HEADER_RE.match(line): continue
        # Stop if a new experience starts
        if j > start:

            # Date line of next experience
            if (_NEW_EXP_DATE_RE.match(line) or _looks_like_date_line(line)) and (
                len(_strip_dates_from(line).split()) < 4
                or _looks_like_designation(line)
            ):
                break

            # Company line of next experience
            next_line = lines[j + 1].strip() if j + 1 < min(end, len(lines)) else ""

            if _is_valid_company(line) and _extract_date_range(next_line):
                break
        if len(line) < 15 or (len(line.split()) <= 4 and not RESPONSIBILITY_VERBS_RE.search(line)): continue

        clean = re.sub(r'^(?:[•➢▪■♦\-\*▸◦]|\d+[\)\.]\s+)', '', line).strip()
        if _looks_like_responsibility(clean) and clean not in result: result.append(clean)
        if len(result) >= 12: break
    return result

def _parse_labeled_experience_blocks(lines: List[str]) -> List[dict]:
    blocks, current = [], None
    label_re = re.compile(r'^(Experience\s*#\d*|Company|Designation|Start Date|End Date|Roles|Responsibilities?)\s*[:\-]?\s*(.*)$', re.IGNORECASE)
    i = 0
    while i < len(lines):
        m = label_re.match(lines[i].strip())
        if m:
            key, value = m.group(1).strip().lower(), m.group(2).strip()
            if key.startswith('experience'):
                if current: blocks.append(current)
                current = {'Company': '', 'Designation': '', 'Start Date': '', 'End Date': '', 'Responsibilities': [], '_line_idx': i}
                i += 1; continue
            if current is None: current = {'Company': '', 'Designation': '', 'Start Date': '', 'End Date': '', 'Responsibilities': [], '_line_idx': i}
            if key == 'company': current['Company'] = value
            elif key == 'designation': current['Designation'] = value
            elif key == 'start date': current['Start Date'] = value
            elif key == 'end date': current['End Date'] = value
        i += 1
    if current: blocks.append(current)
    return blocks

def _extract_designation_duration_blocks(lines: List[str]) -> List[dict]:
    experiences, seen, n, i = [], set(), len(lines), 0
    while i < n:
        desig_m = re.match(r'^(?:Designation|Role|Position)\s*[:\-]\s*(.+)$', lines[i].strip(), re.IGNORECASE)
        if desig_m:
            designation, company = _strip_field_label(desig_m.group(1).strip()), ''
            # Scan backward for the company line, but skip over lines that
            # are themselves noise, another designation (two designations in
            # a row means the real company is further back or absent -- it
            # must NOT be taken as the company), or that fail company
            # validation entirely (e.g. a responsibility sentence like
            # "Assisted Principal Investigators..."). Bound the lookback so
            # we don't wander into an unrelated, distant block.
            for j in range(i - 1, max(-1, i - 6), -1):
                prev = lines[j].strip()
                if not prev or _looks_like_date_line(prev) or re.match(r'^(?:Designation|Role|Position|Duration|Responsibilities?)', prev, re.I):
                    continue
                prev_clean = _strip_field_label(prev)
                if _looks_like_designation(prev_clean):
                    continue
                if not _is_valid_company(prev_clean):
                    continue
                company = prev_clean
                break
            start, end = '', ''
            if i + 1 < n:
                dur_m = re.match(r'^Duration\s*[:\-]\s*(.+)$', lines[i + 1], re.IGNORECASE)
                if dur_m:
                    dates = _extract_date_range(dur_m.group(1).strip())
                    if dates: start, end = dates
            if designation:
                key = (company.lower(), designation.lower(), start.lower(), end.lower())
                if key not in seen:
                    seen.add(key)
                    experiences.append({'Company': company.rstrip('.,; '), 'Designation': designation, 'Start Date': start, 'End Date': end, 'Responsibilities': [], '_line_idx': i})
        i += 1
    return experiences

def extract_summary(text: str) -> str:
    """Extract the Summary/Objective/Profile paragraph, if the resume has
    a clearly headed one. Returns '' if no such section is found (rather
    than guessing from unheaded prose)."""
    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    start = -1
    for idx, line in enumerate(raw_lines):
        if SUMMARY_HEADER_RE.match(line):
            start = idx + 1
            break
    if start == -1:
        return ""
    end = len(raw_lines)
    for idx in range(start, len(raw_lines)):
        if SECTION_HEADER_RE.match(raw_lines[idx]) or any(w in raw_lines[idx].lower() for w in _RESP_STOP_WORDS):
            end = idx
            break
    summary_lines = raw_lines[start:end]
    return " ".join(summary_lines).strip()


def extract_experience_details(text: str) -> List[dict]:
    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lines, global_offset = detect_experience_section(raw_lines)
    if not lines: return []
    lines = [_strip_leading_bullet(ln) for ln in lines]
    candidate_pools = []

    labeled = _parse_labeled_experience_blocks(lines)
    if labeled and any(e['Company'] or e['Designation'] for e in labeled):
        for idx, exp in enumerate(labeled):
            exp["Responsibilities"] = extract_responsibilities(lines, exp["_line_idx"] + 1, labeled[idx+1]["_line_idx"] if idx+1 < len(labeled) else len(lines))
        candidate_pools.append(labeled)

    durations = _extract_designation_duration_blocks(lines)
    if durations:
        for idx, exp in enumerate(durations):
            exp["Responsibilities"] = extract_responsibilities(lines, exp["_line_idx"] + 1, durations[idx+1]["_line_idx"] if idx+1 < len(durations) else len(lines))
        candidate_pools.append(durations)

    fallback_experiences, seen, n = [], set(), len(lines)
    used_indices = set()

    def _add(c: str, d: str, s_dt: str, e_dt: str, idx: int):
        c, d = c.strip(), d.strip()
        if _is_noise(c) or _is_noise(d): return
        key = (c.lower(), d.lower(), s_dt.lower(), e_dt.lower())
        if key in seen: return
        seen.add(key); fallback_experiences.append({"Company": c, "Designation": d, "Start Date": s_dt, "End Date": e_dt, "Responsibilities": [], "_line_idx": idx})

    for i, line in enumerate(lines):
        # Lines already consumed as the designation/date portion of a
        # previously matched entry must not be re-evaluated as the START of
        # a new entry. Without this guard, a standalone designation line
        # (e.g. "Sr. Clinical Data Analyst") immediately followed by its own
        # date line matches the generic "company + date" fallback pattern
        # on its own, producing a spurious duplicate entry one line after
        # the real one. That duplicate's _line_idx then collapses the real
        # entry's responsibility-extraction range to zero lines, silently
        # emptying Responsibilities even though the bullet text is present.
        if i in used_indices:
            continue
        nx1 = lines[i+1] if i+1 < n else ''; nx2 = lines[i+2] if i+2 < n else ''; nx3 = lines[i+3] if i+3 < n else ''
        company_date_m = re.match(rf'^(?P<company>.+?)\s*\(\s*(?:\d{{1,2}}(?:st|nd|rd|th)?\s+)?(?P<start>{PARTIAL_DATE})\s*(?:to|till|thru|through|[-–—])\s*(?P<end>{DATE_TOKEN})\s*\)\s*$', line, re.I)
        if company_date_m:
            has_desig = _looks_like_designation(nx1)
            _add(company_date_m.group('company').strip().rstrip(' ,;:-'), nx1 if has_desig else '', company_date_m.group('start'), company_date_m.group('end'), i)
            if has_desig: used_indices.add(i + 1)
            continue
        if '|' in line:
            parts = [p.strip() for p in line.split('|')]; dp = [p for p in parts if _looks_like_date_line(p)]; non_date = [p for p in parts if p not in dp and p]
            if dp and len(non_date) >= 2:
                dates = _extract_date_range(dp[0])
                if dates: _add(non_date[1], non_date[0], *dates, i) if _looks_like_designation(non_date[0]) else _add(non_date[0], non_date[1], *dates, i); continue
        at_m = re.match(r'^(.+?)\s+at\s+(.+)$', line, re.I)
        if at_m and _looks_like_designation(at_m.group(1)):
            dates = _extract_date_range(nx1) or _extract_date_range(nx2)
            if dates:
                _add(at_m.group(2), at_m.group(1), *dates, i)
                used_indices.add(i + 1 if _extract_date_range(nx1) else i + 2)
            continue
        inline = _extract_date_range(line)
        if inline:
            rem = _strip_dates_from(line); sub = [p.strip() for p in re.split(r'[,|/]', rem) if p.strip()]
            if len(sub) >= 2: _add(sub[1], sub[0], *inline, i) if _looks_like_designation(sub[0]) else _add(sub[0], sub[1], *inline, i); continue
        if _is_valid_company(line) and _looks_like_designation(nx1):
            dates = _extract_date_range(nx2) or _extract_date_range(nx3)
            if dates:
                _add(line, nx1, *dates, i)
                used_indices.add(i + 1)
                used_indices.add(i + 2 if _extract_date_range(nx2) else i + 3)
                continue

        # --------------------------------------------------
        # Company
        # Date
        # Responsibilities... / Designation (searched ahead up to 3 lines)
        # --------------------------------------------------

        if _is_valid_company(line):

            dates = _extract_date_range(nx1)

            if dates:
                designation = ""
                designation_idx = None

                for k in range(i + 2, min(i + 5, n)):
                    if _looks_like_designation(lines[k]):
                        designation = lines[k].strip()
                        designation_idx = k
                        break

                _add(
                    line,
                    designation,
                    dates[0],
                    dates[1],
                    i
                )
                used_indices.add(i + 1)
                if designation_idx is not None:
                    used_indices.add(designation_idx)
                continue

    if fallback_experiences:
        for idx, exp in enumerate(fallback_experiences):
            exp["Responsibilities"] = extract_responsibilities(lines, exp["_line_idx"] + 1, fallback_experiences[idx+1]["_line_idx"] if idx+1 < len(fallback_experiences) else n)
        candidate_pools.append(fallback_experiences)

    if not candidate_pools:
        block_records = []
        for block in split_into_experience_blocks(lines):
            if not block: continue
            comp, des, start, end = "", "", "", ""
            for bline in block:
                dates = _extract_date_range(bline)
                if dates: start, end = dates
                if _is_valid_designation(bline) and not des: des = bline
                elif _is_valid_company(bline) and not comp and not _looks_like_date_line(bline): comp = bline
            # A block with no date at all and no valid (length-bounded) company
            # is almost certainly prose (Summary/Objective text), not a real
            # job entry — don't emit it.
            if (comp or des) and (start or end or comp): block_records.append({"Company": comp, "Designation": des, "Start Date": start, "End Date": end, "Responsibilities": extract_responsibilities(block, 0, len(block))})
        if block_records: candidate_pools.append(block_records)

    # Each strategy sees the same OCR text differently.  Filter every pool
    # before scoring so a large set of weak, duplicate matches cannot win.
    candidate_pools = [
        filtered for pool in candidate_pools
        if (filtered := _filter_experience_pool(pool))
    ]

    if not candidate_pools: return []
    candidate_pools.sort(key=lambda pool: sum(score_experience_block(x) for x in pool), reverse=True)
    best_pool = candidate_pools[0]

    for item in best_pool:

        item.pop("_line_idx", None)

        item["Company"] = _strip_field_label(item["Company"]).strip().strip(',-–—: ')

        desig = _strip_field_label(item["Designation"]).strip().strip(',-–—: ')

        if desig:

            if item.get("Start Date") and item["Start Date"] in desig:
                desig = desig.replace(item["Start Date"], "")

            if item.get("End Date") and item["End Date"] in desig:
                desig = desig.replace(item["End Date"], "")

            desig = re.sub(
                rf'\b{PARTIAL_DATE}\b|\b{PRESENT_WORDS}\b',
                '',
                DATE_RANGE_SPACED_RE.sub(
                    '',
                    DATE_RANGE_RE.sub('', desig)
                ),
                flags=re.IGNORECASE
            )

            item["Designation"] = re.sub(
                r'\s+to\s+',
                ' ',
                desig,
                flags=re.IGNORECASE
            ).strip().strip(',-–—\u2013\u2014: ')

        if item.get("Responsibilities") and item.get("Designation"):

            item["Responsibilities"] = [
                r for r in item["Responsibilities"]
                if not (
                    item["Designation"].lower() in r.lower()
                    and len(r.split()) <= len(item["Designation"].split()) + 4
                )
                and not (
                    item["Company"].lower() in r.lower()
                    and len(r.split()) <= len(item["Company"].split()) + 3
                )
            ]


    # -------------------------------------------------------
    # Split Company and Designation
    # Example:
    # Tata Consultancy Services [Analyst-Life Science]
    # -------------------------------------------------------

    for item in best_pool:

        company = item["Company"]

        if "[" in company and "]" in company:

            left = company.split("[", 1)[0].strip()

            right = company.split("[", 1)[1].replace("]", "").strip()

            item["Company"] = left

            if not item["Designation"]:
                item["Designation"] = right


    return [x for x in best_pool if x["Company"] or x["Designation"]]