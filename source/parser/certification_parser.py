import re
from typing import List, Dict, Optional


# ─── Section boundary detection ───────────────────────────────────────────────

_CERT_SECTION_START = re.compile(
    r'^\s*(?:certifications?|certificates?|professional\s+certifications?|'
    r'licenses?\s+(?:and\s+)?certifications?|credentials?|'
    r'professional\s+credentials?|courses?\s+(?:and\s+)?certifications?|'
    r'training\s+(?:and\s+)?certifications?|achievements?\s+(?:and\s+)?certifications?|'
    r'awards?\s+(?:and\s+)?certifications?)\s*[:\-]?\s*$',
    re.IGNORECASE,
)

_CERT_SECTION_STOP = re.compile(
    r'^\s*(?:experience|professional\s+experience|work\s+experience|employment|'
    r'employment\s+history|career\s+history|work\s+history|'
    r'education|academic|skills?|technical\s+skills?|projects?|languages?|'
    r'personal\s+(?:details?|information)|declaration|references?|hobbies|'
    r'interests?|publications?|patents?|summary|objective|profile)\b',
    re.IGNORECASE,
)

# ─── Line classification regexes ──────────────────────────────────────────────

# Year: standalone 4-digit year in range 1990–2035
_YEAR_RE = re.compile(r'\b((?:19[9]\d|20[0-3]\d))\b')

# Issuing org indicators — structural signals, not hardcoded names
_ORG_INDICATORS = re.compile(
    r'\b(?:issued?\s+by|certified?\s+by|accredited?\s+by|authorized?\s+by|'
    r'provided?\s+by|offered?\s+by|from|by)\b',
    re.IGNORECASE,
)

# Known org patterns — used to infer org from cert text itself
_ORG_SUFFIX_RE = re.compile(
    r'\b(?:institute|university|college|academy|association|board|council|'
    r'foundation|society|organization|centre|center|school|corporation|'
    r'inc\.?|ltd\.?|llc\.?|corp\.?|pvt\.?)\b',
    re.IGNORECASE,
)

# Bullet/list prefix -- extended to cover OCR-mangled bullet glyphs that
# commonly appear when a bulleted list gets flattened by OCR (e.g. "«", "»",
# "=", "¢", "§"), which previously slipped through and stayed glued to the
# front of a skills-list line, making it look more cert-entry-shaped than it
# was.
_BULLET_RE = re.compile(r'^\s*[•▪▸◦➢\-\*>→«»=¢§·‣]\s*')

# Lines that are clearly NOT certification entries
_NOISE_RE = re.compile(
    r'^\s*(?:page\s+\d+|\d+\s+of\s+\d+|references?\s+available|'
    r'declaration|i\s+hereby|place\s*:|date\s*:|signature\s*:)\s*$',
    re.IGNORECASE,
)

# A "Label: comma, separated, list" line -- e.g. "Tools: Oracle DMW, Life
# Sciences Hub (LSH)", "Programming Language : SAS", "Areas Worked: SAS 9.4,
# SAS enterprise guide", "Statistical Software : Base SAS". These are Skills
# section content, not named certifications, even though they frequently
# mention a vendor/tool name that trips the weak-cert-signal check below.
# Matched regardless of position (start of a cert-section block or anywhere
# in the whole-document scan) because a label like this is unambiguous.
_SKILL_LIST_LABEL_RE = re.compile(
    r'^\s*(?:'
    r'(?:other\s+|key\s+|technical\s+|core\s+|sas\s+|soft\s+)?tools?|'
    r'technolog(?:y|ies)|programming(?:\s+languages?)?|software(?:\s+skills?)?|'
    r'skills?|areas?\s+worked|statistical\s+software|compliance(?:\s*&\s*tools?)?|'
    r'product\s+skills?|standards?|microsoft\s+tools?|systems?|'
    r'languages?\s+known|packages?'
    r')\s*[:\-]',
    re.IGNORECASE,
)

