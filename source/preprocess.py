import cv2
import matplotlib.pyplot as plt
import numpy as np


# ============================
# Read Image
# ============================

def read_image(path):

    image = cv2.imread(path)

    if image is None:
        raise FileNotFoundError(f"Image not found: {path}")

    return image


# ============================
# Convert BGR to RGB
# ============================

def convert_to_rgb(image):

    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


# ============================
# Resize Image
# ============================

def resize_image(image, width=1800):

    h, w = image.shape[:2]

    new_height = int(h * (width / w))

    resized = cv2.resize(
    image,
    (width, new_height),
    interpolation=cv2.INTER_CUBIC
    )

    return resized


# ============================
# Convert to Grayscale
# ============================

def convert_to_gray(image):

    return cv2.cvtColor(image, cv2.COLOR_RGB2GRAY)


# ============================
# Remove Noise
# ============================

def remove_noise(image):

    return cv2.medianBlur(image, 3)


# ============================
# CLAHE
# ============================

def apply_clahe(image):

    clahe = cv2.createCLAHE(
        clipLimit=2.0,
        tileGridSize=(8, 8)
    )

    return clahe.apply(image)

# ============================
# Adaptive Thresholding
# ============================


def adaptive_threshold(image, block_size=15, c=8):

    threshold = cv2.adaptiveThreshold(
        image,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        block_size,
        c
    )

    return threshold

    return threshold

# ============================
# Sharpen Image
# ============================

def sharpen_image(image):

    kernel = np.array([
        [-1, -1, -1],
        [-1,  9, -1],
        [-1, -1, -1]
    ])

    sharpened = cv2.filter2D(image, -1, kernel)

    return sharpened


# ============================
# Display Results
# ============================

def display_results(
    original,
    resized,
    gray,
    denoised,
    clahe_image,
    binary
):

    plt.figure(figsize=(30,8))

    plt.subplot(1,6,1)
    plt.imshow(original)
    plt.title("Original")
    plt.axis("off")

    plt.subplot(1,6,2)
    plt.imshow(resized)
    plt.title("Resized")
    plt.axis("off")

    plt.subplot(1,6,3)
    plt.imshow(gray, cmap="gray")
    plt.title("Grayscale")
    plt.axis("off")

    plt.subplot(1,6,4)
    plt.imshow(denoised, cmap="gray")
    plt.title("Noise Removed")
    plt.axis("off")

    plt.subplot(1,6,5)
    plt.imshow(clahe_image, cmap="gray")
    plt.title("CLAHE")
    plt.axis("off")

    plt.subplot(1,6,6)
    plt.imshow(binary, cmap="gray")
    plt.title("Binary")
    plt.axis("off")

    plt.tight_layout()
    plt.show()


# ============================
# Print Image Information
# ============================

def print_image_info(
    original,
    resized,
    gray,
    denoised,
    clahe_image,
    binary
):

    print("\n========== IMAGE INFORMATION ==========\n")

    print("Original Shape :", original.shape)
    print("Resized Shape  :", resized.shape)
    print("Gray Shape     :", gray.shape)
    print("Denoised Shape :", denoised.shape)
    print("CLAHE Shape    :", clahe_image.shape)
    print("Binary Shape   :", binary.shape)

    print("\nHeight :", original.shape[0])
    print("Width  :", original.shape[1])
    print("Channels :", original.shape[2])

import os


def preprocess_resume(image_path, output_path):

    # ============================
    # Read Image
    # ============================
    image = read_image(image_path)

    # ============================
    # Convert to RGB
    # ============================
    rgb = convert_to_rgb(image)

    # ============================
    # Resize (1800 px using INTER_CUBIC)
    # ============================
    resized = resize_image(rgb)

    # ============================
    # Convert to Grayscale
    # ============================
    gray = convert_to_gray(resized)

    # ============================
    # CLAHE
    # ============================
    clahe = apply_clahe(gray)

    # ============================
    # Adaptive Threshold
    # ============================
    binary = adaptive_threshold(
        clahe,
        block_size=15,
        c=8
    )

    # ============================
    # Sharpen
    # ============================
    binary = sharpen_image(binary)

    # ============================
    # Save Processed Image
    # ============================
    cv2.imwrite(output_path, binary)

    print(f"Processed: {output_path}")