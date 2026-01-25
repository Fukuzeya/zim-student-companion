# ============================================================================
# Admin API Endpoints - Part 2: Content, Documents, Conversations
# ============================================================================
"""
Content management, document upload, and conversation monitoring endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID
import io

from app.api.v1.admin import require_admin
from app.core.database import get_db
from app.models.user import User
from app.services.admin.content_service import ContentManagementService
from app.services.admin.document_service_enhanced import DocumentUploadServiceEnhanced as DocumentUploadService
from app.services.admin.conversation_service import ConversationMonitoringService
from app.services.admin.system_service import SystemService, AuditAction
from app.schemas.admin import (
    SubjectCreate, SubjectUpdate, SubjectResponse, SubjectListResponse,
    SubjectSortField, SortOrder, SubjectBulkAction, SubjectBulkActionResponse,
    SubjectStats, SubjectDetailResponse, SubjectExportRequest, SubjectExportResponse,
    SubjectDependencyWarning
)

router = APIRouter(prefix="/admin", tags=["admin-content"])


# ============================================================================
# Subject Management Endpoints
# ============================================================================
@router.get("/subjects", response_model=SubjectListResponse)
async def list_subjects(
    # Filtering
    search: Optional[str] = Query(None, description="Search in name, code, description"),
    education_level: Optional[str] = Query(None, description="Filter by education level"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    has_topics: Optional[bool] = Query(None, description="Filter subjects with/without topics"),
    has_questions: Optional[bool] = Query(None, description="Filter subjects with/without questions"),
    # Sorting
    sort_by: SubjectSortField = Query(SubjectSortField.NAME, description="Field to sort by"),
    sort_order: SortOrder = Query(SortOrder.ASC, description="Sort direction"),
    # Pagination
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=10, le=100, description="Items per page"),
    # Auth
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    List subjects with filtering, sorting, and pagination.

    Supports:
    - Full-text search across name, code, and description
    - Filter by education level, active status, content availability
    - Sort by name, code, created date, topic count, or question count
    - Server-side pagination
    """
    service = ContentManagementService(db)
    return await service.list_subjects_paginated(
        search=search,
        education_level=education_level,
        is_active=is_active,
        has_topics=has_topics,
        has_questions=has_questions,
        sort_by=sort_by.value,
        sort_order=sort_order.value,
        page=page,
        page_size=page_size
    )


@router.get("/subjects/stats", response_model=SubjectStats)
async def get_subject_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get comprehensive subject statistics including counts, distribution, and trends"""
    service = ContentManagementService(db)
    return await service.get_subject_stats()


@router.get("/subjects/{subject_id}", response_model=SubjectDetailResponse)
async def get_subject_detail(
    subject_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed subject information including topics, coverage, and difficulty distribution"""
    service = ContentManagementService(db)
    result = await service.get_subject_detail(subject_id)
    if not result:
        raise HTTPException(status_code=404, detail="Subject not found")
    return result


