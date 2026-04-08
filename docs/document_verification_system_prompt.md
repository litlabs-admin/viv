# Comprehensive AI System Prompt: Automated Multi-Document Verification System

---

## PROJECT OVERVIEW

You are building a **production-grade, end-to-end Automated Document Verification System** that authenticates real-world physical and digital documents using a multi-layered AI pipeline. The system must handle real photographs and scans of documents — not just clean digital exports — and produce an interpretable verification report with precise localization of any tampering or anomalies detected.

The four primary document types supported are:
1. **SPPU Academic Marksheets** (Savitribai Phule Pune University)
2. **Aadhaar Card** (Government of India biometric identity)
3. **PAN Card** (Permanent Account Number card)
4. **Experience/Employment Certificates**

The system must combine OCR-based text extraction, rule-based validation, CNN-based visual forgery detection, NLP-based semantic consistency checking, and Isolation Forest anomaly detection — producing a weighted cumulative confidence score and a detailed, annotated verification report.

---

## TECH STACK

| Layer | Technology |
|---|---|
| **Backend** | Python (FastAPI or Flask) |
| **Frontend** | React.js + TailwindCSS (or Next.js) |
| **Database** | Supabase (PostgreSQL + Storage + Auth) |
| **OCR** | Tesseract OCR + Google Vision API (fallback) + LLM-based extraction (e.g., via Ollama/LM Studio for layered documents) |
| **CNN Model** | PyTorch or TensorFlow — ResNet-50 or EfficientNet-B4 fine-tuned for forgery detection |
| **NLP** | spaCy / HuggingFace Transformers |
| **Anomaly Detection** | scikit-learn Isolation Forest |
| **Image Processing** | OpenCV, Pillow, scikit-image |
| **Data Augmentation** | Albumentations library |
| **Deployment** | Docker + Supabase backend |

---

## SYSTEM ARCHITECTURE

The system is structured as a sequential pipeline with parallel validation stages:

```
[Document Upload (Image/PDF)]
        ↓
[Preprocessing & Enhancement Module]
        ↓
[OCR & Text Extraction Engine]  ←→  [LLM Fallback for Layered Documents]
        ↓
[Document Classification & Template Matching]
        ↓
        ├──→ [Rule-Based Validation Engine]
        ├──→ [NLP Semantic Consistency Checker]
        ├──→ [CNN Forgery Detection Model]       ← PRIORITY MODULE
        └──→ [Isolation Forest Anomaly Detector]
                        ↓
        [Weighted Confidence Score Aggregator]
                        ↓
        [Tamper Localization & Annotation Module]
                        ↓
        [Verification Report Generator]
                        ↓
        [Supabase Storage + Dashboard Display]
```

---

## MODULE 1: PREPROCESSING & ENHANCEMENT

### Goal
Normalize all uploaded document images (photos or scans) to improve OCR and CNN model accuracy. Real-world inputs will include camera photos taken at angles, low-resolution scans, laminated card photos with glare, and crumpled or folded documents.

### Implementation Steps

1. **Format Handling**
   - Accept JPEG, PNG, HEIC (mobile photos), PDF (multi-page)
   - Convert PDFs to per-page images at 300 DPI using `pdf2image`
   - Convert HEIC to JPEG using `pyheif`

2. **Geometric Correction**
   - Detect document boundary using OpenCV contour detection or a deep-learning document boundary detector (e.g., DocUNet or a fine-tuned CRAFT model)
   - Apply perspective correction / homographic transformation to deskew the document
   - Detect and correct skew angle using Hough line detection

3. **Image Quality Enhancement**
   - Apply adaptive histogram equalization (CLAHE) to improve contrast
   - Apply denoising: Non-local means denoising for scanned documents, bilateral filter for photos
   - Binarization using Sauvola or Niblack adaptive thresholding (better than global Otsu for uneven lighting)
   - Sharpening using unsharp masking

4. **Glare / Lamination Removal (for Aadhaar, PAN)**
   - Detect specular highlights using HSV threshold
   - Inpaint glare regions using `cv2.inpaint()` with the Telea or Navier-Stokes method

5. **Resolution Upscaling**
   - If DPI < 150, apply ESRGAN or Real-ESRGAN super-resolution model to upscale to at least 300 DPI before OCR

---

## MODULE 2: OCR & TEXT EXTRACTION ENGINE

