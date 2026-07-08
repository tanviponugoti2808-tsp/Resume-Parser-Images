# generate_training_labels.py
import json
import re
import openpyxl
from pathlib import Path

EXCEL_FILE = Path("dataset/consolidated_resumes.xlsx")
TEXT_DIR = Path("dataset/normalized_text")
OUTPUT_FILE = Path("dataset/ner_training_data.jsonl")


def find_span(text: str, value: str):
    """Find character start/end of value in text (case-insensitive, first match)."""
    if not value or not str(value).strip():
        return None
    value = str(value).strip()
    idx = text.lower().find(value.lower())
    if idx == -1:
        return None
    return (idx, idx + len(value))


def remove_overlaps(entities):
    """Keep longest non-overlapping spans, sorted by start position."""
    entities = sorted(entities, key=lambda e: (e[0], -(e[1] - e[0])))
    result = []
    last_end = -1
    for start, end, label in entities:
        if start >= last_end:
            result.append((start, end, label))
            last_end = end
    return result


def load_excel_data():
    wb = openpyxl.load_workbook(EXCEL_FILE, data_only=True)

    candidates = {}
    ws = wb["Candidates"]
    headers = [c.value for c in ws[1]]
    for row in ws.iter_rows(min_row=2, values_only=True):
        rec = dict(zip(headers, row))
        file_name = rec.get("File Name")
        if file_name:
            candidates[file_name] = rec

    education = {}
    ws = wb["Education"]
    headers = [c.value for c in ws[1]]
    for row in ws.iter_rows(min_row=2, values_only=True):
        rec = dict(zip(headers, row))
        fn = rec.get("File Name")
        if fn:
            education.setdefault(fn, []).append(rec)

    experience = {}
    ws = wb["Experience"]
    headers = [c.value for c in ws[1]]
    for row in ws.iter_rows(min_row=2, values_only=True):
        rec = dict(zip(headers, row))
        fn = rec.get("File Name")
        if fn:
            experience.setdefault(fn, []).append(rec)

    certificates = {}
    ws = wb["Certificates"]
    headers = [c.value for c in ws[1]]
    for row in ws.iter_rows(min_row=2, values_only=True):
        rec = dict(zip(headers, row))
        fn = rec.get("File Name")
        if fn:
            certificates.setdefault(fn, []).append(rec)

    return candidates, education, experience, certificates


def build_examples():
    candidates, education, experience, certificates = load_excel_data()

    examples = []
    skipped_no_text = []
    total_entities = 0

    for file_name, cand in candidates.items():
        # file_name is like "Amit Resume.png" -> resume_name is "Amit Resume"
        resume_name = Path(file_name).stem
        text_file = TEXT_DIR / f"{resume_name}.txt"

        if not text_file.exists():
            skipped_no_text.append(resume_name)
            continue

        text = text_file.read_text(encoding="utf-8")
        entities = []

        # --- Candidate-level scalar fields ---
        field_label_map = [
            ("Name", "NAME"),
            ("Email", "EMAIL"),
            ("Phone", "PHONE"),
            ("Location", "LOCATION"),
        ]
        for field, label in field_label_map:
            span = find_span(text, cand.get(field))
            if span:
                entities.append((span[0], span[1], label))

        # --- Skills (semicolon-separated string) ---
        skills_raw = cand.get("Skills") or ""
        for skill in skills_raw.split(";"):
            skill = skill.strip()
            span = find_span(text, skill)
            if span:
                entities.append((span[0], span[1], "SKILL"))

        # --- Education rows ---
        for edu in education.get(file_name, []):
            for field, label in [
                ("Degree", "DEGREE"),
                ("Institution", "ORG"),
                ("Start Year", "DATE"),
                ("End Year", "DATE"),
            ]:
                span = find_span(text, edu.get(field))
                if span:
                    entities.append((span[0], span[1], label))

        # --- Experience rows ---
        for exp in experience.get(file_name, []):
            for field, label in [
                ("Company", "ORG"),
                ("Designation", "TITLE"),
                ("Start Date", "DATE"),
                ("End Date", "DATE"),
            ]:
                span = find_span(text, exp.get(field))
                if span:
                    entities.append((span[0], span[1], label))

        # --- Certificates ---
        for cert in certificates.get(file_name, []):
            for field, label in [
                ("Certification", "CERTIFICATION"),
                ("Issuing Organization", "ORG"),
            ]:
                span = find_span(text, cert.get(field))
                if span:
                    entities.append((span[0], span[1], label))

        if entities:
            entities = remove_overlaps(entities)
            total_entities += len(entities)
            examples.append({"text": text, "entities": entities})

    OUTPUT_FILE.write_text(
        "\n".join(json.dumps(ex) for ex in examples),
        encoding="utf-8"
    )

    print(f"Generated {len(examples)} training examples -> {OUTPUT_FILE}")
    print(f"Total entity spans labeled: {total_entities}")
    if skipped_no_text:
        print(f"\nSkipped {len(skipped_no_text)} candidates (no matching normalized text file):")
        for name in skipped_no_text:
            print(f"  - {name}")


if __name__ == "__main__":
    build_examples()