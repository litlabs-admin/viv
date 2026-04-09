#!/usr/bin/env python3
"""
Simple augmentation script that applies image augmentations while updating YOLO-format labels.
Assumptions:
- Your dataset folder contains image files and corresponding `.txt` label files with the same basename.
- Label files use YOLO format: "class x_center y_center width height" with values normalized to [0,1].
- `raw/classes.txt` contains class names (one per line).

Usage example (PowerShell):
python .\augment.py --src raw --out augmented --num-aug 3

The script will create `out/images/` and `out/labels/` under the `--out` folder.
"""

import argparse
import os
import glob
import cv2
import numpy as np
from tqdm import tqdm

try:
    import albumentations as A
except Exception as e:
    raise ImportError("Please install albumentations (pip install albumentations) and ensure opencv-python and numpy are installed.")


def parse_args():
    p = argparse.ArgumentParser(description="Augment images and YOLO labels (normalized bboxes)")
    p.add_argument("--src", required=True, help="Source dataset folder containing images and .txt labels (e.g. raw)")
    p.add_argument("--out", required=True, help="Output folder for augmented images/labels")
    p.add_argument("--classes", default=None, help="Path to classes.txt (optional). If not provided will look in src/classes.txt")
    p.add_argument("--num-aug", type=int, default=5, help="Number of augmentations to generate per source image")
    p.add_argument("--img-exts", default="jpg,jpeg,png", help="Comma-separated image extensions to search for (default: jpg,jpeg,png)")
    p.add_argument("--skip-empty", action="store_true", help="Skip augmenting images that have no bounding boxes (empty .txt)")
    p.add_argument("--seed", type=int, default=42, help="Random seed for reproducibility")
    return p.parse_args()


def read_classes(classes_path):
    if not os.path.exists(classes_path):
        return []
    with open(classes_path, "r", encoding="utf-8") as f:
        lines = [l.strip() for l in f.read().splitlines() if l.strip()]
    return lines


def find_image_for_basename(src_dir, basename, exts):
    for e in exts:
        candidate = os.path.join(src_dir, basename + "." + e)
        if os.path.exists(candidate):
            return candidate
    # fallback: glob search case-insensitive
    for e in exts:
        pattern = os.path.join(src_dir, basename + ".*")
        for path in glob.glob(pattern):
            if path.lower().endswith('.' + e.lower()):
                return path
    return None


def read_yolo_label(path):
    boxes = []
    labels = []
    if not os.path.exists(path):
        return boxes, labels
    with open(path, "r", encoding="utf-8") as f:
        for line in f.read().splitlines():
            line = line.strip()
            if not line:
                continue
            parts = line.split()
            if len(parts) != 5:
                # ignore malformed
                continue
            cls = int(parts[0])
            vals = [float(x) for x in parts[1:]]
            # albumentations expects [x_center, y_center, w, h] for 'yolo' format
            boxes.append(tuple(vals))
            labels.append(cls)
    return boxes, labels


def write_yolo_label(path, boxes, labels):
    # boxes: list of (x_center, y_center, w, h) normalized
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        for (x, y, w, h), cls in zip(boxes, labels):
            f.write(f"{int(cls)} {x:.6f} {y:.6f} {w:.6f} {h:.6f}\n")


def build_transform():
    # Compose a set of augmentations suitable for documents/general objects
    return A.Compose([
        A.HorizontalFlip(p=0.5),
        A.RandomBrightnessContrast(p=0.3, brightness_limit=0.2, contrast_limit=0.2),
        A.ShiftScaleRotate(shift_limit=0.03, scale_limit=0.05, rotate_limit=5, border_mode=cv2.BORDER_CONSTANT, p=0.5),
        A.OneOf([A.GaussNoise(var_limit=(5.0, 30.0)), A.GaussianBlur(blur_limit=3)], p=0.3),
        A.HueSaturationValue(hue_shift_limit=5, sat_shift_limit=10, val_shift_limit=10, p=0.2),
    ], bbox_params=A.BboxParams(format='yolo', label_fields=['class_labels'], min_visibility=0.2))


def main():
    args = parse_args()
    np.random.seed(args.seed)

    src = args.src
    out = args.out
    os.makedirs(out, exist_ok=True)
    out_images = os.path.join(out, "images")
    out_labels = os.path.join(out, "labels")
    os.makedirs(out_images, exist_ok=True)
    os.makedirs(out_labels, exist_ok=True)

    classes_path = args.classes if args.classes else os.path.join(src, "classes.txt")
    classes = read_classes(classes_path)
    if classes:
        print(f"Loaded {len(classes)} classes from {classes_path}")

    exts = [e.strip().lower() for e in args.img_exts.split(",") if e.strip()]

    # find all .txt label files in src (except classes.txt)
    label_files = sorted([p for p in glob.glob(os.path.join(src, "*.txt")) if os.path.basename(p) != os.path.basename(classes_path)])
    if not label_files:
        print("No label .txt files found in src folder. Make sure txt label files exist with same basename as images.")
        return

    transform = build_transform()

    for lbl_path in tqdm(label_files, desc="Processing label files"):
        basename = os.path.splitext(os.path.basename(lbl_path))[0]
        img_path = find_image_for_basename(src, basename, exts)
        if img_path is None:
            # skip if no corresponding image
            tqdm.write(f"Warning: no image found for {basename}, skipping")
            continue

        image = cv2.imread(img_path)
        if image is None:
            tqdm.write(f"Warning: failed to read image {img_path}")
            continue

        boxes, labels = read_yolo_label(lbl_path)
        if len(boxes) == 0 and args.skip_empty:
            # optionally skip background-only images
            continue

        # convert boxes/list into albumentations expected format
        for i in range(args.num_aug):
            # apply transform
            try:
                augmented = transform(image=image, bboxes=boxes, class_labels=labels)
            except Exception as e:
                # in rare cases albumentations might error on some box cases, fallback to no-bbox transform
                augmented = A.Compose([A.HorizontalFlip(p=0.5), A.RandomBrightnessContrast(p=0.2)])(image=image)
                aug_image = augmented['image']
                aug_bboxes = []
                aug_labels = []
            else:
                aug_image = augmented['image']
                aug_bboxes = augmented.get('bboxes', [])
                aug_labels = augmented.get('class_labels', [])

            # save image and label
            img_ext = os.path.splitext(img_path)[1] or ".jpg"
            out_img_name = f"{basename}_aug{i}{img_ext}"
            out_lbl_name = f"{basename}_aug{i}.txt"

            out_img_path = os.path.join(out_images, out_img_name)
            out_lbl_path = os.path.join(out_labels, out_lbl_name)

            # ensure proper type
            cv2.imwrite(out_img_path, aug_image)

            # albumentations returns YOLO normalized values if format='yolo'
            if len(aug_bboxes) > 0:
                write_yolo_label(out_lbl_path, aug_bboxes, aug_labels)
            else:
                # write empty label file
                open(out_lbl_path, "w", encoding="utf-8").close()

    print(f"Augmentation complete. Augmented images in: {out_images}, labels in: {out_labels}")


if __name__ == '__main__':
    main()