### Goal
Accurately extract structured text from all document types, including SPPU marksheets that have a **security overlay/background layer** that interferes with standard OCR.

### Standard OCR Pipeline

1. Run **Tesseract OCR** (v5+) with LSTM engine in `--psm 6` (assume uniform block of text) or `--psm 3` (auto)
2. Post-process Tesseract output: remove noise characters, normalize whitespace, reconstruct table structure from bounding boxes

### SPPU Marksheet Layer Problem — Specialized Solution

SPPU marksheets contain a repeating watermark/security pattern layer printed over the text content, causing standard OCR to fail or produce garbled output. Use a **multi-strategy cascade**:

**Strategy A — Frequency Domain Separation:**
- Apply DFT (Discrete Fourier Transform) to the image
- Identify and mask the periodic frequency components corresponding to the repeating pattern
- Apply inverse DFT to reconstruct a cleaner image
- Pass the reconstructed image to Tesseract

**Strategy B — LLM Vision-Based Extraction (Primary Fallback):**
- When Tesseract confidence is below a threshold (e.g., < 70%), invoke a local or API-based multimodal LLM (e.g., LLaVA via Ollama, GPT-4o, or Gemini Vision)
- Provide a document-type-specific prompt instructing the LLM to extract structured fields (PRN, student name, subject names, marks, grades, SGPA, total credits) and return them in JSON format
- Validate the LLM JSON output against a schema before accepting it

**Strategy C — Targeted Region Cropping (for tables):**
- Use YOLO v8 (or a fine-tuned Detectron2 model) to detect and crop individual cells of the marks table
- Run OCR on each individual cell crop, which is cleaner than the whole document

**Strategy D — Color Channel Separation:**
- Split the image into its R, G, B channels
- Sometimes the security pattern is printed in a specific ink that is dominant in one channel
- Run OCR on the channel where pattern interference is lowest

**Combine results:** Take a majority-vote or highest-confidence result across strategies.

### Per-Document Field Extraction Schema

#### SPPU Marksheet
```json
{
  "prn": "string",
  "student_name": "string",
  "exam_seat_number": "string",
  "month_year": "string",
  "university": "SPPU",
  "course": "string",
  "semester": "int",
  "subjects": [
    {
      "subject_code": "string",
      "subject_name": "string",
      "credits": "int",
      "internal_marks": "int",
      "external_marks": "int",
      "total_marks": "int",
      "grade": "string",
      "grade_points": "float"
    }
  ],
  "total_credits": "int",
  "sgpa": "float",
  "result": "string"
}
```

#### Aadhaar Card
```json
{
  "aadhaar_number": "string (12 digits, masked or full)",
  "name": "string",
  "dob": "string (DD/MM/YYYY)",
  "gender": "string",
  "address": "string",
  "vid": "string (optional)",
  "issue_date": "string"
}
```

#### PAN Card
```json
{
  "pan_number": "string (XXXXX9999X format)",
  "name": "string",
  "fathers_name": "string",
  "dob": "string (DD/MM/YYYY)",
  "signature_present": "boolean"
}
```

#### Experience Certificate
```json
{
  "employee_name": "string",
  "employee_id": "string",
  "designation": "string",
  "department": "string",
  "company_name": "string",
  "date_of_joining": "string",
  "date_of_relieving": "string",
  "duration": "string",
  "certifying_authority_name": "string",
  "certifying_authority_designation": "string",
  "issue_date": "string",
  "company_letterhead_present": "boolean",
  "seal_present": "boolean",
  "signature_present": "boolean"
}
```

---

## MODULE 3: DOCUMENT CLASSIFICATION & TEMPLATE MATCHING

### Goal
Automatically identify the document type and match it to the correct verification template before applying type-specific validation.

### Implementation

1. **Document Type Classifier**
   - Train a CNN image classifier (MobileNetV3 for speed) on labeled samples of each document type
   - Classes: `sppu_marksheet`, `aadhaar_card`, `pan_card`, `experience_certificate`, `unknown`
   - Use confidence threshold: if below 85%, flag for manual review

2. **Template Anchor Detection**
   - For each document type, define visual anchors (logos, header text, fixed layout zones)
   - Use ORB or SIFT feature matching against a stored template image to verify structural alignment
   - Significant deviation in anchor alignment → structural tampering flag

---

## MODULE 4: RULE-BASED VALIDATION ENGINE

