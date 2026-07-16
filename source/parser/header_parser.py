import re

_LINKEDIN_RE = re.compile(
    r'(?:(?:https?:/?/?|www\.)\s*)?(?:in\.)?linkedin\s*\.\s*com\s*/\s*in\s*/\s*([A-Za-z0-9][A-Za-z0-9._%\- ]{1,90})',
    re.IGNORECASE
)

_LOCATION_LABEL_RE = re.compile(
    r'^\s*(?:current\s+)?(?:location|address|current\s+address|present\s+address|permanent\s+address)\s*[:\-–—]?\s*(.+)$',
    re.IGNORECASE
)

_LOCATION_HINT_RE = re.compile(
    r'\b(?:india|remote|hybrid|bangalore|bengaluru|hyderabad|chennai|pune|mumbai|delhi|'
    r'gurgaon|gurugram|noida|coimbatore|cochin|kochi|kerala|karnataka|telangana|'
    r'tamil\s+nadu|andhra\s+pradesh|maharashtra|west\s+bengal|himachal\s+pradesh)\b',
    re.IGNORECASE
)

_EMAIL_BLACKLIST = {
    r'^recuritmentind@clinovo\.com$',
    r'^(?:recruit|recruitment|careers|hr|humanresources|jobs|info|contact|support|admin|office|team)@',
    r'^(?:no-reply|noreply|donotreply|do-not-reply)@',
    # Placeholder/sample domains commonly left over from resume templates
    # or "format" instructions (e.g. "Email: yourname@example.com").
    r'@example\.(?:com|org|net)$',
    r'@(?:domain|company|yourcompany|sample|test|placeholder)\.(?:com|org|net)$',
    r'^(?:john\.doe|jane\.doe|firstname\.lastname|your\.name|yourname|'
    r'name\.surname|abc|xyz|test|sample|placeholder)@',
}

def _clean_linkedin_slug(slug: str) -> str:
    slug = re.sub(r'\s+', '', slug or '')
    slug = slug.strip('.,;:|)]}>')
    slug = re.sub(r'[^A-Za-z0-9._%-].*$', '', slug)
    slug = re.sub(
        r'(?i)(?:bangalore|bengaluru|hyderabad|chennai|pune|mumbai|delhi|india|remote|hybrid)$',
        '',
        slug
    )
    return slug

def extract_linkedin(text: str) -> str:
    if not text:
        return ""

    compact_text = re.sub(r'(?i)linked\s+in', 'linkedin', text)
    compact_text = re.sub(r'(?i)linked\s*in', 'linkedin', compact_text)

    for match in _LINKEDIN_RE.finditer(compact_text):
        slug = _clean_linkedin_slug(match.group(1))
        if len(slug) < 3:
            continue
        return f"https://www.linkedin.com/in/{slug}"

    return ""

def _clean_location(value: str) -> str:
    value = re.sub(r'\s+', ' ', value or '').strip()
    value = re.sub(r'^(?:city|state|country)\s*[:\-]\s*', '', value, flags=re.IGNORECASE)
    value = value.strip(' .,:;|[]()')
    value = re.split(r'\b(?:email|e-mail|phone|mobile|linkedin|www\.|https?://)\b', value, flags=re.IGNORECASE)[0].strip()
    value = re.sub(r'(?i)\b(India)\b.*$', r'\1', value)
    value = re.sub(r'(?i)\b(Kerala|Karnataka|Telangana|Tamil Nadu|Andhra Pradesh|Maharashtra|West Bengal|Himachal Pradesh)\b.*$', r'\1', value)
    value = re.sub(
        r'^(?:[A-Za-z]\s+)?(?=(?:New\s+Delhi|Delhi|Bangalore|Bengaluru|Hyderabad|Chennai|Pune|Mumbai|Cochin|Kochi|Coimbatore)\b)',
        '',
        value,
        flags=re.IGNORECASE
    )
    value = re.sub(r'\s+[A-Za-z]$', '', value)
    value = re.sub(r'\s{2,}', ' ', value)
    return value.strip(' .,:;|[]()')

def _looks_like_location(value: str) -> bool:
    if not value:
        return False
    if re.search(r'@|linkedin|https?://|www\.', value, re.IGNORECASE):
        return False
    if len(value) < 3 or len(value) > 140:
        return False
    if len(re.findall(r'\d', value)) > 8:
        return False
    if re.search(
        r'\b(?:study|studies|clinical|trial|data|programming|validation|query|queries|'
        r'experience|experienced|expertise|skills|python|sas|rave|edc|migration|custom)\b',
        value,
        re.IGNORECASE
    ):
        return False
    if _LOCATION_HINT_RE.search(value):
        return True
    return bool(re.search(r'\b[A-Za-z][A-Za-z .-]+,\s*[A-Za-z][A-Za-z .-]+\b', value))