# A dense comma-separated list of short fragments reads as a skills/tools
# enumeration ("Oracle Clinical, EDC, InForm" / "Medidata Rave, Inform,
# IBM-CD, Oracle Clinical") rather than a single named certification, even
# with no explicit label prefix at all. Only used to veto WEAK-signal-only
# matches (a bare vendor name mention) -- a genuine certification title like
# "AWS Certified Cloud Practitioner" has no commas and is never affected.
_DENSE_LIST_RE = re.compile(r'^(?:[\w/&\.\-]{1,25},\s*){2,}[\w/&\.\-]{1,25}\.?$')

# A bare "Org Name, City, State" line (no cert/degree signal at all) is
# almost always a continuation/address line following a real certification
# entry, not a certification in its own right.
_ADDRESS_LIKE_RE = re.compile(
    r'^(?:[A-Z][\w&.\']*\s*){1,5},\s*[A-Z][a-zA-Z]+(?:,\s*[A-Z][a-zA-Z]+)*\.?$'
)

# Lines that look like section headings mid-text (short, all-caps or title-case)
_HEADING_LIKE_RE = re.compile(
    r'^\s*[A-Z][A-Z\s&/]{3,40}[A-Z]\s*[:\-]?\s*$'
)

# Continuation line indicators (line is part of previous cert, not new one)
_CONTINUATION_WORDS = re.compile(
    r'^\s*(?:professional|associate|foundation|'
    r'practitioner|architect|developer|analyst|expert|specialist|'
    r'fundamentals|level\s+\d+|advanced|intermediate|basic|'
    r'track|series|bootcamp|workshop|training|course|program)\b',
    re.IGNORECASE,
)

# Stripped bare "designation" and "program" to eliminate prose sentence leaks
_CERT_SIGNAL = re.compile(
    r'\b(certif(?:ied|icate|ication)|diploma|accreditation|'
    r'credential|licence|license|fellowship|assessment|badge)\b',
    re.IGNORECASE
)

# Let weak signals catch program structures when paired tightly with clinical contexts
_WEAK_CERT_SIGNAL = re.compile(
    r'\b(pmp|csm|aws|gcp|azure|cissp|ceh|ccna|ccnp|itil|prince2|'
    r'scrum|agile|six\s+sigma|lean|iso|iec|sas|spss|tableau|'
    r'google|microsoft|oracle|cisco|comptia|redhat|ibm|salesforce|'
    r'clinical\s+research|gcp\b)',
    re.IGNORECASE
)

# Deny list — lines that mention certs but are clearly job responsibilities
_RESPONSIBILITY_VERBS = re.compile(
    r'^\s*(?:responsible|managed?|performed?|developed?|created?|reviewed?|'
    r'led|supported?|coordinated?|implemented?|analysed?|analyzed?|worked?\s+on|'
    r'handled?|checked?|monitored?|maintained?|prepared?|ensured?|conducted?)\b',
    re.IGNORECASE,
)

# Same verbs, but matched anywhere in the line (not just at the start) — used
# to catch sentence-style job-description lines in the whole-document scan.
RESPONSIBILITY_VERBS_INLINE = re.compile(
    r'\b(?:responsible\s+for|managed?|performed?|generated?|developed?|created?|'
    r'reviewed?|led|supported?|coordinated?|implemented?|analysed?|analyzed?|'
    r'worked?\s+on|handled?|checked?|monitored?|maintained?|prepared?|ensured?|'
    r'conducted?)\b',
    re.IGNORECASE,
)


# ─── State machine ────────────────────────────────────────────────────────────

class _State:
    OUTSIDE   = "OUTSIDE"
    IN_CERT   = "IN_CERT"
    IN_SECTION = "IN_SECTION"


def _clean_line(line: str) -> str:
    """Strip bullets, leading symbols, and trailing punctuation."""
    line = _BULLET_RE.sub("", line)
    line = re.sub(r'^[\s\d]+[\.\)]\s+', '', line)  # numbered lists
    line = re.sub(r'^\s*\d{1,4}\s*\|\s*', '', line)  # stray index/page number before a pipe
    return line.strip(" .,-:;|")


def _extract_year(text: str) -> str:
    m = _YEAR_RE.search(text)
    return m.group(1) if m else ""


