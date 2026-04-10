# Demo Script — Document Verification System

A step-by-step walkthrough for demonstrating the project in a viva/presentation.

## Pre-demo checklist

- [ ] LM Studio is running with LLaVA 7B loaded on port 1234
- [ ] Backend started: `cd backend && source venv/bin/activate && uvicorn main:app --reload --port 8000`
- [ ] Frontend started: `cd frontend && npm run dev`
- [ ] Browser open at `http://localhost:5173`
- [ ] Sample documents ready in `sample_documents/` (at least one genuine + one tampered per type)
- [ ] Terminal with test runner ready: `cd backend && python -m pytest tests/ -q`

## 1. Introduction (1 min)

> "This is a document verification system that analyzes Indian educational and identity documents through a 9-stage AI pipeline. It detects forgery using a combination of computer vision, OCR, rule-based validation, NLP consistency checks, and statistical anomaly detection. Everything runs **locally** — no document is sent to any cloud service."

**Show**: the Upload page. Point out the four supported document types.

## 2. Architecture overview (1 min)

Open `README.md` or a diagram, briefly mention:

- **Frontend**: React + Vite + TailwindCSS
- **Backend**: FastAPI + SQLite
- **OCR**: Local LM Studio with LLaVA vision model
- **Forgery Detection**: ELA + EfficientNet-B0 + Grad-CAM
- **Anomaly Detection**: Isolation Forest trained on synthetic authentic features

## 3. Live verification — genuine document (3 min)

1. Drag in a **genuine SPPU marksheet** from `sample_documents/`
2. Click **Verify Document**
3. Walk through the **processing animation** — explain each stage briefly:
   - Preprocessing (deskew + enhance)
   - Classification (template + keyword matching)
   - OCR (LLaVA vision model extracts fields)
   - Rule Validation (SPPU grading rules, SGPA bounds)
   - NLP Consistency (name/date/institution checks)
   - CNN Forgery Detection (ELA + EfficientNet)
   - Anomaly Detection (Isolation Forest)
   - Report Generation
4. On the **Results page**, point out:
   - Green **VERIFIED** banner
   - Confidence gauge (>85%)
   - Summary text
   - Score breakdown with weighted contributions
   - Expand **OCR Extraction** — show structured fields
   - Expand **Rule Validation** — show passed rules
   - Expand **CNN Forgery Detection** — show ELA image and Grad-CAM heatmap (should be uniform for genuine)

## 4. Live verification — forged document (3 min)

1. Go back to **Upload**
2. Drag in a **tampered SPPU marksheet** (e.g., edited marks)
3. Verify
4. On the Results page, show:
   - Red **FRAUDULENT** or yellow **NEEDS_REVIEW** banner
   - Lower confidence score
   - **Score Breakdown** showing which module(s) flagged issues
   - Expand **CNN Forgery** — Grad-CAM should highlight tampered regions
   - Expand **Rule Validation** — show failed rules (if applicable)
   - Expand **Anomaly Detection** — show anomaly flag (if applicable)
   - Read the **summary** out loud — it explains in plain English why the document was flagged

## 5. History and filtering (1 min)

Click the **History** tab:
- Show the list of all verified documents
- Point out the stats cards (total, verified, needs review, fraudulent)
- Demonstrate filtering by document type and verdict
- Click a row to reopen its results

## 6. Code walkthrough (3 min)

Open VS Code and briefly highlight:

1. **`backend/pipeline.py`** — the orchestrator with `_safe_run` wrapper so one failing module doesn't break the pipeline
2. **`backend/modules/cnn_forgery.py`** — ELA + EfficientNet + Grad-CAM
3. **`backend/modules/score_aggregator.py`** — weighted scoring formula and hard override rules
4. **`backend/modules/nlp_checker.py`** — name/date/institution fuzzy matching with graceful spaCy fallback
5. **`frontend/src/pages/ResultsPage.jsx`** — how the UI renders module results

## 7. Test suite (1 min)

In the terminal:

```bash
cd backend
source venv/bin/activate
python -m pytest tests/ -q
```

Show the output:

> "214 tests passing — covering all 9 modules, the API endpoints, and edge cases."

## 8. Q&A Prep — Likely Questions

**Q: Why LM Studio and LLaVA instead of a cloud OCR API?**
> Privacy-first design. Everything runs locally so sensitive documents (Aadhaar, PAN) never leave the machine. LLaVA also returns structured JSON, not just raw text.

**Q: How does CNN forgery detection work?**
> Error Level Analysis (ELA) highlights regions with inconsistent JPEG compression — tampered areas show up as bright spots. We then feed the ELA image to a fine-tuned EfficientNet-B0 which outputs a forgery probability. Grad-CAM visualizes which regions the CNN "looked at" to make its decision.

**Q: Why Isolation Forest for anomaly detection?**
> It works well with limited training data (we use 200 synthetic authentic samples) and doesn't require labeled forgery examples. It detects any statistical outlier — e.g., a marksheet with perfect marks in every subject is anomalous even if individual fields pass validation.

**Q: How is the final score calculated?**
> Weighted combination:  `0.4 × (1 − cnn_forgery) + 0.25 × rule + 0.15 × nlp + 0.1 × (1 − anomaly) + 0.1 × ocr`. Plus hard overrides — e.g., 3+ critical rule failures cap the score at 0.60, and CNN forgery above 0.90 caps the verdict at NEEDS_REVIEW even if other modules pass.

**Q: What happens if one module fails?**
> The pipeline orchestrator wraps each module in try/except. If a module crashes, the failure is recorded in the report and the remaining modules still run. The user sees a partial result with the error flagged.

**Q: Can this be deployed to production?**
> This is a research/demo project — not production-ready. For production you'd need: auth/RBAC, rate limiting, GPU for CNN inference, proper ML model versioning, and a real training dataset for the forgery detector.

## 9. Closing (30 sec)

> "The full system runs locally in under 30 seconds per document, supports 4 document types out of the box, and is extensible to new types by adding a new classifier template, OCR schema, and rule set. All code, tests, and documentation are in the repository."

## Backup plan — if LM Studio is unreachable

- OCR will return a skipped/error status
- Rule validation, NLP, and anomaly modules will auto-skip (no fields to validate)
- CNN Forgery Detection **still runs** (it works on the image directly)
- Use this to demo that pipeline gracefully degrades and still produces a partial verdict
