"""Results endpoint: fetch verification results for a document."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import Document, VerificationResult

router = APIRouter(prefix="/api", tags=["results"])


@router.get("/results/{document_id}")
async def get_results(document_id: str, db: Session = Depends(get_db)):
    """Get verification results for a document."""
    document = db.query(Document).filter(Document.id == document_id).first()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")

    # Get latest verification result if exists
    result = (
        db.query(VerificationResult)
        .filter(VerificationResult.document_id == document_id)
        .order_by(VerificationResult.created_at.desc())
        .first()
    )

    response = {
        "document_id": document_id,
        "filename": document.original_filename,
        "document_type": document.document_type,
        "status": document.status,
        "uploaded_at": document.uploaded_at.isoformat() if document.uploaded_at else None,
    }

    if result:
        response["verification"] = {
            "verdict": result.verdict,
            "confidence_score": result.confidence_score,
            "ocr_confidence": result.ocr_confidence,
            "rule_validation_score": result.rule_validation_score,
            "nlp_consistency_score": result.nlp_consistency_score,
            "cnn_forgery_score": result.cnn_forgery_score,
            "isolation_forest_score": result.isolation_forest_score,
            "full_report": result.full_report,
            "extracted_data": result.extracted_data,
            "failed_rules": result.failed_rules,
            "forgery_regions": result.forgery_regions,
            "annotated_image_path": result.annotated_image_path,
            "processing_time_ms": result.processing_time_ms,
            "created_at": result.created_at.isoformat() if result.created_at else None,
        }
    else:
        response["verification"] = None

    return response
