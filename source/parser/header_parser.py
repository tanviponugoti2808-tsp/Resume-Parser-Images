import re

_EMAIL_BLACKLIST = {
    r'^recuritmentind@clinovo\.com$',
    r'^(?:recruit|recruitment|careers|hr|humanresources|jobs|info|contact|support|admin|office|team)@',
    r'^(?:no-reply|noreply|donotreply|do-not-reply)@',
}

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

def extract_phone(text: str) -> str:
    candidates = []
    for m in re.finditer(
        r'(?<!\d)(\+?91[\s\-]?)?([6-9]\d{9}|[0-9]{3}[\s\-][0-9]{3}[\s\-][0-9]{4}|\d{10,12})(?!\d)',
        text
    ):
        raw = re.sub(r'[\s\-\+]', '', m.group())
        if raw.startswith('91') and len(raw) == 12:
            raw = raw[2:]
        if len(raw) == 10 and raw.isdigit():
            candidates.append(raw)
    if not candidates:
        for m in re.finditer(r'(?<!\d)\d{10}(?!\d)', text):
            candidates.append(m.group())
    return candidates[0] if candidates else ""