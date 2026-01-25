# ============================================================================
# Document Upload & RAG Ingestion Models
# ============================================================================
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Float
from sqlalchemy import Text, Enum, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentType(str, enum.Enum):
    PAST_PAPER = "past_paper"
    MARKING_SCHEME = "marking_scheme"
    SYLLABUS = "syllabus"
    TEXTBOOK = "textbook"
    TEACHER_NOTES = "teacher_notes"


class UploadedDocument(Base):
    """
    Tracks documents uploaded for RAG ingestion.

    Provides:
    - Upload history and audit trail
    - Processing status and progress tracking
    - Error logging for failed uploads
    - Metadata for vector store management
    """
    __tablename__ = "uploaded_documents"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # File information
    filename = Column(String(500), nullable=False)  # Stored filename
    original_filename = Column(String(500), nullable=False)  # User's original filename
    file_path = Column(String(1000), nullable=False)  # Full path to stored file
    file_size = Column(Integer, nullable=False)  # Size in bytes
    file_hash = Column(String(64), nullable=False, index=True)  # SHA-256 hash for deduplication
    mime_type = Column(String(100))

    # Document metadata
    document_type = Column(Enum(DocumentType), nullable=False, index=True)
    subject = Column(String(100), index=True)
    grade = Column(String(20))
    education_level = Column(String(20), default="secondary")
    year = Column(Integer)  # For past papers
    paper_number = Column(String(20))  # "Paper 1", "Paper 2", etc.
    term = Column(String(20))

    # Processing status
    status = Column(Enum(DocumentStatus), nullable=False, default=DocumentStatus.PENDING, index=True)
    chunks_created = Column(Integer, default=0)
    chunks_indexed = Column(Integer, default=0)
    processing_progress = Column(Float, default=0.0)  # 0.0 to 100.0

    # Error tracking
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)

    # Processing metadata
    processing_metadata = Column(JSON, default=dict)  # Extraction stats, chunking info, etc.
    vector_store_collection = Column(String(100))  # Qdrant collection name

    # Timestamps
    uploaded_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    processing_started_at = Column(DateTime(timezone=True))
    processed_at = Column(DateTime(timezone=True))
    processing_time_ms = Column(Integer)

    # Uploader tracking
    uploaded_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Soft delete
    is_deleted = Column(Boolean, default=False, index=True)
    deleted_at = Column(DateTime(timezone=True))

    # Relationships
    uploader = relationship("User", foreign_keys=[uploaded_by])

    def __repr__(self):
        return f"<UploadedDocument {self.original_filename} ({self.status.value})>"

    @property
    def file_size_mb(self) -> float:
        """File size in megabytes"""
        return round(self.file_size / (1024 * 1024), 2)

    @property
    def is_processing(self) -> bool:
        """Check if document is currently being processed"""
        return self.status in [DocumentStatus.PENDING, DocumentStatus.PROCESSING]

    @property
    def can_retry(self) -> bool:
        """Check if document can be retried"""
        return self.status == DocumentStatus.FAILED and self.retry_count < 3

    def to_dict(self, include_metadata: bool = False) -> dict:
        """Convert to dictionary for API responses"""
        data = {
            "document_id": str(self.id),
            "filename": self.original_filename,
            "file_size": self.file_size,
            "file_size_mb": self.file_size_mb,
            "document_type": self.document_type.value,
            "subject": self.subject,
            "grade": self.grade,
            "education_level": self.education_level,
            "year": self.year,
            "status": self.status.value,
            "chunks_created": self.chunks_created,
            "chunks_indexed": self.chunks_indexed,
            "processing_progress": self.processing_progress,
            "error": self.error_message,
            "retry_count": self.retry_count,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "processed_at": self.processed_at.isoformat() if self.processed_at else None,
            "processing_time_ms": self.processing_time_ms,
        }

        if include_metadata:
            data["processing_metadata"] = self.processing_metadata
            data["vector_store_collection"] = self.vector_store_collection
            data["file_hash"] = self.file_hash
            data["file_path"] = self.file_path
            data["uploaded_by"] = str(self.uploaded_by) if self.uploaded_by else None

        return data


class DocumentProcessingLog(Base):
    """
    Detailed logs for document processing steps.
    Useful for debugging and monitoring the RAG pipeline.
    """
    __tablename__ = "document_processing_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    document_id = Column(UUID(as_uuid=True), ForeignKey("uploaded_documents.id", ondelete="CASCADE"), nullable=False, index=True)

    # Log details
    stage = Column(String(50), nullable=False)  # extraction, chunking, embedding, indexing
    status = Column(String(20), nullable=False)  # started, completed, failed
    message = Column(Text)
    details = Column(JSON, default=dict)

    # Timing
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    duration_ms = Column(Integer)

    # Relationships
    document = relationship("UploadedDocument")

    def __repr__(self):
        return f"<ProcessingLog {self.stage} {self.status}>"
