import fitz  # PyMuPDF
import os
import shutil
from pathlib import Path

# ---- CONFIGURATION ----
TEXT_THRESHOLD = 50
OUTPUT_DIR = "converted_pages"
DPI = 300

# This must match main.py's DATASET_DIR so process_resume() can find the images
DATASET_DIR = Path("dataset/images")


def is_text_pdf(pdf_path: str) -> bool:
    doc = fitz.open(pdf_path)
    total_chars = 0
    page_count = len(doc)

    for page in doc:
        text = page.get_text().strip()
        total_chars += len(text)

    doc.close()

    avg_chars_per_page = total_chars / max(page_count, 1)
    return avg_chars_per_page >= TEXT_THRESHOLD


def convert_pdf_to_images(pdf_path: str, output_dir: str = OUTPUT_DIR) -> list:
    os.makedirs(output_dir, exist_ok=True)

    doc = fitz.open(pdf_path)
    pdf_name = Path(pdf_path).stem
    image_paths = []

    zoom = DPI / 72
    mat = fitz.Matrix(zoom, zoom)

    for page_num, page in enumerate(doc, start=1):
        pix = page.get_pixmap(matrix=mat)
        image_path = os.path.join(output_dir, f"{pdf_name}_page{page_num}.png")
        pix.save(image_path)
        image_paths.append(image_path)
        print(f"  Saved: {image_path}")

    doc.close()
    return image_paths


def route_input(file_path: str):
    ext = Path(file_path).suffix.lower()

    if not os.path.exists(file_path):
        return {"action": "error", "files": None, "reason": f"File not found: {file_path}"}

    if ext in [".png", ".jpg", ".jpeg"]:
        return {
            "action": "send_to_pipeline",
            "files": [file_path],
            "reason": "Input is already an image. Sending directly to pipeline."
        }

    if ext == ".pdf":
        if is_text_pdf(file_path):
            return {
                "action": "send_to_text_module",
                "files": [file_path],
                "reason": "Detected as a text PDF. Not my module's job — handing off."
            }
        else:
            print("Detected scanned/image PDF. Converting pages to PNG...")
            image_paths = convert_pdf_to_images(file_path)
            return {
                "action": "send_to_pipeline",
                "files": image_paths,
                "reason": "Detected as a scanned PDF. Converted to PNG(s) for pipeline."
            }

    return {"action": "error", "files": None, "reason": f"Unsupported file type: {ext}"}


# ---- INTEGRATION: hooked into your real pipeline (main.py) ----
def send_to_existing_pipeline(image_paths: list, resume_name: str = None):
    """
    Organizes image(s) into dataset/images/<resume_name>/ (matching what
    main.py's process_resume() expects), then runs the real pipeline on it.
    """
    from main import process_resume  # import here to avoid circular import issues

    if not image_paths:
        print("  No images to process.")
        return None

    # Derive resume_name from the first image's filename if not given
    if resume_name is None:
        first_stem = Path(image_paths[0]).stem
        # strip a trailing "_pageN" if present (from PDF conversion)
        resume_name = first_stem.split("_page")[0]

    target_folder = DATASET_DIR / resume_name
    target_folder.mkdir(parents=True, exist_ok=True)

    for img_path in image_paths:
        dest = target_folder / Path(img_path).name
        shutil.copy(img_path, dest)
        print(f"  -> Copied {img_path} to {dest}")

    print(f"  -> Running pipeline on folder: {target_folder}")
    result = process_resume(target_folder)
    return result


# ---- CLI runner ----
if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        print("Usage: python pdf_router.py <path_to_file>")
        sys.exit(1)

    input_file = sys.argv[1]
    result = route_input(input_file)

    print("\n--- ROUTING RESULT ---")
    print(f"Action: {result['action']}")
    print(f"Reason: {result['reason']}")

    if result["action"] == "send_to_pipeline":
        send_to_existing_pipeline(result["files"])
    elif result["action"] == "send_to_text_module":
        print(f"Files to hand off to text-extraction module: {result['files']}")
    elif result["action"] == "error":
        print(f"ERROR: {result['reason']}")