### Goal
Apply deterministic, domain-specific logical rules per document type to catch semantic inconsistencies — the kinds of tampering that look visually fine but fail mathematically or logically.

### SPPU Marksheet Rules
- PRN must be exactly 11 digits and start with a valid prefix for the university year/branch
- Exam Seat Number must follow SPPU format (e.g., prefix + 6 digits)
- Each subject's `total_marks = internal_marks + external_marks`
- Grade must correspond to the correct range per SPPU grading scale (O=91-100, A+=81-90, A=71-80, B+=61-70, B=51-60, C=41-50, F=<40)
- Grade points must match the university-defined grade-to-point mapping
- SGPA = (Σ grade_points × credits) / Σ credits — must match within ±0.05 tolerance (rounding)
- Total credits earned must not exceed the defined maximum for the semester
- `result` field ("PASS" / "FAIL") must be consistent with individual subject pass/fail rules

### Aadhaar Card Rules
- Aadhaar number must pass the **Verhoeff algorithm checksum** (standard UIDAI checksum)
- DoB must be a valid calendar date and person must be ≥0 years old and ≤120 years old
- Address must contain recognizable Indian state/district names (use NLP entity matching)
- If VID is present, it must be 16 digits

### PAN Card Rules
- PAN must match the regex: `[A-Z]{5}[0-9]{4}[A-Z]{1}`
- 4th character of PAN encodes entity type (P=Person, C=Company, H=HUF, etc.) — must be consistent with the name on card
- 5th character is the first letter of the surname — must match the extracted name
- DoB must be a valid calendar date

### Experience Certificate Rules
- Date of relieving must be after date of joining
- Duration of employment mentioned in text must be consistent with computed difference between joining and relieving dates (±1 month tolerance)
- Company name must appear in the letterhead, body, and seal (NLP entity consistency check)
- Certifying authority's designation must be consistent with standard HR roles

---

## MODULE 5: NLP SEMANTIC CONSISTENCY CHECKER

### Goal
Use NLP to check for semantic-level inconsistencies within the document text that rule-based checks cannot catch.

### Implementation

1. **Named Entity Recognition (NER)**
   - Extract all PERSON, ORG, DATE, LOCATION entities using spaCy or a fine-tuned BERT NER model
   - Cross-check: does the person's name appear consistently across all fields?
   - For experience certificates: does the company name match across letterhead, body, seal?

2. **Language Consistency**
   - Detect unusual phrasing or grammar patterns that are inconsistent with standard official document language (use a language model perplexity score — abnormally low perplexity on formulaic fields or abnormally high on official text blocks may indicate copy-paste alterations)

3. **Temporal Consistency**
   - All dates must form a logically consistent timeline (e.g., DoB < graduation date < experience dates)

4. **Institution Validation**
   - Maintain a curated database of valid SPPU-affiliated colleges with their codes and names
   - Validate the college name/code on the marksheet against this database

5. **Signature Block Validation (Experience Certificates)**
   - Check that the signatory name, designation, and company in the signature block are consistent with the document header

---

## MODULE 6: CNN-BASED FORGERY DETECTION (PRIMARY/EMPHASIZED MODULE)

### Goal
Detect visual-level tampering — the most common form of document fraud — including: cloning/copy-paste of regions, ink/color inconsistency, font irregularities, seal forgery, signature forgery, background texture manipulation, and re-printing artifacts.

**This is the highest-weight module in the final confidence score.**

### Model Architecture

**Primary Model: EfficientNet-B4 fine-tuned for forgery detection**
- Input: 512×512 image patches extracted from document
- Output: per-patch forgery probability + forgery class (clone, erase, splicing, texture_anomaly, font_anomaly)
- Use **Grad-CAM** (Gradient-weighted Class Activation Mapping) to generate heatmaps identifying the precise spatial region of tampering

**Secondary Model: Error Level Analysis (ELA) CNN**
- Re-save the document image at a known JPEG quality (e.g., 85%)
- Compute the difference (ELA image) between original and re-saved
- Feed ELA image into a secondary CNN to detect regions with inconsistent compression levels (strong indicator of digital splicing)

**Tertiary Analysis: Frequency Domain Forgery Detection**
- Apply DFT / DCT to detect periodic noise patterns introduced by double-compression or copy-paste operations
- Use wavelet decomposition to identify texture discontinuities at tampered boundaries

### Key Detection Targets Per Document

