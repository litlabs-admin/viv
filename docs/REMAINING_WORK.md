# Remaining Work — Phases 6 & 7

**Last updated:** 2026-04-09

---

## Completed Phases (1-5) — Backend Fully Done

| Phase | Status | Tests |
|-------|--------|-------|
| Phase 1: Foundation & Preprocessing | Done | 13 + 10 tests |
| Phase 2: OCR + LM Studio Integration | Done | 33 tests |
| Phase 3: Rule-Based Validation | Done | 51 tests |
| Phase 4: CNN Forgery Detection | Done | 20 tests |
| Phase 5: NLP + Anomaly + Score Aggregation | Done | 76 tests |
| **Total** | **214 tests passing** | |

---

## Phase 6: Frontend UI

The frontend has a basic scaffold (React + Vite + TailwindCSS), but most pages need to be built out properly to match the backend's full API response.

### 6.1 Setup & Config
- [x] React + Vite initialized
- [x] TailwindCSS installed
- [x] react-router-dom, axios, react-dropzone installed
- [x] Basic Navbar, FileUploader, VerdictBanner components exist
- [ ] Set up React Router with all routes: `/`, `/upload`, `/processing/:id`, `/results/:id`, `/history`
- [ ] Configure API base URL (proxy to localhost:8000)

### 6.2 Upload Page (`UploadPage.jsx`)
- [x] Basic page exists (~99 lines)
- [ ] Drag-and-drop file upload with image preview
- [ ] Document type dropdown (auto-detect or manual select)
- [ ] File size and type validation errors
- [ ] "Verify Document" button → calls `POST /api/upload` then `POST /api/verify/{id}`
- [ ] Loading state while uploading
- [ ] Redirect to processing/results page after submission

### 6.3 Processing Page (`ProcessingPage.jsx`)
- [ ] **Create this page** — does not exist yet
- [ ] Poll `GET /api/results/{id}` every 2 seconds until `status: "completed"`
- [ ] Step-by-step progress indicator:
  - Preprocessing... (spinner → checkmark)
  - OCR Extraction...
  - Rule Validation...
  - NLP Analysis...
  - AI Forgery Detection...
  - Anomaly Detection...
  - Generating Report...
- [ ] Auto-redirect to Results page when done

### 6.4 Results Page (`ResultsPage.jsx`)
- [x] Basic page exists (~134 lines)
- [ ] **Verdict Banner** — large colored banner (green/yellow/red) with verdict text and score
- [ ] **Confidence Gauge** — circular SVG progress showing final score percentage
- [ ] **Summary Text** — display the plain-English summary from report generator
- [ ] **Side-by-side Images** — original document | annotated document (with verdict border)
- [ ] **ELA Image** — show Error Level Analysis image from CNN module
- [ ] **Grad-CAM Heatmap** — show heatmap overlay (base64 images from API)
- [ ] **Module Result Cards** (expandable/collapsible):
  - OCR Extraction: extracted fields table
  - Rule Validation: passed rules (green) / failed rules (red) with severity badges
  - NLP Consistency: findings list
  - CNN Forgery: probability bar, ELA image, Grad-CAM heatmap
  - Anomaly Detection: score, anomaly flag
- [ ] **Score Breakdown** — show weighted module scores from `score_aggregation.module_scores`
- [ ] **Extracted Data Table** — show all OCR-extracted fields in a clean table

### 6.5 History Page (`HistoryPage.jsx`)
- [x] Basic page exists (~137 lines)
- [ ] Table showing all past verifications from `GET /api/history`
- [ ] Columns: Date, Filename, Document Type, Verdict (colored badge), Score
- [ ] Click row → navigate to Results page
- [ ] Filter by document type and verdict
- [ ] Handle empty state (no verifications yet)

