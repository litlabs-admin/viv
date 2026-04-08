import uuid
from datetime import datetime

from sqlalchemy import Column, String, Float, Integer, DateTime, Text, ForeignKey, JSON
from sqlalchemy.orm import relationship

from database import Base


def generate_uuid():
    return str(uuid.uuid4())


class Document(Base):
    __tablename__ = "documents"

    id = Column(String, primary_key=True, default=generate_uuid)
    original_filename = Column(String, nullable=False)
    document_type = Column(String, default="unknown")  # sppu_marksheet, aadhaar_card, pan_card, experience_certificate, unknown
    file_path = Column(String, nullable=False)  # path to saved file
    file_hash = Column(String)  # SHA-256 hash
    file_size = Column(Integer)  # bytes
    status = Column(String, default="uploaded")  # uploaded, processing, completed, failed
    uploaded_at = Column(DateTime, default=datetime.utcnow)

    # Relationship to verification results
    verification_results = relationship("VerificationResult", back_populates="document")


class VerificationResult(Base):
    __tablename__ = "verification_results"

    id = Column(String, primary_key=True, default=generate_uuid)
    document_id = Column(String, ForeignKey("documents.id"), nullable=False)

    # Final verdict
    verdict = Column(String)  # VERIFIED, NEEDS_REVIEW, FRAUDULENT
    confidence_score = Column(Float)

    # Per-module scores
    ocr_confidence = Column(Float)
    rule_validation_score = Column(Float)
    nlp_consistency_score = Column(Float)
    cnn_forgery_score = Column(Float)
    isolation_forest_score = Column(Float)

    # Detailed results as JSON
    full_report = Column(JSON)
    extracted_data = Column(JSON)
    failed_rules = Column(JSON)
    forgery_regions = Column(JSON)

    # Annotated output image path
    annotated_image_path = Column(String)

    processing_time_ms = Column(Integer)
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationship
    document = relationship("Document", back_populates="verification_results")
