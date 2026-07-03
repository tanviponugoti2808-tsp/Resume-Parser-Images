import cv2
import numpy as np


def detect_sections(image_path):

    image = cv2.imread(image_path)

    gray = cv2.cvtColor(
        image,
        cv2.COLOR_BGR2GRAY
    )

    _, binary = cv2.threshold(
        gray,
        220,
        255,
        cv2.THRESH_BINARY_INV
    )

    kernel = cv2.getStructuringElement(
        cv2.MORPH_RECT,
        (40, 5)
    )

    dilated = cv2.dilate(
        binary,
        kernel,
        iterations=2
    )

    contours, _ = cv2.findContours(
        dilated,
        cv2.RETR_EXTERNAL,
        cv2.CHAIN_APPROX_SIMPLE
    )

    boxes = []

    for cnt in contours:

        x, y, w, h = cv2.boundingRect(cnt)

        if w < 100 or h < 25:
            continue

        boxes.append((x, y, w, h))

    boxes = sorted(
        boxes,
        key=lambda b: b[1]
    )

    return image, boxes