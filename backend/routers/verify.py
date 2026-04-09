"""Verify endpoint: triggers the verification pipeline on an uploaded document."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import Document
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

router = APIRouter(prefix="/api", tags=["verify"])


@router.post("/verify/{document_id}")
async def verify_document(document_id: str, db: Session = Depends(get_db)):
    """
    Start verification pipeline for an uploaded document.

    Phase 2: Preprocessing + Classification + OCR extraction.
    Other modules return placeholders.
    """
    # Fetch document from DB
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    if document.status == "processing":
        raise HTTPException(status_code=409, detail="Document is already being processed")

    # Update status
    document.status = "processing"
    db.commit()

    try:
        # --- Module 1: Preprocessing ---
        preprocessed = preprocess_document(document.file_path)
        saved_paths = save_preprocessed(preprocessed, str(OUTPUT_DIR), document_id)

        preprocessing_result = {
            "status": "success",
            "output_images": saved_paths,
            "image_shape": {
                "height": preprocessed["original"].shape[0],
                "width": preprocessed["original"].shape[1],
            },
        }

        # --- Module 2: Classification ---
        classification_result = classify_document(document.file_path)
        doc_type = classification_result.get("doc_type", "unknown")

        # Update document type in DB
        if doc_type != "unknown":
            document.doc_type = doc_type

        # --- Module 3: OCR Extraction ---
        if doc_type != "unknown":
            ocr_result = extract_document_data(document.file_path, doc_type)
        else:
            ocr_result = {
                "extracted_fields": None,
                "raw_response": None,
                "doc_type": "unknown",
                "status": "skipped",
                "error": "Document type could not be determined",
            }

        # --- Module 4: Rule-Based Validation ---
        extracted_fields = ocr_result.get("extracted_fields")
        if doc_type != "unknown" and extracted_fields:
            rule_result = validate_document(doc_type, extracted_fields)
        else:
            rule_result = {
                "score": 0.0,
                "passed": [],
                "failed": [],
                "doc_type": doc_type,
                "status": "skipped",
                "error": "No extracted fields to validate" if not extracted_fields else "Unknown document type",
            }

        # --- Module 5: CNN Forgery Detection ---
        forgery_result = detect_forgery(document.file_path)

        # --- Module 6: NLP Consistency Check ---
        if extracted_fields:
            nlp_result = check_nlp_consistency(extracted_fields, doc_type)
        else:
            nlp_result = {
                "score": 0.0,
                "findings": [],
                "status": "skipped",
                "error": "No extracted fields for NLP check",
            }

        # --- Module 7: Anomaly Detection ---
        if extracted_fields:
            anomaly_result = detect_anomaly(extracted_fields, doc_type)
        else:
            anomaly_result = {
                "anomaly_score": 0.0,
                "is_anomaly": False,
                "features": None,
                "method": "none",
                "status": "skipped",
                "error": "No extracted fields for anomaly detection",
            }

        # --- Module 8: Score Aggregation ---
        ocr_confidence = 1.0 if ocr_result.get("status") == "success" else 0.0
        aggregation_result = aggregate_scores(
            cnn_forgery_probability=forgery_result.get("forgery_probability", 0.0),
            rule_score=rule_result.get("score", 0.0),
            nlp_score=nlp_result.get("score", 0.0),
            anomaly_score=anomaly_result.get("anomaly_score", 0.0),
            ocr_confidence=ocr_confidence,
            failed_rules=rule_result.get("failed", []),
        )

        # --- Module 9: Report Generation ---
        report_result = generate_report(
            document_id=document_id,
            doc_type=doc_type,
            image_path=document.file_path,
            preprocessing_result=preprocessing_result,
            classification_result=classification_result,
            ocr_result=ocr_result,
            rule_result=rule_result,
            nlp_result=nlp_result,
            forgery_result=forgery_result,
            anomaly_result=anomaly_result,
            aggregation_result=aggregation_result,
        )

        # Update document status
        document.status = "completed"
        db.commit()

        return {
            "document_id": document_id,
            "status": "completed",
            "verdict": aggregation_result.get("verdict"),
            "final_score": aggregation_result.get("final_score"),
            "summary": report_result.get("summary"),
            "preprocessing": preprocessing_result,
            "classification": {
                "doc_type": doc_type,
                "confidence": classification_result.get("confidence", 0),
                "method": classification_result.get("method", "unknown"),
            },
            "ocr": {
                "status": ocr_result.get("status"),
                "extracted_fields": ocr_result.get("extracted_fields"),
                "error": ocr_result.get("error"),
            },
            "rule_validation": {
                "status": rule_result.get("status"),
                "score": rule_result.get("score"),
                "passed": rule_result.get("passed"),
                "failed": rule_result.get("failed"),
                "error": rule_result.get("error"),
            },
            "cnn_forgery": {
                "status": forgery_result.get("status"),
                "forgery_detected": forgery_result.get("forgery_detected"),
                "forgery_probability": forgery_result.get("forgery_probability"),
                "method": forgery_result.get("method"),
                "ela_image_base64": forgery_result.get("ela_image_base64"),
                "gradcam_heatmap_base64": forgery_result.get("gradcam_heatmap_base64"),
                "ela_stats": forgery_result.get("ela_stats"),
                "error": forgery_result.get("error"),
            },
            "nlp_check": {
                "status": nlp_result.get("status"),
                "score": nlp_result.get("score"),
                "findings": nlp_result.get("findings"),
                "error": nlp_result.get("error"),
            },
            "anomaly_detection": {
                "status": anomaly_result.get("status"),
                "anomaly_score": anomaly_result.get("anomaly_score"),
                "is_anomaly": anomaly_result.get("is_anomaly"),
                "method": anomaly_result.get("method"),
                "error": anomaly_result.get("error"),
            },
            "score_aggregation": {
                "final_score": aggregation_result.get("final_score"),
                "verdict": aggregation_result.get("verdict"),
                "verdict_color": aggregation_result.get("verdict_color"),
                "module_scores": aggregation_result.get("module_scores"),
                "override_reason": aggregation_result.get("override_reason"),
            },
            "report": {
                "summary": report_result.get("summary"),
                "annotated_image_path": report_result.get("annotated_image_path"),
            },
        }

    except Exception as e:
        document.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")