| Document | Primary Forgery Targets |
|---|---|
| SPPU Marksheet | Grade/marks region (copy-paste of different grade), SGPA tampering, university seal alteration, PRN modification |
| Aadhaar Card | Photo replacement (face swap), name/address field erasure and re-typing, Aadhaar number alteration, hologram tampering |
| PAN Card | Photo replacement, name/DoB field alteration, PAN number tampering, signature forgery |
| Experience Certificate | Date alteration (joining/relieving), designation upgrade, company seal forgery, signature forgery, letterhead cloning |

### Training Data & Data Augmentation (Critical)

**Augmentation pipeline using Albumentations:**
```python
augmentation_pipeline = A.Compose([
    # Geometric transforms (simulate real-world capture conditions)
    A.Rotate(limit=45, p=0.7),               # Documents photographed at angle
    A.HorizontalFlip(p=0.3),                  # Mirrored scans
    A.ShiftScaleRotate(shift_limit=0.1, scale_limit=0.15, rotate_limit=30, p=0.6),
    A.Perspective(scale=(0.05, 0.15), p=0.5), # Perspective distortion from phone camera
    
    # Photographic quality simulation
    A.RandomBrightnessContrast(brightness_limit=0.3, contrast_limit=0.3, p=0.6),
    A.GaussNoise(var_limit=(10, 50), p=0.5),  # Scan noise
    A.MotionBlur(blur_limit=5, p=0.3),         # Camera shake
    A.ImageCompression(quality_lower=60, quality_upper=95, p=0.5),  # JPEG artifacts
    A.GaussianBlur(blur_limit=3, p=0.3),
    
    # Lighting conditions
    A.RandomShadow(p=0.3),                    # Shadows from uneven lighting
    A.CLAHE(p=0.4),
    A.HueSaturationValue(p=0.3),
    
    # Stamp/seal simulation
    A.GridDistortion(p=0.2),
    A.ElasticTransform(p=0.2),
])
```

**Synthetic Forgery Generation for Training:**
- **Grade tampering**: Programmatically change specific text regions in known-authentic documents
- **Copy-paste forgery**: Clone grade cells from one document into another using Poisson blending
- **Seal forgery**: Apply degraded/resized seal stamps from other documents
- **Photo swap**: Use face detection to locate photo region, replace with different face
- **Background texture manipulation**: Apply different paper texture to specific regions

**Training Dataset Composition:**
- 60% authentic documents (real scans with augmentation)
- 25% synthetically forged documents (programmatically generated)
- 15% real forged documents (if available)

### Output Format

The CNN module outputs:
```json
{
  "forgery_detected": true,
  "overall_forgery_probability": 0.87,
  "forgery_regions": [
    {
      "region_id": 1,
      "bounding_box": {"x": 120, "y": 340, "w": 200, "h": 40},
      "forgery_type": "text_replacement",
      "confidence": 0.91,
      "description": "Potential grade/marks value replacement detected"
    }
  ],
  "ela_anomaly_score": 0.76,
  "frequency_anomaly_score": 0.43,
  "grad_cam_heatmap": "base64_encoded_heatmap_image"
}
```

---

## MODULE 7: ISOLATION FOREST ANOMALY DETECTION

### Goal
Detect statistical outliers in the numerical/structural features of a document compared to a learned distribution of authentic documents. This catches subtle tampering that neither rules nor CNN easily catch.

### Feature Vector Construction (per document type)

**SPPU Marksheet features:**
- SGPA value
- Distribution of grades across subjects (histogram of O, A+, A, B+, B, C, F)
- Ratio of internal to external marks per subject
- Total credits
- Standard deviation of marks across subjects

**Aadhaar/PAN features:**
- Aspect ratio of document
- Photo region aspect ratio
- Font size consistency score (extracted from OCR bounding boxes)
- Color histogram of key regions (header background, photo region)

### Training
- Train Isolation Forest on feature vectors extracted from a corpus of confirmed-authentic documents
- Tune `contamination` parameter based on expected fraud rate in your use case (suggested: 0.05–0.1)

### Output
- `anomaly_score`: float between 0 and 1 (higher = more anomalous)
- `anomalous_features`: list of feature names that contributed most to the anomaly score

---

## MODULE 8: WEIGHTED CONFIDENCE SCORE AGGREGATOR

### Scoring Formula

