# ============================================================================
# Enhanced Admin Document Upload & Ingestion Service
# ============================================================================
"""
Enhanced service layer for document management with:
- Database persistence instead of in-memory storage
- Real-time progress tracking
- Better error handling and validation
- Detailed processing logs
- File preview and metadata extraction
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_
from datetime import datetime
from uuid import UUID, uuid4
from pathlib import Path
import logging
import asyncio
import aiofiles
import hashlib
import mimetypes

from app.models.document import (
    UploadedDocument,
    DocumentProcessingLog,
    DocumentStatus,
    DocumentType
)

logger = logging.getLogger(__name__)


class DocumentUploadServiceEnhanced:
    """
    Enhanced document upload and ingestion service.

    Improvements over original:
    - Persists to database (PostgreSQL)
    - Detailed progress tracking with logs
    - Better validation and error messages
    - File preview capabilities
    - Duplicate detection via database
    - Batch upload with progress callbacks
    """

    # Supported file extensions with MIME types
    ALLOWED_TYPES = {
        '.pdf': 'application/pdf',
        '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
        '.doc': 'application/msword',
        '.txt': 'text/plain',
    }

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

    # =========================================================================
    # File Upload & Validation
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
        paper_number: Optional[str] = None,
        term: Optional[str] = None,
        process_immediately: bool = True
    ) -> Dict[str, Any]:
        """
        Upload and optionally process a document.

        Returns comprehensive upload result with validation errors.
        """
        # Validate file
        validation_result = self._validate_file(file_content, filename)
        if not validation_result["valid"]:
            return {
                "success": False,
                "error": validation_result["error"],
                "error_code": validation_result["error_code"]
            }

        # Calculate file hash
        file_hash = hashlib.sha256(file_content).hexdigest()

        # Check for duplicates in database
        duplicate = await self._check_duplicate(file_hash)
        if duplicate:
            return {
                "success": False,
                "error": f"Document already exists: {duplicate.original_filename}",
                "error_code": "DUPLICATE_FILE",
                "duplicate_id": str(duplicate.id),
                "duplicate_info": duplicate.to_dict()
            }

        # Generate unique filename and save
        doc_id = uuid4()
        ext = Path(filename).suffix.lower()
        safe_filename = f"{doc_id}{ext}"
        file_path = self.upload_dir / safe_filename

        try:
            async with aiofiles.open(file_path, 'wb') as f:
                await f.write(file_content)
        except Exception as e:
            logger.error(f"Failed to save file: {e}")
            return {
                "success": False,
                "error": "Failed to save file to disk",
                "error_code": "SAVE_ERROR"
            }

        # Detect MIME type
        mime_type = mimetypes.guess_type(filename)[0] or self.ALLOWED_TYPES.get(ext)

        # Create database record
        try:
            doc_type = DocumentType(document_type)
        except ValueError:
            return {
                "success": False,
                "error": f"Invalid document type: {document_type}",
                "error_code": "INVALID_TYPE"
            }

        document = UploadedDocument(
            id=doc_id,
            filename=safe_filename,
            original_filename=filename,
            file_path=str(file_path),
            file_size=len(file_content),
            file_hash=file_hash,
            mime_type=mime_type,
            document_type=doc_type,
            subject=subject,
            grade=grade,
            education_level=education_level,
            year=year,
            paper_number=paper_number,
            term=term,
            status=DocumentStatus.PENDING,
            uploaded_by=uploaded_by,
            processing_progress=0.0
        )

        self.db.add(document)
        await self.db.commit()
        await self.db.refresh(document)

        logger.info(f"Document uploaded: {filename} ({len(file_content)} bytes) - ID: {doc_id}")

        # Start processing if requested
        if process_immediately:
            asyncio.create_task(self._process_document_async(doc_id))

        return {
            "success": True,
            "document_id": str(doc_id),
            "document": document.to_dict(),
            "message": "Document uploaded successfully" + (" - processing started" if process_immediately else "")
        }

    def _validate_file(self, content: bytes, filename: str) -> Dict[str, Any]:
        """Validate file type and size"""
        # Check extension
        ext = Path(filename).suffix.lower()
        if ext not in self.ALLOWED_TYPES:
            return {
                "valid": False,
                "error": f"Unsupported file type: {ext}. Allowed: {', '.join(self.ALLOWED_TYPES.keys())}",
                "error_code": "INVALID_EXTENSION"
            }

        # Check size
        if len(content) > self.MAX_FILE_SIZE:
            max_mb = self.MAX_FILE_SIZE // (1024 * 1024)
            actual_mb = len(content) / (1024 * 1024)
            return {
                "valid": False,
                "error": f"File too large ({actual_mb:.1f}MB). Maximum: {max_mb}MB",
                "error_code": "FILE_TOO_LARGE"
            }

        # Check if empty
        if len(content) == 0:
            return {
                "valid": False,
                "error": "File is empty",
                "error_code": "EMPTY_FILE"
            }

        return {"valid": True}

    async def _check_duplicate(self, file_hash: str) -> Optional[UploadedDocument]:
        """Check if document with same hash exists"""
        result = await self.db.execute(
            select(UploadedDocument)
            .where(
                and_(
                    UploadedDocument.file_hash == file_hash,
                    UploadedDocument.status == DocumentStatus.COMPLETED,
                    UploadedDocument.is_deleted == False
                )
            )
        )
        return result.scalars().first()

    # =========================================================================
    # Document Processing
    # =========================================================================
    async def _process_document_async(self, doc_id: UUID) -> None:
        """
        Process document in background.
        Updates progress and logs steps.
        """
        # Get fresh document from DB
        result = await self.db.execute(
            select(UploadedDocument).where(UploadedDocument.id == doc_id)
        )
        document = result.scalars().first()

        if not document:
            logger.error(f"Document not found: {doc_id}")
            return

        start_time = datetime.utcnow()
        file_path = Path(document.file_path)

        # Update status
        document.status = DocumentStatus.PROCESSING
        document.processing_started_at = start_time
        document.processing_progress = 0.0
        await self.db.commit()

        await self._log_processing_step(doc_id, "processing", "started", "Document processing started")

        try:
            # Step 1: Extract content (0-30%)
            await self._update_progress(doc_id, 5.0, "Extracting text from document...")
            await self._log_processing_step(doc_id, "extraction", "started", "Starting content extraction")

            from app.services.rag import (
                DocumentProcessor,
                ZIMSECDocument,
                create_embedding_service,
                create_vector_store,
            )

            # Create RAG document
            rag_doc = ZIMSECDocument(
                file_path=str(file_path),
                document_type=document.document_type.value,
                subject=document.subject or "Unknown",
                education_level=document.education_level,
                grade=document.grade or "Form 3",
                year=document.year,
                paper_number=document.paper_number,
                term=document.term,
            )

            processor = DocumentProcessor()

            await self._update_progress(doc_id, 30.0, "Content extracted successfully")
            await self._log_processing_step(doc_id, "extraction", "completed", "Content extraction completed")

            # Step 2: Chunk content (30-60%)
            await self._update_progress(doc_id, 35.0, "Chunking document...")
            await self._log_processing_step(doc_id, "chunking", "started", "Starting document chunking")

            processed = await processor.process_document(rag_doc)
            chunks_count = len(processed.chunks)

            document.processing_metadata = processed.processing_metadata
            document.chunks_created = chunks_count
            await self.db.commit()

            await self._update_progress(doc_id, 60.0, f"Created {chunks_count} chunks")
            await self._log_processing_step(
                doc_id, "chunking", "completed",
                f"Created {chunks_count} chunks",
                {"chunks_count": chunks_count, "metadata": processed.processing_metadata}
            )

            # Step 3: Generate embeddings and index (60-100%)
            await self._update_progress(doc_id, 65.0, "Generating embeddings...")
            await self._log_processing_step(doc_id, "embedding", "started", "Generating embeddings")

            embedding_service = create_embedding_service(self.settings)
            vector_store = create_vector_store(self.settings, embedding_service)

            await vector_store.initialize_collections()

            # Map document type to collection
            collection_map = {
                DocumentType.PAST_PAPER: "past_papers",
                DocumentType.MARKING_SCHEME: "marking_schemes",
                DocumentType.SYLLABUS: "syllabi",
                DocumentType.TEXTBOOK: "textbooks",
                DocumentType.TEACHER_NOTES: "teacher_notes",
            }
            collection_key = collection_map.get(document.document_type, "past_papers")
            document.vector_store_collection = collection_key
            await self.db.commit()

            await self._update_progress(doc_id, 80.0, "Indexing to vector store...")
            await self._log_processing_step(doc_id, "indexing", "started", f"Indexing to collection: {collection_key}")

            indexed = await vector_store.add_documents(
                chunks=processed.chunks,
                collection_key=collection_key,
                batch_size=50,
                show_progress=False
            )

            await vector_store.close()

            # Success
            end_time = datetime.utcnow()
            processing_time = int((end_time - start_time).total_seconds() * 1000)

            document.status = DocumentStatus.COMPLETED
            document.chunks_indexed = indexed
            document.processed_at = end_time
            document.processing_time_ms = processing_time
            document.processing_progress = 100.0
            await self.db.commit()

            await self._log_processing_step(
                doc_id, "indexing", "completed",
                f"Successfully indexed {indexed} chunks in {processing_time}ms",
                {"chunks_indexed": indexed, "processing_time_ms": processing_time}
            )

            logger.info(f"Document processed successfully: {doc_id} - {indexed} chunks in {processing_time}ms")

        except Exception as e:
            logger.error(f"Document processing failed: {doc_id} - {str(e)}")
            document.status = DocumentStatus.FAILED
            document.error_message = str(e)
            document.processed_at = datetime.utcnow()
            document.processing_progress = 0.0
            await self.db.commit()

            await self._log_processing_step(
                doc_id, "processing", "failed",
                f"Processing failed: {str(e)}",
                {"error": str(e), "error_type": type(e).__name__}
            )

    async def _update_progress(self, doc_id: UUID, progress: float, message: str = "") -> None:
        """Update document processing progress"""
        result = await self.db.execute(
            select(UploadedDocument).where(UploadedDocument.id == doc_id)
        )
        document = result.scalars().first()
        if document:
            document.processing_progress = progress
            if message:
                if not document.processing_metadata:
                    document.processing_metadata = {}
                document.processing_metadata["last_message"] = message
            await self.db.commit()
            logger.debug(f"Document {doc_id} progress: {progress}% - {message}")

    async def _log_processing_step(
        self,
        doc_id: UUID,
        stage: str,
        status: str,
        message: str,
        details: Optional[Dict] = None
    ) -> None:
        """Log a processing step to database"""
        log = DocumentProcessingLog(
            document_id=doc_id,
            stage=stage,
            status=status,
            message=message,
            details=details or {}
        )
        self.db.add(log)
        await self.db.commit()

    # =========================================================================
    # Status & Management
    # =========================================================================
    async def get_document_status(self, doc_id: UUID) -> Optional[Dict[str, Any]]:
        """Get current status of a document"""
        result = await self.db.execute(
            select(UploadedDocument).where(
                and_(
                    UploadedDocument.id == doc_id,
                    UploadedDocument.is_deleted == False
                )
            )
        )
        document = result.scalars().first()

        if not document:
            return None

        # Get processing logs
        logs_result = await self.db.execute(
            select(DocumentProcessingLog)
            .where(DocumentProcessingLog.document_id == doc_id)
            .order_by(DocumentProcessingLog.created_at.desc())
            .limit(10)
        )
        logs = logs_result.scalars().all()

        doc_dict = document.to_dict(include_metadata=True)
        doc_dict["processing_logs"] = [
            {
                "stage": log.stage,
                "status": log.status,
                "message": log.message,
                "created_at": log.created_at.isoformat()
            }
            for log in logs
        ]

        return doc_dict

    async def list_documents(
        self,
        status: Optional[str] = None,
        document_type: Optional[str] = None,
        subject: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> Dict[str, Any]:
        """List documents with filtering and pagination"""
        query = select(UploadedDocument).where(UploadedDocument.is_deleted == False)

        # Apply filters
        if status:
            try:
                status_enum = DocumentStatus(status)
                query = query.where(UploadedDocument.status == status_enum)
            except ValueError:
                pass

        if document_type:
            try:
                type_enum = DocumentType(document_type)
                query = query.where(UploadedDocument.document_type == type_enum)
            except ValueError:
                pass

        if subject:
            query = query.where(UploadedDocument.subject.ilike(f"%{subject}%"))

        # Get total count
        count_query = select(func.count()).select_from(query.subquery())
        total_result = await self.db.execute(count_query)
        total = total_result.scalar()

        # Order and paginate
        query = query.order_by(UploadedDocument.uploaded_at.desc())
        query = query.limit(limit).offset(offset)

        result = await self.db.execute(query)
        documents = result.scalars().all()

        return {
            "documents": [doc.to_dict() for doc in documents],
            "total": total,
            "limit": limit,
            "offset": offset,
            "has_more": (offset + limit) < total
        }

    async def retry_processing(self, doc_id: UUID) -> Dict[str, Any]:
        """Retry processing a failed document"""
        result = await self.db.execute(
            select(UploadedDocument).where(
                and_(
                    UploadedDocument.id == doc_id,
                    UploadedDocument.is_deleted == False
                )
            )
        )
        document = result.scalars().first()

        if not document:
            return {"success": False, "error": "Document not found"}

        if not document.can_retry:
            return {
                "success": False,
                "error": f"Cannot retry document in {document.status.value} status or retry limit reached"
            }

        # Check if file still exists
        file_path = Path(document.file_path)
        if not file_path.exists():
            return {"success": False, "error": "Source file no longer exists"}

        # Reset for retry
        document.status = DocumentStatus.PENDING
        document.error_message = None
        document.processing_progress = 0.0
        document.retry_count += 1
        await self.db.commit()

        # Start processing
        asyncio.create_task(self._process_document_async(doc_id))

        logger.info(f"Retrying document processing: {doc_id} (attempt {document.retry_count})")

        return {
            "success": True,
            "document_id": str(doc_id),
            "retry_count": document.retry_count,
            "message": "Processing retry started"
        }

    async def delete_document(self, doc_id: UUID, hard_delete: bool = False) -> Dict[str, Any]:
        """Delete a document (soft delete by default)"""
        result = await self.db.execute(
            select(UploadedDocument).where(UploadedDocument.id == doc_id)
        )
        document = result.scalars().first()

        if not document:
            return {"success": False, "error": "Document not found"}

        if hard_delete:
            # Remove file
            file_path = Path(document.file_path)
            if file_path.exists():
                file_path.unlink()

            # Delete from database
            await self.db.delete(document)
            await self.db.commit()

            logger.info(f"Document hard deleted: {doc_id}")
            return {
                "success": True,
                "document_id": str(doc_id),
                "message": "Document permanently deleted"
            }
        else:
            # Soft delete
            document.is_deleted = True
            document.deleted_at = datetime.utcnow()
            await self.db.commit()

            logger.info(f"Document soft deleted: {doc_id}")
            return {
                "success": True,
                "document_id": str(doc_id),
                "message": "Document deleted (can be restored)"
            }

    # =========================================================================
    # RAG Statistics
    # =========================================================================
    async def get_rag_stats(self) -> Dict[str, Any]:
        """Get comprehensive RAG system statistics"""
        try:
            # Document upload stats
            stats_query = select(
                UploadedDocument.status,
                func.count(UploadedDocument.id).label("count"),
                func.sum(UploadedDocument.chunks_indexed).label("total_chunks"),
                func.sum(UploadedDocument.file_size).label("total_size")
            ).where(
                UploadedDocument.is_deleted == False
            ).group_by(UploadedDocument.status)

            result = await self.db.execute(stats_query)
            status_stats = result.all()

            stats_by_status = {}
            total_chunks = 0
            total_size = 0

            for row in status_stats:
                stats_by_status[row.status.value] = {
                    "count": row.count,
                    "chunks": row.total_chunks or 0
                }
                total_chunks += row.total_chunks or 0
                total_size += row.total_size or 0

            # Document type breakdown
            type_query = select(
                UploadedDocument.document_type,
                func.count(UploadedDocument.id).label("count")
            ).where(
                and_(
                    UploadedDocument.is_deleted == False,
                    UploadedDocument.status == DocumentStatus.COMPLETED
                )
            ).group_by(UploadedDocument.document_type)

            type_result = await self.db.execute(type_query)
            type_stats = type_result.all()

            by_type = {row.document_type.value: row.count for row in type_stats}

            # Last ingestion
            last_doc_query = select(UploadedDocument).where(
                and_(
                    UploadedDocument.status == DocumentStatus.COMPLETED,
                    UploadedDocument.is_deleted == False
                )
            ).order_by(UploadedDocument.processed_at.desc()).limit(1)

            last_result = await self.db.execute(last_doc_query)
            last_doc = last_result.scalars().first()

            # Try to get vector store stats
            try:
                from app.services.rag import create_embedding_service, create_vector_store

                embedding_service = create_embedding_service(self.settings)
                vector_store = create_vector_store(self.settings, embedding_service)
                vector_stats = await vector_store.get_stats()
                await vector_store.close()
            except Exception as e:
                logger.warning(f"Could not get vector store stats: {e}")
                vector_stats = {"error": "Vector store unavailable"}

            return {
                "uploads": {
                    "by_status": stats_by_status,
                    "by_type": by_type,
                    "total_chunks_indexed": total_chunks,
                    "total_storage_bytes": total_size,
                    "total_storage_mb": round(total_size / (1024 * 1024), 2),
                },
                "last_ingestion": last_doc.processed_at.isoformat() if last_doc else None,
                "last_document": last_doc.to_dict() if last_doc else None,
                "vector_store": vector_stats,
                "health": self._assess_health(stats_by_status)
            }

        except Exception as e:
            logger.error(f"Failed to get RAG stats: {e}")
            return {
                "error": str(e),
                "health": "unhealthy"
            }

    def _assess_health(self, stats_by_status: Dict) -> str:
        """Assess system health based on stats"""
        processing = stats_by_status.get("processing", {}).get("count", 0)
        failed = stats_by_status.get("failed", {}).get("count", 0)

        if processing > 20:
            return "degraded - too many processing"
        if failed > 10:
            return "degraded - too many failures"
        if processing > 50:
            return "unhealthy - processing backlog"

        return "healthy"

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
        """Upload multiple documents"""
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
                paper_number=common_metadata.get("paper_number"),
                term=common_metadata.get("term"),
                process_immediately=False
            )
            results.append(result)

        # Start processing all successful uploads
        successful = [r for r in results if r.get("success")]
        for upload in successful:
            doc_id = UUID(upload["document_id"])
            asyncio.create_task(self._process_document_async(doc_id))

        return {
            "total": len(files),
            "successful": len(successful),
            "failed": len(files) - len(successful),
            "results": results
        }
