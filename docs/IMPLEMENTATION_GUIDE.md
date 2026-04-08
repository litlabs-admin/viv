# Document Verification System - Complete Implementation Guide

> **Context for AI assistants (Claude Code):** This is a college BE (Bachelor of Engineering) project. It does NOT need production-grade security, authentication, deployment, or scalability. The goal is a working local demo that accurately verifies documents and impresses the teacher. All components run locally on the student's machine. The LLM component uses **LM Studio** (free, local). No cloud APIs, no paid services.

---

## PROJECT SUMMARY

Build a local, end-to-end Automated Document Verification System that:
1. Accepts uploads of Indian documents (SPPU Marksheets, Aadhaar, PAN, Experience Certificates)
2. Extracts text via OCR + LLM fallback (LM Studio)
3. Validates extracted data using rules, NLP, CNN forgery detection, and anomaly detection
4. Produces a confidence score and annotated verification report

**Reference spec:** `docs/document_verification_system_prompt.md`

---

## TECH STACK (Simplified for Local/College Use)

| Layer | Technology | Why |
|---|---|---|
| **Backend** | Python 3.11+ with FastAPI | Simple, async, auto-generates API docs |
| **Frontend** | React 18 + TailwindCSS (Vite) | Fast setup, looks professional |
| **Database** | SQLite via SQLAlchemy | Zero setup, single file DB, no server needed |
| **OCR** | Tesseract OCR (pytesseract) | Free, local, no API key |
| **LLM (Vision + Text)** | LM Studio running **LLaVA 1.6 7B** or **MiniCPM-V 2.6** | Free local multimodal model for OCR fallback + report generation |
| **CNN Model** | PyTorch - EfficientNet-B0 (lighter than B4) | Pretrained on ImageNet, fine-tune for forgery |
| **NLP** | spaCy (en_core_web_sm) | Free, fast, local NER |
| **Anomaly Detection** | scikit-learn Isolation Forest | Simple, effective |
| **Image Processing** | OpenCV + Pillow | Standard, well-documented |

### LM Studio Setup
- **Download:** https://lmstudio.ai (free for local use)
- **Model to download inside LM Studio:**
  - Primary: `lmstudio-community/llava-v1.6-mistral-7b-gguf` (multimodal - can read document images)
  - Alternative: `lmstudio-community/MiniCPM-V-2_6-GGUF` (better for document understanding)
  - Text-only fallback: `lmstudio-community/Meta-Llama-3.1-8B-Instruct-GGUF` (for report generation)
- **How it works:** LM Studio runs a local OpenAI-compatible API server at `http://localhost:1234/v1`
- **Your code calls it exactly like OpenAI API** using the `openai` Python package, just pointing to localhost

---

## FOLDER STRUCTURE

