# ============================================================================
# Report Generation Tasks
# ============================================================================
from celery import shared_task
import logging

from app.tasks.daily_tasks import run_async

logger = logging.getLogger(__name__)

@shared_task(name="app.tasks.report_tasks.send_weekly_parent_reports")
def send_weekly_parent_reports():
    """Send weekly reports to all linked parents"""
    async def _send_reports():
        from app.core.database import async_session_maker
        from app.models.user import ParentStudentLink, User, Student
        from app.services.notifications.parent_reports import ParentReportService
        from app.services.notifications.push_notifications import NotificationService
        from sqlalchemy import select
        
        async with async_session_maker() as db:
            # Get all verified parent-student links with notifications enabled
            result = await db.execute(
                select(ParentStudentLink)
                .where(ParentStudentLink.verified == True)
                .where(ParentStudentLink.notifications_enabled == True)
            )
            links = result.scalars().all()
            
            report_service = ParentReportService(db)
            notification_service = NotificationService(db)
            
            sent_count = 0
            
            for link in links:
                try:
                    # Generate report
                    report = await report_service.generate_report(
                        link.student_id, "weekly"
                    )
                    
                    # Send to parent
                    success = await notification_service.send_parent_weekly_report(
                        parent_user_id=link.parent_user_id,
                        student_id=link.student_id,
                        report=report
                    )
                    
                    if success:
                        sent_count += 1
                except Exception as e:
                    logger.error(f"Failed to send report for link {link.id}: {e}")
            
            logger.info(f"Sent {sent_count} weekly parent reports")
            return sent_count
    
    return run_async(_send_reports())

@shared_task(name="app.tasks.report_tasks.generate_school_report")
def generate_school_report(school_name: str):
    """Generate report for a school"""
    async def _generate():
        from app.core.database import async_session_maker
        from app.models.user import Student
        from app.services.analytics.student_progress import StudentProgressAnalytics
        from sqlalchemy import select, func
        
        async with async_session_maker() as db:
            # Get all students from the school
            result = await db.execute(
                select(Student).where(Student.school_name == school_name)
            )
            students = result.scalars().all()
            
            if not students:
                return {"error": "No students found for this school"}
            
            analytics = StudentProgressAnalytics(db)
            
            school_stats = {
                "school_name": school_name,
                "total_students": len(students),
                "grade_breakdown": {},
                "overall_stats": {
                    "total_xp": 0,
                    "avg_level": 0,
                    "total_questions": 0
                }
            }
            
            for student in students:
                school_stats["overall_stats"]["total_xp"] += student.total_xp or 0
                
                grade = student.grade
                if grade not in school_stats["grade_breakdown"]:
                    school_stats["grade_breakdown"][grade] = {"count": 0, "total_xp": 0}
                
                school_stats["grade_breakdown"][grade]["count"] += 1
                school_stats["grade_breakdown"][grade]["total_xp"] += student.total_xp or 0
            
            school_stats["overall_stats"]["avg_level"] = sum(
                s.level or 1 for s in students
            ) / len(students)
            
            return school_stats
    
    return run_async(_generate())