"""Verify endpoint: runs the full verification pipeline and persists results."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import Document, VerificationResult
from pipeline import run_verification_pipeline

router = APIRouter(prefix="/api", tags=["verify"])


@router.post("/verify/{document_id}")
async def verify_document(document_id: str, db: Session = Depends(get_db)):
    """
    Run the full verification pipeline on an uploaded document.

    Executes all 9 modules (preprocessing, classification, OCR, rules,
    NLP, CNN forgery, anomaly, aggregation, report) and persists the
    full result to the VerificationResult table.
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
        # Run the full pipeline
        result = run_verification_pipeline(document_id, document.file_path)

        doc_type = result.get("doc_type", "unknown")
        if doc_type != "unknown":
            document.document_type = doc_type

        # Extract module scores for DB persistence
        ocr_confidence = 1.0 if result["ocr"].get("status") == "success" else 0.0
        rule_score = result["rule_validation"].get("score", 0.0)
        nlp_score = result["nlp_check"].get("score", 0.0)
        cnn_prob = result["cnn_forgery"].get("forgery_probability", 0.0)
        anomaly_score = result["anomaly_detection"].get("anomaly_score", 0.0)

        # Save VerificationResult to DB
        verification = VerificationResult(
            document_id=document_id,
            verdict=result.get("verdict"),
            confidence_score=result.get("final_score"),
            ocr_confidence=ocr_confidence,
            rule_validation_score=rule_score,
            nlp_consistency_score=nlp_score,
            cnn_forgery_score=cnn_prob,
            isolation_forest_score=anomaly_score,
            full_report=result.get("report", {}).get("full_report", {}),
            extracted_data=result["ocr"].get("extracted_fields"),
            failed_rules=result["rule_validation"].get("failed", []),
            forgery_regions=None,
            annotated_image_path=result.get("report", {}).get("annotated_image_path"),
            processing_time_ms=result.get("processing_time_ms"),
        )
        db.add(verification)
        document.status = "completed"
        db.commit()

        # Return the full result (same shape as before)
        return {
            "document_id": document_id,
            "status": "completed",
            "verdict": result.get("verdict"),
            "final_score": result.get("final_score"),
            "summary": result.get("summary"),
            "processing_time_ms": result.get("processing_time_ms"),
            "preprocessing": {
                "status": result["preprocessing"].get("status"),
                "image_shape": result["preprocessing"].get("image_shape"),
            },
            "classification": {
                "doc_type": doc_type,
                "confidence": result["classification"].get("confidence", 0),
                "method": result["classification"].get("method", "unknown"),
            },
            "ocr": {
                "status": result["ocr"].get("status"),
                "extracted_fields": result["ocr"].get("extracted_fields"),
                "error": result["ocr"].get("error"),
            },
            "rule_validation": {
                "status": result["rule_validation"].get("status"),
                "score": result["rule_validation"].get("score"),
                "passed": result["rule_validation"].get("passed"),
                "failed": result["rule_validation"].get("failed"),
                "error": result["rule_validation"].get("error"),
            },
            "cnn_forgery": {
                "status": result["cnn_forgery"].get("status"),
                "forgery_detected": result["cnn_forgery"].get("forgery_detected"),
                "forgery_probability": result["cnn_forgery"].get("forgery_probability"),
                "method": result["cnn_forgery"].get("method"),
                "ela_image_base64": result["cnn_forgery"].get("ela_image_base64"),
                "gradcam_heatmap_base64": result["cnn_forgery"].get("gradcam_heatmap_base64"),
                "ela_stats": result["cnn_forgery"].get("ela_stats"),
                "error": result["cnn_forgery"].get("error"),
            },
            "nlp_check": {
                "status": result["nlp_check"].get("status"),
                "score": result["nlp_check"].get("score"),
                "findings": result["nlp_check"].get("findings"),
                "error": result["nlp_check"].get("error"),
            },
            "anomaly_detection": {
                "status": result["anomaly_detection"].get("status"),
                "anomaly_score": result["anomaly_detection"].get("anomaly_score"),
                "is_anomaly": result["anomaly_detection"].get("is_anomaly"),
                "method": result["anomaly_detection"].get("method"),
                "error": result["anomaly_detection"].get("error"),
            },
            "score_aggregation": {
                "final_score": result["score_aggregation"].get("final_score"),
                "verdict": result["score_aggregation"].get("verdict"),
                "verdict_color": result["score_aggregation"].get("verdict_color"),
                "module_scores": result["score_aggregation"].get("module_scores"),
                "override_reason": result["score_aggregation"].get("override_reason"),
            },
            "report": {
                "summary": result["report"].get("summary"),
                "annotated_image_path": result["report"].get("annotated_image_path"),
            },
        }

    except Exception as e:
        document.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")