# Words that show up in the certification-name half of a line and must
# never be mistaken for part of the issuing organization (this is what
# previously produced garbage orgs like "Certification GCP National
# Institute" or "Role Certification Castor Academy" -- those came from
# scanning capitalized words across the *entire* line rather than
# respecting the name/org boundary).
_ORG_STOPWORDS = {
    "certification", "certificate", "certified", "diploma", "training",
    "course", "program", "programme", "level", "role", "module",
    "accreditation", "credential", "license", "licence", "fellowship",
    "badge", "assessment",
}
_ORG_DASH_RE = re.compile(r'\s*[—–]\s*')
_ORG_COMMA_RE = re.compile(r',\s*')


def _split_first(pattern: "re.Pattern", text: str) -> Optional[tuple]:
    m = pattern.search(text)
    if not m:
        return None
    return text[:m.start()].strip(), text[m.end():].strip()


def _extract_org(text: str) -> str:
    """
    Certification name and issuing org are almost always separated by a
    structural marker -- an em/en-dash ("Cert Name — Org") or a comma
    ("Cert Name (Certification), Org"). Split on the FIRST such marker and
    treat everything after it as the org candidate, rather than scanning
    capitalized words across the whole line (which pulled in unrelated
    words from the certification-name half, like "Certification" or
    "Role").
    """
    rest = None
    split = _split_first(_ORG_DASH_RE, text)
    if split:
        rest = split[1]
    else:
        split = _split_first(_ORG_COMMA_RE, text)
        if split:
            rest = split[1]

    if rest:
        rest_clean = rest.strip(" .,;:")
        words_lower = {w.lower().strip('(),.:;') for w in rest_clean.split()}
        if rest_clean and not (words_lower & _ORG_STOPWORDS) and 2 < len(rest_clean) < 160:
            return rest_clean

    # Fallback: explicit "issued by X" / "from X" phrase anywhere in the line.
    m = re.search(
        r'\b(?:issued?\s+by|certified?\s+by|from|by)\s+([A-Z][A-Za-z\s\.&,]+)',
        text, re.IGNORECASE
    )
    if m:
        org = m.group(1).strip().strip(".,;:")
        if 2 < len(org) < 60:
            return org

    return ""


def _strip_org_from_name(name: str, org: str) -> str:
    """If `org` was extracted from the tail of `name` (via the same dash/comma
    split _extract_org uses), remove that tail from the name. Without this,
    the name keeps the full original text -- including the org half -- and
    whatever formats "{name} - {org}" downstream ends up duplicating the org,
    e.g. "Jaipur National University, Jaipur - Jaipur"."""
    if not org:
        return name
    stripped = name.rstrip(" .,;:")
    org_clean = org.strip(" .,;:")
    if org_clean and stripped.endswith(org_clean):
        stripped = stripped[: -len(org_clean)]
        stripped = re.sub(r'[\s,\-\u2013\u2014]+$', '', stripped)
        return stripped
    return name


def _remove_year_and_org_phrases(text: str) -> str:
    """Strip year and org-attribution phrases from a cert name."""
    text = _YEAR_RE.sub("", text)
    text = re.sub(
        r'\s*[-–—|]\s*(?:issued?\s+by|from|by)\s+.+$', "", text, flags=re.IGNORECASE
    )
    text = re.sub(r'\s*\(\s*\)', "", text)
    return re.sub(r'\s+', ' ', text).strip(" .,-:;|")


# Bare repeats of the section header itself (no cert name attached) --
# common when OCR/layout duplicates a heading mid-list, e.g. a stray
# "CERTIFICATION" line sitting after the real entries. These satisfy
# _CERT_SIGNAL trivially (they ARE the signal word) but carry no actual
# certification content, so they must be rejected before that check.
_BARE_HEADER_RE = re.compile(
    r'^\s*(?:certifications?|certificates?|credentials?|licenses?|accreditations?)\s*$',
    re.IGNORECASE,
)


