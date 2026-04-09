"""
Synthetic Forgery Data Generator

Generates forged document images from authentic samples using 4 techniques:
1. Text replacement — blank out a text region, write different text
2. Copy-paste (splice) — copy a region and paste elsewhere
3. Color/brightness inconsistency — alter brightness of a region
4. JPEG noise injection — resave a region at different compression

Also augments authentic images to expand the training set.
"""

import os
import sys
import random
import glob

import cv2
import numpy as np
from PIL import Image

# Reproducibility
random.seed(42)
np.random.seed(42)


# ─── Forgery Techniques ───────────────────────────────────────────


def text_replacement_forgery(image: np.ndarray) -> np.ndarray:
    """Blank out a random text-sized region and write different text."""
    h, w = image.shape[:2]
    forged = image.copy()

    # Pick a random region (text-like: wide, short)
    rw = random.randint(w // 6, w // 3)
    rh = random.randint(h // 20, h // 10)
    x = random.randint(w // 8, w - rw - 10)
    y = random.randint(h // 8, h - rh - 10)

    # Sample background color from the region
    region = forged[y:y+rh, x:x+rw]
    bg_color = np.median(region, axis=(0, 1)).astype(int).tolist()

    # Blank out with background color
    cv2.rectangle(forged, (x, y), (x + rw, y + rh), bg_color, -1)

    # Write fake text
    fake_texts = ["9.85", "PASS", "A+", "100", "MODIFIED", "95", "8.5"]
    text = random.choice(fake_texts)
    font_scale = rh / 30.0
    thickness = max(1, int(rh / 15))
    text_color = (0, 0, 0) if np.mean(bg_color) > 128 else (255, 255, 255)
    cv2.putText(forged, text, (x + 5, y + rh - 5),
                cv2.FONT_HERSHEY_SIMPLEX, font_scale, text_color, thickness)

    return forged


def copy_paste_forgery(image: np.ndarray) -> np.ndarray:
    """Copy a region from one location and paste to another."""
    h, w = image.shape[:2]
    forged = image.copy()

    # Source region
    rw = random.randint(w // 8, w // 4)
    rh = random.randint(h // 15, h // 8)
    sx = random.randint(10, w - rw - 10)
    sy = random.randint(10, h - rh - 10)

    source = forged[sy:sy+rh, sx:sx+rw].copy()

    # Destination (different location)
    dx = random.randint(10, w - rw - 10)
    dy = random.randint(10, h - rh - 10)
    # Ensure destination is different enough from source
    while abs(dx - sx) < rw // 2 and abs(dy - sy) < rh // 2:
        dx = random.randint(10, w - rw - 10)
        dy = random.randint(10, h - rh - 10)

    # Paste with slight blending at edges
    forged[dy:dy+rh, dx:dx+rw] = source

    return forged


def brightness_forgery(image: np.ndarray) -> np.ndarray:
    """Alter brightness/contrast of a random region to simulate tampering."""
    h, w = image.shape[:2]
    forged = image.copy()

    # Region
    rw = random.randint(w // 6, w // 3)
    rh = random.randint(h // 10, h // 5)
    x = random.randint(10, w - rw - 10)
    y = random.randint(10, h - rh - 10)

    region = forged[y:y+rh, x:x+rw].astype(np.float32)

    # Random brightness/contrast change
    alpha = random.uniform(0.7, 1.3)  # contrast
    beta = random.randint(-30, 30)     # brightness
    region = np.clip(alpha * region + beta, 0, 255).astype(np.uint8)

    forged[y:y+rh, x:x+rw] = region
    return forged


def jpeg_noise_forgery(image: np.ndarray) -> np.ndarray:
    """Apply different JPEG compression to a region vs the rest."""
    h, w = image.shape[:2]
    forged = image.copy()

    # Region
    rw = random.randint(w // 5, w // 3)
    rh = random.randint(h // 8, h // 4)
    x = random.randint(10, w - rw - 10)
    y = random.randint(10, h - rh - 10)

    region = forged[y:y+rh, x:x+rw]

    # Compress region at very low quality
    quality = random.randint(10, 40)
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quality]
    _, encoded = cv2.imencode(".jpg", region, encode_param)
    decoded = cv2.imdecode(encoded, cv2.IMREAD_COLOR)

    if decoded is not None and decoded.shape == region.shape:
        forged[y:y+rh, x:x+rw] = decoded

    return forged


FORGERY_TECHNIQUES = [
    text_replacement_forgery,
    copy_paste_forgery,
    brightness_forgery,
    jpeg_noise_forgery,
]


# ─── Augmentation for Authentic Images ────────────────────────────


def augment_image(image: np.ndarray) -> list:
    """Generate augmented versions of an authentic image."""
    augmented = []
    h, w = image.shape[:2]

    # 1. Slight rotation
    angle = random.uniform(-3, 3)
    M = cv2.getRotationMatrix2D((w // 2, h // 2), angle, 1.0)
    augmented.append(cv2.warpAffine(image, M, (w, h), borderValue=(255, 255, 255)))

    # 2. Brightness change
    bright = np.clip(image.astype(np.float32) + random.randint(-20, 20), 0, 255).astype(np.uint8)
    augmented.append(bright)

    # 3. Gaussian blur
    ksize = random.choice([3, 5])
    augmented.append(cv2.GaussianBlur(image, (ksize, ksize), 0))

    # 4. JPEG compression artifact (whole image)
    quality = random.randint(50, 80)
    _, encoded = cv2.imencode(".jpg", image, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    augmented.append(cv2.imdecode(encoded, cv2.IMREAD_COLOR))

    # 5. Slight scale
    scale = random.uniform(0.9, 1.1)
    new_w, new_h = int(w * scale), int(h * scale)
    scaled = cv2.resize(image, (new_w, new_h))
    # Crop/pad back to original size
    canvas = np.full_like(image, 255)
    paste_h = min(new_h, h)
    paste_w = min(new_w, w)
    canvas[:paste_h, :paste_w] = scaled[:paste_h, :paste_w]
    augmented.append(canvas)

    return augmented


# ─── Main Generator ───────────────────────────────────────────────


def generate_dataset(
    source_dir: str,
    authentic_out: str,
    forged_out: str,
    augmentations_per_image: int = 5,
    forgeries_per_image: int = 5,
):
    """
    Generate training dataset from source authentic images.

    Args:
        source_dir: Directory containing original authentic images
        authentic_out: Output directory for augmented authentic images
        forged_out: Output directory for forged images
        augmentations_per_image: Number of augmented versions per authentic image
        forgeries_per_image: Number of forged versions per authentic image
    """
    os.makedirs(authentic_out, exist_ok=True)
    os.makedirs(forged_out, exist_ok=True)

    image_paths = sorted(
        glob.glob(os.path.join(source_dir, "*.jpg")) +
        glob.glob(os.path.join(source_dir, "*.jpeg")) +
        glob.glob(os.path.join(source_dir, "*.png"))
    )

    if not image_paths:
        print(f"No images found in {source_dir}")
        return

    print(f"Found {len(image_paths)} source images in {source_dir}")

    auth_count = 0
    forge_count = 0

    for img_path in image_paths:
        image = cv2.imread(img_path)
        if image is None:
            print(f"  Skipping unreadable: {img_path}")
            continue

        base_name = os.path.splitext(os.path.basename(img_path))[0]

        # Save original as authentic
        cv2.imwrite(os.path.join(authentic_out, f"{base_name}_orig.jpg"), image)
        auth_count += 1

        # Generate augmented authentic versions
        augmented = augment_image(image)
        for i, aug in enumerate(augmented[:augmentations_per_image]):
            out_path = os.path.join(authentic_out, f"{base_name}_aug{i}.jpg")
            cv2.imwrite(out_path, aug)
            auth_count += 1

        # Generate forged versions
        for i in range(forgeries_per_image):
            # Apply 1-2 random forgery techniques
            forged = image.copy()
            num_techniques = random.randint(1, 2)
            techniques_used = random.sample(FORGERY_TECHNIQUES, num_techniques)
            for technique in techniques_used:
                forged = technique(forged)

            out_path = os.path.join(forged_out, f"{base_name}_forge{i}.jpg")
            cv2.imwrite(out_path, forged)
            forge_count += 1

    print(f"Generated {auth_count} authentic + {forge_count} forged images")


if __name__ == "__main__":
    # Project paths
    project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    source_dir = os.path.join(project_root, "sample_documents", "authentic")
    dataset_dir = os.path.join(project_root, "backend", "training", "dataset")

    print("=== Generating Forgery Detection Training Data ===\n")

    generate_dataset(
        source_dir=source_dir,
        authentic_out=os.path.join(dataset_dir, "authentic"),
        forged_out=os.path.join(dataset_dir, "forged"),
        augmentations_per_image=5,
        forgeries_per_image=5,
    )

    print("\nDone!")
