"""
Isolation Forest Anomaly Detector

Detects statistically unusual documents by building feature vectors
from extracted fields and scoring them with an Isolation Forest model.

Supports:
- SPPU marksheets: SGPA, mean marks, std dev, subject count, internal/external ratio
- Generic documents: basic field-count and string-length features

Falls back to heuristic scoring if no trained model is available.
"""

import os
import json

import numpy as np

# scikit-learn — optional
try:
    from sklearn.ensemble import IsolationForest
    import joblib
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

from config import BASE_DIR


MODEL_PATH = os.path.join(BASE_DIR, "ml_models", "isolation_forest.pkl")


# ─── Feature Extraction ─────────────────────────────────────────


def extract_marksheet_features(fields: dict) -> list:
    """
    Extract numerical feature vector from SPPU marksheet fields.

    Features:
    1. SGPA value
    2. Mean total marks across subjects
    3. Std dev of total marks
    4. Number of subjects
    5. Mean internal/external ratio
    6. Max total marks
    7. Min total marks
    """
    subjects = fields.get("subjects", [])
    if not subjects or not isinstance(subjects, list):
        return None

    totals = []
    ratios = []
    for subj in subjects:
        if not isinstance(subj, dict):
            continue
        total = subj.get("total_marks")
        internal = subj.get("internal_marks")
        external = subj.get("external_marks")

        if total is not None:
            try:
                totals.append(float(total))
            except (ValueError, TypeError):
                pass

        if internal is not None and external is not None:
            try:
                ext = float(external)
                if ext > 0:
                    ratios.append(float(internal) / ext)
            except (ValueError, TypeError, ZeroDivisionError):
                pass

    if not totals:
        return None

    sgpa = fields.get("sgpa")
    try:
        sgpa_val = float(sgpa) if sgpa is not None else 0.0
    except (ValueError, TypeError):
        sgpa_val = 0.0

    features = [
        sgpa_val,                                    # SGPA
        float(np.mean(totals)),                      # Mean marks
        float(np.std(totals)) if len(totals) > 1 else 0.0,  # Std dev
        float(len(totals)),                          # Subject count
        float(np.mean(ratios)) if ratios else 0.5,  # Mean internal/external ratio
        float(max(totals)),                          # Max marks
        float(min(totals)),                          # Min marks
    ]

    return features


def extract_generic_features(fields: dict) -> list:
    """
    Extract basic features from any document type.

    Features:
    1. Number of non-null fields
    2. Total character count across string fields
    3. Number of numeric fields
    4. Average string field length
    """
    non_null = 0
    total_chars = 0
    numeric_count = 0
    string_lengths = []

    for key, val in fields.items():
        if val is not None:
            non_null += 1
        if isinstance(val, str) and val.strip():
            total_chars += len(val)
            string_lengths.append(len(val))
        if isinstance(val, (int, float)):
            numeric_count += 1

    avg_str_len = float(np.mean(string_lengths)) if string_lengths else 0.0

    return [
        float(non_null),
        float(total_chars),
        float(numeric_count),
        avg_str_len,
    ]


# ─── Model Loading ──────────────────────────────────────────────


def load_isolation_forest():
    """
    Load the trained Isolation Forest model.
    Returns the model or None if not available.
    """
    if not SKLEARN_AVAILABLE:
        return None
    if not os.path.exists(MODEL_PATH):
        return None

    try:
        model = joblib.load(MODEL_PATH)
        return model
    except Exception:
        return None


# ─── Heuristic Fallback ─────────────────────────────────────────


def heuristic_anomaly_score(features: list, doc_type: str) -> float:
    """
    Simple heuristic anomaly scoring when no trained model is available.
    Returns a score between 0 (normal) and 1 (anomalous).
    """
    if doc_type == "sppu_marksheet" and len(features) >= 7:
        score = 0.0
        sgpa, mean_marks, std_marks, num_subjects, ratio, max_m, min_m = features[:7]

        # SGPA out of range
        if sgpa < 0 or sgpa > 10:
            score += 0.3
        # Very high or very low SGPA
        if sgpa > 9.8 or sgpa < 2.0:
            score += 0.1

        # Marks anomalies
        if mean_marks > 140 or mean_marks < 20:
            score += 0.2
        if std_marks > 50:
            score += 0.1

        # Subject count anomalies
        if num_subjects < 3 or num_subjects > 12:
            score += 0.1

        # Internal/external ratio anomalies (typical ~0.5-1.0)
        if ratio > 3.0 or ratio < 0.1:
            score += 0.1

        # All subjects same marks (suspicious)
        if std_marks < 1.0 and num_subjects > 3:
            score += 0.2

        return min(score, 1.0)

    # Generic: low anomaly score
    return 0.1


# ─── Main Detection Function ────────────────────────────────────


def detect_anomaly(extracted_fields: dict, doc_type: str) -> dict:
    """
    Run anomaly detection on extracted document fields.

    Args:
        extracted_fields: Dict of fields from OCR extraction.
        doc_type: Document type string.

    Returns:
        Dict with keys: anomaly_score, is_anomaly, features, method, status, error
    """
    if not extracted_fields:
        return {
            "anomaly_score": 0.0,
            "is_anomaly": False,
            "features": None,
            "method": "none",
            "status": "skipped",
            "error": "No extracted fields",
        }

    try:
        # Extract features based on doc type
        if doc_type == "sppu_marksheet":
            features = extract_marksheet_features(extracted_fields)
        else:
            features = extract_generic_features(extracted_fields)

        if features is None:
            return {
                "anomaly_score": 0.0,
                "is_anomaly": False,
                "features": None,
                "method": "none",
                "status": "skipped",
                "error": "Could not extract features",
            }

        # Try trained model first
        model = load_isolation_forest()

        if model is not None and doc_type == "sppu_marksheet":
            try:
                features_array = np.array(features).reshape(1, -1)
                # decision_function: negative = anomaly, positive = normal
                raw_score = model.decision_function(features_array)[0]
                # Convert to 0-1 scale (more negative = more anomalous)
                # Typical range is -0.5 to 0.5
                anomaly_score = max(0.0, min(1.0, 0.5 - raw_score))
                is_anomaly = model.predict(features_array)[0] == -1

                return {
                    "anomaly_score": round(float(anomaly_score), 4),
                    "is_anomaly": bool(is_anomaly),
                    "features": features,
                    "method": "isolation_forest",
                    "status": "success",
                    "error": None,
                }
            except Exception:
                pass

        # Fallback to heuristic
        anomaly_score = heuristic_anomaly_score(features, doc_type)

        return {
            "anomaly_score": round(anomaly_score, 4),
            "is_anomaly": anomaly_score > 0.5,
            "features": features,
            "method": "heuristic",
            "status": "success",
            "error": None,
        }

    except Exception as e:
        return {
            "anomaly_score": 0.0,
            "is_anomaly": False,
            "features": None,
            "method": "none",
            "status": "error",
            "error": f"Anomaly detection failed: {str(e)}",
        }