```
confidence_score = (
    w_cnn        × cnn_authenticity_score      +   # Weight: 0.40 (highest)
    w_rule       × rule_validation_score        +   # Weight: 0.25
    w_nlp        × nlp_consistency_score        +   # Weight: 0.15
    w_isolation  × (1 - isolation_anomaly_score)+   # Weight: 0.10
    w_ocr        × ocr_extraction_confidence    +   # Weight: 0.10
) / (w_cnn + w_rule + w_nlp + w_isolation + w_ocr)
```

**Weights rationale:** CNN forgery detection carries the highest weight (0.40) because it directly detects visual manipulation, which is the most common and dangerous form of document fraud.

### Final Verdict Thresholds

| Score Range | Verdict | Color |
|---|---|---|
| 0.85 – 1.00 | ✅ VERIFIED — Authentic | Green |
| 0.65 – 0.84 | ⚠️ NEEDS REVIEW — Suspicious indicators present | Yellow |
| 0.00 – 0.64 | ❌ FRAUDULENT — Tampering detected | Red |

### Hard Override Rules
- If any rule-based validation produces a **critical failure** (e.g., Verhoeff checksum fails for Aadhaar, SGPA calculation mismatch > 0.5), the verdict is immediately set to **FRAUDULENT** regardless of score.
- If CNN forgery probability > 0.90 for any region, the verdict is set to at least **NEEDS REVIEW**.

---

## MODULE 9: TAMPER LOCALIZATION & VERIFICATION REPORT

### Goal
Generate an interpretable, annotated report that pinpoints exactly where and what the problem is on the document.

### Annotated Image Output
- Overlay bounding boxes on the original document image at each detected tamper region
- Color-code boxes by forgery type: Red = high confidence forgery, Orange = suspicious, Yellow = minor anomaly
- Label each box with the detected issue (e.g., "Grade value replacement — confidence 91%")
- Overlay Grad-CAM heatmap as a semi-transparent layer for CNN findings

### Verification Report Structure (JSON + PDF)

```json
{
  "report_id": "uuid",
  "timestamp": "ISO8601",
  "document_type": "sppu_marksheet",
  "document_hash": "sha256_of_original",
  
  "extracted_data": { /* structured JSON per schema above */ },
  
  "verification_summary": {
    "final_verdict": "FRAUDULENT",
    "confidence_score": 0.23,
    "processing_time_ms": 4200
  },
  
  "module_results": {
    "ocr": {
      "extraction_confidence": 0.88,
      "strategy_used": "LLM_fallback",
      "fields_extracted": 24,
      "fields_failed": 2
    },
    "rule_validation": {
      "score": 0.40,
      "passed_rules": 8,
      "failed_rules": [
        {
          "rule_id": "sgpa_calculation",
          "description": "SGPA on document (8.91) does not match computed SGPA from grade points (7.43). Discrepancy: 1.48",
          "severity": "critical"
        }
      ]
    },
    "nlp_consistency": {
      "score": 0.75,
      "findings": ["College name in header does not match college name in seal region"]
    },
    "cnn_forgery": {
      "overall_forgery_probability": 0.87,
      "forgery_regions": [ /* ... */ ],
      "ela_anomaly_score": 0.76,
      "annotated_image_url": "supabase_storage_url"
    },
    "isolation_forest": {
      "anomaly_score": 0.82,
      "anomalous_features": ["sgpa_value", "grade_distribution"]
    }
  },
  
  "final_summary_text": "This SPPU marksheet shows strong indicators of tampering. The SGPA printed on the document (8.91) is inconsistent with the computed SGPA derived from the extracted subject-wise grade points (7.43), suggesting the SGPA value was altered after the rest of the document was generated. Additionally, CNN-based analysis identified a high-confidence copy-paste artifact in the grades column of Subject 3 (Engineering Mathematics III). The Aadhaar number checksum validation passed. Manual review is strongly recommended."
}
```

---

## MODULE 10: SUPABASE DATABASE SCHEMA