### 6.6 Styling & Polish
- [ ] Consistent color scheme: dark nav, white content
- [ ] Verdict colors: green (#22c55e), yellow (#eab308), red (#ef4444)
- [ ] Responsive layout (desktop + mobile)
- [ ] Loading spinners/skeletons
- [ ] Error states and toast notifications
- [ ] Professional fonts and spacing

---

## Phase 7: Integration, Testing & Demo Prep

### 7.1 Pipeline Orchestrator (`backend/pipeline.py`)
- [ ] Create `run_verification_pipeline(document_id)` that runs all 9 modules in sequence
- [ ] Each module wrapped in try/except — if one fails, others still run
- [ ] Save full results to `verification_results` DB table
- [ ] Return complete result object

### 7.2 End-to-End Integration Testing
- [ ] Test full flow for each document type: Upload → Process → View Results
- [ ] Test with authentic documents → expect VERIFIED (green, score > 0.85)
- [ ] Test with tampered documents → expect FRAUDULENT (red, score < 0.65)
- [ ] Test with borderline documents → expect NEEDS_REVIEW (yellow)
- [ ] Verify all API endpoints return correct data shapes
- [ ] Test error handling — what happens when LM Studio is down?

### 7.3 Prepare Sample Documents
- [x] `sample_documents/authentic/` has 10 images
- [ ] Add more authentic samples for each document type (Aadhaar, PAN, Experience Cert)
- [ ] Create 2-3 tampered documents in `sample_documents/forged/`:
  - Modified marksheet (changed SGPA/marks)
  - Altered PAN (changed name)
  - Tampered Aadhaar (modified number)
- [ ] Create a **demo script** documenting which documents to upload in what order

### 7.4 Error Handling & Resilience
- [ ] Graceful degradation when LM Studio is offline (skip OCR, use defaults)
- [ ] User-friendly error messages in frontend (not raw stack traces)
- [ ] Handle large file uploads gracefully
- [ ] Timeout handling for LM Studio calls

### 7.5 Performance Optimization
- [ ] Measure end-to-end processing time per document
- [ ] Target: under 30 seconds per document
- [ ] If slow: reduce CNN input size, cache LM Studio results, skip non-essential modules
- [ ] Consider async processing with status polling

### 7.6 Demo Preparation
- [ ] Demo script with exact sequence:
  1. Authentic SPPU marksheet → VERIFIED (green)
  2. Tampered marksheet (changed SGPA) → FRAUDULENT (red)
  3. Borderline document → NEEDS_REVIEW (yellow)
- [ ] Ensure LM Studio is running with correct model before demo
- [ ] Test demo sequence 3+ times end-to-end
- [ ] Backup plan: pre-generated results JSON if LM Studio is slow
- [ ] Prepare talking points for teacher:
  - Verhoeff algorithm for Aadhaar
  - Grad-CAM heatmap explainability
  - Multi-layer AI pipeline (5 modules)
  - 100% local, no cloud APIs
  - ELA visualization

### 7.7 Final Documentation
- [ ] Update README.md with setup instructions
- [ ] Add screenshots of the UI to docs
- [ ] Architecture diagram
- [ ] Record a short demo video (optional but impressive)

---

## Quick Reference — What's Built vs What's Needed

### Backend (COMPLETE)
```
modules/
  ├── preprocessor.py      ✅ Image preprocessing (CLAHE, deskew, binarize)
  ├── classifier.py        ✅ Document type classification (keyword + LLM)
  ├── ocr_engine.py        ✅ LM Studio vision OCR
  ├── rule_validator.py    ✅ Verhoeff, SGPA, PAN, dates (51 tests)
  ├── nlp_checker.py       ✅ NER, name/date consistency, institution matching
  ├── cnn_forgery.py       ✅ ELA + EfficientNet-B0 + Grad-CAM
  ├── anomaly_detector.py  ✅ Isolation Forest (trained, 1.5KB model)
  ├── score_aggregator.py  ✅ Weighted scoring + verdict + overrides
  └── report_generator.py  ✅ Summary + annotated image + full report

ml_models/
  ├── efficientnet_forgery.pth  ✅ Trained CNN (76.7% val accuracy)
  └── isolation_forest.pkl      ✅ Trained anomaly detector

training/
  ├── generate_synthetic_data.py  ✅ Forgery generator
  ├── train_forgery_cnn.py        ✅ CNN training script
  └── train_isolation_forest.py   ✅ Isolation Forest training script
```

### Frontend (NEEDS WORK)
```
src/
  ├── App.jsx                     ⚠️  Needs routing setup
  ├── api/client.js               ✅ Axios client exists
  ├── components/
  │   ├── Navbar.jsx              ⚠️  Basic, needs polish
  │   ├── FileUploader.jsx        ⚠️  Basic, needs polish
  │   └── VerdictBanner.jsx       ⚠️  Basic, needs polish
  ├── pages/
  │   ├── UploadPage.jsx          ⚠️  Basic, needs full implementation
  │   ├── ProcessingPage.jsx      ❌ Does not exist
  │   ├── ResultsPage.jsx         ⚠️  Basic, needs full implementation
  │   └── HistoryPage.jsx         ⚠️  Basic, needs full implementation
  └── components/ (missing)
      ├── ConfidenceGauge.jsx     ❌ Does not exist
      ├── ModuleResultCard.jsx    ❌ Does not exist
      ├── AnnotatedImage.jsx      ❌ Does not exist
      └── ExtractedDataTable.jsx  ❌ Does not exist
```

### Integration (NEEDS WORK)
```
backend/pipeline.py               ❌ Does not exist
sample_documents/forged/           ❌ Empty
Demo script                        ❌ Not created
README.md                          ⚠️  Needs update
```
