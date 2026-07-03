import pytesseract
from PIL import Image

# ===========================
# Tell Python where Tesseract is installed
# ===========================

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

print("Tesseract Loaded Successfully!")

# ===========================
# Tesseract Configuration
# ===========================

custom_config = r'--oem 3 --psm 4 -l eng'

# ===========================
# OCR
# ===========================

def extract_text(image_path):

    print("\nRunning OCR...\n")

    image = Image.open(image_path)

    text = pytesseract.image_to_string(
        image,
        config=custom_config
    )

    return text


# ===========================
# Print OCR
# ===========================

def print_ocr(text):

    print("\n========== OCR OUTPUT ==========\n")

    print(text)