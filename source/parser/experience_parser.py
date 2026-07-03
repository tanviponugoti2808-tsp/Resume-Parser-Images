import re
from typing import List, Dict, Any, Tuple, Optional

_MONTH_PAT = r'(?:Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?)'
PARTIAL_DATE = rf'(?:\d{{1,2}}(?:st|nd|rd|th)?\s+)?{_MONTH_PAT}[,\s\'’\-]+\d{{2,4}}|\d{{1,2}}[/-]{_MONTH_PAT}[/-]\d{{4}}|\d{{1,2}}/\d{{4}}|Q[1-4]\s*\d{{4}}|\d{{4}}'
PRESENT_WORDS = r'(?:Present|Current|Till\s+Date|Till\s+Now|Ongoing|Now|Continuing|To\s+Date|Still\s+working)'
DATE_TOKEN = rf'(?:{PARTIAL_DATE}|{PRESENT_WORDS})'

DATE_RANGE_RE = re.compile(
    rf'({PARTIAL_DATE})\s*(?:to|-|–|—|~|till|thru|through)\s*({DATE_TOKEN})',
    re.IGNORECASE
)
DATE_RANGE_SPACED_RE = re.compile(rf'({PARTIAL_DATE})\s+({DATE_TOKEN})', re.IGNORECASE)
SECTION_HEADER_RE = re.compile(r'^\s*(?:work\s+experience|professional\s+experience|employment\s+history|experience|career\s+(?:history|summary)|employment\s+details|professional\s+background)\s*[:\-]?\s*$', re.IGNORECASE)
SUMMARY_HEADER_RE = re.compile(r'^\s*(?:professional\s+summary|career\s+objective|profile\s+summary|about\s+me|summary|profile)\s*[:\-]?\s*$', re.IGNORECASE)

_COMPANY_NOISE_WORDS = ['responsibilities','summary','objective','profile','skills','education','certification','project','achievements','awards','publications','references','languages','hobbies','interests','declaration','personal details','personal information','regional team','cross functional','client']
DESIGNATION_KEYWORDS = sorted(['chief','head of','vice president','vp ','director','president','ceo','cto','coo','cfo','senior','lead','principal','staff','manager','associate','specialist','consultant','analyst','executive','officer','coordinator','administrator','engineer','developer','scientist','researcher','technician','intern','trainee','assistant','fellow','architect','programmer','designer','writer','recruiter','accountant','instructor','professor','teacher','clinical data manager','statistical programmer','data manager','study coordinator','regulatory affairs','pharmacovigilance','drug safety','bioinformatics','backend','frontend','full stack','devops','cloud','qa','automation','network','system'], key=len, reverse=True)

RESPONSIBILITY_VERBS_RE = re.compile(r'\b(?:responsible|managed?|performed?|developed?|created?|reviewed?|led|supported?|coordinated?|implemented?|analy[sz]ed?|worked?\s+on|handled?|checked?|monitored?|maintained?|prepared?|ensured?|conducted?|collected?|reported?|assisted?|processed?|validated?|reconciled?|designed?|built?|established?|generated?|tracked?|trained?|mentored?|collaborated?|communicated?|contributed?|participated?|provided?|spearheaded?|oversaw|overseen|identified?|resolved?|initiated?|prioritized?|streamlined?|automated?|documented?|submitted?|started?|set[\s\-]?up|gained?\s+knowledge|used?\s+efficient|leading|mentoring|auditing|writing|reviewing|cleaning|managing|coordinating|investigating|evaluating|assessing)\b', re.IGNORECASE)
_RESP_STOP_WORDS = ["education","academic","qualification","skills","certifications","projects","languages","personal information","personal details","awards","references","declaration","key skills","technical skills","patents","publications"]
_RESP_HEADER_RE = re.compile(r'^\s*(?:key\s+)?(?:roles?\s+(?:and|&)\s+)?(?:responsibilities?|duties?|tasks?|deliverables|accountabilities)\s*[:\-]?\s*$', re.IGNORECASE)
_NEW_EXP_DATE_RE = re.compile(r'^\s*(?:(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[\w]*\s+\d{4}|\d{4}\s*[-–—])', re.IGNORECASE)
_RESP_LINE_RE = re.compile(r'^(?:[•➢▪■♦\-\*▸◦]|\d+[\)\.]\s+)?')
_PAGE_NOISE_RE = re.compile(r'^(?:page\s+\d+|\d+\s+of\s+\d+|\s*)$', re.IGNORECASE)

