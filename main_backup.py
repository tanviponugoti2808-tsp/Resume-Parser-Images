import argparse
import json
from pathlib import Path
import re


from preprocess import preprocess_resume
from text_cleaner import clean_text
from ocr_columnaware import ocr_page
from normalize import normalize_resume
from parser.header_parser import extract_email, extract_phone
from parser.name_parser import extract_name
from parser.experience_parser import extract_experience_details, extract_summary
from parser.overall_experience import extract_overall_experience
from parser.education_parser import extract_education
from parser.certification_parser import extract_certifications
from parser.skill_parser import extract_skills
from parser.summary_parser import extract_summary

from excel import build_workbook

# -----------------------------
# Paths
# -----------------------------
DATASET_DIR = Path("dataset/images")
OUTPUT_DIR = Path("dataset/output_json_normalized")
TEXT_DIR = Path("dataset/extracted_text_no_blur")
NEW_RESUMES_DIR = Path("dataset/new_resumes")
#NORMALIZED_DIR = Path("dataset/normalized_text")
NORMALIZED_DIR = Path("dataset/new_normalized_text")
PROCESSED_DIR = Path("dataset/processed_no_blur")
#EXCEL_FILE = Path("dataset/consolidated_resumes.xlsx")
EXCEL_FILE = Path("dataset/new_resumes.xlsx")  # <-- NEW

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEXT_DIR.mkdir(parents=True, exist_ok=True)
NEW_RESUMES_DIR.mkdir(parents=True, exist_ok=True)
NORMALIZED_DIR.mkdir(parents=True, exist_ok=True)
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

USE_NORMALIZATION = True

# -----------------------------
# Resume JSON Template
# -----------------------------
def create_resume_template():
    return {
        "file_name": "",
        "name": "",
        "email": "",
        "phone": "",
        "linkedin": "",
        "location": "",
        "overall_experience": "",
        "summary": "",
        "education": [],
        "experience": [],
        "skills": [],
        "certificates": [],
        "languages": [],
        "projects": [],
        "achievements": []
    }

def fix_icon_contaminated_email(text: str) -> str:
    """Remove OCR garbage introduced by contact icons."""

    # Remove short garbage before an email
    text = re.sub(
        r'\b[a-zA-Z]{1,4}\s+(?=[A-Za-z0-9._%+-]*@)',
        '',
        text
    )

    # Repair common domain corruptions
    text = re.sub(
        r'@email[t1i]?com',
        '@gmail.com',
        text,
        flags=re.IGNORECASE
    )

    text = re.sub(
        r'@gmailc?om\b',
        '@gmail.com',
        text,
        flags=re.IGNORECASE
    )

    return text

def fix_broken_contact_lines(text: str):
    # -----------------------------------------
    # Remove OCR icon contamination first
    # -----------------------------------------
    text = fix_icon_contaminated_email(text)

    lines = text.splitlines()
    fixed_lines = []
    i = 0

    while i < len(lines):
        line = lines[i].strip()

        # --------------------------------------------------
        # Case 1: Broken email
        # Example:
        # b
        # armoriaarun1998
        # gmail.com
        # ->
        # armoriaarun1998@gmail.com
        # --------------------------------------------------
        if 1 <= len(line) <= 3 and line.isalpha():

            lookahead = lines[i:i + 6]
            joined = "".join(l.strip() for l in lookahead)

            if re.search(
                r'(gmail|yahoo|hotmail|outlook|icloud)\.com',
                joined,
                re.IGNORECASE,
            ):

                merged = ""
                consumed = 0

                for l in lookahead:
                    merged += l.strip()
                    consumed += 1

                    if re.search(
                        r'(gmail|yahoo|hotmail|outlook|icloud)\.com',
                        merged,
                        re.IGNORECASE,
                    ):
                        break

                domain_match = re.search(
                    r'(gmail|yahoo|hotmail|outlook|icloud)\.com',
                    merged,
                    re.IGNORECASE,
                )

                if domain_match and "@" not in merged:
                    split_point = domain_match.start()
                    merged = (
                        merged[:split_point]
                        + "@"
                        + merged[split_point:]
                    )

                # Final cleanup in case icon garbage still exists
                merged = fix_icon_contaminated_email(merged)

                fixed_lines.append(merged)
                i += consumed
                continue

        # --- Case 2: Broken phone number (e.g. "96" / "25069509" split across lines) ---
        if re.fullmatch(r'[\d\-\s]{1,5}', line) and any(c.isdigit() for c in line):
            lookahead = lines[i:i+4]
            digit_fragments = []
            consumed = 0

            for l in lookahead:
                stripped = l.strip()
                # Stop if we hit a clearly non-numeric line (new field starting)
                if stripped and not re.fullmatch(r'[\d\-\s]+', stripped):
                    break
                if stripped:
                    digit_fragments.append(re.sub(r'\D', '', stripped))
                consumed += 1

            merged_digits = "".join(digit_fragments)

            # Only treat as a phone number if it lands in a sane length range
            if 10 <= len(merged_digits) <= 13:
                fixed_lines.append(merged_digits)
                i += consumed
                continue

        # --- Case 3: Stray single icon-adjacent characters that are neither ---
        # (e.g. a lone "%", "S", "O" left over from a misread icon glyph)
        if line in ("%", "S", "O", "#", "*", "«", "=", "@") :
            i += 1
            continue

        fixed_lines.append(line)
        i += 1

    return "\n".join(fixed_lines)


