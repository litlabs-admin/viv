"""Verify endpoint: triggers the verification pipeline on an uploaded document."""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import Document
from modules.preprocessor import preprocess_document, save_preprocessed
from config import OUTPUT_DIR

router = APIRouter(prefix="/api", tags=["verify"])


@router.post("/verify/{document_id}")
async def verify_document(document_id: str, db: Session = Depends(get_db)):
    """
    Start verification pipeline for an uploaded document.

    Phase 1: Only preprocessing is implemented. Other modules return placeholders.
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

        # Save preprocessed images
        saved_paths = save_preprocessed(preprocessed, str(OUTPUT_DIR), document_id)

        # Update document status
        document.status = "completed"
        db.commit()

        return {
            "document_id": document_id,
            "status": "completed",
            "preprocessing": {
                "status": "success",
                "output_images": saved_paths,
                "image_shape": {
                    "height": preprocessed["original"].shape[0],
                    "width": preprocessed["original"].shape[1],
                },
            },
            "ocr": {"status": "not_implemented", "message": "Coming in Phase 2"},
            "classification": {"status": "not_implemented", "message": "Coming in Phase 3"},
            "rule_validation": {"status": "not_implemented", "message": "Coming in Phase 3"},
            "nlp_check": {"status": "not_implemented", "message": "Coming in Phase 5"},
            "cnn_forgery": {"status": "not_implemented", "message": "Coming in Phase 4"},
            "anomaly_detection": {"status": "not_implemented", "message": "Coming in Phase 5"},
        }

    except Exception as e:
        document.status = "failed"
        db.commit()
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")
