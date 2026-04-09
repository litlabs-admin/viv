# Phase 5: NLP + Anomaly Detection + Score Aggregation — COMPLETE

**Date:** 2026-04-09

---

## Summary

Phase 5 adds the final intelligence layers to the verification pipeline: NLP semantic consistency checking, Isolation Forest anomaly detection, weighted score aggregation, and report generation. The system now produces a final **VERIFIED / NEEDS_REVIEW / FRAUDULENT** verdict with a confidence score combining all 5 verification modules.

---

## Modules Implemented

### 1. NLP Semantic Checker (`backend/modules/nlp_checker.py`)

Validates extracted document data for semantic consistency using spaCy NER and fuzzy matching.

**Checks performed:**
- **Name consistency** — primary name exists, has first+last parts, father's name differs from candidate
- **Date consistency** — temporal logic per doc type (age at exam, age at joining, working age, impossible ages)
- **Institution validity** — fuzzy-matches college name against 40+ known SPPU-affiliated colleges (using fuzzywuzzy)
- **Field completeness** — verifies required fields are present per document type
- **NER cross-check** — uses spaCy `en_core_web_sm` to extract PERSON entities and check against declared names

**Scoring:** 0 findings = 1.0, 1-2 = 0.7, 3-4 = 0.4, 5+ = 0.2

### 2. Isolation Forest Anomaly Detector (`backend/modules/anomaly_detector.py`)

Detects statistically unusual documents using scikit-learn's Isolation Forest.

**SPPU Marksheet features (7-dimensional vector):**
1. SGPA value
2. Mean total marks across subjects
3. Std deviation of marks
4. Number of subjects
5. Mean internal/external marks ratio
6. Max total marks
7. Min total marks

**Heuristic fallback** when no trained model: checks for impossible SGPA, unusual marks ranges, suspicious subject counts, identical marks across subjects.

**Training:** 200 synthetic authentic data points, contamination=0.1, correctly flags:
- Perfect marks (SGPA=10, all 150) → ANOMALY
- Mismatched SGPA vs marks → ANOMALY
- Single subject only → ANOMALY
- Normal student (SGPA=7.5) → Normal

### 3. Score Aggregator (`backend/modules/score_aggregator.py`)

Combines all module scores with weighted formula:

| Module | Weight |
|--------|--------|
| CNN Forgery Detection | 40% |
| Rule-Based Validation | 25% |
| NLP Consistency | 15% |
| Anomaly Detection | 10% |
| OCR Confidence | 10% |

**Formula:** `final = 0.4*(1-cnn) + 0.25*rule + 0.15*nlp + 0.1*(1-anomaly) + 0.1*ocr`

**Hard override rules:**
- 3+ critical (high severity) rule failures → cap score at 0.60
- CNN forgery probability > 90% → cap at NEEDS_REVIEW

**Verdict thresholds:**
- 0.85 - 1.00 → **VERIFIED** (green)
- 0.65 - 0.84 → **NEEDS_REVIEW** (yellow)
- 0.00 - 0.64 → **FRAUDULENT** (red)

### 4. Report Generator (`backend/modules/report_generator.py`)

Produces final verification output:
- **Plain-English summary** — template-based, mentions key findings (forgery, rule failures, NLP issues, anomalies)
- **Annotated image** — adds colored border (green/yellow/red) and verdict text overlay
- **Full JSON report** — complete structured report with all module results, timestamps, scores

---

## Files Created/Modified

### New Files
| File | Description |
|------|-------------|
| `backend/modules/nlp_checker.py` | NLP semantic consistency checker |
| `backend/modules/anomaly_detector.py` | Isolation Forest anomaly detection |
| `backend/modules/score_aggregator.py` | Weighted score aggregation + verdict |
| `backend/modules/report_generator.py` | Report + summary + annotated image |
| `backend/training/train_isolation_forest.py` | Isolation Forest training script |
| `backend/ml_models/isolation_forest.pkl` | Trained Isolation Forest model (1.5 KB) |
| `backend/tests/test_nlp_checker.py` | 30 tests for NLP checker |
| `backend/tests/test_anomaly_detector.py` | 22 tests for anomaly detector |
| `backend/tests/test_score_aggregator.py` | 13 tests for score aggregator |
| `backend/tests/test_report_generator.py` | 11 tests for report generator |

### Modified Files
| File | Changes |
|------|---------|
| `backend/routers/verify.py` | Added modules 6-9: NLP, anomaly, aggregation, report |
| `backend/requirements.txt` | Added spacy, scikit-learn, joblib, fuzzywuzzy, python-Levenshtein |

---

## Dependencies Added

```
spacy>=3.7.0          # NLP / NER
scikit-learn>=1.5.0   # Isolation Forest
joblib>=1.4.0         # Model serialization
fuzzywuzzy>=0.18.0    # Fuzzy string matching
python-Levenshtein>=0.25.0  # Fast Levenshtein distance
```

Plus: `python -m spacy download en_core_web_sm` (English NER model)

---

## Test Results

```
214 passed in 6.58s

Breakdown:
- test_anomaly_detector.py:  22 tests
- test_api.py:               10 tests
- test_cnn_forgery.py:       20 tests
- test_nlp_checker.py:       30 tests
- test_ocr.py:               33 tests
- test_preprocessor.py:      13 tests
- test_report_generator.py:  11 tests
- test_rule_validator.py:    51 tests
- test_score_aggregator.py:  13 tests
- TOTAL:                    214 tests
```

---

## API Response (verify endpoint)

The `POST /api/verify/{document_id}` endpoint now returns the full pipeline results:

```json
{
  "document_id": "...",
  "status": "completed",
  "verdict": "VERIFIED",
  "final_score": 0.92,
  "summary": "The SPPU Marksheet has been verified as authentic...",
  "preprocessing": {...},
  "classification": {...},
  "ocr": {...},
  "rule_validation": {"score": 0.9, "passed": [...], "failed": [...]},
  "cnn_forgery": {"forgery_detected": false, "forgery_probability": 0.05, ...},
  "nlp_check": {"score": 1.0, "findings": [], ...},
  "anomaly_detection": {"anomaly_score": 0.1, "is_anomaly": false, ...},
  "score_aggregation": {"final_score": 0.92, "verdict": "VERIFIED", "module_scores": {...}},
  "report": {"summary": "...", "annotated_image_path": "..."}
}
```

---

## Pipeline Architecture (Complete)

```
Upload → Preprocess → Classify → OCR Extract
                                      ↓
                    ┌─────────────────┼─────────────────┐
                    ↓                 ↓                  ↓
              Rule Validator    NLP Checker    CNN Forgery + ELA
                    ↓                 ↓                  ↓
                    └─────────────────┼─────────────────┘
                                      ↓
                              Anomaly Detector
                                      ↓
                              Score Aggregator
                                      ↓
                              Report Generator
                                      ↓
                           Final Verdict + Report
```

---

## Next Phase

**Phase 6: Frontend UI** — React + TailwindCSS frontend with upload, processing, results, and history pages.
