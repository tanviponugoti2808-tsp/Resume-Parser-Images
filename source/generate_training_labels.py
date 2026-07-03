import json
import re
from pathlib import Path
 
TEXT_DIR  = Path("dataset/extracted_text_no_blur")
JSON_DIR  = Path("dataset/output_json")
OUT_DIR   = Path("dataset/ner_training_data")
OUT_DIR.mkdir(parents=True, exist_ok=True)
 
# Tag set — every field type we want the model to eventually recognize
TAG_TYPES = [
    "NAME", "EMAIL", "PHONE",
    "COMPANY", "DESIGNATION", "DATE",
    "DEGREE", "COLLEGE", "UNIVERSITY",
    "SKILL", "LANGUAGE", "CERTIFICATION",
]
 
 
def tokenize(text: str):
    """
    Simple whitespace + punctuation-aware tokenizer.
    Keeps emails and dates intact as much as possible.
    """
    # Split on whitespace, but keep punctuation attached where it matters (emails, dates)
    raw_tokens = re.findall(r"\S+", text)
    return raw_tokens
 
 
def find_token_span(tokens, value: str):
    """
    Find the start/end token index where `value` appears in `tokens`.
    Returns (start_idx, end_idx) inclusive, or None if not found.
 
    Matches case-insensitively and tolerates minor whitespace differences.
    """
    if not value or not value.strip():
        return None
 
    value_tokens = tokenize(value.strip())
    if not value_tokens:
        return None
 
    value_norm = [t.lower().strip(".,;:") for t in value_tokens]
    n = len(value_norm)
 
    for i in range(len(tokens) - n + 1):
        window = [t.lower().strip(".,;:") for t in tokens[i:i + n]]
        if window == value_norm:
            return (i, i + n - 1)
 
    # Fallback: try matching just the first token of multi-word values
    # (helps when OCR garbled a middle word)
    if n > 1:
        first_word = value_norm[0]
        for i, t in enumerate(tokens):
            if t.lower().strip(".,;:") == first_word:
                # Confirm at least 50% of remaining words match nearby
                window = [tt.lower().strip(".,;:") for tt in tokens[i:i + n]]
                matches = sum(1 for a, b in zip(window, value_norm) if a == b)
                if matches >= max(1, n // 2):
                    return (i, i + n - 1)
 
    return None
 
 
def apply_bio_tags(tags: list, span, tag_type: str):
    """Apply B-/I- tags over a token span, without overwriting existing tags."""
    if span is None:
        return
    start, end = span
    for idx in range(start, min(end + 1, len(tags))):
        if tags[idx] != "O":
            continue  # don't overwrite a tag already assigned (avoid overlaps)
        tags[idx] = f"B-{tag_type}" if idx == start else f"I-{tag_type}"
 
 
def label_resume(text: str, parsed: dict):
    tokens = tokenize(text)
    tags = ["O"] * len(tokens)
 
    # ── Header fields ──────────────────────────────────────────────
    apply_bio_tags(tags, find_token_span(tokens, parsed.get("name", "")), "NAME")
    apply_bio_tags(tags, find_token_span(tokens, parsed.get("email", "")), "EMAIL")
    apply_bio_tags(tags, find_token_span(tokens, parsed.get("phone", "")), "PHONE")
 
    # ── Skills ──────────────────────────────────────────────────────
    skills = parsed.get("skills", {})
    skill_list = skills.get("all", []) if isinstance(skills, dict) else []
    for skill in skill_list:
        apply_bio_tags(tags, find_token_span(tokens, skill), "SKILL")
 
    # ── Experience ──────────────────────────────────────────────────
    for job in parsed.get("experience", []):
        apply_bio_tags(tags, find_token_span(tokens, job.get("company", "")), "COMPANY")
        apply_bio_tags(tags, find_token_span(tokens, job.get("designation", "")), "DESIGNATION")
        apply_bio_tags(tags, find_token_span(tokens, job.get("duration", "")), "DATE")
 
    # ── Education ──────────────────────────────────────────────────
    for edu in parsed.get("education", []):
        apply_bio_tags(tags, find_token_span(tokens, edu.get("degree", "")), "DEGREE")
        apply_bio_tags(tags, find_token_span(tokens, edu.get("college", "")), "COLLEGE")
        apply_bio_tags(tags, find_token_span(tokens, edu.get("university", "")), "UNIVERSITY")
 
    # ── Languages ──────────────────────────────────────────────────
    for lang in parsed.get("languages", []):
        apply_bio_tags(tags, find_token_span(tokens, lang), "LANGUAGE")
 
    # ── Certifications ────────────────────────────────────────────
    for cert in parsed.get("certifications", []):
        apply_bio_tags(tags, find_token_span(tokens, cert), "CERTIFICATION")
 
    return tokens, tags
 
 
def main():
    text_files = sorted(TEXT_DIR.glob("*.txt"))
    print(f"Found {len(text_files)} text files.\n")
 
    total_tagged_tokens = 0
    total_tokens = 0
    success = 0
 
    for text_file in text_files:
        resume_name = text_file.stem
        json_file = JSON_DIR / f"{resume_name}.json"
 
        if not json_file.exists():
            print(f"  [SKIP] No JSON found for {resume_name}")
            continue
 
        text = text_file.read_text(encoding="utf-8")
        parsed = json.loads(json_file.read_text(encoding="utf-8"))
 
        tokens, tags = label_resume(text, parsed)
 
        tagged_count = sum(1 for t in tags if t != "O")
        total_tagged_tokens += tagged_count
        total_tokens += len(tokens)
 
        coverage = (tagged_count / len(tokens) * 100) if tokens else 0
 
        out_path = OUT_DIR / f"{resume_name}.jsonl"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(json.dumps({"tokens": tokens, "tags": tags}, ensure_ascii=False))
 
        print(f"  [{resume_name}] {len(tokens)} tokens, {tagged_count} tagged ({coverage:.1f}% coverage)")
        success += 1
 
    print(f"\nDone. {success}/{len(text_files)} resumes labeled.")
    overall_coverage = (total_tagged_tokens / total_tokens * 100) if total_tokens else 0
    print(f"Overall label coverage: {overall_coverage:.1f}% of tokens tagged")
    print(f"\nOutput saved to: {OUT_DIR}/")
    print("Next step: review a sample of these .jsonl files for correctness before training.")
 
 
if __name__ == "__main__":
    main()