@router.get("/subjects/{subject_id}/dependencies", response_model=SubjectDependencyWarning)
async def check_subject_dependencies(
    subject_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Check dependencies before deleting a subject. Returns warnings if subject has related content."""
    service = ContentManagementService(db)
    return await service.check_subject_dependencies(subject_id)


@router.post("/subjects", response_model=SubjectResponse)
async def create_subject(
    data: SubjectCreate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new subject with full validation.

    Code must be unique, uppercase, and match pattern [A-Z0-9-]+
    """
    service = ContentManagementService(db)
    result = await service.create_subject(data.model_dump())

    # Audit log
    system_service = SystemService(db)
    await system_service.log_action(
        admin_id=admin.id,
        admin_email=admin.email or "",
        action=AuditAction.CREATE,
        resource_type="subject",
        resource_id=result.get("id"),
        details=data.model_dump()
    )

    return result


@router.put("/subjects/{subject_id}", response_model=SubjectResponse)
async def update_subject(
    subject_id: UUID,
    data: SubjectUpdate,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing subject with partial data"""
    service = ContentManagementService(db)
    updates = data.model_dump(exclude_none=True)

    if not updates:
        raise HTTPException(status_code=400, detail="No update data provided")

    result = await service.update_subject(subject_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Subject not found")

    # Audit log
    system_service = SystemService(db)
    await system_service.log_action(
        admin_id=admin.id,
        admin_email=admin.email or "",
        action=AuditAction.UPDATE,
        resource_type="subject",
        resource_id=subject_id,
        details={"updated_fields": list(updates.keys())}
    )

    return result


@router.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Soft delete (deactivate) a subject. Check dependencies first with GET /subjects/{id}/dependencies"""
    service = ContentManagementService(db)

    # Check dependencies first
    deps = await service.check_subject_dependencies(subject_id)
    if not deps["can_delete"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete subject: {', '.join(deps['warnings'])}"
        )

    if await service.delete_subject(subject_id):
        # Audit log
        system_service = SystemService(db)
        await system_service.log_action(
            admin_id=admin.id,
            admin_email=admin.email or "",
            action=AuditAction.DELETE,
            resource_type="subject",
            resource_id=subject_id,
            details={"soft_delete": True}
        )
        return {"message": "Subject deactivated successfully"}

    raise HTTPException(status_code=404, detail="Subject not found")


@router.post("/subjects/bulk", response_model=SubjectBulkActionResponse)
async def bulk_subject_action(
    data: SubjectBulkAction,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Perform bulk actions on multiple subjects.

    Actions:
    - activate: Activate multiple subjects
    - deactivate: Deactivate multiple subjects
    - delete: Soft delete multiple subjects (with dependency check)
    """
    service = ContentManagementService(db)
    result = await service.bulk_subject_action(
        subject_ids=data.subject_ids,
        action=data.action,
        admin_id=admin.id
    )

    # Audit log
    system_service = SystemService(db)
    await system_service.log_action(
        admin_id=admin.id,
        admin_email=admin.email or "",
        action=AuditAction.UPDATE,
        resource_type="subject_bulk",
        resource_id=None,
        details={
            "action": data.action,
            "subject_count": len(data.subject_ids),
            "successful": result["successful"],
            "failed": result["failed"]
        }
    )

    return result


@router.post("/subjects/export", response_model=SubjectExportResponse)
async def export_subjects(
    data: SubjectExportRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Export subjects to CSV or JSON format.

    Options:
    - Export all subjects or specific ones by ID
    - Include related topics in export
    """
    service = ContentManagementService(db)
    result = await service.export_subjects(
        format=data.format.value,
        subject_ids=data.subject_ids,
        include_topics=data.include_topics,
        include_questions=data.include_questions
    )

    # Audit log
    system_service = SystemService(db)
    await system_service.log_action(
        admin_id=admin.id,
        admin_email=admin.email or "",
        action=AuditAction.EXPORT,
        resource_type="subject",
        resource_id=None,
        details={"format": data.format.value, "count": result["record_count"]}
    )

    return result


# ============================================================================
# Topic Management Endpoints
# ============================================================================
@router.get("/topics")
async def list_topics(
    subject_id: Optional[UUID] = None,
    grade: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List topics with filtering"""
    service = ContentManagementService(db)
    return await service.list_topics(
        subject_id=subject_id,
        grade=grade,
        is_active=is_active
    )


@router.post("/topics")
async def create_topic(
    subject_id: UUID = Form(...),
    name: str = Form(...),
    grade: str = Form(...),
    description: Optional[str] = Form(None),
    parent_topic_id: Optional[UUID] = Form(None),
    syllabus_reference: Optional[str] = Form(None),
    order_index: int = Form(0),
    estimated_hours: Optional[float] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new topic"""
    service = ContentManagementService(db)
    data = {
        "subject_id": subject_id,
        "name": name,
        "grade": grade,
        "description": description,
        "parent_topic_id": parent_topic_id,
        "syllabus_reference": syllabus_reference,
        "order_index": order_index,
        "estimated_hours": estimated_hours
    }
    return await service.create_topic(data)


@router.put("/topics/{topic_id}")
async def update_topic(
    topic_id: UUID,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    syllabus_reference: Optional[str] = Form(None),
    order_index: Optional[int] = Form(None),
    is_active: Optional[bool] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing topic"""
    service = ContentManagementService(db)
    updates = {k: v for k, v in {
        "name": name, "description": description,
        "syllabus_reference": syllabus_reference,
        "order_index": order_index, "is_active": is_active
    }.items() if v is not None}
    
    result = await service.update_topic(topic_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Topic not found")
    return result


@router.post("/topics/reorder")
async def reorder_topics(
    orders: List[dict],  # [{"id": UUID, "order_index": int}]
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Bulk update topic ordering"""
    service = ContentManagementService(db)
    return await service.reorder_topics(orders)


# ============================================================================
# Question Management Endpoints
# ============================================================================
@router.get("/questions")
async def list_questions(
    subject_id: Optional[UUID] = None,
    topic_id: Optional[UUID] = None,
    difficulty: Optional[str] = None,
    question_type: Optional[str] = None,
    source: Optional[str] = None,
    is_active: Optional[bool] = None,
    search: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=10, le=100),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List questions with comprehensive filtering"""
    service = ContentManagementService(db)
    return await service.list_questions(
        subject_id=subject_id,
        topic_id=topic_id,
        difficulty=difficulty,
        question_type=question_type,
        source=source,
        is_active=is_active,
        search=search,
        page=page,
        page_size=page_size
    )


@router.get("/questions/{question_id}")
async def get_question_detail(
    question_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get full question details including answer"""
    service = ContentManagementService(db)
    result = await service.get_question_detail(question_id)
    if not result:
        raise HTTPException(status_code=404, detail="Question not found")
    return result


@router.post("/questions")
async def create_question(
    subject_id: UUID = Form(...),
    question_text: str = Form(...),
    question_type: str = Form(...),
    correct_answer: str = Form(...),
    topic_id: Optional[UUID] = Form(None),
    options: Optional[str] = Form(None),  # JSON string for MCQ
    marking_scheme: Optional[str] = Form(None),
    explanation: Optional[str] = Form(None),
    marks: int = Form(1),
    difficulty: str = Form("medium"),
    source: str = Form("admin"),
    source_year: Optional[int] = Form(None),
    tags: Optional[str] = Form(None),  # Comma-separated
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new question"""
    import json
    
    service = ContentManagementService(db)
    data = {
        "subject_id": subject_id,
        "topic_id": topic_id,
        "question_text": question_text,
        "question_type": question_type,
        "options": json.loads(options) if options else None,
        "correct_answer": correct_answer,
        "marking_scheme": marking_scheme,
        "explanation": explanation,
        "marks": marks,
        "difficulty": difficulty,
        "source": source,
        "source_year": source_year,
        "tags": tags.split(",") if tags else []
    }
    return await service.create_question(data)


@router.put("/questions/{question_id}")
async def update_question(
    question_id: UUID,
    question_text: Optional[str] = Form(None),
    correct_answer: Optional[str] = Form(None),
    marking_scheme: Optional[str] = Form(None),
    explanation: Optional[str] = Form(None),
    difficulty: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing question"""
    service = ContentManagementService(db)
    updates = {k: v for k, v in {
        "question_text": question_text,
        "correct_answer": correct_answer,
        "marking_scheme": marking_scheme,
        "explanation": explanation,
        "difficulty": difficulty,
        "is_active": is_active
    }.items() if v is not None}
    
    result = await service.update_question(question_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Question not found")
    return result


@router.post("/questions/bulk")
async def bulk_upload_questions(
    file: UploadFile = File(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Bulk upload questions from JSON file.
    
    Expected JSON format:
    [
        {
            "subject_id": "uuid",
            "topic_id": "uuid" (optional),
            "question_text": "...",
            "question_type": "multiple_choice|short_answer|...",
            "correct_answer": "...",
            "options": ["a", "b", "c", "d"] (for MCQ),
            "marks": 1,
            "difficulty": "easy|medium|hard"
        }
    ]
    """
    import json
    
    content = await file.read()
    try:
        questions_data = json.loads(content)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON file")
    
    service = ContentManagementService(db)
    return await service.bulk_import_questions(questions_data)


@router.post("/questions/{question_id}/flag")
async def flag_question(
    question_id: UUID,
    reason: str = Form(...),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Flag a question for review"""
    service = ContentManagementService(db)
    return await service.flag_question(question_id, reason, admin.id)


@router.get("/questions/stats")
async def get_question_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get question bank statistics"""
    service = ContentManagementService(db)
    return await service.get_question_stats()


# ============================================================================
# Curriculum Overview Endpoints
# ============================================================================
@router.get("/curriculum/tree")
async def get_curriculum_tree(
    education_level: Optional[str] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get hierarchical curriculum tree for visualization"""
    service = ContentManagementService(db)
    return await service.get_curriculum_tree(education_level)


@router.get("/curriculum/coverage/{subject_id}")
async def get_coverage_analysis(
    subject_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Analyze curriculum coverage - find topics without questions"""
    service = ContentManagementService(db)
    return await service.get_coverage_analysis(subject_id)


# ============================================================================
# Document Management Endpoints
# ============================================================================
@router.post("/documents/upload")
async def upload_document(
    file: UploadFile = File(...),
    document_type: str = Form(...),
    subject: Optional[str] = Form(None),
    grade: Optional[str] = Form(None),
    education_level: str = Form("secondary"),
    year: Optional[int] = Form(None),
    process_immediately: bool = Form(True),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Upload a document for RAG ingestion.

    Supported document types:
    - past_paper: Past examination papers
    - marking_scheme: Marking schemes
    - syllabus: ZIMSEC syllabi
    - textbook: Textbook content
    - teacher_notes: Teacher notes and guides

    The document will be processed, chunked, and indexed into the vector store.
    """
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Validate file exists
        if not file or not file.filename:
            raise HTTPException(status_code=400, detail="No file provided")

        # Read file content
        content = await file.read()

        if len(content) == 0:
            raise HTTPException(status_code=400, detail="File is empty")

        logger.info(f"Received document upload: {file.filename} ({len(content)} bytes) - type: {document_type}")

        service = DocumentUploadService(db)
        result = await service.upload_document(
            file_content=content,
            filename=file.filename,
            document_type=document_type,
            uploaded_by=admin.id,
            subject=subject,
            grade=grade,
            education_level=education_level,
            year=year,
            process_immediately=process_immediately
        )

        if not result.get("success"):
            logger.warning(f"Document upload failed: {result.get('error')}")
            raise HTTPException(
                status_code=400,
                detail=result.get("error", "Upload failed")
            )

        logger.info(f"Document uploaded successfully: {result.get('document_id')}")
        return result

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error during document upload: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Failed to process document: {str(e)}"
        )


@router.get("/documents")
async def list_documents(
    status: Optional[str] = None,
    document_type: Optional[str] = None,
    limit: int = Query(50, ge=10, le=200),
    offset: int = Query(0, ge=0),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List uploaded documents with status"""
    service = DocumentUploadService(db)
    return await service.list_documents(
        status=status,
        document_type=document_type,
        limit=limit,
        offset=offset
    )


@router.get("/documents/{document_id}")
async def get_document_status(
    document_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get processing status of an uploaded document"""
    service = DocumentUploadService(db)
    result = await service.get_document_status(document_id)
    if not result:
        raise HTTPException(status_code=404, detail="Document not found")
    return result


@router.post("/documents/{document_id}/retry")
async def retry_document_processing(
    document_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Retry processing a failed document"""
    service = DocumentUploadService(db)
    return await service.retry_processing(document_id)


@router.delete("/documents/{document_id}")
async def delete_document(
    document_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete an uploaded document"""
    service = DocumentUploadService(db)
    return await service.delete_document(document_id)


@router.get("/rag/stats")
async def get_rag_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get RAG system statistics"""
    service = DocumentUploadService(db)
    return await service.get_rag_stats()


# ============================================================================
# Conversation Monitoring Endpoints
# ============================================================================
@router.get("/conversations/live")
async def get_live_conversations(
    status: Optional[str] = None,
    subject_id: Optional[UUID] = None,
    limit: int = Query(50, ge=10, le=200),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Get currently active conversations for monitoring.
    
    Status options:
    - active: Messages within last 2 minutes
    - idle: Messages within last 10 minutes
    - needs_attention: Flagged for admin review
    """
    service = ConversationMonitoringService(db)
    return await service.get_live_conversations(
        status=status,
        subject_id=subject_id,
        limit=limit
    )


@router.get("/conversations/pipeline")
async def get_conversation_pipeline_status(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation processing pipeline status"""
    service = ConversationMonitoringService(db)
    return await service.get_pipeline_status()


@router.get("/conversations/{conversation_id}")
async def get_conversation_detail(
    conversation_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get detailed conversation with message history"""
    service = ConversationMonitoringService(db)
    result = await service.get_conversation_detail(conversation_id=conversation_id)
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result


@router.get("/conversations/{conversation_id}/messages")
async def get_conversation_messages(
    conversation_id: UUID,
    limit: int = Query(100, ge=10, le=500),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get messages for a specific conversation"""
    service = ConversationMonitoringService(db)
    result = await service.get_conversation_detail(
        conversation_id=conversation_id,
        limit=limit
    )
    if not result:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return result.get("messages", [])


@router.post("/conversations/{student_id}/intervene")
async def intervene_in_conversation(
    student_id: UUID,
    message: str = Form(...),
    intervention_type: str = Form("guidance"),
    notify_student: bool = Form(True),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """
    Admin intervention in a student conversation.
    
    Intervention types:
    - guidance: Provide helpful direction
    - correction: Correct a misunderstanding
    - escalation: Escalate to support
    """
    service = ConversationMonitoringService(db)
    result = await service.intervene_in_conversation(
        student_id=student_id,
        admin_id=admin.id,
        message=message,
        intervention_type=intervention_type,
        notify_student=notify_student
    )
    
    # Log the intervention
    system_service = SystemService(db)
    await system_service.log_action(
        admin_id=admin.id,
        admin_email=admin.email or "",
        action=AuditAction.UPDATE,
        resource_type="conversation",
        resource_id=student_id,
        details={"intervention_type": intervention_type}
    )
    
    return result


@router.get("/conversations/analytics")
async def get_conversation_analytics(
    days: int = Query(7, ge=1, le=90),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Get conversation analytics for the specified period"""
    service = ConversationMonitoringService(db)
    return await service.get_conversation_analytics(days=days)


@router.get("/conversations/search")
async def search_conversations(
    query: str = Query(..., min_length=2),
    student_id: Optional[UUID] = None,
    limit: int = Query(50, ge=10, le=200),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Search conversation content"""
    service = ConversationMonitoringService(db)
    return await service.search_conversations(
        query=query,
        student_id=student_id,
        limit=limit
    )