```sql
-- Users table (handled by Supabase Auth)
-- profiles table extends auth.users
CREATE TABLE profiles (
  id UUID REFERENCES auth.users PRIMARY KEY,
  full_name TEXT,
  organization TEXT,
  role TEXT CHECK (role IN ('individual', 'verifier', 'admin')),
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Documents table
CREATE TABLE documents (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id UUID REFERENCES profiles(id),
  original_filename TEXT,
  document_type TEXT CHECK (document_type IN ('sppu_marksheet', 'aadhaar_card', 'pan_card', 'experience_certificate', 'unknown')),
  storage_path TEXT,  -- Supabase Storage bucket path for original file
  annotated_image_path TEXT,  -- Path to annotated output image
  document_hash TEXT,  -- SHA-256 of original file
  uploaded_at TIMESTAMPTZ DEFAULT NOW()
);

-- Verification results table
CREATE TABLE verification_results (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  document_id UUID REFERENCES documents(id),
  verdict TEXT CHECK (verdict IN ('VERIFIED', 'NEEDS_REVIEW', 'FRAUDULENT')),
  confidence_score FLOAT,
  
  -- Per-module scores
  ocr_confidence FLOAT,
  rule_validation_score FLOAT,
  nlp_consistency_score FLOAT,
  cnn_forgery_score FLOAT,
  isolation_forest_score FLOAT,
  
  -- Full JSON result
  full_report JSONB,
  extracted_data JSONB,
  
  -- Rule failures
  failed_rules JSONB,
  
  -- CNN forgery regions
  forgery_regions JSONB,
  
  processing_time_ms INT,
  created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Analytics view
CREATE VIEW verification_analytics AS
SELECT 
  document_type,
  verdict,
  COUNT(*) as count,
  AVG(confidence_score) as avg_confidence,
  DATE_TRUNC('day', created_at) as date
FROM verification_results vr
JOIN documents d ON d.id = vr.document_id
GROUP BY document_type, verdict, date;
```

**Supabase Storage Buckets:**
- `documents-original`: private, authenticated access only
- `documents-annotated`: private, authenticated access only
- `model-assets`: public read for frontend model assets

**Row Level Security (RLS):**
- `individual` users can only read/write their own documents
- `verifier` users can read all documents assigned to them
- `admin` users have full access

---

## MODULE 11: FRONTEND UI/UX

### Design Principles
- Clean, professional, minimal — inspired by modern gov-tech and fintech dashboards
- Responsive for both desktop and mobile (many users will upload phone photos on mobile)
- Real-time feedback during processing (streaming progress updates via WebSocket or SSE)
- Accessibility compliant (WCAG 2.1 AA)

### Core Pages & Components

**1. Upload Page**
- Large drag-and-drop zone with camera capture option (mobile)
- Real-time file preview with image rotation/crop tool
- Document type auto-detection with manual override
- Multiple file upload for batch verification
- File format and size validation with clear error messages

**2. Processing Page (Real-time)**
- Animated pipeline progress indicator showing each module as it completes:
  - 📄 Preprocessing... ✅
  - 🔍 OCR Extraction... ✅
  - 📏 Rule Validation... ✅
  - 🧠 AI Forgery Detection... (spinner)
  - 📊 Generating Report...
- Estimated time remaining
- WebSocket connection for real-time status updates

**3. Results Page**
- Large verdict banner (GREEN/YELLOW/RED) with confidence score as a circular gauge
- Side-by-side view: original document | annotated document (with forgery highlights)
- Collapsible cards for each validation module's results
- "Rule Violations" section with human-readable descriptions
- Extracted data table showing all OCR-extracted fields
- "Download Report" button (generates PDF report)
- Grad-CAM heatmap toggle overlay

**4. Dashboard / History Page**
- Table of all submitted documents with verdict badges
- Filters: date range, document type, verdict
- Analytics charts: verdict distribution, document type distribution, fraud rate over time
- Search by document hash, name, or PRN (for SPPU marksheets)

**5. Admin Panel (for verifier/admin roles)**
- View all documents across users
- Override verdict (human-in-the-loop)
- Model performance metrics
- Reprocess documents with updated models

---

## DATA AUGMENTATION STRATEGY (FOR MODEL TRAINING)

### Augmentation Goals
- Make models robust to real-world document capture conditions (phone photos, old scanners, varying lighting)
- Expose models to geometric distortions without losing document feature integrity
- Generate sufficient training data for each document type, including rare forgery types

### Augmentation Categories

**Category 1: Geometric (simulate photo capture)**
- Rotation: ±5° (subtle, for scans), ±45° (aggressive, for phone photos)
- Perspective warp: simulate phone held at angle (up to 30° tilt)
- Horizontal flip: for mirror-image scans
- Random crop and zoom: simulate partial document capture