def _is_cert_line(line: str) -> bool:
    """Determine if a cleaned line looks like a certification entry."""
    if len(line) < 5 or len(line) > 300:
        return False
    if _BARE_HEADER_RE.match(line):
        return False
    if _NOISE_RE.match(line):
        return False
    if _RESPONSIBILITY_VERBS.match(line):
        return False
    # A "Label: comma, list" shape is Skills/Tools content, not a named
    # certification -- reject outright regardless of any cert-signal word
    # matching elsewhere in the line.
    if _SKILL_LIST_LABEL_RE.match(line):
        return False
    has_strong = bool(_CERT_SIGNAL.search(line))
    if has_strong:
        # Even a strong signal doesn't save a bare address/continuation
        # line like "SaSTAT Organization, Ahmedabad, Gujarat" -- but such
        # lines never actually contain "certification"/"diploma"/etc, so
        # this only filters the rare case where a strong-signal line is
        # otherwise indistinguishable from a location list.
        if _ADDRESS_LIKE_RE.match(line) and not _CERT_SIGNAL.search(line.split(',')[0]):
            return False
        return True
    if _WEAK_CERT_SIGNAL.search(line):
        # A weak (vendor-name-only) signal is only trustworthy when the line
        # reads like a single title, not a comma-separated tool/skill
        # enumeration -- "Oracle Clinical, EDC, InForm" and "SAS 9.4
        # (SAS/BASE, SAS/SQL, SAS/Macros, SAS/ODS)" both matched here
        # before, purely because a vendor name ("Oracle"/"SAS") appears.
        # Two or more commas anywhere in the line (list items, whether or
        # not inside parentheses) is a reliable enough signal of a list.
        if line.count(',') >= 2:
            return False
        if _DENSE_LIST_RE.match(line):
            return False
        if _ADDRESS_LIKE_RE.match(line):
            return False
        return True
    return False


def _is_continuation(line: str) -> bool:
    """Return True if this line looks like the second line of a multi-line
    cert (e.g. a lone "Professional" or "- Associate" tier fragment after
    "AWS Certified Solutions Architect"), as opposed to an independent cert
    title that happens to start with the same word ("Basic of Clinical
    Research Certification", "Advanced SAS Programming Certificate").
    Genuine continuation fragments are short and don't restate a strong
    cert-signal word themselves; independent titles usually do both."""
    if not _CONTINUATION_WORDS.match(line):
        return False
    if len(line.split()) > 4 or _CERT_SIGNAL.search(line):
        return False
    return True


def _fingerprint(cert: str) -> str:
    """Normalized key for deduplication."""
    return re.sub(r'[^a-z0-9]', '', cert.lower())


# ─── Main extraction function ─────────────────────────────────────────────────

def extract_certifications(text: str) -> List[Dict[str, str]]:
    """
    Extract certifications from normalized resume text.

    Args:
        text: Full normalized resume text (may contain multiple sections).

    Returns:
        List of dicts: [{"Certification": ..., "Issuing_Organization": ..., "Year": ...}]
    """
    lines = [l.rstrip() for l in text.splitlines()]
    results: List[Dict[str, str]] = []
    seen: set = set()

    # ── Pass 1: Extract from the dedicated certification section ──────────────
    state = _State.OUTSIDE
    section_lines: List[str] = []
    section_line_indices: set = set()

    for i, line in enumerate(lines):
        stripped = line.strip()

        if state == _State.OUTSIDE:
            if _CERT_SECTION_START.match(stripped):
                state = _State.IN_SECTION
            continue

        if state == _State.IN_SECTION:
            if _CERT_SECTION_STOP.match(stripped) and stripped:
                break
            if stripped:
                section_lines.append(stripped)
                section_line_indices.add(i)

    # Parse collected section lines with the state machine
    _parse_cert_lines(section_lines, results, seen)

    # ── Pass 2: Scan entire text for inline cert mentions (e.g. in summary) ──
    # Only add if not already found in Pass 1. Lines already consumed by the
    # dedicated-section parse above are skipped entirely here -- rescanning
    # them let a continuation-merged entry ("AWS Certified Solutions
    # Architect Professional") reappear as a separate partial duplicate
    # ("AWS Certified Solutions Architect"), since the two have different
    # dedup fingerprints despite being the same certification.
    for i, line in enumerate(lines):
        if i in section_line_indices:
            continue
        stripped = line.strip()
        if not stripped:
            continue
        # Skip if this line is inside what we already parsed
        cleaned = _clean_line(stripped)
        if not cleaned or not _is_cert_line(cleaned):
            continue
        # Outside a dedicated Certifications section, a weak (vendor-name-
        # only) signal is far too easy to trip on ordinary Skills/Summary/
        # Experience prose ("Oracle Clinical, EDC, InForm", "Microsoft
        # Office Suite"). Require an explicit certification/diploma/etc word
        # for anything picked up by this whole-document scan.
        if not _CERT_SIGNAL.search(cleaned):
            continue
        # A line with several words and a responsibility verb anywhere in it
        # (not just at the start) is a job-description sentence, even if it
        # happens to mention a tool/skill that weakly resembles a cert name.
        if len(cleaned.split()) > 6 and RESPONSIBILITY_VERBS_INLINE.search(cleaned):
            continue
        # Weak signals (tool/vendor names like "SAS", "AWS") are only
        # trustworthy as a certification mention on short, title-like lines.
        if not _CERT_SIGNAL.search(cleaned) and _WEAK_CERT_SIGNAL.search(cleaned) and len(cleaned.split()) > 8:
            continue
        name = _remove_year_and_org_phrases(cleaned)
        year = _extract_year(cleaned)
        org  = _extract_org(cleaned)
        name = _strip_org_from_name(name, org)
        if not name or len(name) < 5:
            continue
        fp = _fingerprint(name)
        if fp not in seen:
            results.append({
                "Certification":       name,
                "Issuing_Organization": org,
                "Year":                year,
            })
            seen.add(fp)

    return results


