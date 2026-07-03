import re

SECTION_HEADERS = [
    "SUMMARY",
    "OBJECTIVE",
    "CONTACT",
    "EDUCATION",
    "WORK EXPERIENCE",
    "EXPERIENCE",
    "TECHNICAL SKILLS",
    "SKILLS",
    "CERTIFICATION",
    "CERTIFICATIONS",
    "PROJECTS",
    "LANGUAGES",
    "ACHIEVEMENTS"
]


def reconstruct_document(text: str):

    lines = [line.strip() for line in text.splitlines() if line.strip()]

    # -----------------------------
    # Locate probable name block
    # -----------------------------
    name_start = None

    for i in range(len(lines)):

        if (
            lines[i].isupper()
            and len(lines[i].split()) <= 2
            and not any(h in lines[i] for h in SECTION_HEADERS)
            and lines[i] not in ["PHONE", "EMAIL", "CONTACT"]
        ):
            name_start = i
            break

    if name_start is None:
        return "\n".join(lines)

    # -----------------------------
    # Collect header block
    # -----------------------------
    header = []

    i = name_start

    while i < len(lines):

        line = lines[i]

        if line.upper() == "SUMMARY":
            break

        header.append(line)

        i += 1

    # -----------------------------
    # Remaining document
    # -----------------------------
    remaining = lines[:name_start] + lines[i:]

    # -----------------------------
    # Move CONTACT under header
    # -----------------------------
    contact = []

    remaining2 = []

    in_contact = False

    for line in remaining:

        if line.upper() == "CONTACT":
            in_contact = True
            contact.append(line)
            continue

        if in_contact and line.upper() in SECTION_HEADERS:
            in_contact = False

        if in_contact:
            contact.append(line)
        else:
            remaining2.append(line)

    # -----------------------------
    # Final reconstructed order
    # -----------------------------
    final = []

    final.extend(header)

    final.append("")

    final.extend(contact)

    final.append("")

    final.extend(remaining2)

    return "\n".join(final)