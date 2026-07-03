import re
import datetime
from typing import List, Tuple, Optional, Dict, Any

_MONTH_MAP = {
    'jan': 1, 'feb': 2, 'mar': 3, 'apr': 4, 'may': 5, 'jun': 6,
    'jul': 7, 'aug': 8, 'sep': 9, 'oct': 10, 'nov': 11, 'dec': 12,
}

def _parse_date_to_ym(token: str) -> Optional[Tuple[int, int]]:
    if not token:
        return None
    token = token.strip().lower()

    if re.match(r'^(present|current|till\s+date|till\s+now|ongoing|now|continuing|to\s+date)$', token):
        now = datetime.date.today()
        return now.year, now.month

    m = re.match(r'^([a-z]+)[,\s\-\']+(\d{4})$', token)
    if m:
        mo = _MONTH_MAP.get(m.group(1)[:3])
        if mo: return int(m.group(2)), mo

    m = re.match(r'^([a-z]+)[,\s\-\']+(\d{2})$', token)
    if m:
        mo = _MONTH_MAP.get(m.group(1)[:3])
        if mo: return 2000 + int(m.group(2)), mo

    m = re.match(r'^(\d{1,2})/(\d{4})$', token)
    if m: return int(m.group(2)), int(m.group(1))

    m = re.match(r'^(\d{4})[./](\d{1,2})$', token)
    if m: return int(m.group(1)), int(m.group(2))

    m = re.match(r'^(\d{4})$', token)
    if m: return int(m.group(1)), 6
    return None

def _extract_explicit_experience(text: str) -> Optional[float]:
    lines = text.splitlines()[:50]
    header_text = "\n".join(lines)
    explicit_pats = [
        r'(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)\s+(?:of\s+)?(?:total\s+|overall\s+)?(?:experience|exp)',
        r'(?:total|overall|having)\s+(?:of\s+)?(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)',
        r'experience\s+of\s+(\d+(?:\.\d+)?)\+?\s*(?:years?|yrs?)',
    ]
    for pat in explicit_pats:
        vals = [float(x) for x in re.findall(pat, header_text, re.IGNORECASE) if 0 < float(x) < 50]
        if vals: return max(vals)
    return None

def _merge_overlapping_ranges(intervals: List[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if not intervals:
        return []
    sorted_intervals = sorted(intervals, key=lambda x: x[0])
    merged = [sorted_intervals[0]]
    for current_start, current_end in sorted_intervals[1:]:
        prev_start, prev_end = merged[-1]
        if current_start <= prev_end + 1:
            merged[-1] = (prev_start, max(prev_end, current_end))
        else:
            merged.append((current_start, current_end))
    return merged

def _extract_date_ranges(text: str) -> List[Tuple[int, int]]:
    intervals = []
    DATE_RANGE_INFER = re.compile(
        r'\b(?:(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|\d{1,2}|\d{4})[,\s\.\-\'/ ]+(\d{4}|\d{2})?)\s*(?:to|-|–|—|till|thru)\s*(?:(Jan(?:uary)?|Feb(?:ruary)?|Mar(?:ch)?|Apr(?:il)?|May|Jun(?:e)?|Jul(?:y)?|Aug(?:ust)?|Sep(?:tember)?|Oct(?:ober)?|Nov(?:ember)?|Dec(?:ember)?|Present|Current|Till\s+Date|Till\s+Now|Ongoing|Now|\d{1,2}|\d{4})[,\s\.\-\'/ ]*(\d{4}|\d{2})?)\b',
        re.IGNORECASE
    )
    for m in DATE_RANGE_INFER.finditer(text):
        start_tok = m.group(1) + (f" {m.group(2)}" if m.group(2) else "")
        end_tok = m.group(3) + (f" {m.group(4)}" if m.group(4) else "")
        s = _parse_date_to_ym(start_tok)
        e = _parse_date_to_ym(end_tok)
        if s and e:
            start_idx = s[0] * 12 + s[1]
            end_idx = e[0] * 12 + e[1]
            if start_idx <= end_idx: intervals.append((start_idx, end_idx))

    if not intervals:
        YEAR_RANGE = re.compile(r'\b(\d{4})\s*[-–—]\s*(\d{4}|Present|Current|Now)\b', re.IGNORECASE)
        for m in YEAR_RANGE.finditer(text):
            sy = int(m.group(1))
            ey = datetime.date.today().year if re.match(r'(?i)present|current|now', m.group(2)) else int(m.group(2))
            if sy <= ey: intervals.append((sy * 12 + 6, ey * 12 + 6))
    return intervals

def extract_overall_experience(text: str, structured_experiences: Optional[List[Dict[str, Any]]] = None) -> str:
    explicit_yrs = _extract_explicit_experience(text)
    intervals = []
    if structured_experiences:
        for exp in structured_experiences:
            s = _parse_date_to_ym(exp.get('Start Date', ''))
            e = _parse_date_to_ym(exp.get('End Date', ''))
            if s and e: intervals.append((s[0] * 12 + s[1], e[0] * 12 + e[1]))
    else:
        intervals = _extract_date_ranges(text)

    total_months = sum(max(0, end - start+1) for start, end in _merge_overlapping_ranges(intervals))
    calculated_yrs = round(total_months / 12, 1)
    if calculated_yrs < 0.3 or calculated_yrs > 60: calculated_yrs = 0.0

    final_yrs = 0.0
    if explicit_yrs and calculated_yrs:
        final_yrs = explicit_yrs if abs(explicit_yrs - calculated_yrs) <= 1.5 else calculated_yrs
    else:
        final_yrs = explicit_yrs or calculated_yrs

    if final_yrs <= 0: return "Not Found"
    return f"{int(final_yrs)} Years" if final_yrs.is_integer() else f"{final_yrs:.1f} Years"