import cv2
import numpy as np
import os


# ==========================================
# Detect Resume Layout
# ==========================================

def detect_layout(image_path):

    image = cv2.imread(image_path)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(
        gray,
        200,
        255,
        cv2.THRESH_BINARY_INV
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (12,3)
    )

    dilated = cv2.dilate(
        thresh,
        kernel,
        iterations=1
    )

    contours, _ = cv2.findContours(
        dilated,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    output = image.copy()

    width = image.shape[1]

    left_boxes = 0
    right_boxes = 0

    for cnt in contours:

        x,y,w,h = cv2.boundingRect(cnt)

        if w < 80 or h < 20:
            continue

        cv2.rectangle(
            output,
            (x,y),
            (x+w,y+h),
            (0,255,0),
            2
        )

        center = x + w//2

        if center < width//2:
            left_boxes += 1
        else:
            right_boxes += 1

    cv2.imwrite(
        "dataset/debug_layout.png",
        output
    )

    if left_boxes > 3 and right_boxes > 3:
        return "two_column"

    return "single_column"


# ==========================================
# Split Resume Automatically
# ==========================================

def split_resume(image_path):

    image = cv2.imread(image_path)

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    _, binary = cv2.threshold(
        gray,
        200,
        255,
        cv2.THRESH_BINARY_INV
    )

    # Vertical projection
    projection = np.sum(binary > 0, axis=0)

    width = binary.shape[1]

    start = int(width * 0.30)
    end = int(width * 0.70)

    separator = np.argmin(
        projection[start:end]
    ) + start

    OVERLAP = 20
    
    left = image[:, :separator + OVERLAP]
    
    right = image[:, separator - OVERLAP:]


    os.makedirs(
        "dataset/split",
        exist_ok=True
    )

    left_path = "dataset/split/left.png"
    right_path = "dataset/split/right.png"

    cv2.imwrite(left_path, left)
    cv2.imwrite(right_path, right)

    print("\nSeparator Found At :", separator)

    return left_path, right_path

def crop_whitespace(img):

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    _, thresh = cv2.threshold(
        gray,
        250,
        255,
        cv2.THRESH_BINARY_INV
    )

    coords = cv2.findNonZero(thresh)

    x, y, w, h = cv2.boundingRect(coords)

    return img[y:y+h, x:x+w]
