# ============================================================================
# Admin Conversation Monitoring Service
# ============================================================================
"""
Service layer for conversation monitoring and intervention.
Handles live conversation tracking, message review, and admin intervention capabilities.
"""
from typing import Dict, List, Optional, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_, or_, desc
from sqlalchemy.orm import selectinload
from datetime import datetime, timedelta
from uuid import UUID
import logging

from app.models.user import Student
from app.models.conversation import Conversation
from app.models.curriculum import Subject, Topic
from app.models.practice import PracticeSession

logger = logging.getLogger(__name__)


class ConversationMonitoringService:
    """
    Conversation monitoring and intervention service.
    
    Provides:
    - Live conversation monitoring
    - Conversation history retrieval
    - Admin intervention capabilities
    - Processing pipeline status
    - Conversation analytics
    """
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    # =========================================================================
    # Live Conversations
    # =========================================================================
    async def get_live_conversations(
        self,
        status: Optional[str] = None,
        subject_id: Optional[UUID] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Get currently active conversations for monitoring.
        
        Args:
            status: Filter by status (active, idle, needs_attention)
            subject_id: Filter by subject
            limit: Maximum conversations to return
            
        Returns:
            List of active conversations with student info
        """
        # Get conversations from last 30 minutes (considered "live")
        cutoff = datetime.utcnow() - timedelta(minutes=30)
        
        # Subquery to get latest message per student
        latest_subq = (
            select(
                Conversation.student_id,
                func.max(Conversation.created_at).label("last_message")
            )
            .where(Conversation.created_at >= cutoff)
            .group_by(Conversation.student_id)
            .subquery()
        )
        
        # Main query
        query = (
            select(Conversation, Student)
            .join(Student, Conversation.student_id == Student.id)
            .join(
                latest_subq,
                and_(
                    Conversation.student_id == latest_subq.c.student_id,
                    Conversation.created_at == latest_subq.c.last_message
                )
            )
            .order_by(desc(Conversation.created_at))
            .limit(limit)
        )
        
        if subject_id:
            query = query.where(Conversation.subject_id == subject_id)
        
        result = await self.db.execute(query)
        rows = result.all()
        
        conversations = []
        for conv, student in rows:
            # Calculate conversation stats
            stats = await self._get_conversation_stats(conv.student_id, cutoff)
            
            # Determine status
            time_since_last = (datetime.utcnow() - conv.created_at).total_seconds()
            if time_since_last < 120:  # Active within 2 minutes
                conv_status = "active"
            elif time_since_last < 600:  # Active within 10 minutes
                conv_status = "idle"
            else:
                conv_status = "inactive"
            
            # Check if needs attention (e.g., long response times, negative sentiment)
            needs_attention = await self._check_needs_attention(conv.student_id)
            if needs_attention:
                conv_status = "needs_attention"
            
            if status and conv_status != status:
                continue
            
            # Get subject name
            subject_name = None
            if conv.subject_id:
                subj_result = await self.db.execute(
                    select(Subject.name).where(Subject.id == conv.subject_id)
                )
                subject_name = subj_result.scalar_one_or_none()
            
            # Get topic name
            topic_name = None
            if conv.topic_id:
                topic_result = await self.db.execute(
                    select(Topic.name).where(Topic.id == conv.topic_id)
                )
                topic_name = topic_result.scalar_one_or_none()
            
            conversations.append({
                "id": str(conv.id),
                "student_id": str(student.id),
                "student_name": student.full_name,
                "student_grade": student.grade,
                "subject": subject_name,
                "topic": topic_name,
                "last_message_at": conv.created_at.isoformat(),
                "last_message_preview": conv.content[:100] + "..." if len(conv.content) > 100 else conv.content,
                "message_count": stats["message_count"],
                "status": conv_status,
                "context_type": conv.context_type,
                "time_since_last_seconds": int(time_since_last)
            })
        
        return conversations
    
    async def _get_conversation_stats(
        self,
        student_id: UUID,
        since: datetime
    ) -> Dict[str, Any]:
        """Get conversation statistics for a student"""
        result = await self.db.execute(
            select(func.count(Conversation.id))
            .where(Conversation.student_id == student_id)
            .where(Conversation.created_at >= since)
        )
        message_count = result.scalar() or 0
        
        return {"message_count": message_count}
    
    async def _check_needs_attention(self, student_id: UUID) -> bool:
        """
        Check if a conversation needs admin attention.
        
        Criteria:
        - Multiple unanswered questions
        - Negative sentiment indicators
        - Explicit help requests
        - Long wait times
        """
        # Check for help keywords in recent messages
        recent = datetime.utcnow() - timedelta(minutes=10)
        result = await self.db.execute(
            select(Conversation.content)
            .where(Conversation.student_id == student_id)
            .where(Conversation.created_at >= recent)
            .where(Conversation.role == "user")
        )
        messages = result.scalars().all()
        
        help_keywords = ["help", "stuck", "don't understand", "confused", "wrong", "not working"]
        for message in messages:
            if any(keyword in message.lower() for keyword in help_keywords):
                return True
        
        return False
    
    # =========================================================================
    # Conversation Details
    # =========================================================================
    async def get_conversation_detail(
        self,
        conversation_id: Optional[UUID] = None,
        student_id: Optional[UUID] = None,
        limit: int = 100
    ) -> Optional[Dict[str, Any]]:
        """
        Get detailed conversation history.
        
        Args:
            conversation_id: Specific conversation ID
            student_id: Get all conversations for a student
            limit: Maximum messages to return
            
        Returns:
            Conversation details with full message history
        """
        if student_id:
            # Get all recent conversations for student
            query = (
                select(Conversation)
                .where(Conversation.student_id == student_id)
                .order_by(desc(Conversation.created_at))
                .limit(limit)
            )
        elif conversation_id:
            # Get specific conversation context
            # First get the conversation to find the student
            conv_result = await self.db.execute(
                select(Conversation).where(Conversation.id == conversation_id)
            )
            conv = conv_result.scalar_one_or_none()
            if not conv:
                return None
            
            # Get surrounding messages
            query = (
                select(Conversation)
                .where(Conversation.student_id == conv.student_id)
                .where(Conversation.created_at >= conv.created_at - timedelta(hours=1))
                .where(Conversation.created_at <= conv.created_at + timedelta(hours=1))
                .order_by(Conversation.created_at)
            )
        else:
            return None
        
        result = await self.db.execute(query)
        messages = result.scalars().all()
        
        if not messages:
            return None
        
        # Get student info
        student_result = await self.db.execute(
            select(Student).where(Student.id == messages[0].student_id)
        )
        student = student_result.scalar_one_or_none()
        
        # Calculate totals
        total_tokens = sum(m.tokens_used or 0 for m in messages)
        response_times = [m.response_time_ms for m in messages if m.response_time_ms]
        avg_response_time = sum(response_times) / len(response_times) if response_times else 0
        
        # Get unique subjects discussed
        subjects = set()
        for msg in messages:
            if msg.subject_id:
                subj_result = await self.db.execute(
                    select(Subject.name).where(Subject.id == msg.subject_id)
                )
                subj_name = subj_result.scalar_one_or_none()
                if subj_name:
                    subjects.add(subj_name)
        
        return {
            "student_id": str(student.id) if student else None,
            "student_name": student.full_name if student else "Unknown",
            "messages": [
                {
                    "id": str(m.id),
                    "role": m.role,
                    "content": m.content,
                    "context_type": m.context_type,
                    "tokens_used": m.tokens_used,
                    "response_time_ms": m.response_time_ms,
                    "sources_used": m.sources_used,
                    "retrieval_score": m.retrieval_score,
                    "created_at": m.created_at.isoformat()
                }
                for m in messages
            ],
            "total_messages": len(messages),
            "total_tokens": total_tokens,
            "avg_response_time_ms": round(avg_response_time, 2),
            "subjects_discussed": list(subjects),
            "started_at": messages[0].created_at.isoformat() if messages else None,
            "last_message_at": messages[-1].created_at.isoformat() if messages else None
        }
    
    # =========================================================================
    # Admin Intervention
    # =========================================================================
    async def intervene_in_conversation(
        self,
        student_id: UUID,
        admin_id: UUID,
        message: str,
        intervention_type: str = "guidance",
        notify_student: bool = True
    ) -> Dict[str, Any]:
        """
        Allow admin to intervene in a conversation.
        
        Args:
            student_id: Student to send message to
            admin_id: Admin performing intervention
            message: Message to send
            intervention_type: Type of intervention (guidance, correction, escalation)
            notify_student: Whether to notify via WhatsApp
            
        Returns:
            Intervention result
        """
        # Verify student exists
        student_result = await self.db.execute(
            select(Student).where(Student.id == student_id)
        )
        student = student_result.scalar_one_or_none()
        
        if not student:
            return {"success": False, "error": "Student not found"}
        
        # Create intervention message in conversation history
        intervention = Conversation(
            student_id=student_id,
            role="system",
            content=f"[Admin Intervention - {intervention_type}] {message}",
            context_type="admin_intervention",
            sources_used=0
        )
        
        self.db.add(intervention)
        await self.db.commit()
        await self.db.refresh(intervention)
        
        # In production, send via WhatsApp if notify_student is True
        if notify_student:
            # await send_whatsapp_message(student.user.phone_number, message)
            pass
        
        logger.info(
            f"Admin intervention: Admin {admin_id} sent '{intervention_type}' "
            f"message to student {student_id}"
        )
        
        return {
            "success": True,
            "intervention_id": str(intervention.id),
            "student_id": str(student_id),
            "intervention_type": intervention_type,
            "notified": notify_student,
            "message": "Intervention sent successfully"
        }
    
    # =========================================================================
    # Processing Pipeline
    # =========================================================================
    async def get_pipeline_status(self) -> Dict[str, Any]:
        """
        Get conversation processing pipeline status.
        
        Returns:
            Pipeline health metrics and queue status
        """
        now = datetime.utcnow()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        
        # Messages processed today
        processed_result = await self.db.execute(
            select(func.count(Conversation.id))
            .where(Conversation.created_at >= today_start)
            .where(Conversation.role == "assistant")
        )
        processed_today = processed_result.scalar() or 0
        
        # Average response time today
        avg_time_result = await self.db.execute(
            select(func.avg(Conversation.response_time_ms))
            .where(Conversation.created_at >= today_start)
            .where(Conversation.response_time_ms.isnot(None))
        )
        avg_processing_time = avg_time_result.scalar() or 0
        
        # Failed/slow responses (>5 seconds)
        slow_result = await self.db.execute(
            select(func.count(Conversation.id))
            .where(Conversation.created_at >= today_start)
            .where(Conversation.response_time_ms > 5000)
        )
        slow_count = slow_result.scalar() or 0
        
        # Determine health
        if avg_processing_time < 2000:
            health = "healthy"
        elif avg_processing_time < 5000:
            health = "degraded"
        else:
            health = "critical"
        
        return {
            "pending": 0,  # Would come from message queue
            "processing": 0,  # Would come from active workers
            "completed_today": processed_today,
            "failed_today": slow_count,
            "avg_processing_time_ms": round(avg_processing_time, 2),
            "queue_health": health,
            "last_updated": now.isoformat()
        }
    
    # =========================================================================
    # Conversation Analytics
    # =========================================================================
    async def get_conversation_analytics(
        self,
        days: int = 7
    ) -> Dict[str, Any]:
        """Get conversation analytics for the specified period"""
        start_date = datetime.utcnow() - timedelta(days=days)
        
        # Total conversations
        total_result = await self.db.execute(
            select(func.count(Conversation.id))
            .where(Conversation.created_at >= start_date)
        )
        total_messages = total_result.scalar() or 0
        
        # By context type
        context_result = await self.db.execute(
            select(Conversation.context_type, func.count(Conversation.id))
            .where(Conversation.created_at >= start_date)
            .group_by(Conversation.context_type)
        )
        by_context = {row[0] or "general": row[1] for row in context_result.all()}
        
        # By subject
        subject_result = await self.db.execute(
            select(Subject.name, func.count(Conversation.id))
            .join(Subject, Conversation.subject_id == Subject.id)
            .where(Conversation.created_at >= start_date)
            .group_by(Subject.name)
        )
        by_subject = {row[0]: row[1] for row in subject_result.all()}
        
        # Daily volume
        daily_result = await self.db.execute(
            select(
                func.date(Conversation.created_at).label("date"),
                func.count(Conversation.id).label("count")
            )
            .where(Conversation.created_at >= start_date)
            .group_by(func.date(Conversation.created_at))
            .order_by(func.date(Conversation.created_at))
        )
        daily_volume = [
            {"date": row.date.isoformat(), "count": row.count}
            for row in daily_result.all()
        ]
        
        # Average tokens per conversation
        tokens_result = await self.db.execute(
            select(func.avg(Conversation.tokens_used))
            .where(Conversation.created_at >= start_date)
            .where(Conversation.tokens_used.isnot(None))
        )
        avg_tokens = tokens_result.scalar() or 0
        
        # Unique students
        students_result = await self.db.execute(
            select(func.count(func.distinct(Conversation.student_id)))
            .where(Conversation.created_at >= start_date)
        )
        unique_students = students_result.scalar() or 0
        
        return {
            "period_days": days,
            "total_messages": total_messages,
            "unique_students": unique_students,
            "messages_per_student": round(total_messages / unique_students, 2) if unique_students > 0 else 0,
            "by_context_type": by_context,
            "by_subject": by_subject,
            "daily_volume": daily_volume,
            "avg_tokens_per_message": round(avg_tokens, 2)
        }
    
    async def search_conversations(
        self,
        query: str,
        student_id: Optional[UUID] = None,
        date_from: Optional[datetime] = None,
        date_to: Optional[datetime] = None,
        limit: int = 50
    ) -> List[Dict[str, Any]]:
        """
        Search conversation content.
        
        Args:
            query: Search query string
            student_id: Filter by student
            date_from: Start date filter
            date_to: End date filter
            limit: Maximum results
            
        Returns:
            Matching conversation messages
        """
        search_query = select(Conversation, Student).join(
            Student, Conversation.student_id == Student.id
        ).where(
            Conversation.content.ilike(f"%{query}%")
        )
        
        if student_id:
            search_query = search_query.where(Conversation.student_id == student_id)
        
        if date_from:
            search_query = search_query.where(Conversation.created_at >= date_from)
        
        if date_to:
            search_query = search_query.where(Conversation.created_at <= date_to)
        
        search_query = search_query.order_by(desc(Conversation.created_at)).limit(limit)
        
        result = await self.db.execute(search_query)
        rows = result.all()
        
        return [
            {
                "id": str(conv.id),
                "student_id": str(student.id),
                "student_name": student.full_name,
                "role": conv.role,
                "content": conv.content,
                "context_type": conv.context_type,
                "created_at": conv.created_at.isoformat()
            }
            for conv, student in rows
        ]