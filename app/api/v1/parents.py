# ============================================================================
# Parent Endpoints
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import List
from uuid import UUID

from app.core.database import get_db
from app.core.security import get_current_active_user
from app.models.user import User, UserRole, Student, ParentStudentLink
from app.services.notifications.parent_reports import ParentReportService

router = APIRouter(prefix="/parents", tags=["parents"])

class LinkChildRequest(BaseModel):
    verification_code: str

@router.get("/children")
async def get_linked_children(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get all linked children for a parent"""
    if current_user.role != UserRole.PARENT:
        raise HTTPException(status_code=403, detail="Parents only")
    
    result = await db.execute(
        select(ParentStudentLink, Student)
        .join(Student, ParentStudentLink.student_id == Student.id)
        .where(ParentStudentLink.parent_user_id == current_user.id)
        .where(ParentStudentLink.verified == True)
    )
    
    children = []
    for link, student in result.all():
        children.append({
            "student_id": str(student.id),
            "name": f"{student.first_name} {student.last_name}",
            "grade": student.grade,
            "school": student.school_name,
            "relationship": link.relationship_type
        })
    
    return {"children": children}

@router.post("/link-child")
async def link_child(
    request: LinkChildRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Link a child using verification code"""
    # Find the pending link
    result = await db.execute(
        select(ParentStudentLink)
        .where(ParentStudentLink.verification_code == request.verification_code.upper())
        .where(ParentStudentLink.verified == False)
    )
    link = result.scalar_one_or_none()
    
    if not link:
        raise HTTPException(status_code=404, detail="Invalid or expired code")
    
    # Update parent role if needed
    if current_user.role != UserRole.PARENT:
        current_user.role = UserRole.PARENT
    
    # Activate link
    link.parent_user_id = current_user.id
    link.verified = True
    
    await db.commit()
    
    # Get student name
    student = await db.get(Student, link.student_id)
    
    return {
        "message": f"Successfully linked to {student.first_name}'s account",
        "student_id": str(student.id)
    }

@router.get("/report/{student_id}")
async def get_child_report(
    student_id: UUID,
    report_type: str = "weekly",
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Get report for a specific child"""
    # Verify parent has access to this student
    result = await db.execute(
        select(ParentStudentLink)
        .where(ParentStudentLink.parent_user_id == current_user.id)
        .where(ParentStudentLink.student_id == student_id)
        .where(ParentStudentLink.verified == True)
    )
    
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Not authorized to view this student")
    
    report_service = ParentReportService(db)
    report = await report_service.generate_report(student_id, report_type)
    
    return report

@router.put("/notifications/{student_id}")
async def update_notification_settings(
    student_id: UUID,
    enabled: bool,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """Update notification settings for a child"""
    result = await db.execute(
        select(ParentStudentLink)
        .where(ParentStudentLink.parent_user_id == current_user.id)
        .where(ParentStudentLink.student_id == student_id)
    )
    link = result.scalar_one_or_none()
    
    if not link:
        raise HTTPException(status_code=404, detail="Link not found")
    
    link.notifications_enabled = enabled
    await db.commit()
    
    return {"message": "Notification settings updated"}