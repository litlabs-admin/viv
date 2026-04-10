# Document Verification System

An AI-powered document verification pipeline that checks the authenticity of Indian educational and identity documents (SPPU Marksheets, Aadhaar Cards, PAN Cards, Experience Certificates) through a 9-stage analysis pipeline.

## Features

- **Image Preprocessing** — deskew, denoise, contrast enhance, binarize
- **Document Classification** — auto-detect document type (template matching + keyword scoring)
- **OCR Extraction** — vision-LLM-based structured data extraction (LM Studio / LLaVA)
- **Rule-Based Validation** — domain-specific rules (Verhoeff checksum for Aadhaar, SPPU grading, PAN format, etc.)
- **NLP Consistency Check** — entity recognition + semantic checks with spaCy + fuzzy institution matching
- **CNN Forgery Detection** — ELA (Error Level Analysis) + EfficientNet-B0 + Grad-CAM visualization
- **Isolation Forest Anomaly Detection** — statistical outlier detection on extracted features
- **Weighted Score Aggregation** — combines module scores with hard override rules
- **Report Generation** — human-readable summary + annotated image + full JSON report

## Architecture

```
┌─────────────┐    ┌─────────────┐    ┌──────────────────┐
│  React UI   │───▶│  FastAPI    │───▶│  Pipeline        │
│  (Vite)     │    │  Backend    │    │  Orchestrator    │
└─────────────┘    └─────────────┘    └──────────────────┘
                          │                    │
                          ▼                    ▼
                   ┌────────────┐       ┌────────────────┐
                   │  SQLite    │       │  9 Modules     │
                   │  (results) │       │  (CV/OCR/ML)   │
                   └────────────┘       └────────────────┘
```

## Requirements

- **Python 3.9+**
- **Node.js 18+**
- **LM Studio** with a vision model (e.g. LLaVA 7B) running on `http://localhost:1234` — required for OCR extraction
- ~6 GB RAM for the full pipeline

## Setup

### 1. Clone and set up backend

```bash
cd backend

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download spaCy English model (for NLP checker)
python -m spacy download en_core_web_sm

# Initialize database
python -c "from database import init_db; init_db()"

# Train the Isolation Forest (generates synthetic data)
python training/train_isolation_forest.py
```

### 2. Set up frontend

```bash
cd ../frontend
npm install
```

### 3. Start LM Studio

1. Open LM Studio
2. Load a vision model (recommended: **LLaVA 1.5 7B** or **LLaVA 1.6 Mistral 7B**)
3. Start the local server on port **1234**
4. Leave it running

### 4. Run the app

In one terminal (backend):
```bash
cd backend
source venv/bin/activate
uvicorn main:app --reload --port 8000
```

In another terminal (frontend):
```bash
cd frontend
npm run dev
```

Then open **http://localhost:5173** in your browser.

## Usage

1. Go to the **Upload** page
2. Drag and drop a document image (JPG, PNG, or PDF)
3. Click **Verify Document**
4. Watch the 8-stage processing animation
5. Review the verdict, confidence gauge, extracted fields, rule validation results, NLP findings, ELA/Grad-CAM visualizations, and anomaly score
6. All past verifications are available under the **History** tab

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/upload` | Upload a document |
| POST | `/api/verify/{document_id}` | Run full verification pipeline |
| GET | `/api/results/{document_id}` | Get verification results |
| GET | `/api/history` | List all verified documents (filterable by doc_type) |
| GET | `/api/health` | Health check |

Full OpenAPI docs: **http://localhost:8000/docs**

## Testing

```bash
cd backend
source venv/bin/activate
python -m pytest tests/ -v
```

Currently: **214 tests passing**.

## Scoring Model

Final verdict is based on a weighted combination of module scores:

```
final_score = 0.40 × (1 - cnn_forgery_prob)
            + 0.25 × rule_validation_score
            + 0.15 × nlp_consistency_score
            + 0.10 × (1 - anomaly_score)
            + 0.10 × ocr_confidence
```

Verdict thresholds:
- **VERIFIED** — final_score ≥ 0.85
- **NEEDS_REVIEW** — 0.65 ≤ final_score < 0.85
- **FRAUDULENT** — final_score < 0.65

Hard overrides apply when 3+ critical rule failures occur or CNN forgery probability exceeds 0.90.

## Project Structure

```
BE-PROJECT/
├── backend/
│   ├── main.py                 # FastAPI app entry
│   ├── pipeline.py             # Orchestrator
│   ├── routers/                # API endpoints
│   ├── modules/                # 9 verification modules
│   ├── models/                 # SQLAlchemy models
│   ├── training/               # Model training scripts
│   ├── tests/                  # 214 unit/integration tests
│   └── ml_models/              # Saved ML artifacts
├── frontend/
│   ├── src/
│   │   ├── pages/              # Upload, Processing, Results, History
│   │   ├── components/         # UI building blocks
│   │   └── api/                # Axios client
│   └── vite.config.js
├── docs/                       # Phase completion docs
└── sample_documents/           # Test documents
```

## Troubleshooting

- **OCR returns empty/error**: Confirm LM Studio is running on port 1234 and a vision model is loaded.
- **spaCy model not found**: Run `python -m spacy download en_core_web_sm`.
- **Isolation forest missing**: Run `python training/train_isolation_forest.py`.
- **Frontend can't reach backend**: Confirm backend is on port 8000; Vite proxies `/api`, `/uploads`, and `/outputs`.

## Credits

BE Final Year Project — Document Verification System using OCR, CNN Forgery Detection, NLP, and Anomaly Detection.
