# ============================================================================
# Admin Document Upload & Ingestion Service
# ============================================================================
"""
Service layer for document management and RAG system administration.
Handles document uploads, processing, and vector store operations through the UI.

This service provides a UI-friendly alternative to command-line document ingestion,
allowing administrators to upload and process documents directly from the admin panel.
"""
from typing import Dict, List, Optional, Any, BinaryIO
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from uuid import UUID, uuid4
from pathlib import Path
from dataclasses import dataclass
from enum import Enum
import logging
import asyncio
import aiofiles
import os
import tempfile
import hashlib

logger = logging.getLogger(__name__)


# ============================================================================
# Document Models (for tracking uploads)
# ============================================================================
class DocumentStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"

class DocumentType(str, Enum):
    PAST_PAPER = "past_paper"
    MARKING_SCHEME = "marking_scheme"
    SYLLABUS = "syllabus"
    TEXTBOOK = "textbook"
    TEACHER_NOTES = "teacher_notes"

@dataclass
class UploadedDocument:
    """Represents an uploaded document with metadata"""
    id: UUID
    filename: str
    original_filename: str
    file_size: int
    file_hash: str
    document_type: DocumentType
    subject: Optional[str]
    grade: Optional[str]
    education_level: str
    year: Optional[int]
    status: DocumentStatus
    chunks_created: int
    error_message: Optional[str]
    uploaded_by: UUID
    uploaded_at: datetime
    processed_at: Optional[datetime]
    processing_time_ms: Optional[int]


# ============================================================================
# Collection Mapping
# ============================================================================
COLLECTION_MAP = {
    DocumentType.PAST_PAPER: "past_papers",
    DocumentType.MARKING_SCHEME: "marking_schemes",
    DocumentType.SYLLABUS: "syllabi",
    DocumentType.TEXTBOOK: "textbooks",
    DocumentType.TEACHER_NOTES: "teacher_notes",
}