def _parse_cert_lines(
    lines: List[str],
    results: List[Dict[str, str]],
    seen: set,
) -> None:
    """
    State machine parser for a block of certification section lines.
    Handles multi-line cert names and org/year on separate lines.
    """
    state        = _State.OUTSIDE
    current_name = ""
    current_org  = ""
    current_year = ""

    def flush():
        nonlocal current_name, current_org, current_year
        name = _remove_year_and_org_phrases(current_name).strip()
        name = _strip_org_from_name(name, current_org.strip())
        if name and len(name) >= 5:
            fp = _fingerprint(name)
            if fp not in seen:
                results.append({
                    "Certification":        name,
                    "Issuing_Organization": current_org.strip(),
                    "Year":                 current_year.strip(),
                })
                seen.add(fp)
        current_name = ""
        current_org  = ""
        current_year = ""

    for line in lines:
        cleaned = _clean_line(line)
        if not cleaned:
            continue
        if _NOISE_RE.match(cleaned):
            continue

        year = _extract_year(cleaned)
        org  = _extract_org(cleaned)

        if state == _State.OUTSIDE:
            if _is_cert_line(cleaned):
                state        = _State.IN_CERT
                current_name = cleaned
                current_year = year
                current_org  = org
            # else: skip non-cert lines outside a cert entry

        elif state == _State.IN_CERT:
            # Check if this is the start of a NEW cert entry
            if _is_cert_line(cleaned) and not _is_continuation(cleaned):
                flush()
                current_name = cleaned
                current_year = year
                current_org  = org
                state        = _State.IN_CERT
            # Check if this is a continuation of the current cert name
            elif _is_continuation(cleaned):
                current_name += " " + cleaned
                if not current_year and year:
                    current_year = year
                if not current_org and org:
                    current_org = org
            # Check if this line is just a year (standalone date line)
            elif re.fullmatch(r'\s*\d{4}\s*', cleaned):
                if not current_year:
                    current_year = cleaned.strip()
            # Check if this line looks like an org attribution
            elif _ORG_INDICATORS.search(cleaned) or _ORG_SUFFIX_RE.search(cleaned):
                if not current_org:
                    # This whole line IS the org (e.g. "SAS Institute Inc.,
                    # USA" on its own line) -- use it directly rather than
                    # running _extract_org's name/org-split logic on it,
                    # which assumes a "cert name, org" shape that doesn't
                    # apply to a standalone org/address line and previously
                    # threw away everything but the last fragment ("USA").
                    current_org = cleaned
            # Otherwise this is a non-cert line — flush current and go outside
            else:
                flush()
                state = _State.OUTSIDE

    # Flush any remaining entry
    if state == _State.IN_CERT:
        flush()