**Category 2: Photometric (simulate lighting/quality)**
- Brightness/contrast jitter
- Random shadow injection (simulate hand or object shadow)
- JPEG compression at varying quality (60–95)
- Gaussian blur (simulate out-of-focus)
- Motion blur (simulate camera shake)
- Film grain / Gaussian noise
- Color temperature shift (warm/cool lighting)

**Category 3: Document-Specific**
- Simulate creases/folds using thin-plate spline transforms
- Simulate stains/marks using random ellipse overlays with low opacity
- Simulate lamination glare with specular highlight overlay
- Simulate ink fading using desaturation in specific regions

**Category 4: Forgery Augmentation (for CNN training only)**
- Copy-paste splicing: copy a region from Document A onto Document B
- Text replacement: use inpainting to remove text and re-render different text in the same font
- Seal/stamp replacement: overlay degraded or mismatched seals
- Photo swap in ID documents

### Augmentation Library
Use **Albumentations** for all augmentation. All augmentations must be applied with reproducible seeds for dataset versioning.

---

## PERFORMANCE TARGETS

| Module | Target Metric |
|---|---|
| OCR Extraction (SPPU) | Field-level accuracy ≥ 90% on layered documents |
| OCR Extraction (Aadhaar/PAN) | Field-level accuracy ≥ 95% |
| Rule Validation | Zero false negatives on rule violations (100% recall) |
| CNN Forgery Detection | AUC ≥ 0.96, F1 ≥ 0.94 |
| Isolation Forest | Anomaly detection recall ≥ 85% |
| End-to-End Processing Time | < 10 seconds per document |
| Overall System Accuracy | ≥ 96% on held-out test set |

---

## ADDITIONAL IMPORTANT CONSIDERATIONS

### 1. Privacy & Security
- All uploaded documents contain sensitive PII (Aadhaar, PAN, grades)
- Enforce HTTPS everywhere
- Encrypt documents at rest in Supabase Storage (AES-256)
- Auto-delete original documents from storage after 30 days (configurable)
- Never log raw document content — only hashes and metadata
- Aadhaar numbers must be masked in all logs and reports (show only last 4 digits)
- Implement rate limiting on the upload API endpoint

### 2. Model Versioning & Continuous Improvement
- Store model version used for each verification result in the database
- Allow reprocessing of historical documents with newer models
- Implement A/B testing infrastructure for model updates
- Maintain a feedback loop: allow verifiers to flag incorrect verdicts, use corrections to improve model

### 3. Explainability
- Every verdict must be explainable: show exactly which rules failed, which regions were flagged by CNN, which features were anomalous in Isolation Forest
- Use plain-English summaries in the report (auto-generated using a small LLM or template-based generation)
- Never return a "black box" result — every flag must have a reason

### 4. Edge Case Handling
- Documents with extremely poor image quality: flag as "Image quality insufficient for reliable verification" and request re-upload
- Partial documents (cropped or folded): flag specific fields as "not extractable" rather than failing the whole document
- Unknown document type (classifier confidence < 85%): request manual document type selection before proceeding
- Multi-page PDFs: verify each page independently, then produce a combined report

### 5. Batch Processing
- Support batch upload of up to 50 documents at a time
- Process in parallel using a task queue (Celery + Redis or Supabase Edge Functions)
- Send email/notification when batch processing completes

---

## IMPLEMENTATION PHASES

### Phase 1 — Core MVP (SPPU Marksheets only)
- Upload + preprocessing pipeline
- Tesseract OCR + LLM fallback for layered documents
- Rule-based validation for SPPU marksheets
- Basic CNN (ResNet-50) for forgery detection
- Simple frontend with upload + results display
- Supabase database setup

### Phase 2 — Expanded Document Support
- Add Aadhaar Card and PAN Card support
- Improve CNN with EfficientNet-B4 + ELA
- Implement Isolation Forest module
- NLP semantic consistency checker
- Full annotated report with Grad-CAM heatmap

### Phase 3 — Experience Certificates + Full UI
- Experience Certificate support
- Complete frontend dashboard
- Batch processing
- Admin panel
- Report PDF export

### Phase 4 — Hardening & Optimization
- Model distillation for speed optimization
- Full data augmentation pipeline + model retraining
- End-to-end testing + adversarial testing
- Security audit
- Production deployment

---

*This prompt defines the complete scope, architecture, and implementation plan for the Automated Multi-Document Verification System. Every AI agent, developer, or model implementing this system should follow this specification as the primary reference document.*
