# Phase 4: CNN Forgery Detection - Completion Report

> **Status: COMPLETE**
> **Date: 2026-04-09**

---

## What Was Built

### 1. Synthetic Data Generator (`backend/training/generate_synthetic_data.py`)

Generates forged document images from authentic samples using 4 techniques:

| Technique | Description |
|-----------|-------------|
| **Text replacement** | Blanks out a random text region with background color, writes fake text (grades, SGPA values) |
| **Copy-paste (splice)** | Copies a region from one location and pastes it elsewhere in the document |
| **Brightness forgery** | Alters brightness/contrast of a random region to simulate editing |
| **JPEG noise injection** | Re-compresses a region at very low quality, creating compression artifact inconsistencies |

Also generates 5 augmented versions of each authentic image (rotation, brightness, blur, JPEG artifacts, scaling).

**Generated dataset:**
- 100 authentic images (10 originals + 5 augmentations each, across categories)
- 50 forged images (5 forgeries per source image, each with 1-2 random techniques)
- Total: 150 training images

### 2. Error Level Analysis — ELA (`backend/modules/cnn_forgery.py`)

```python
compute_ela(image_path, quality=90, scale=15) -> numpy array
```

- Re-saves image at known JPEG quality
- Computes pixel-wise difference between original and re-saved version
- Amplifies differences by scale factor (15x)
- Tampered regions appear brighter because they have different compression artifacts
- Returns ELA image as base64 for API response
- **Key demo feature** — visually shows where tampering might exist

### 3. EfficientNet-B0 CNN (`backend/training/train_forgery_cnn.py`)

Transfer learning on EfficientNet-B0 (pretrained on ImageNet):

| Setting | Value |
|---------|-------|
| Input size | 224x224 |
| Batch size | 16 |
| Epochs | 25 |
| Optimizer | Adam (lr=1e-4) |
| Scheduler | ReduceLROnPlateau (patience=3) |
| Loss | CrossEntropyLoss |
| Train/Val split | 80/20 |
| Frozen layers | features[:6] (early layers) |
| Device | Apple Silicon MPS GPU |

**Training Results:**
- Best validation accuracy: **76.7%**
- Training accuracy: ~92%
- Training time: ~43 seconds on M-series Mac
- Model saved to: `backend/ml_models/efficientnet_forgery.pth`

### 4. Grad-CAM Visualization (`backend/modules/cnn_forgery.py`)

- Implements Grad-CAM (Gradient-weighted Class Activation Mapping)
- Uses hooks on the last convolutional layer of EfficientNet-B0
- Generates heatmap showing WHERE the model detects tampering
- Overlays heatmap on original image (60% original + 40% heatmap)
- Saves heatmap to `backend/outputs/` directory
- Returns as base64 in API response
- **Key demo feature** — shows the model is "explainable AI"

### 5. Forgery Detection Pipeline (`backend/modules/cnn_forgery.py`)

```python
detect_forgery(image_path) -> dict
```

Full pipeline:
1. **ELA** — always runs, provides visual tampering indicator
2. **CNN inference** — runs if trained model exists, gives probability score
3. **Grad-CAM** — generates heatmap when forgery probability > 0.3
4. **Fallback** — if no CNN model, uses ELA heuristic (mean brightness scoring)

Returns:
```json
{
    "forgery_detected": false,
    "forgery_probability": 0.1234,
    "ela_image_base64": "...",
    "gradcam_heatmap_base64": "...",
    "method": "cnn+ela",
    "ela_stats": {"mean_brightness": 5.23, "std_brightness": 8.41},
    "status": "success"
}
```

### 6. Updated Verify Endpoint (`backend/routers/verify.py`)

Pipeline now runs **5 stages**:
1. Preprocessing (Phase 1)
2. Classification (Phase 2)
3. OCR Extraction (Phase 2)
4. Rule Validation (Phase 3)
5. **CNN Forgery Detection (Phase 4)** — NEW

### 7. Tests (`backend/tests/test_cnn_forgery.py`)

**20 new tests** covering:
- ELA: returns valid image, correct dimensions, different quality settings, invalid image error, base64 encoding, forged vs authentic comparison (6 tests)
- Forgery pipeline: required keys, success status, ELA image present, probability range, invalid image error, ELA stats, fallback method (7 tests)
- Synthetic data generator: all 4 forgery techniques + augmentation function (6 tests)
- PyTorch availability (1 test)

---

## Architecture

```
Document Image
    │
    ├── Phase 1: Preprocessing
    ├── Phase 2: Classification + OCR
    ├── Phase 3: Rule Validation
    │
    └── Phase 4: Forgery Detection ← NEW
                 │
                 ├── ELA (Error Level Analysis)
                 │   └── Re-compress → diff → amplify → bright regions = tampered
                 │
                 ├── EfficientNet-B0 CNN
                 │   └── Input (224x224) → features → classifier → [authentic, forged]
                 │
                 └── Grad-CAM Heatmap
                     └── Last conv layer gradients → weighted activation → overlay
```

---

## File Structure (Phase 4 additions marked with ←)

```
backend/
├── ml_models/
│   └── efficientnet_forgery.pth          # Trained CNN model ←
├── modules/
│   ├── preprocessor.py                   # Phase 1
│   ├── ocr_engine.py                     # Phase 2
│   ├── classifier.py                     # Phase 2
│   ├── rule_validator.py                 # Phase 3
│   └── cnn_forgery.py                    # NEW: ELA + CNN + Grad-CAM ←
├── training/
│   ├── generate_synthetic_data.py        # NEW: Forgery data generator ←
│   ├── train_forgery_cnn.py              # NEW: CNN training script ←
│   └── dataset/
│       ├── authentic/                    # 100 authentic images ←
│       └── forged/                       # 50 forged images ←
├── routers/
│   └── verify.py                         # Updated: 5-stage pipeline ←
├── requirements.txt                      # Updated: +torch, +torchvision ←
└── tests/
    ├── test_api.py                       # Phase 1 (10 tests)
    ├── test_preprocessor.py              # Phase 1 (13 tests)
    ├── test_ocr.py                       # Phase 2 (33 tests)
    ├── test_rule_validator.py            # Phase 3 (51 tests)
    └── test_cnn_forgery.py               # NEW: 20 tests ←
```

**Total tests: 127** (10 API + 13 preprocessor + 33 OCR + 51 rule validator + 20 forgery)

---

## How to Retrain the Model

If you add more sample documents:

```bash
cd backend
source venv/bin/activate

# 1. Generate new synthetic data
python training/generate_synthetic_data.py

# 2. Train the model
python training/train_forgery_cnn.py
```

---

## What's Next: Phase 5 (NLP + Anomaly Detection + Score Aggregation)

Phase 5 will implement:
1. NLP consistency checking (cross-field logic validation using LM Studio)
2. Isolation Forest anomaly detection (statistical outlier detection)
3. Final score aggregation (weighted combination of all module scores)
4. Full end-to-end pipeline completion
