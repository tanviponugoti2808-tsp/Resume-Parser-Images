import os

from ocr import extract_text
from layout import detect_layout, split_resume
from text_cleaner import clean_text


# =====================================
# Input / Output folders
# =====================================

processed_folder = "dataset/processed_no_blur"
output_folder = "dataset/extracted_text_no_blur"

os.makedirs(output_folder, exist_ok=True)

# =====================================
# TEST ONLY AMIT RESUME
# =====================================

resume_folder = os.path.join(
    processed_folder,
    "Amit Resume"
)

for root, dirs, files in os.walk(processed_folder):
    
    image_files = sorted(
        [
            f for f in files
            if f.lower().endswith((".png", ".jpg", ".jpeg"))
        ]
    )

    if len(image_files) == 0:
        continue

    resume_name = os.path.basename(root)

    output_path = os.path.join(
        output_folder,
        resume_name + ".txt"
    )

    print("\n========================================")
    print("Resume :", resume_name)
    print("========================================")

    all_text = ""

    for page in image_files:

        image_path = os.path.join(root, page)

        print("\nProcessing :", page)

        layout = detect_layout(image_path)

        print("Detected Layout :", layout)

        all_text += "\n"
        all_text += "=" * 60
        all_text += "\n"
        all_text += page
        all_text += "\n"
        all_text += "=" * 60
        all_text += "\n\n"

        # =====================================
        # SINGLE COLUMN
        # =====================================

        if layout == "single_column":

            print("Running OCR...")

            text = extract_text(image_path)

            text = clean_text(text)

            all_text += text
            all_text += "\n\n"

        # =====================================
        # TWO COLUMN
        # =====================================

        else:

            print("Splitting Resume...")

            left_path, right_path = split_resume(image_path)

            print("OCR Left Column...")

            left_text = extract_text(left_path)

            left_text = clean_text(left_text)

            print("OCR Right Column...")

            right_text = extract_text(right_path)

            right_text = clean_text(right_text)

            all_text += left_text
            all_text += "\n\n"
            all_text += right_text
            all_text += "\n\n"

    with open(
        output_path,
        "w",
        encoding="utf-8"
    ) as f:

        f.write(all_text)

    print("\nSaved ->", output_path)

print("\n========================================")
print("Finished Successfully!")
print("========================================")