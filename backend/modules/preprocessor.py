"""
Module 1: Preprocessing & Enhancement

Takes raw document images (photos, scans, PDFs) and normalizes them
for better OCR and CNN accuracy.

Pipeline:
  load_image -> correct_orientation -> deskew -> enhance -> binarize
"""

import cv2
import numpy as np
from PIL import Image, ExifTags
from pathlib import Path

from config import MAX_IMAGE_DIMENSION


def load_image(file_path: str) -> np.ndarray:
    """Load an image from file path. Handles JPEG, PNG, and PDF (first page)."""
    path = Path(file_path)
    suffix = path.suffix.lower()

    if suffix == ".pdf":
        return _load_pdf_page(file_path)
    elif suffix == ".heic":
        # Convert HEIC to JPEG via Pillow (requires pillow-heif)
        pil_img = Image.open(file_path)
        img_array = np.array(pil_img)
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    else:
        img = cv2.imread(file_path)
        if img is None:
            raise ValueError(f"Could not load image: {file_path}")
        return img


def _load_pdf_page(file_path: str, page_num: int = 0) -> np.ndarray:
    """Convert first page of PDF to image."""
    try:
        from pdf2image import convert_from_path
        images = convert_from_path(file_path, first_page=1, last_page=1, dpi=300)
        if not images:
            raise ValueError("PDF has no pages")
        img_array = np.array(images[0])
        return cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR)
    except ImportError:
        raise ImportError("pdf2image is required for PDF support. Install it with: pip install pdf2image")


def correct_orientation(image: np.ndarray, file_path: str = None) -> np.ndarray:
    """Auto-rotate image using EXIF orientation data (common in phone photos)."""
    if file_path is None:
        return image

    try:
        pil_img = Image.open(file_path)
        exif = pil_img._getexif()
        if exif is None:
            return image

        # Find orientation tag
        orientation_key = None
        for key, val in ExifTags.TAGS.items():
            if val == "Orientation":
                orientation_key = key
                break

        if orientation_key is None or orientation_key not in exif:
            return image

        orientation = exif[orientation_key]

        if orientation == 3:
            image = cv2.rotate(image, cv2.ROTATE_180)
        elif orientation == 6:
            image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
        elif orientation == 8:
            image = cv2.rotate(image, cv2.ROTATE_90_COUNTERCLOCKWISE)

    except Exception:
        pass  # If EXIF reading fails, return original

    return image


def resize_if_needed(image: np.ndarray) -> np.ndarray:
    """Resize image if any dimension exceeds MAX_IMAGE_DIMENSION."""
    h, w = image.shape[:2]
    if max(h, w) <= MAX_IMAGE_DIMENSION:
        return image

    scale = MAX_IMAGE_DIMENSION / max(h, w)
    new_w = int(w * scale)
    new_h = int(h * scale)
    return cv2.resize(image, (new_w, new_h), interpolation=cv2.INTER_AREA)


def deskew(image: np.ndarray) -> np.ndarray:
    """Detect and correct skew angle using Hough Line Transform."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()

    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Detect lines
    lines = cv2.HoughLinesP(edges, 1, np.pi / 180, threshold=100,
                            minLineLength=100, maxLineGap=10)

    if lines is None:
        return image

    # Calculate angles of all detected lines
    angles = []
    for line in lines:
        x1, y1, x2, y2 = line[0]
        angle = np.degrees(np.arctan2(y2 - y1, x2 - x1))
        # Only consider near-horizontal lines (likely text baselines)
        if abs(angle) < 45:
            angles.append(angle)

    if not angles:
        return image

    # Median angle is more robust than mean
    median_angle = np.median(angles)

    # Only correct if skew is noticeable but not extreme
    if abs(median_angle) < 0.5 or abs(median_angle) > 15:
        return image

    # Rotate to correct skew
    h, w = image.shape[:2]
    center = (w // 2, h // 2)
    rotation_matrix = cv2.getRotationMatrix2D(center, median_angle, 1.0)
    corrected = cv2.warpAffine(image, rotation_matrix, (w, h),
                                flags=cv2.INTER_CUBIC,
                                borderMode=cv2.BORDER_REPLICATE)
    return corrected


def enhance_image(image: np.ndarray) -> np.ndarray:
    """Apply contrast enhancement and denoising."""
    # Convert to LAB color space for CLAHE on luminance channel
    if len(image.shape) == 3:
        lab = cv2.cvtColor(image, cv2.COLOR_BGR2LAB)
        l_channel, a_channel, b_channel = cv2.split(lab)

        # Apply CLAHE (Contrast Limited Adaptive Histogram Equalization)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        l_enhanced = clahe.apply(l_channel)

        # Merge back
        enhanced_lab = cv2.merge([l_enhanced, a_channel, b_channel])
        enhanced = cv2.cvtColor(enhanced_lab, cv2.COLOR_LAB2BGR)
    else:
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(image)

    # Denoise
    denoised = cv2.fastNlMeansDenoisingColored(enhanced, None, 10, 10, 7, 21)

    return denoised


def binarize(image: np.ndarray) -> np.ndarray:
    """Convert to binary (black & white) using adaptive thresholding. Used for OCR."""
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY) if len(image.shape) == 3 else image.copy()

    # Adaptive thresholding works better than global for documents with uneven lighting
    binary = cv2.adaptiveThreshold(
        gray, 255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        blockSize=15,
        C=11
    )
    return binary


def sharpen(image: np.ndarray) -> np.ndarray:
    """Apply unsharp masking to sharpen text edges."""
    gaussian = cv2.GaussianBlur(image, (0, 0), 3)
    sharpened = cv2.addWeighted(image, 1.5, gaussian, -0.5, 0)
    return sharpened


def preprocess_document(file_path: str) -> dict:
    """
    Full preprocessing pipeline. Returns dict with different versions of the image.

    Returns:
        {
            "original": np.ndarray,       # Original loaded image
            "corrected": np.ndarray,      # Orientation + deskew corrected
            "enhanced": np.ndarray,       # Contrast enhanced + denoised (for CNN)
            "binary": np.ndarray,         # Binarized (for OCR)
            "sharpened": np.ndarray,      # Sharpened version
        }
    """
    # Step 1: Load
    original = load_image(file_path)

    # Step 2: Resize if too large
    resized = resize_if_needed(original)

    # Step 3: Correct orientation
    corrected = correct_orientation(resized, file_path)

    # Step 4: Deskew
    deskewed = deskew(corrected)

    # Step 5: Enhance (for CNN input)
    enhanced = enhance_image(deskewed)

    # Step 6: Sharpen
    sharpened = sharpen(enhanced)

    # Step 7: Binarize (for OCR input)
    binary = binarize(deskewed)

    return {
        "original": original,
        "corrected": deskewed,
        "enhanced": enhanced,
        "binary": binary,
        "sharpened": sharpened,
    }


def save_preprocessed(images: dict, output_dir: str, doc_id: str) -> dict:
    """Save preprocessed images to disk and return their paths."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)

    saved_paths = {}
    for name, img in images.items():
        file_path = output_path / f"{doc_id}_{name}.jpg"
        cv2.imwrite(str(file_path), img)
        saved_paths[name] = str(file_path)

    return saved_paths