```
BE-PROJECT/
├── docs/
│   ├── document_verification_system_prompt.md   # Original spec (already exists)
│   └── IMPLEMENTATION_GUIDE.md                  # This file
│
├── backend/
│   ├── main.py                        # FastAPI app entry point
│   ├── requirements.txt               # Python dependencies
│   ├── config.py                      # Configuration (paths, thresholds, LM Studio URL)
│   ├── database.py                    # SQLite setup with SQLAlchemy
│   ├── models/                        # SQLAlchemy DB models
│   │   └── schemas.py                 # Document, VerificationResult tables
│   │
│   ├── routers/                       # API route handlers
│   │   ├── upload.py                  # POST /api/upload
│   │   ├── verify.py                  # POST /api/verify/{doc_id}
│   │   ├── results.py                 # GET /api/results/{doc_id}
│   │   └── history.py                 # GET /api/history
│   │
│   ├── modules/                       # Core verification pipeline modules
│   │   ├── preprocessor.py            # Module 1: Image preprocessing
│   │   ├── ocr_engine.py              # Module 2: Tesseract OCR + LM Studio fallback
│   │   ├── classifier.py              # Module 3: Document type classification
│   │   ├── rule_validator.py          # Module 4: Rule-based validation
│   │   ├── nlp_checker.py             # Module 5: NLP semantic consistency
│   │   ├── cnn_forgery.py             # Module 6: CNN forgery detection
│   │   ├── anomaly_detector.py        # Module 7: Isolation Forest
│   │   ├── score_aggregator.py        # Module 8: Weighted confidence scoring
│   │   └── report_generator.py        # Module 9: Report + annotation generation
│   │
│   ├── pipeline.py                    # Orchestrates all modules in sequence
│   │
│   ├── ml_models/                     # Saved/trained model files
│   │   ├── efficientnet_forgery.pth   # Trained CNN weights (generated after training)
│   │   ├── doc_classifier.pth         # Document type classifier weights
│   │   └── isolation_forest.pkl       # Trained Isolation Forest model
│   │
│   ├── templates/                     # Document templates for matching
│   │   ├── sppu_marksheet_template.json
│   │   ├── aadhaar_template.json
│   │   ├── pan_template.json
│   │   └── experience_cert_template.json
│   │
│   ├── training/                      # Model training scripts
│   │   ├── train_forgery_cnn.py       # Train EfficientNet for forgery
│   │   ├── train_classifier.py        # Train document type classifier
│   │   ├── train_isolation_forest.py  # Train anomaly detector
│   │   ├── generate_synthetic_data.py # Generate fake forged docs for training
│   │   └── dataset/                   # Training data (gitignored)
│   │       ├── authentic/
│   │       │   ├── sppu_marksheet/
│   │       │   ├── aadhaar/
│   │       │   ├── pan/
│   │       │   └── experience_cert/
│   │       └── forged/
│   │           ├── sppu_marksheet/
│   │           ├── aadhaar/
│   │           ├── pan/
│   │           └── experience_cert/
│   │
│   ├── uploads/                       # Uploaded documents (gitignored)
│   ├── outputs/                       # Annotated images & reports (gitignored)
│   └── tests/                         # Unit tests
│       ├── test_preprocessor.py
│       ├── test_ocr.py
│       ├── test_rules.py
│       └── test_pipeline.py
│
├── frontend/
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   ├── index.html
│   ├── src/
│   │   ├── App.jsx
│   │   ├── main.jsx
│   │   ├── api/
│   │   │   └── client.js              # Axios API client
│   │   ├── pages/
│   │   │   ├── UploadPage.jsx         # Document upload UI
│   │   │   ├── ProcessingPage.jsx     # Real-time progress display
│   │   │   ├── ResultsPage.jsx        # Verification results display
│   │   │   └── HistoryPage.jsx        # Past verifications
│   │   ├── components/
│   │   │   ├── FileUploader.jsx       # Drag-and-drop upload component
│   │   │   ├── VerdictBanner.jsx      # Green/Yellow/Red verdict display
│   │   │   ├── ConfidenceGauge.jsx    # Circular confidence score gauge
│   │   │   ├── ModuleResultCard.jsx   # Expandable card per module
│   │   │   ├── AnnotatedImage.jsx     # Side-by-side original vs annotated
│   │   │   ├── ExtractedDataTable.jsx # Table showing OCR extracted fields
│   │   │   └── Navbar.jsx
│   │   └── styles/
│   │       └── globals.css
│   └── public/
│
├── sample_documents/                  # Sample test documents (for demo)
│   ├── authentic/
│   │   ├── sample_marksheet.jpg
│   │   ├── sample_aadhaar.jpg
│   │   ├── sample_pan.jpg
│   │   └── sample_experience.jpg
│   └── forged/
│       ├── tampered_marksheet.jpg
│       └── tampered_pan.jpg
│
├── .gitignore
└── README.md
```

---

## PHASE-WISE IMPLEMENTATION PLAN

---

### PHASE 1: Foundation & Preprocessing (Days 1-3)

**Goal:** Set up the project skeleton, backend server, database, file upload, and image preprocessing pipeline.

#### Tasks