# -----------------------------
# Process One Resume Folder
# -----------------------------
def process_resume(resume_folder: Path):

    resume_name = resume_folder.name

    # txt_file = TEXT_DIR / f"{resume_name}.txt"

    # if txt_file.exists():
    #     print(f"[SKIP] OCR already exists for {resume_name}")
    #     return None

    pages = sorted(resume_folder.glob("*.png"))
    pages += sorted(resume_folder.glob("*.jpg"))
    pages += sorted(resume_folder.glob("*.jpeg"))

    pages = sorted(
        pages,
        key=lambda p: int("".join(filter(str.isdigit, p.stem)) or "0")
    )

    if not pages:
        print(f"[SKIP] No images found in {resume_name}")
        return None

    processed_pages = []

    # -----------------------------
    # Preprocess Images
    # -----------------------------
    for page in pages:

        output_img = PROCESSED_DIR / resume_name / page.name
        output_img.parent.mkdir(parents=True, exist_ok=True)

        preprocess_resume(
            str(page),
            str(output_img)
        )

        processed_pages.append(output_img)

    # -----------------------------
    # OCR
    # -----------------------------
    all_text = []

    from layout import detect_layout, split_resume

    for page in processed_pages:

        layout = detect_layout(str(page))

        print(f"\nLayout Detected : {layout}")

        if layout == "single_column":

            text = ocr_page(str(page))

        else:

            left, right = split_resume(str(page))

            left_text = ocr_page(left)

            right_text = ocr_page(right)

            text = left_text + "\n\n" + right_text

        all_text.append(text)

    cleaned_text = clean_text("\n\n".join(all_text))
    cleaned_text = fix_broken_contact_lines(cleaned_text)
    cleaned_text = fix_icon_contaminated_email(cleaned_text)  
    
    # -----------------------------
    # Save OCR Text
    # -----------------------------
    txt_file = TEXT_DIR / f"{resume_name}.txt"
    txt_file.write_text(cleaned_text, encoding="utf-8")

    

    NORMALIZED_FILE = NORMALIZED_DIR / f"{resume_name}.txt"

    if USE_NORMALIZATION:

        if NORMALIZED_FILE.exists():

            print("Using cached normalized text...")

            normalized_text = NORMALIZED_FILE.read_text(
                encoding="utf-8"
            )

        else:

            print("Running Qwen...")

            normalized_text = normalize_resume(cleaned_text)

            NORMALIZED_FILE.write_text(
                normalized_text,
                encoding="utf-8"
            )

    else:

        print("Skipping Qwen normalization...")

        normalized_text = cleaned_text

    # Save raw OCR
    with open("debug_ocr.txt", "w", encoding="utf-8") as f:
        f.write(cleaned_text)

    # Save normalized OCR
    with open("debug_normalized.txt", "w", encoding="utf-8") as f:
        f.write(normalized_text)
    

    # -----------------------------
    # Save OCR Text
    # -----------------------------
    txt_file = TEXT_DIR / f"{resume_name}.txt"

    txt_file.write_text(
        cleaned_text,
        encoding="utf-8"
    )

   

    # -----------------------------
    # Build Resume JSON
    # -----------------------------
    resume = create_resume_template()

    resume["file_name"] = resume_name + ".png"

    resume["name"] = extract_name(
    normalized_text,
    resume_name
    ).get("name", "")

    resume["email"] = extract_email(normalized_text)

    resume["phone"] = extract_phone(normalized_text)

    resume["experience"] = extract_experience_details(
        normalized_text
    )

    resume["education"] = extract_education(
        normalized_text
    )

    resume["certificates"] = extract_certifications(
        normalized_text
    )

    resume["skills"] = extract_skills(
        normalized_text
    )

    resume["overall_experience"] = extract_overall_experience(
        normalized_text,
        resume["experience"]
    )

    try:
        from enhancer import ResumeDataEnhancer
        enhancer = ResumeDataEnhancer()
        resume = enhancer.enhance(resume)
        
        # Print what was fixed (for debugging)
        if enhancer.fixes_applied:
            print(f"\n   Data enhanced: {enhancer.fixes_applied}")
    except Exception as e:
        print(f"   Enhancement skipped: {e}")
    print("\n========== EXPERIENCE PARSED ==========")

    for exp in resume["experience"]:
        print(exp)

    print("=======================================\n")

    # -----------------------------
    # Future Fields
    # -----------------------------
    resume["summary"] = extract_summary(normalized_text)

    resume["languages"] = []

    resume["projects"] = []

    resume["achievements"] = []

    resume["linkedin"] = ""

    resume["location"] = ""

    # -----------------------------
    # Save JSON
    # -----------------------------
    json_file = OUTPUT_DIR / f"{resume_name}.json"

    json_file.write_text(

        json.dumps(
            resume,
            indent=4,
            ensure_ascii=False
        ),

        encoding="utf-8"

    )

    print(
        f"Done -> Name: {resume['name']} | Email: {resume['email']} | Skills: {len(resume['skills'])}"
    )

    return resume



