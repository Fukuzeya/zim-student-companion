# ============================================================================
# Admin API Endpoints - Part 2: Content, Documents, Conversations
# ============================================================================
"""
Content management, document upload, and conversation monitoring endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Form
from sqlalchemy.ext.asyncio import AsyncSession
from typing import Optional, List
from uuid import UUID

from app.api.v1.administration import require_admin
from app.core.database import get_db
from app.models.user import User
from app.services.admin.content_service import ContentManagementService
from app.services.admin.document_service import DocumentUploadService
from app.services.admin.conversation_service import ConversationMonitoringService
from app.services.admin.system_service import SystemService, AuditAction

router = APIRouter(prefix="/admin", tags=["admin-content"])


# ============================================================================
# Subject Management Endpoints
# ============================================================================
@router.get("/subjects")
async def list_subjects(
    education_level: Optional[str] = None,
    is_active: Optional[bool] = None,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """List all subjects with topic and question counts"""
    service = ContentManagementService(db)
    return await service.list_subjects(education_level=education_level, is_active=is_active)


@router.post("/subjects")
async def create_subject(
    name: str = Form(...),
    code: str = Form(...),
    education_level: str = Form(...),
    description: Optional[str] = Form(None),
    icon: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Create a new subject"""
    service = ContentManagementService(db)
    data = {
        "name": name,
        "code": code,
        "education_level": education_level,
        "description": description,
        "icon": icon,
        "color": color
    }
    return await service.create_subject(data)


@router.put("/subjects/{subject_id}")
async def update_subject(
    subject_id: UUID,
    name: Optional[str] = Form(None),
    description: Optional[str] = Form(None),
    icon: Optional[str] = Form(None),
    color: Optional[str] = Form(None),
    is_active: Optional[bool] = Form(None),
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Update an existing subject"""
    service = ContentManagementService(db)
    updates = {k: v for k, v in {
        "name": name, "description": description,
        "icon": icon, "color": color, "is_active": is_active
    }.items() if v is not None}
    
    result = await service.update_subject(subject_id, updates)
    if not result:
        raise HTTPException(status_code=404, detail="Subject not found")
    return result


@router.delete("/subjects/{subject_id}")
async def delete_subject(
    subject_id: UUID,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db)
):
    """Delete (deactivate) a subject"""
    service = ContentManagementService(db)
    if await service.delete_subject(subject_id):
        return {"message": "Subject deactivated"}
    raise HTTPException(status_code=404, detail="Subject not found")


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
    content = await file.read()
    
    service = DocumentUploadService(db)
    return await service.upload_document(
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