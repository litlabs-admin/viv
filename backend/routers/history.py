"""History endpoint: list all uploaded documents and their verification status."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from database import get_db
from models.schemas import Document, VerificationResult

router = APIRouter(prefix="/api", tags=["history"])


@router.get("/history")
async def get_history(
    doc_type: str = Query(None, description="Filter by document type"),
    status: str = Query(None, description="Filter by status"),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db),
):
    """List all uploaded documents with their latest verification status."""
    query = db.query(Document).order_by(Document.uploaded_at.desc())

    if doc_type:
        query = query.filter(Document.document_type == doc_type)
    if status:
        query = query.filter(Document.status == status)

    documents = query.limit(limit).all()

    results = []
    for doc in documents:
        # Get latest verification result
        latest_result = (
            db.query(VerificationResult)
            .filter(VerificationResult.document_id == doc.id)
            .order_by(VerificationResult.created_at.desc())
            .first()
        )

        results.append({
            "document_id": doc.id,
            "filename": doc.original_filename,
            "document_type": doc.document_type,
            "status": doc.status,
            "file_hash": doc.file_hash,
            "uploaded_at": doc.uploaded_at.isoformat() if doc.uploaded_at else None,
            "verdict": latest_result.verdict if latest_result else None,
            "confidence_score": latest_result.confidence_score if latest_result else None,
        })

    return {"total": len(results), "documents": results}