# -----------------------------
# Main
# -----------------------------
def main():

    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--resume",
        help="Process a single resume folder"
    )

    args = parser.parse_args()

    if args.resume:

        folders = [DATASET_DIR / args.resume]

    else:

        normalized_names = {
        txt.stem for txt in NORMALIZED_DIR.glob("*.txt")
        }

        folders = sorted(
            folder
            for folder in DATASET_DIR.iterdir()
            if folder.is_dir() and folder.name in normalized_names
        )

    print(
        f"\nStarting Offline Engine Processing on {len(folders)} folders...\n"
    )

    success = 0
    results = []  # <-- NEW: collect every parsed resume dict

    for folder in folders:

        if not folder.exists():

            continue

        print(f"[{folder.name}]")

        try:

            result = process_resume(folder)

            if result:

                success += 1
                results.append(result)  # <-- NEW

        except Exception as e:

            print(f"\nCRITICAL ERROR : {e}")

            import traceback

            traceback.print_exc()

    print(
        f"\nCompleted run. {success}/{len(folders)} resume structures finalized."
    )

    # -----------------------------
    # Consolidate everything into one Excel workbook
    # -----------------------------
    if results:
        final_results = results
        
        if EXCEL_FILE.exists():
            try:
                # Read the existing spreadsheet
                existing_df = pd.read_excel(EXCEL_FILE)
                merged_data = {}
                
                # 1. Reconstruct old rows perfectly using the saved JSON column
                if "JSON" in existing_df.columns:
                    for _, row in existing_df.iterrows():
                        json_str = row.get("JSON")
                        if pd.notna(json_str):
                            try:
                                # Convert the string back into the EXACT original dictionary
                                old_rec = json.loads(str(json_str))
                                key = str(old_rec.get("file_name", "")).strip().lower()
                                if key:
                                    merged_data[key] = old_rec
                            except json.JSONDecodeError:
                                continue
                
                # 2. Merge the newly processed resume(s)
                for new_rec in results:
                    lookup_key = str(new_rec.get("file_name", "")).strip().lower()
                    if lookup_key in merged_data:
                        print(f"Targeting row boundary for {lookup_key}. Updating in-place...")
                    merged_data[lookup_key] = new_rec
                
                final_results = list(merged_data.values())
                print(f"Row mapping secure. Total database entries locked: {len(final_results)}")
                
            except Exception as e:
                print(f"Warning: Excel row protection fallback triggered ({e})")

        # 3. Let build_workbook do a fresh, single-format write every time
        build_workbook(final_results, str(EXCEL_FILE))
        print(f"Excel file safely synchronized: {EXCEL_FILE}")
    else:
        print("No resumes parsed successfully — skipping Excel export.")

if __name__ == "__main__":
    main()
