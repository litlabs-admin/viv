"""Upload endpoint: accepts document images/PDFs and stores them."""

import hashlib
import uuid
from pathlib import Path

from fastapi import APIRouter, UploadFile, File, Depends, HTTPException
from sqlalchemy.orm import Session

from config import UPLOAD_DIR, ALLOWED_EXTENSIONS, MAX_FILE_SIZE_MB
from database import get_db
from models.schemas import Document

router = APIRouter(prefix="/api", tags=["upload"])


@router.post("/upload")
async def upload_document(file: UploadFile = File(...), db: Session = Depends(get_db)):
    """
    Upload a document image or PDF for verification.

    Returns the document ID to use for verification and status checks.
    """
    # Validate file extension
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{suffix}' not supported. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    # Read file content
    content = await file.read()

    # Validate file size
    file_size = len(content)
    if file_size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Maximum size: {MAX_FILE_SIZE_MB}MB"
        )

    # Generate unique filename
    doc_id = str(uuid.uuid4())
    save_filename = f"{doc_id}{suffix}"
    save_path = UPLOAD_DIR / save_filename

    # Save file to disk
    with open(save_path, "wb") as f:
        f.write(content)

    # Compute SHA-256 hash
    file_hash = hashlib.sha256(content).hexdigest()

    # Create database record
    document = Document(
        id=doc_id,
        original_filename=file.filename,
        file_path=str(save_path),
        file_hash=file_hash,
        file_size=file_size,
        status="uploaded",
    )
    db.add(document)
    db.commit()
    db.refresh(document)

    return {
        "document_id": doc_id,
        "filename": file.filename,
        "file_hash": file_hash,
        "file_size_bytes": file_size,
        "status": "uploaded",
        "message": "Document uploaded successfully. Use /api/verify/{document_id} to start verification.",
    }
