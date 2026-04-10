"""
Full Verification Pipeline Orchestrator

Runs all 9 verification modules in sequence. Each module is wrapped
in try/except — if one fails, the others still run and the failure
is noted in the report.

Usage:
    result = run_verification_pipeline(document_id, file_path)
"""

import time
import traceback

from modules.preprocessor import preprocess_document, save_preprocessed
from modules.classifier import classify_document
from modules.ocr_engine import extract_document_data
from modules.rule_validator import validate_document
from modules.cnn_forgery import detect_forgery
from modules.nlp_checker import check_nlp_consistency
from modules.anomaly_detector import detect_anomaly
from modules.score_aggregator import aggregate_scores
from modules.report_generator import generate_report
from config import OUTPUT_DIR


def _safe_run(fn, default, module_name):
    """Run a module function with error handling."""
    try:
        return fn()
    except Exception as e:
        print(f"[pipeline] Module '{module_name}' failed: {e}")
        traceback.print_exc()
        default["status"] = "error"
        default["error"] = f"{module_name} failed: {str(e)}"
        return default


def run_verification_pipeline(document_id: str, file_path: str) -> dict:
    """
    Run the full verification pipeline on a document.

    Args:
        document_id: Document ID from the database
        file_path: Path to the uploaded document file

    Returns:
        Dict with all module results + final verdict + report
    """
    start_time = time.time()

    # ─── Module 1: Preprocessing ─────────────────────────────────
    def _preprocess():
        preprocessed = preprocess_document(file_path)
        saved_paths = save_preprocessed(preprocessed, str(OUTPUT_DIR), document_id)
        return {
            "status": "success",
            "output_images": saved_paths,
            "image_shape": {
                "height": preprocessed["original"].shape[0],
                "width": preprocessed["original"].shape[1],
            },
            "error": None,
        }

    preprocessing_result = _safe_run(
        _preprocess,
        {"status": "error", "output_images": {}, "image_shape": {}, "error": None},
        "preprocessing",
    )

    # ─── Module 2: Classification ────────────────────────────────
    def _classify():
        return classify_document(file_path)

    classification_result = _safe_run(
        _classify,
        {"doc_type": "unknown", "confidence": 0, "method": "error", "status": "error", "error": None},
        "classification",
    )
    doc_type = classification_result.get("doc_type", "unknown")

    # ─── Module 3: OCR Extraction ────────────────────────────────
    def _ocr():
        if doc_type == "unknown":
            return {
                "extracted_fields": None,
                "raw_response": None,
                "doc_type": "unknown",
                "status": "skipped",
                "error": "Document type could not be determined",
            }
        return extract_document_data(file_path, doc_type)

    ocr_result = _safe_run(
        _ocr,
        {"extracted_fields": None, "raw_response": None, "doc_type": doc_type, "status": "error", "error": None},
        "ocr",
    )
    extracted_fields = ocr_result.get("extracted_fields")

    # ─── Module 4: Rule-Based Validation ─────────────────────────
    def _rules():
        if doc_type == "unknown" or not extracted_fields:
            return {
                "score": 0.0,
                "passed": [],
                "failed": [],
                "doc_type": doc_type,
                "status": "skipped",
                "error": "No extracted fields to validate" if not extracted_fields else "Unknown document type",
            }
        return validate_document(doc_type, extracted_fields)

    rule_result = _safe_run(
        _rules,
        {"score": 0.0, "passed": [], "failed": [], "doc_type": doc_type, "status": "error", "error": None},
        "rule_validation",
    )

    # ─── Module 5: CNN Forgery Detection ─────────────────────────
    def _forgery():
        return detect_forgery(file_path)

    forgery_result = _safe_run(
        _forgery,
        {
            "forgery_detected": False,
            "forgery_probability": 0.0,
            "ela_image_base64": None,
            "gradcam_heatmap_base64": None,
            "method": "none",
            "status": "error",
            "error": None,
            "ela_stats": {},
        },
        "cnn_forgery",
    )

    # ─── Module 6: NLP Consistency Check ─────────────────────────
    def _nlp():
        if not extracted_fields:
            return {
                "score": 0.0,
                "findings": [],
                "status": "skipped",
                "error": "No extracted fields for NLP check",
            }
        return check_nlp_consistency(extracted_fields, doc_type)

    nlp_result = _safe_run(
        _nlp,
        {"score": 0.0, "findings": [], "status": "error", "error": None},
        "nlp",
    )

    # ─── Module 7: Anomaly Detection ─────────────────────────────
    def _anomaly():
        if not extracted_fields:
            return {
                "anomaly_score": 0.0,
                "is_anomaly": False,
                "features": None,
                "method": "none",
                "status": "skipped",
                "error": "No extracted fields for anomaly detection",
            }
        return detect_anomaly(extracted_fields, doc_type)

    anomaly_result = _safe_run(
        _anomaly,
        {"anomaly_score": 0.0, "is_anomaly": False, "features": None, "method": "none", "status": "error", "error": None},
        "anomaly",
    )

    # ─── Module 8: Score Aggregation ─────────────────────────────
    ocr_confidence = 1.0 if ocr_result.get("status") == "success" else 0.0

    def _aggregate():
        return aggregate_scores(
            cnn_forgery_probability=forgery_result.get("forgery_probability", 0.0),
            rule_score=rule_result.get("score", 0.0),
            nlp_score=nlp_result.get("score", 0.0),
            anomaly_score=anomaly_result.get("anomaly_score", 0.0),
            ocr_confidence=ocr_confidence,
            failed_rules=rule_result.get("failed", []),
        )

    aggregation_result = _safe_run(
        _aggregate,
        {
            "final_score": 0.0,
            "verdict": "FRAUDULENT",
            "verdict_color": "red",
            "module_scores": {},
            "weights": {},
            "override_reason": None,
        },
        "aggregation",
    )

    # ─── Module 9: Report Generation ─────────────────────────────
    def _report():
        return generate_report(
            document_id=document_id,
            doc_type=doc_type,
            image_path=file_path,
            preprocessing_result=preprocessing_result,
            classification_result=classification_result,
            ocr_result=ocr_result,
            rule_result=rule_result,
            nlp_result=nlp_result,
            forgery_result=forgery_result,
            anomaly_result=anomaly_result,
            aggregation_result=aggregation_result,
        )

    report_result = _safe_run(
        _report,
        {"summary": "", "annotated_image_path": None, "full_report": {}, "verdict": "FRAUDULENT", "final_score": 0.0},
        "report",
    )

    processing_time_ms = int((time.time() - start_time) * 1000)

    return {
        "document_id": document_id,
        "doc_type": doc_type,
        "processing_time_ms": processing_time_ms,
        "verdict": aggregation_result.get("verdict"),
        "final_score": aggregation_result.get("final_score"),
        "summary": report_result.get("summary"),
        "preprocessing": preprocessing_result,
        "classification": classification_result,
        "ocr": ocr_result,
        "rule_validation": rule_result,
        "cnn_forgery": forgery_result,
        "nlp_check": nlp_result,
        "anomaly_detection": anomaly_result,
        "score_aggregation": aggregation_result,
        "report": {
            "summary": report_result.get("summary"),
            "annotated_image_path": report_result.get("annotated_image_path"),
            "full_report": report_result.get("full_report"),
        },
    }