def _clean(t: str) -> str: return t.strip()
def _is_noise(t: str) -> bool: return any(w in t.lower() for w in _COMPANY_NOISE_WORDS)
def _looks_like_designation(t: str) -> bool: return any(kw in t.lower() for kw in DESIGNATION_KEYWORDS)
def _looks_like_date_line(t: str) -> bool: return bool(DATE_RANGE_RE.search(t) or DATE_RANGE_SPACED_RE.search(t))

def _extract_date_range(t: str) -> Optional[Tuple[str, str]]:
    m = DATE_RANGE_RE.search(t)
    if m: return m.group(1).strip(), m.group(2).strip()
    m = DATE_RANGE_SPACED_RE.search(t)
    if m: return m.group(1).strip(), m.group(2).strip()
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

    if _is_noise(t):
        return False

    if '@' in t:
        return False

    lower = t.lower()

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
    return False if (not t or len(t.split()) > 12 or len(t) < 3 or _is_noise(t)) else _looks_like_designation(t)

def score_experience_block(exp: Dict[Any, Any]) -> float:
    score = 0.0
    if exp.get("Company") and _is_valid_company(exp["Company"]): score += 2.5
    if exp.get("Designation") and _is_valid_designation(exp["Designation"]): score += 2.5
    if exp.get("Start Date"): score += 1.0
    if exp.get("End Date"): score += 1.0
    if exp.get("Responsibilities"): score += min(len(exp["Responsibilities"]) * 0.5, 3.0)
    return score

def detect_experience_section(lines: List[str]) -> Tuple[List[str], int]:
    start_idx, end_idx = -1, len(lines)
    summary_ranges, current_summary_start = [], -1

    for idx, line in enumerate(lines):
        if SUMMARY_HEADER_RE.match(line): current_summary_start = idx
        elif current_summary_start != -1 and (SECTION_HEADER_RE.match(line) or any(w in line.lower() for w in _RESP_STOP_WORDS)):
            summary_ranges.append((current_summary_start, idx)); current_summary_start = -1
    if current_summary_start != -1: summary_ranges.append((current_summary_start, len(lines)))

    for idx, line in enumerate(lines):
        if SECTION_HEADER_RE.match(line) and not any(s <= idx < e for s, e in summary_ranges):
            start_idx = idx + 1; break
    if start_idx == -1:
        for idx, line in enumerate(lines):
            if _looks_like_date_line(line) and _looks_like_designation(line) and not any(s <= idx < e for s, e in summary_ranges):
                start_idx = idx; break
    if start_idx == -1: start_idx = 0

    for j in range(start_idx, len(lines)):
        line_lower = lines[j].lower()
        if any(w == line_lower.strip() or line_lower.startswith(w + " ") for w in _RESP_STOP_WORDS):
            end_idx = j; break

    return [lines[idx] for idx in range(start_idx, end_idx) if not any(s <= idx < e for s, e in summary_ranges)], start_idx

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
        if HARD_STOP_SECTIONS.match(line) or any(w in lower for w in _RESP_STOP_WORDS): break
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
    experiences, n, i = [], len(lines), 0
    while i < n:
        desig_m = re.match(r'^(?:Designation|Role|Position)\s*[:\-]\s*(.+)$', lines[i].strip(), re.IGNORECASE)
        if desig_m:
            designation, company = desig_m.group(1).strip(), ''
            for j in range(i - 1, -1, -1):
                prev = lines[j].strip()
                if not prev or _looks_like_date_line(prev) or re.match(r'^(?:Designation|Role|Position|Duration|Responsibilities?)', prev, re.I): continue
                company = prev; break
            start, end = '', ''
            if i + 1 < n:
                dur_m = re.match(r'^Duration\s*[:\-]\s*(.+)$', lines[i + 1], re.IGNORECASE)
                if dur_m:
                    dates = _extract_date_range(dur_m.group(1).strip())
                    if dates: start, end = dates
            if designation: experiences.append({'Company': company.rstrip('.,; '), 'Designation': designation, 'Start Date': start, 'End Date': end, 'Responsibilities': [], '_line_idx': i})
        i += 1
    return experiences