1. **Project Setup**
   - Initialize git repo
   - Create folder structure as shown above
   - Create Python virtual environment: `python -m venv venv`
   - Create `requirements.txt` with initial dependencies:
     ```
     fastapi==0.115.0
     uvicorn==0.30.0
     python-multipart==0.0.9
     sqlalchemy==2.0.35
     pillow==10.4.0
     opencv-python==4.10.0.84
     pytesseract==0.3.13
     numpy==1.26.4
     pydantic==2.9.0
     ```
   - Install: `pip install -r requirements.txt`
   - Install Tesseract OCR system package:
     - macOS: `brew install tesseract`
   - Create React frontend: `npm create vite@latest frontend -- --template react`
   - Install TailwindCSS in frontend: follow Vite + Tailwind docs

2. **Database Setup (`backend/database.py`)**
   - Use SQLAlchemy with SQLite (`sqlite:///./verification.db`)
   - Create tables:
     - `documents`: id, filename, doc_type, file_path, upload_time
     - `verification_results`: id, document_id, verdict, confidence_score, ocr_score, rule_score, nlp_score, cnn_score, anomaly_score, full_report_json, created_at

3. **FastAPI Skeleton (`backend/main.py`)**
   - Create FastAPI app with CORS middleware (allow localhost:5173 for Vite dev server)
   - Mount `/uploads` as static files
   - Include routers for upload, verify, results, history

4. **File Upload Endpoint (`backend/routers/upload.py`)**
   - `POST /api/upload` - accepts image/PDF file
   - Save to `backend/uploads/` with UUID filename
   - Create DB record in `documents` table
   - Return `{ document_id, filename, status: "uploaded" }`

5. **Preprocessing Module (`backend/modules/preprocessor.py`)**
   - Implement these functions:
     - `load_image(file_path)` -> numpy array (handle JPEG, PNG, PDF)
     - `correct_orientation(image)` -> auto-rotate using EXIF data
     - `deskew(image)` -> detect skew angle with Hough lines, rotate to correct
     - `enhance_image(image)` -> apply CLAHE contrast enhancement + denoising
     - `binarize(image)` -> adaptive thresholding for cleaner OCR
   - For PDF support: `pip install pdf2image` + install poppler (`brew install poppler`)
   - Keep it simple: no need for ESRGAN or glare removal for college demo

#### Success Metrics (Phase 1)
- [ ] `pip install -r requirements.txt` runs without errors
- [ ] FastAPI server starts: `uvicorn main:app --reload` at localhost:8000
- [ ] `/docs` shows Swagger UI with upload endpoint
- [ ] Can upload a document image via Swagger UI, file saved to disk, DB record created
- [ ] Preprocessing pipeline takes an image and outputs a clean, deskewed, enhanced version
- [ ] React app runs at localhost:5173 with a basic page

---

### PHASE 2: OCR Engine + LM Studio Integration (Days 4-6)

**Goal:** Extract structured text from documents using Tesseract + LM Studio as intelligent fallback.

#### Prerequisites
- Download and install LM Studio from https://lmstudio.ai
- Inside LM Studio: download `llava-v1.6-mistral-7b-gguf` (Q4_K_M quantization recommended for 8GB+ RAM)
- Start LM Studio's local server (it runs at `http://localhost:1234/v1`)

#### Tasks

1. **Tesseract OCR (`backend/modules/ocr_engine.py`)**
   - `extract_text_tesseract(image)` -> raw text string
   - `extract_with_confidence(image)` -> list of (text, confidence, bounding_box) tuples
   - Use `pytesseract.image_to_data()` for word-level confidence scores
   - Calculate overall confidence as mean of word confidences
   - Add to requirements: `pytesseract`