class DocumentUploadService:
    """
    Document upload and ingestion service for admin UI.
    
    Provides:
    - File upload with validation
    - Background document processing
    - Progress tracking and status updates
    - Integration with RAG vector store
    - Duplicate detection via file hashing
    """
    
    # Supported file extensions
    ALLOWED_EXTENSIONS = {'.pdf', '.docx', '.doc', '.txt'}
    
    # Maximum file size (50MB)
    MAX_FILE_SIZE = 50 * 1024 * 1024
    
    def __init__(
        self,
        db: AsyncSession,
        upload_dir: str = "/tmp/uploads",
        settings: Optional[Any] = None
    ):
        self.db = db
        self.upload_dir = Path(upload_dir)
        self.upload_dir.mkdir(parents=True, exist_ok=True)
        self.settings = settings
        
        # Track in-memory document status (use Redis in production)
        self._document_status: Dict[UUID, UploadedDocument] = {}
    
    # =========================================================================
    # File Upload
    # =========================================================================
    async def upload_document(
        self,
        file_content: bytes,
        filename: str,
        document_type: str,
        uploaded_by: UUID,
        subject: Optional[str] = None,
        grade: Optional[str] = None,
        education_level: str = "secondary",
        year: Optional[int] = None,
        process_immediately: bool = True
    ) -> Dict[str, Any]:
        """
        Upload and optionally process a document.
        
        Args:
            file_content: Raw file bytes
            filename: Original filename
            document_type: Type of document (past_paper, syllabus, etc.)
            uploaded_by: UUID of admin who uploaded
            subject: Subject name (optional, can be inferred)
            grade: Grade level (optional)
            education_level: Education level (primary, secondary, a_level)
            year: Year of publication (for past papers)
            process_immediately: Whether to start processing immediately
            
        Returns:
            Upload result with document ID and status
        """
        # Validate file extension
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_EXTENSIONS:
            return {
                "success": False,
                "error": f"Unsupported file type: {ext}. Allowed: {', '.join(self.ALLOWED_EXTENSIONS)}"
            }
        
        # Validate file size
        if len(file_content) > self.MAX_FILE_SIZE:
            return {
                "success": False,
                "error": f"File too large. Maximum size: {self.MAX_FILE_SIZE // (1024*1024)}MB"
            }
        
        # Calculate file hash for duplicate detection
        file_hash = hashlib.sha256(file_content).hexdigest()
        
        # Check for duplicates
        if await self._check_duplicate(file_hash):
            return {
                "success": False,
                "error": "Document already exists (duplicate detected)",
                "duplicate": True
            }
        
        # Generate unique filename
        doc_id = uuid4()
        safe_filename = f"{doc_id}_{filename}"
        file_path = self.upload_dir / safe_filename
        
        # Save file to disk
        async with aiofiles.open(file_path, 'wb') as f:
            await f.write(file_content)
        
        # Create document record
        doc_type = DocumentType(document_type)
        document = UploadedDocument(
            id=doc_id,
            filename=safe_filename,
            original_filename=filename,
            file_size=len(file_content),
            file_hash=file_hash,
            document_type=doc_type,
            subject=subject,
            grade=grade,
            education_level=education_level,
            year=year,
            status=DocumentStatus.PENDING,
            chunks_created=0,
            error_message=None,
            uploaded_by=uploaded_by,
            uploaded_at=datetime.utcnow(),
            processed_at=None,
            processing_time_ms=None
        )
        
        self._document_status[doc_id] = document
        
        logger.info(f"Document uploaded: {filename} ({len(file_content)} bytes) - ID: {doc_id}")
        
        # Start processing if requested
        if process_immediately:
            asyncio.create_task(self._process_document(doc_id, file_path))
        
        return {
            "success": True,
            "document_id": str(doc_id),
            "filename": filename,
            "file_size": len(file_content),
            "status": document.status.value,
            "message": "Document uploaded successfully" + (" - processing started" if process_immediately else "")
        }
    
    async def _check_duplicate(self, file_hash: str) -> bool:
        """Check if document with same hash already exists"""
        for doc in self._document_status.values():
            if doc.file_hash == file_hash and doc.status == DocumentStatus.COMPLETED:
                return True
        return False
    
    # =========================================================================
    # Document Processing
    # =========================================================================
    async def _process_document(self, doc_id: UUID, file_path: Path) -> None:
        """
        Process uploaded document - extract text, chunk, and index.
        
        This runs as a background task after upload.
        """
        document = self._document_status.get(doc_id)
        if not document:
            logger.error(f"Document not found for processing: {doc_id}")
            return
        
        start_time = datetime.utcnow()
        document.status = DocumentStatus.PROCESSING
        
        try:
            # Import RAG components (lazy import to avoid circular deps)
            from app.services.rag import (
                DocumentProcessor,
                ZIMSECDocument,
                create_embedding_service,
                create_vector_store,
            )
            
            # Create RAG document object
            rag_doc = ZIMSECDocument(
                file_path=str(file_path),
                document_type=document.document_type.value,
                subject=document.subject or "Unknown",
                education_level=document.education_level,
                grade=document.grade or "Form 3",
                year=document.year,
            )
            
            # Initialize processing components
            processor = DocumentProcessor()
            embedding_service = create_embedding_service(self.settings)
            vector_store = create_vector_store(self.settings, embedding_service)
            
            # Initialize vector store collections
            await vector_store.initialize_collections()
            
            # Process document (extract and chunk)
            logger.info(f"Processing document: {document.original_filename}")
            processed = await processor.process_document(rag_doc)
            
            chunks_count = len(processed.chunks)
            logger.info(f"Created {chunks_count} chunks from document")
            
            # Index to vector store
            collection_key = COLLECTION_MAP.get(document.document_type, "past_papers")
            indexed = await vector_store.add_documents(
                chunks=processed.chunks,
                collection_key=collection_key,
                batch_size=50,
                show_progress=False
            )
            
            # Update document status
            end_time = datetime.utcnow()
            processing_time = int((end_time - start_time).total_seconds() * 1000)
            
            document.status = DocumentStatus.COMPLETED
            document.chunks_created = indexed
            document.processed_at = end_time
            document.processing_time_ms = processing_time
            
            logger.info(f"Document processed successfully: {doc_id} - {indexed} chunks indexed in {processing_time}ms")
            
            # Clean up vector store connection
            await vector_store.close()
            
        except Exception as e:
            logger.error(f"Document processing failed: {doc_id} - {str(e)}")
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            document.processed_at = datetime.utcnow()
        
        finally:
            # Optionally clean up the uploaded file after processing
            # file_path.unlink(missing_ok=True)
            pass
    
    # =========================================================================
    # Status & Management
    # =========================================================================
    async def get_document_status(self, doc_id: UUID) -> Optional[Dict[str, Any]]:
        """
        Get current status of an uploaded document.
        
        Args:
            doc_id: Document UUID
            
        Returns:
            Document status and metadata
        """
        document = self._document_status.get(doc_id)
        if not document:
            return None
        
        return {
            "document_id": str(document.id),
            "filename": document.original_filename,
            "file_size": document.file_size,
            "document_type": document.document_type.value,
            "subject": document.subject,
            "grade": document.grade,
            "education_level": document.education_level,
            "year": document.year,
            "status": document.status.value,
            "chunks_created": document.chunks_created,
            "error": document.error_message,
            "uploaded_at": document.uploaded_at.isoformat(),
            "processed_at": document.processed_at.isoformat() if document.processed_at else None,
            "processing_time_ms": document.processing_time_ms
        }
    
    async def list_documents(
        self,
        status: Optional[str] = None,
        document_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """
        List uploaded documents with filtering.
        
        Args:
            status: Filter by status
            document_type: Filter by document type
            limit: Maximum results
            offset: Pagination offset
            
        Returns:
            List of documents with pagination
        """
        documents = list(self._document_status.values())
        
        # Apply filters
        if status:
            documents = [d for d in documents if d.status.value == status]
        if document_type:
            documents = [d for d in documents if d.document_type.value == document_type]
        
        # Sort by upload time (newest first)
        documents.sort(key=lambda x: x.uploaded_at, reverse=True)
        
        # Paginate
        total = len(documents)
        documents = documents[offset:offset + limit]
        
        return {
            "documents": [
                {
                    "document_id": str(d.id),
                    "filename": d.original_filename,
                    "file_size": d.file_size,
                    "document_type": d.document_type.value,
                    "subject": d.subject,
                    "status": d.status.value,
                    "chunks_created": d.chunks_created,
                    "uploaded_at": d.uploaded_at.isoformat(),
                    "processed_at": d.processed_at.isoformat() if d.processed_at else None
                }
                for d in documents
            ],
            "total": total,
            "limit": limit,
            "offset": offset
        }
    
    async def retry_processing(self, doc_id: UUID) -> Dict[str, Any]:
        """
        Retry processing a failed document.
        
        Args:
            doc_id: Document UUID
            
        Returns:
            Retry result
        """
        document = self._document_status.get(doc_id)
        if not document:
            return {"success": False, "error": "Document not found"}
        
        if document.status != DocumentStatus.FAILED:
            return {"success": False, "error": "Can only retry failed documents"}
        
        # Reset status and retry
        document.status = DocumentStatus.PENDING
        document.error_message = None
        
        file_path = self.upload_dir / document.filename
        if not file_path.exists():
            return {"success": False, "error": "Source file no longer exists"}
        
        asyncio.create_task(self._process_document(doc_id, file_path))
        
        return {
            "success": True,
            "document_id": str(doc_id),
            "message": "Processing retry started"
        }
    
    async def delete_document(self, doc_id: UUID) -> Dict[str, Any]:
        """
        Delete an uploaded document.
        
        Note: This does not remove chunks from the vector store.
        
        Args:
            doc_id: Document UUID
            
        Returns:
            Deletion result
        """
        document = self._document_status.get(doc_id)
        if not document:
            return {"success": False, "error": "Document not found"}
        
        # Remove file
        file_path = self.upload_dir / document.filename
        if file_path.exists():
            file_path.unlink()
        
        # Remove from tracking
        del self._document_status[doc_id]
        
        logger.info(f"Document deleted: {doc_id}")
        
        return {
            "success": True,
            "document_id": str(doc_id),
            "message": "Document deleted"
        }
    
    # =========================================================================
    # RAG Statistics
    # =========================================================================
    async def get_rag_stats(self) -> Dict[str, Any]:
        """
        Get RAG system statistics.
        
        Returns:
            Vector store health, chunk counts, collection info
        """
        try:
            from app.services.rag import create_embedding_service, create_vector_store
            
            embedding_service = create_embedding_service(self.settings)
            vector_store = create_vector_store(self.settings, embedding_service)
            
            # Get collection statistics
            stats = await vector_store.get_stats()
            
            await vector_store.close()
            
            # Add document upload stats
            total_docs = len(self._document_status)
            completed = sum(1 for d in self._document_status.values() if d.status == DocumentStatus.COMPLETED)
            processing = sum(1 for d in self._document_status.values() if d.status == DocumentStatus.PROCESSING)
            failed = sum(1 for d in self._document_status.values() if d.status == DocumentStatus.FAILED)
            
            # Find last ingestion
            completed_docs = [d for d in self._document_status.values() if d.processed_at]
            last_ingestion = max((d.processed_at for d in completed_docs), default=None)
            
            return {
                "vector_store": stats,
                "uploads": {
                    "total_documents": total_docs,
                    "completed": completed,
                    "processing": processing,
                    "failed": failed
                },
                "last_ingestion": last_ingestion.isoformat() if last_ingestion else None,
                "health": "healthy" if processing < 10 and failed < 5 else "degraded"
            }
            
        except Exception as e:
            logger.error(f"Failed to get RAG stats: {e}")
            return {
                "error": str(e),
                "health": "unhealthy"
            }
    
    # =========================================================================
    # Bulk Operations
    # =========================================================================
    async def bulk_upload(
        self,
        files: List[Dict[str, Any]],
        document_type: str,
        uploaded_by: UUID,
        common_metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload multiple documents at once.
        
        Args:
            files: List of {"content": bytes, "filename": str}
            document_type: Type for all documents
            uploaded_by: Admin UUID
            common_metadata: Shared metadata (subject, grade, etc.)
            
        Returns:
            Bulk upload results
        """
        common_metadata = common_metadata or {}
        results = []
        
        for file_data in files:
            result = await self.upload_document(
                file_content=file_data["content"],
                filename=file_data["filename"],
                document_type=document_type,
                uploaded_by=uploaded_by,
                subject=common_metadata.get("subject"),
                grade=common_metadata.get("grade"),
                education_level=common_metadata.get("education_level", "secondary"),
                year=common_metadata.get("year"),
                process_immediately=False  # Queue all, then process
            )
            results.append(result)
        
        # Start processing all uploaded documents
        successful_uploads = [r for r in results if r.get("success")]
        for upload in successful_uploads:
            doc_id = UUID(upload["document_id"])
            document = self._document_status.get(doc_id)
            if document:
                file_path = self.upload_dir / document.filename
                asyncio.create_task(self._process_document(doc_id, file_path))
        
        return {
            "total": len(files),
            "successful": len(successful_uploads),
            "failed": len(files) - len(successful_uploads),
            "results": results
        }