def extract_location(text: str) -> str:
    if not text:
        return ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    header_lines = lines[:15]

    for line in header_lines:
        match = _LOCATION_LABEL_RE.match(line)
        if not match:
            continue
        location = _clean_location(match.group(1))
        if _looks_like_location(location):
            return location

    for line in header_lines[:8]:
        has_contact_context = bool(re.search(
            r'@|\+?\d[\d \t\-()]{7,}\d|linkedin|https?://|www\.',
            line,
            re.IGNORECASE
        ))
        if not has_contact_context:
            continue

        line = re.sub(r'\+?\d[\d \t\-()]{7,}\d', ' ', line)
        line = re.sub(r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}', ' ', line)
        line = re.sub(r'(?:(?:https?:/?/?|www\.)\s*)?(?:in\.)?linkedin\s*\.\s*com\s*/\s*in\s*/\s*[A-Za-z0-9._%\- ]+', ' ', line, flags=re.IGNORECASE)
        line = _clean_location(line)
        if len(line) > 70:
            continue

        comma_match = re.search(
            r'\b([A-Za-z][A-Za-z .-]{2,40},\s*(?:[A-Za-z][A-Za-z .-]{2,40})(?:,\s*[A-Za-z][A-Za-z .-]{2,40})?)\b',
            line
        )
        if comma_match:
            location = _clean_location(comma_match.group(1))
            if _looks_like_location(location):
                return location

        hint_match = re.search(
            r'\b([A-Za-z][A-Za-z .-]{2,40}\s*(?:\(|,)?\s*(?:India|Remote|Hybrid)\)?)\b',
            line,
            re.IGNORECASE
        )
        if hint_match:
            location = _clean_location(hint_match.group(1))
            if _looks_like_location(location):
                return location

    return ""

def extract_email(text: str) -> str:
    if not text:
        return "Not Found"

    text = re.sub(r'\s*@\s*', '@', text)
    text = re.sub(r'@\s+', '@', text)
    text = re.sub(r'\s+\.', '.', text)
    text = re.sub(r'\.\s+', '.', text)

    emails = re.findall(
        r'[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}',
        text, flags=re.IGNORECASE
    )

    cleaned = []
    for email in emails:
        email = email.strip().rstrip('.,;:|)]}>')

        if email.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.svg', '.pdf')):
            continue

        reject = False
        for pat in _EMAIL_BLACKLIST:
            try:
                if re.search(pat, email, re.IGNORECASE):
                    reject = True
                    break
            except re.error:
                pass

        if not reject:
            cleaned.append(email)

    cleaned = list(dict.fromkeys(cleaned))

    generic_prefixes = {
        "info", "support", "contact", "admin",
        "help", "career", "careers", "hr",
        "jobs", "recruitment", "team"
    }

    cleaned.sort(
        key=lambda e: (
            e.split('@')[0].lower() in generic_prefixes,
            len(e)
        )
    )

    return cleaned[0] if cleaned else " "

# FIX: use [ \t\-] instead of \s so the match cannot bridge across a
# newline. \s matches "\n", which previously let the regex merge two
# separate phone numbers sitting on consecutive lines (e.g. "93800 73830"
# and "97412 72466") into one malformed candidate that failed validation,
# leaving the phone field empty.
_PHONE_CANDIDATE_RE = re.compile(r'(?<!\d)(\+?\d{1,3}[ \t\-]?)?(\d[\d \t\-]{7,14}\d)(?!\d)')

def extract_phone(text: str) -> str:
    candidates = []
    for m in _PHONE_CANDIDATE_RE.finditer(text):
        raw = re.sub(r'[\s\-\+]', '', m.group())
        if not raw.isdigit():
            continue

        if len(raw) > 10:
            # Strip a leading India country code first ("91" + 10-digit number).
            if raw.startswith('91') and len(raw) - 2 == 10:
                raw = raw[2:]
            # Otherwise, if only a small amount of leading cruft is present
            # (duplicated/garbled country code, stray digit from OCR), trim
            # down to the last 10 digits rather than discarding the match.
            elif len(raw) - 10 <= 4:
                raw = raw[-10:]
            else:
                continue

        if len(raw) == 10 and raw[0] in '6789':
            candidates.append(raw)

    return candidates[0] if candidates else ""
