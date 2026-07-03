import cv2
import numpy as np
import pytesseract
from layout import detect_layout, split_resume

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

_PRIMARY_CONFIG = "--oem 3 --psm 4 -c load_system_dawg=0 -c load_freq_dawg=0"
_FALLBACK_CONFIG = "--oem 3 --psm 6 -c load_system_dawg=0 -c load_freq_dawg=0"
_SPARSE_CONFIG = "--oem 3 --psm 11 -c load_system_dawg=0 -c load_freq_dawg=0"


def _preprocess_heavy(gray: np.ndarray) -> np.ndarray:
    denoised = cv2.bilateralFilter(gray, 9, 75, 75)
    binary = cv2.adaptiveThreshold(
        denoised,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        35,
        11
    )
    return cv2.copyMakeBorder(binary, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)


def _preprocess_light(gray: np.ndarray) -> np.ndarray:
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    return cv2.copyMakeBorder(binary, 15, 15, 15, 15, cv2.BORDER_CONSTANT, value=255)


def _run_ocr(img: np.ndarray, config: str) -> str:
    rgb = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)
    return pytesseract.image_to_string(rgb, config=config).strip()


def ocr_page(image_path: str, layout: str = "single_column") -> str:

    img = cv2.imread(str(image_path))

    if img is None:
        raise FileNotFoundError(f"Cannot read image path: {image_path}")

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY) if len(img.shape) == 3 else img

    h, w = gray.shape[:2]
    if h < 2000:
        gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

    light_img = _preprocess_light(gray)
    text_light = _run_ocr(light_img, _PRIMARY_CONFIG)

    heavy_img = _preprocess_heavy(gray)
    text_heavy = _run_ocr(heavy_img, _FALLBACK_CONFIG)

    text_sparse = _run_ocr(light_img, _SPARSE_CONFIG)

    combined = _merge_ocr_results(text_light, text_heavy, text_sparse)

    return combined


def _merge_ocr_results(text_light: str, text_heavy: str, text_sparse: str) -> str:
    candidates = [text_light, text_heavy, text_sparse]
    base = max(candidates, key=len)

    base_lines = [l for l in base.splitlines() if l.strip()]
    first_line = base_lines[0].strip() if base_lines else ""

    def looks_like_name(line: str) -> bool:
        if not line or "@" in line or any(c.isdigit() for c in line):
            return False
        words = line.split()
        return 1 <= len(words) <= 4 and all(w.replace(".", "").isalpha() for w in words)

    if not looks_like_name(first_line):
        for alt in candidates:
            alt_lines = [l for l in alt.splitlines() if l.strip()]
            for line in alt_lines[:3]:
                if looks_like_name(line.strip()):
                    base = line.strip() + "\n" + base
                    return base

    return base