import cv2
import numpy as np
import pytesseract
from layout import detect_layout, split_resume

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Advanced Tesseract Flags: 
# --psm 3 handles automatic layout tracking
# load_system_dawg=0/load_freq_dawg=0 disables strict language dictionaries so specialized codes (like SDTM/ADaM domains) don't get forced into random dictionary words.
_ADVANCED_CONFIG = "--oem 3 --psm 6 -c load_system_dawg=0 -c load_freq_dawg=0"

import cv2
import numpy as np
import pytesseract

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# Advanced Tesseract Flags
_ADVANCED_CONFIG = "--oem 3 --psm 6 -c load_system_dawg=0 -c load_freq_dawg=0"


def ocr_page(image_path: str, layout: str = "single_column") -> str:

    img = cv2.imread(str(image_path))

    if img is None:
        raise FileNotFoundError(f"Cannot read image path: {image_path}")

    # Standardize colorspace
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    # Upscale
    h, w = gray.shape[:2]

    if h < 2000:
        gray = cv2.resize(
            gray,
            None,
            fx=2.5,
            fy=2.5,
            interpolation=cv2.INTER_CUBIC
        )

    # Denoise
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)

    # Adaptive Threshold
    binary = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        25,
        15
    )

    # Padding
    processed = cv2.copyMakeBorder(
        binary,
        15,
        15,
        15,
        15,
        cv2.BORDER_CONSTANT,
        value=255
    )

    rgb = cv2.cvtColor(processed, cv2.COLOR_GRAY2RGB)

    return pytesseract.image_to_string(
        rgb,
        config=_ADVANCED_CONFIG
    ).strip()