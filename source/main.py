import argparse
import json
from pathlib import Path

from preprocess import preprocess_resume
from text_cleaner import clean_text
from ocr_columnaware import ocr_page
from normalize import normalize_resume
from parser.header_parser import extract_email, extract_phone
from parser.name_parser import extract_name
from parser.experience_parser import extract_experience_details
from parser.overall_experience import extract_overall_experience
from parser.education_parser import extract_education
from parser.certification_parser import extract_certifications
from parser.skill_parser import extract_skills
from excel import build_workbook

# -----------------------------
# Paths
# -----------------------------
DATASET_DIR = Path("dataset/images")
OUTPUT_DIR = Path("dataset/output_json_normalized")
TEXT_DIR = Path("dataset/extracted_text_no_blur")
NORMALIZED_DIR = Path("dataset/normalized_text")
PROCESSED_DIR = Path("dataset/processed_no_blur")
EXCEL_FILE = Path("dataset/consolidated_resumes.xlsx")  # <-- NEW

OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
TEXT_DIR.mkdir(parents=True, exist_ok=True)
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


# -----------------------------
# Process One Resume Folder
# -----------------------------
def process_resume(resume_folder: Path):

    resume_name = resume_folder.name

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
        normalized_text,
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
    print("\n========== EXPERIENCE PARSED ==========")

    for exp in resume["experience"]:
        print(exp)

    print("=======================================\n")

    # -----------------------------
    # Future Fields
    # -----------------------------
    resume["summary"] = ""

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

        folders = sorted(
            folder
            for folder in DATASET_DIR.iterdir()
            if folder.is_dir()
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
        build_workbook(results, str(EXCEL_FILE))
        print(f"Excel file created: {EXCEL_FILE}")
    else:
        print("No resumes parsed successfully — skipping Excel export.")


if __name__ == "__main__":

    main()