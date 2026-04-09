# Data Augmentation

This project contains a simple augmenter for image datasets with YOLO-style labels (normalized bboxes).

Assumptions
- Your dataset folder (`raw` by example) contains image files and matching `.txt` label files with the same basename (e.g. `image_001.jpg` and `image_001.txt`).
- Label format is YOLO: `class x_center y_center width height` where coordinates are normalized to [0,1].
- `raw/classes.txt` contains class names (one per line).

Files created
- `augment.py` - augmentation script using albumentations. Saves augmented images to `OUT/images/` and labels to `OUT/labels/`.
- `requirements.txt` - dependencies for the script.

Quick start (PowerShell)

1. Create a virtual environment and install deps (PowerShell):

```powershell
python -m venv .venv; .\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
```

2. Run the augmenter (example):

```powershell
python .\augment.py --src raw --out augmented --num-aug 3
```

Options
- `--src`: folder containing the dataset (images + txts)
- `--out`: output folder for augmented images/labels
- `--classes`: (optional) path to classes.txt
- `--num-aug`: number of augmented variants per original image
- `--skip-empty`: skip images with empty label files

Notes & next steps
- I assumed image files exist in the same `--src` folder as the `.txt` files. If your images live in a different folder, pass the `--src` accordingly or update `augment.py` to point to the correct images folder.
- Some augmentation transforms can move/scale boxes; the script uses albumentations with `format='yolo'` and will write normalized boxes back.
- Test on a couple of examples first (use `--num-aug 1`) and visually inspect `augmented/images/` and `augmented/labels/`.

If you want, I can now:
- Run a small test for you (if you point to where images are),
- Add functionality to only augment certain classes or to balance the dataset,
- Or convert labels between formats (VOC, COCO, YOLO) before/after augmentation.