def extract_experience_details(text: str) -> List[dict]:
    raw_lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    lines, global_offset = detect_experience_section(raw_lines)
    if not lines: return []
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
    def _add(c: str, d: str, s_dt: str, e_dt: str, idx: int):
        c, d = c.strip(), d.strip()
        if _is_noise(c) or _is_noise(d): return
        key = (c.lower(), d.lower(), s_dt.lower(), e_dt.lower())
        if key in seen: return
        seen.add(key); fallback_experiences.append({"Company": c, "Designation": d, "Start Date": s_dt, "End Date": e_dt, "Responsibilities": [], "_line_idx": idx})

    for i, line in enumerate(lines):
        nx1 = lines[i+1] if i+1 < n else ''; nx2 = lines[i+2] if i+2 < n else ''; nx3 = lines[i+3] if i+3 < n else ''
        company_date_m = re.match(rf'^(?P<company>.+?)\s*\(\s*(?:\d{{1,2}}(?:st|nd|rd|th)?\s+)?(?P<start>{PARTIAL_DATE})\s*(?:to|till|thru|through|[-–—])\s*(?P<end>{DATE_TOKEN})\s*\)\s*$', line, re.I)
        if company_date_m:
            _add(company_date_m.group('company').strip().rstrip(' ,;:-'), nx1 if _looks_like_designation(nx1) else '', company_date_m.group('start'), company_date_m.group('end'), i); continue
        if '|' in line:
            parts = [p.strip() for p in line.split('|')]; dp = [p for p in parts if _looks_like_date_line(p)]; non_date = [p for p in parts if p not in dp and p]
            if dp and len(non_date) >= 2:
                dates = _extract_date_range(dp[0])
                if dates: _add(non_date[1], non_date[0], *dates, i) if _looks_like_designation(non_date[0]) else _add(non_date[0], non_date[1], *dates, i); continue
        at_m = re.match(r'^(.+?)\s+at\s+(.+)$', line, re.I)
        if at_m and _looks_like_designation(at_m.group(1)):
            dates = _extract_date_range(nx1) or _extract_date_range(nx2)
            if dates: _add(at_m.group(2), at_m.group(1), *dates, i); continue
        inline = _extract_date_range(line)
        if inline:
            rem = _strip_dates_from(line); sub = [p.strip() for p in re.split(r'[,|/]', rem) if p.strip()]
            if len(sub) >= 2: _add(sub[1], sub[0], *inline, i) if _looks_like_designation(sub[0]) else _add(sub[0], sub[1], *inline, i); continue
        if _is_valid_company(line) and _looks_like_designation(nx1):
            dates = _extract_date_range(nx2) or _extract_date_range(nx3)
            if dates: _add(line, nx1, *dates, i); continue

        # --------------------------------------------------
        # Company
        # Date
        # Responsibilities...
        # (No designation line)
        # --------------------------------------------------

        if _is_valid_company(line):

            dates = _extract_date_range(nx1)

            if dates:

                _add(
                    line,
                    "",
                    dates[0],
                    dates[1],
                    i
                )

                continue

        # --------------------------------------------------
        # Company
        # Date
        # (Handles company followed directly by date)
        # --------------------------------------------------

        # if _is_valid_company(line):

        #     dates = _extract_date_range(nx1)

        #     if dates:

        #         _add(
        #             line,
        #             "",
        #             dates[0],
        #             dates[1],
        #             i
        #         )

        #         continue
        if "Quartesian" in line:
            print("\nFOUND QUARTESIAN")
            print("LINE :", line)
            print("NEXT :", nx1)
            print("VALID:", _is_valid_company(line))
            print("DATES:", _extract_date_range(nx1))

        if _is_valid_company(line):

            dates = _extract_date_range(nx1)

            if dates:
                designation = ""

                for k in range(i + 2, min(i + 5, n)):
                    if _looks_like_designation(lines[k]):
                        designation = lines[k].strip()
                        break

                _add(
                    line,
                    designation,
                    dates[0],
                    dates[1],
                    i
                )
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
                if _looks_like_designation(bline) and not des: des = bline
                elif _is_valid_company(bline) and not comp and not _looks_like_date_line(bline): comp = bline
            if comp or des: block_records.append({"Company": comp, "Designation": des, "Start Date": start, "End Date": end, "Responsibilities": extract_responsibilities(block, 0, len(block))})
        if block_records: candidate_pools.append(block_records)

    if not candidate_pools: return []
    print("\n========== CANDIDATE POOLS ==========")

    for idx, pool in enumerate(candidate_pools):

        print(f"\nPOOL {idx + 1}")

        for exp in pool:
            print(exp)

    print("=====================================\n")
    candidate_pools.sort(key=lambda pool: sum(score_experience_block(x) for x in pool), reverse=True)
    best_pool = candidate_pools[0]

    for item in best_pool:

        item.pop("_line_idx", None)

        item["Company"] = item["Company"].strip().strip(',-–—: ')

        desig = item["Designation"].strip().strip(',-–—: ')

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

        print("BEFORE:", company)

        if "[" in company and "]" in company:

            left = company.split("[", 1)[0].strip()

            right = company.split("[", 1)[1].replace("]", "").strip()

            item["Company"] = left

            if not item["Designation"]:
                item["Designation"] = right

        print("AFTER :", item["Company"], "|", item["Designation"])


    return [x for x in best_pool if x["Company"] or x["Designation"]]