2. **LM Studio Vision Fallback**
   - Install: `pip install openai` (used as client for LM Studio's OpenAI-compatible API)
   - When Tesseract confidence < 70%, call LM Studio's vision model
   - Function: `extract_with_llm(image_path, doc_type)` 
   - Convert image to base64, send to LM Studio with a prompt like:
     ```
     You are a document data extractor. Extract all fields from this {doc_type} image.
     Return ONLY valid JSON with these fields: {schema_for_doc_type}
     ```
   - Parse LLM JSON response, validate against expected schema
   - Code pattern for calling LM Studio:
     ```python
     from openai import OpenAI
     
     client = OpenAI(base_url="http://localhost:1234/v1", api_key="lm-studio")
     
     response = client.chat.completions.create(
         model="llava-v1.6-mistral-7b",  # whatever model name LM Studio shows
         messages=[
             {"role": "user", "content": [
                 {"type": "text", "text": "Extract all fields from this document as JSON..."},
                 {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{base64_image}"}}
             ]}
         ],
         temperature=0.1,
         max_tokens=2000
     )
     extracted = response.choices[0].message.content
     ```

3. **Document Field Schemas (`backend/templates/`)**
   - Create JSON schema files for each document type defining expected fields
   - `sppu_marksheet_template.json`: prn, student_name, semester, subjects[], sgpa, etc.
   - `aadhaar_template.json`: aadhaar_number, name, dob, gender, address
   - `pan_template.json`: pan_number, name, fathers_name, dob
   - `experience_cert_template.json`: employee_name, company_name, dates, etc.

4. **Combined OCR Pipeline**
   - `extract_document_data(image, doc_type)` -> structured dict
   - Flow: Tesseract first -> check confidence -> LLM fallback if needed -> validate against schema -> return

#### Success Metrics (Phase 2)
- [ ] LM Studio running locally, server accessible at localhost:1234
- [ ] Tesseract extracts readable text from a clear document scan
- [ ] LM Studio vision model extracts structured JSON from a document image
- [ ] Fallback mechanism works: low-confidence Tesseract triggers LLM extraction
- [ ] Extracted data matches expected schema for at least one document type

---

### PHASE 3: Document Classification + Rule-Based Validation (Days 7-9)

**Goal:** Auto-classify document type and validate extracted data against domain rules.

#### Tasks

1. **Simple Document Classifier (`backend/modules/classifier.py`)**
   - For college project, use a **keyword-based classifier** instead of training a CNN:
     - If text contains "Savitribai Phule" or "SPPU" or "SGPA" -> `sppu_marksheet`
     - If text contains "AADHAAR" or "UIDAI" or 12-digit number pattern -> `aadhaar_card`
     - If text contains "PERMANENT ACCOUNT NUMBER" or "INCOME TAX" -> `pan_card`
     - If text contains "experience" + "certificate" or "relieving" -> `experience_certificate`
   - Also try a visual approach: use LM Studio vision to classify:
     ```
     "What type of Indian document is this? Reply with ONLY one of: sppu_marksheet, aadhaar_card, pan_card, experience_certificate"
     ```
   - Combine text + visual classification for better accuracy

2. **Rule Validator (`backend/modules/rule_validator.py`)**
   - Implement validation functions per document type:
   
   **SPPU Marksheet rules:**
   - `validate_prn(prn)` -> must be 11 digits (basic check)
   - `validate_marks_total(subjects)` -> internal + external == total for each subject
   - `validate_grade(total_marks)` -> grade matches SPPU grading scale
   - `validate_sgpa(subjects, claimed_sgpa)` -> computed SGPA matches within ±0.05
   - `validate_result(subjects, claimed_result)` -> PASS/FAIL consistency
   
   **Aadhaar rules:**
   - `validate_aadhaar_checksum(number)` -> Verhoeff algorithm implementation
   - `validate_dob(dob_string)` -> valid date, age 0-120
   
   **PAN rules:**
   - `validate_pan_format(pan)` -> regex `[A-Z]{5}[0-9]{4}[A-Z]`
   - `validate_pan_name_match(pan, name)` -> 5th char matches surname initial
   
   **Experience Certificate rules:**
   - `validate_dates(joining, relieving)` -> relieving after joining
   - `validate_duration(joining, relieving, claimed_duration)` -> consistent within ±1 month
   
   - Return a result object: `{ score: float, passed: list, failed: list[{rule, description, severity}] }`

3. **Verhoeff Algorithm** (for Aadhaar validation)
   - Implement the standard Verhoeff checksum algorithm (available as public pseudocode)
   - This is a strong demo point for the teacher

#### Success Metrics (Phase 3)
- [ ] Classifier correctly identifies document type from 4 sample images
- [ ] SPPU marksheet SGPA calculation works correctly
- [ ] Aadhaar Verhoeff checksum correctly validates real Aadhaar format numbers
- [ ] PAN regex + name matching works
- [ ] Rule validator returns structured pass/fail results with descriptions

---

### PHASE 4: CNN Forgery Detection (Days 10-14)

**Goal:** Build and train a CNN model that detects visual tampering in documents. This is the **most important module** (40% weight in final score).

#### Tasks

1. **Prepare Training Data (`backend/training/generate_synthetic_data.py`)**
   - Since you won't have real forged documents, **generate synthetic forgeries**:
     - Take authentic document images
     - **Text replacement forgery:** Use OpenCV to select a text region, blank it out with background color, write different text using `cv2.putText()` with a similar font
     - **Copy-paste forgery:** Copy a grade/marks cell from one location, paste to another using `cv2.seamlessClone()` (Poisson blending)
     - **Color inconsistency:** Slightly alter brightness/contrast of a pasted region
     - **Noise injection:** Add different JPEG compression to a region vs the rest
   - Create at least:
     - 50 "authentic" images (use data augmentation to expand from ~10-15 real scans)
     - 50 "forged" images (generated synthetically from the authentic ones)
   - Use Albumentations for augmentation: `pip install albumentations`
   - Save in `backend/training/dataset/authentic/` and `backend/training/dataset/forged/`

2. **Error Level Analysis (ELA) (`backend/modules/cnn_forgery.py`)**
   - Implement ELA as a preprocessing step:
     ```python
     def compute_ela(image_path, quality=90):
         # Re-save at known quality
         # Compute pixel-wise difference
         # Amplify difference (scale * 15)
         # Tampered regions show brighter in ELA image
     ```
   - This alone is a powerful visual indicator of tampering
   - Show ELA image in the results (impressive for demo)

3. **Train EfficientNet-B0 (`backend/training/train_forgery_cnn.py`)**
   - Use `torchvision.models.efficientnet_b0(pretrained=True)`
   - Replace final classifier layer: `model.classifier[1] = nn.Linear(1280, 2)` (authentic vs forged)
   - Training setup:
     - Input: 224x224 image patches
     - Batch size: 16
     - Epochs: 20-30
     - Optimizer: Adam, lr=1e-4
     - Loss: CrossEntropyLoss
     - Train/Val split: 80/20
   - Save model to `backend/ml_models/efficientnet_forgery.pth`
   - Add to requirements: `torch`, `torchvision`, `albumentations`

4. **Grad-CAM Visualization**
   - Implement Grad-CAM to show WHERE the model thinks tampering is:
     ```python
     # Use hooks to capture gradients from last conv layer
     # Generate heatmap overlay on original image
     ```
   - This is a KEY demo feature - shows the model is "explainable"
   - Save heatmap overlay image to `backend/outputs/`

5. **Forgery Detection Pipeline**
   - `detect_forgery(image)` -> returns:
     ```python
     {
         "forgery_detected": bool,
         "forgery_probability": float,
         "ela_image": numpy_array,
         "gradcam_heatmap": numpy_array,
         "forgery_regions": [{"bbox": [...], "confidence": float, "type": str}]
     }
     ```

#### Success Metrics (Phase 4)
- [ ] Synthetic forged dataset generated (50+ authentic, 50+ forged)
- [ ] ELA correctly shows brighter regions on tampered areas
- [ ] CNN training completes without errors, achieves >80% validation accuracy
- [ ] Grad-CAM heatmap correctly highlights tampered regions
- [ ] Full forgery detection pipeline returns structured results

---

### PHASE 5: NLP + Anomaly Detection + Score Aggregation (Days 15-17)

**Goal:** Add NLP consistency checking, Isolation Forest anomaly detection, and combine all module scores.

#### Tasks

1. **NLP Semantic Checker (`backend/modules/nlp_checker.py`)**
   - Install spaCy: `pip install spacy && python -m spacy download en_core_web_sm`
   - `check_entity_consistency(extracted_data)`:
     - Extract named entities (PERSON, ORG, DATE) from all text fields
     - Check name appears consistently across fields
     - Check dates are temporally consistent (DoB < graduation < experience)
   - `check_institution_validity(college_name)`:
     - Maintain a small JSON list of valid SPPU-affiliated colleges
     - Check if extracted college name fuzzy-matches any entry (use `fuzzywuzzy`)
   - Return: `{ score: float, findings: list[str] }`

2. **Isolation Forest (`backend/modules/anomaly_detector.py`)**
   - For SPPU marksheets, build feature vector:
     - SGPA value
     - Mean marks across subjects
     - Std dev of marks
     - Number of subjects
     - Ratio of internal to external marks
   - Train on feature vectors from ~20-30 authentic marksheet data points (can be manually created/entered)
   - Save model: `joblib.dump(model, 'ml_models/isolation_forest.pkl')`
   - At inference: `detect_anomaly(feature_vector)` -> anomaly_score (0 to 1)
   - Add to requirements: `scikit-learn`, `joblib`

3. **Score Aggregator (`backend/modules/score_aggregator.py`)**
   - Combine all module scores with weights:
     ```python
     weights = {
         'cnn': 0.40,
         'rule': 0.25,
         'nlp': 0.15,
         'anomaly': 0.10,
         'ocr': 0.10
     }
     
     final_score = (
         weights['cnn'] * (1 - cnn_forgery_probability) +
         weights['rule'] * rule_score +
         weights['nlp'] * nlp_score +
         weights['anomaly'] * (1 - anomaly_score) +
         weights['ocr'] * ocr_confidence
     )
     ```
   - Apply hard override rules:
     - If any critical rule fails -> FRAUDULENT
     - If CNN forgery probability > 0.90 -> at least NEEDS_REVIEW
   - Determine verdict:
     - 0.85-1.00 -> VERIFIED (green)
     - 0.65-0.84 -> NEEDS_REVIEW (yellow)
     - 0.00-0.64 -> FRAUDULENT (red)

4. **Report Generator (`backend/modules/report_generator.py`)**
   - `generate_report(document_id, all_module_results)` -> JSON report
   - Annotate original image with bounding boxes around tampered regions
   - Save annotated image to `backend/outputs/`
   - Optionally use LM Studio to generate a plain-English summary:
     ```
     "Given these verification results: {results_json}, write a 2-3 sentence human-readable summary explaining the verdict."
     ```

5. **Full Pipeline Orchestrator (`backend/pipeline.py`)**
   - `run_verification_pipeline(document_id)`:
     1. Load document from DB
     2. Preprocess image
     3. Classify document type
     4. Extract text (OCR + LLM)
     5. Run rule validation
     6. Run NLP consistency check
     7. Run CNN forgery detection
     8. Run anomaly detection
     9. Aggregate scores
     10. Generate report
     11. Save results to DB
     12. Return full result

#### Success Metrics (Phase 5)
- [ ] NLP checker detects name inconsistencies across document fields
- [ ] Isolation Forest flags documents with unusual statistical patterns
- [ ] Score aggregator produces correct weighted scores
- [ ] Hard override rules work (critical failure -> FRAUDULENT)
- [ ] Full pipeline runs end-to-end on a test document and produces a verdict
- [ ] Annotated output image shows bounding boxes on flagged regions

---

### PHASE 6: Frontend UI (Days 18-22)

**Goal:** Build a clean, professional React frontend that showcases the verification system.

#### Tasks

1. **Setup & Layout**
   - Install dependencies: `npm install axios react-router-dom react-dropzone`
   - Install TailwindCSS + configure
   - Create Navbar with: Upload | History
   - Set up React Router with routes: `/`, `/upload`, `/processing/:id`, `/results/:id`, `/history`

2. **Upload Page (`frontend/src/pages/UploadPage.jsx`)**
   - Drag-and-drop zone using `react-dropzone`
   - Image preview after file selection
   - Document type dropdown (auto-detect or manual select)
   - "Verify Document" button -> calls `POST /api/upload` then `POST /api/verify/{id}`
   - Show file size, type validation errors

3. **Processing Page (`frontend/src/pages/ProcessingPage.jsx`)**
   - Poll `GET /api/results/{id}` every 2 seconds until status is "completed"
   - Show step-by-step progress:
     - Preprocessing... (spinner or checkmark)
     - OCR Extraction...
     - Rule Validation...
     - AI Forgery Detection...
     - Generating Report...
   - Use a simple progress bar or stepper component

4. **Results Page (`frontend/src/pages/ResultsPage.jsx`)**
   - **Verdict Banner**: Large colored banner (green/yellow/red) with verdict text
   - **Confidence Gauge**: Circular progress showing score (use a simple SVG circle or CSS)
   - **Side-by-side Images**: Original document | Annotated document (with forgery highlights)
   - **Module Result Cards**: Expandable/collapsible cards for each module:
     - OCR Extraction: confidence %, fields extracted
     - Rule Validation: passed/failed rules list
     - NLP Consistency: findings
     - CNN Forgery: probability, Grad-CAM heatmap image
     - Anomaly Detection: score, flagged features
   - **Extracted Data Table**: Show all OCR-extracted fields in a clean table
   - **Summary Text**: LLM-generated plain-English explanation

5. **History Page (`frontend/src/pages/HistoryPage.jsx`)**
   - Table showing all past verifications
   - Columns: Date, Filename, Document Type, Verdict (with colored badge), Score
   - Click row to navigate to results page
   - Simple filter by document type and verdict

6. **Styling**
   - Use TailwindCSS for clean, modern look
   - Color scheme: dark sidebar or top nav, white content area
   - Responsive (looks good on both desktop and mobile)
   - Verdict colors: green (#22c55e), yellow (#eab308), red (#ef4444)

#### Success Metrics (Phase 6)
- [ ] Upload page accepts file drag-and-drop and previews image
- [ ] Processing page shows real-time progress updates
- [ ] Results page displays verdict with all module details
- [ ] Side-by-side original vs annotated image comparison works
- [ ] Grad-CAM heatmap is visible on results page
- [ ] History page lists all past verifications
- [ ] UI is clean and professional looking

---

### PHASE 7: Integration, Testing & Demo Prep (Days 23-25)

**Goal:** Connect everything end-to-end, test with sample documents, prepare demo.

#### Tasks

1. **End-to-End Integration Testing**
   - Test full flow: Upload -> Process -> View Results for each document type
   - Test with both authentic and tampered sample documents
   - Fix any bugs in the pipeline
   - Ensure all API endpoints return correct data

2. **Prepare Sample Documents**
   - Collect or create sample documents for demo:
     - 2-3 authentic documents (each type)
     - 2-3 tampered documents (modify marks, change names, etc.)
   - Place in `sample_documents/` folder
   - Create a demo script: which documents to upload in what order to show different verdicts

3. **Error Handling**
   - Add basic try/except around each pipeline module
   - If one module fails, still run the others and note the failure in the report
   - Show user-friendly error messages in frontend

4. **Performance Check**
   - Measure end-to-end processing time
   - If > 30 seconds, consider:
     - Reducing CNN input image size
     - Skipping non-essential modules for demo
     - Caching LM Studio results

5. **Demo Preparation**
   - Ensure LM Studio is running before demo
   - Prepare a sequence of documents to show:
     1. First: authentic document -> shows VERIFIED (green)
     2. Second: tampered document -> shows FRAUDULENT (red)
     3. Third: borderline document -> shows NEEDS_REVIEW (yellow)
   - Test this exact sequence multiple times
   - Have backup plan if LM Studio is slow (show pre-generated results)

#### Success Metrics (Phase 7)
- [ ] Full pipeline works end-to-end for all 4 document types
- [ ] Authentic documents score > 0.85 (VERIFIED)
- [ ] Tampered documents score < 0.65 (FRAUDULENT)
- [ ] Processing time is under 30 seconds per document
- [ ] Demo sequence runs smoothly 3 times in a row
- [ ] No crashes or unhandled errors during demo flow

---

## CRITICAL DEPENDENCIES TO INSTALL

### System Dependencies (macOS)
```bash
brew install tesseract
brew install poppler    # for PDF support
```

### Python Dependencies (complete `requirements.txt`)
```
fastapi==0.115.0
uvicorn==0.30.0
python-multipart==0.0.9
sqlalchemy==2.0.35
pillow==10.4.0
opencv-python==4.10.0.84
pytesseract==0.3.13
numpy==1.26.4
pydantic==2.9.0
openai==1.50.0
torch==2.4.0
torchvision==0.19.0
albumentations==1.4.0
spacy==3.7.0
scikit-learn==1.5.0
joblib==1.4.0
fuzzywuzzy==0.18.0
python-Levenshtein==0.25.0
pdf2image==1.17.0
```

### Frontend Dependencies
```
react-router-dom
axios
react-dropzone
```

---

## HOW TO RUN THE PROJECT

### Terminal 1: LM Studio
1. Open LM Studio
2. Load `llava-v1.6-mistral-7b` model
3. Click "Start Server" (runs at localhost:1234)

### Terminal 2: Backend
```bash
cd backend
source venv/bin/activate   # or: . venv/bin/activate
uvicorn main:app --reload --port 8000
```

### Terminal 3: Frontend
```bash
cd frontend
npm run dev
# Opens at http://localhost:5173
```

### Access
- Frontend: http://localhost:5173
- Backend API docs: http://localhost:8000/docs
- LM Studio API: http://localhost:1234/v1

---

## KEY SIMPLIFICATIONS vs ORIGINAL SPEC

| Original Spec | College Version | Reason |
|---|---|---|
| Supabase (PostgreSQL + Auth) | SQLite (no auth) | No server setup needed |
| EfficientNet-B4 | EfficientNet-B0 | Faster training, smaller model |
| Google Vision API fallback | LM Studio only | Free, local |
| Docker deployment | Just run locally | No deployment needed |
| ESRGAN super-resolution | Skip | Overkill for demo |
| WebSocket real-time updates | Polling every 2s | Much simpler to implement |
| Batch processing (50 docs) | Single document at a time | Sufficient for demo |
| Rate limiting, encryption, RLS | None | College project, not production |
| YOLO for table detection | Skip | LM Studio handles this |
| Model versioning / A/B testing | Skip | Single model version is fine |
| Admin panel / roles | Skip | Single user is fine |

---

## TIPS FOR IMPRESSING THE TEACHER

1. **Grad-CAM heatmaps** - Show the model visually highlighting tampered regions. This is very visual and impressive.
2. **ELA (Error Level Analysis)** - Show the ELA image side-by-side with the original. Tampered regions glow differently.
3. **Verhoeff algorithm** - Mention you implemented the actual government checksum algorithm for Aadhaar validation.
4. **SGPA recalculation** - Live demo: show how the system catches a marksheet where someone changed the SGPA number.
5. **LM Studio integration** - Emphasize this runs 100% locally with no API costs, using open-source AI models.
6. **Multi-layered approach** - 5 different validation modules combine their scores. This is the "multi-AI pipeline" aspect.
7. **Explainability** - Every verdict has a clear reason. Nothing is a black box.

---

## NOTES FOR FUTURE CLAUDE CODE SESSIONS

- The project root is `/Users/vivek/BE-PROJECT/`
- The original detailed spec is at `docs/document_verification_system_prompt.md`
- This implementation guide is at `docs/IMPLEMENTATION_GUIDE.md`
- LM Studio runs locally at `http://localhost:1234/v1` and uses OpenAI-compatible API
- The primary vision model for LM Studio is LLaVA 1.6 (7B, GGUF format)
- This is a college project - keep things simple, working, and demo-ready
- SQLite is the database - no external DB server needed
- No authentication/authorization needed
- Focus on accuracy and visual results over robustness
- When implementing a module, refer to the corresponding MODULE section in the original spec for detailed requirements
- The CNN module has the highest weight (0.40) and is the most important to get right
- For training data, generate synthetic forgeries programmatically rather than collecting real forged docs
