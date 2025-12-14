# ============================================================================
# Message Handlers
# ============================================================================
from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging

from app.services.whatsapp.client import WhatsAppClient, WhatsAppMessage
from app.services.whatsapp.flows import ConversationFlow, FlowState
from app.services.rag.rag_engine import RAGEngine
from app.models.user import User, Student
from app.models.conversation import Conversation
from app.core.redis import cache

logger = logging.getLogger(__name__)

class MessageHandler:
    """Handles incoming WhatsApp messages"""
    
    def __init__(
        self,
        wa_client: WhatsAppClient,
        rag_engine: RAGEngine,
        db: AsyncSession
    ):
        self.wa = wa_client
        self.rag = rag_engine
        self.db = db
        self.flow = ConversationFlow(wa_client, db)
    
    async def handle_message(self, message: WhatsAppMessage) -> None:
        """Main message handler"""
        phone = message.from_number
        
        # Mark as read
        await self.wa.mark_as_read(message.message_id)
        
        # Get or create user
        user = await self._get_or_create_user(phone)
        
        # Get current flow state
        state = await self._get_flow_state(phone)
        
        # Determine message intent
        text = self._get_message_text(message)
        
        if not text:
            await self.wa.send_text(
                phone,
                "I can only understand text messages right now. Please type your question! 📝"
            )
            return
        
        # Check for commands
        if text.lower() in ["menu", "help", "start"]:
            await self.flow.show_main_menu(phone, user)
            return
        
        # Route based on flow state
        if state and state.flow_name == "onboarding":
            await self.flow.handle_onboarding(phone, message, state)
        elif state and state.flow_name == "practice":
            await self._handle_practice(phone, message, user, state)
        elif state and state.flow_name == "parent_link":
            await self.flow.handle_parent_linking(phone, message, state)
        else:
            # General conversation - use RAG
            await self._handle_general_query(phone, text, user)
    
    async def _get_or_create_user(self, phone: str) -> Optional[User]:
        """Get existing user or start onboarding"""
        result = await self.db.execute(
            select(User).where(User.phone_number == phone)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            # Start onboarding flow
            await self.flow.start_onboarding(phone)
            return None
        
        return user
    
    async def _get_flow_state(self, phone: str) -> Optional[FlowState]:
        """Get current conversation flow state from Redis"""
        state_data = await cache.get_json(f"flow_state:{phone}")
        if state_data:
            return FlowState(**state_data)
        return None
    
    def _get_message_text(self, message: WhatsAppMessage) -> Optional[str]:
        """Extract text from various message types"""
        if message.text:
            return message.text
        if message.button_reply:
            return message.button_reply.get("id")
        if message.list_reply:
            return message.list_reply.get("id")
        return None
    
    async def _handle_general_query(
        self,
        phone: str,
        text: str,
        user: User
    ) -> None:
        """Handle general questions using RAG"""
        # Get student profile
        result = await self.db.execute(
            select(Student).where(Student.user_id == user.id)
        )
        student = result.scalar_one_or_none()
        
        if not student:
            await self.wa.send_text(
                phone,
                "Please complete your profile first. Type 'start' to begin setup."
            )
            return
        
        # Check rate limit
        rate_key = f"questions:{user.id}:{user.subscription_tier}"
        limit = self._get_question_limit(user.subscription_tier)
        allowed, remaining = await cache.check_rate_limit(rate_key, limit)
        
        if not allowed:
            await self.wa.send_text(
                phone,
                f"🚫 You've reached your daily question limit!\n\n"
                f"Upgrade to Premium for unlimited questions.\n"
                f"Type 'upgrade' to see plans."
            )
            return
        
        # Build student context
        student_context = {
            "first_name": student.first_name,
            "education_level": student.education_level.value,
            "grade": student.grade,
            "current_subject": student.subjects[0] if student.subjects else None,
            "preferred_language": student.preferred_language
        }
        
        # Get conversation history
        history = await self._get_conversation_history(student.id)
        
        # Query RAG
        response, sources = await self.rag.query(
            question=text,
            student_context=student_context,
            conversation_history=history,
            mode="socratic"
        )
        
        # Save conversation
        await self._save_conversation(student.id, text, response)
        
        # Send response
        await self.wa.send_text(phone, response)
        
        # Show remaining questions for free users
        if user.subscription_tier.value == "free" and remaining <= 2:
            await self.wa.send_text(
                phone,
                f"💡 You have {remaining} questions left today.\n"
                f"Upgrade for unlimited learning!"
            )
    
    async def _handle_practice(
        self,
        phone: str,
        message: WhatsAppMessage,
        user: User,
        state: FlowState
    ) -> None:
        """Handle practice session responses"""
        from app.services.practice.session_manager import PracticeSessionManager
        
        session_manager = PracticeSessionManager(self.db, self.rag)
        text = self._get_message_text(message)
        
        # Get student
        result = await self.db.execute(
            select(Student).where(Student.user_id == user.id)
        )
        student = result.scalar_one_or_none()
        
        if text.lower() in ["quit", "exit", "stop", "end"]:
            # End practice session
            summary = await session_manager.end_session(
                state.data.get("session_id"),
                student.id
            )
            await self.wa.send_text(phone, summary)
            await cache.delete(f"flow_state:{phone}")
            return
        
        if text.lower() == "hint":
            # Provide hint
            hint = await session_manager.get_hint(
                state.data.get("current_question_id"),
                state.data.get("hints_used", 0)
            )
            state.data["hints_used"] = state.data.get("hints_used", 0) + 1
            await cache.set_json(f"flow_state:{phone}", state.__dict__)
            await self.wa.send_text(phone, f"💡 Hint:\n{hint}")
            return
        
        if text.lower() == "skip":
            # Skip question
            next_q = await session_manager.skip_question(
                state.data.get("session_id"),
                state.data.get("current_question_id")
            )
            if next_q:
                state.data["current_question_id"] = str(next_q.id)
                state.data["hints_used"] = 0
                await cache.set_json(f"flow_state:{phone}", state.__dict__)
                await self.wa.send_text(phone, next_q.formatted_text)
            else:
                # Session complete
                summary = await session_manager.end_session(
                    state.data.get("session_id"),
                    student.id
                )
                await self.wa.send_text(phone, summary)
                await cache.delete(f"flow_state:{phone}")
            return
        
        # Evaluate answer
        result = await session_manager.evaluate_answer(
            session_id=state.data.get("session_id"),
            question_id=state.data.get("current_question_id"),
            student_answer=text,
            student_id=student.id,
            hints_used=state.data.get("hints_used", 0)
        )
        
        await self.wa.send_text(phone, result["feedback"])
        
        # Next question or end
        if result.get("next_question"):
            state.data["current_question_id"] = str(result["next_question"].id)
            state.data["hints_used"] = 0
            await cache.set_json(f"flow_state:{phone}", state.__dict__)
            await self.wa.send_text(phone, result["next_question"].formatted_text)
        else:
            summary = await session_manager.end_session(
                state.data.get("session_id"),
                student.id
            )
            await self.wa.send_text(phone, summary)
            await cache.delete(f"flow_state:{phone}")
    
    def _get_question_limit(self, tier: str) -> int:
        """Get daily question limit based on subscription tier"""
        from app.config import get_settings
        settings = get_settings()
        
        limits = {
            "free": settings.FREE_DAILY_QUESTIONS,
            "basic": settings.BASIC_DAILY_QUESTIONS,
            "premium": settings.PREMIUM_DAILY_QUESTIONS,
            "family": settings.PREMIUM_DAILY_QUESTIONS,
        }
        return limits.get(tier, settings.FREE_DAILY_QUESTIONS)
    
    async def _get_conversation_history(
        self,
        student_id: str,
        limit: int = 10
    ) -> list:
        """Get recent conversation history"""
        result = await self.db.execute(
            select(Conversation)
            .where(Conversation.student_id == student_id)
            .order_by(Conversation.created_at.desc())
            .limit(limit)
        )
        conversations = result.scalars().all()
        
        history = []
        for conv in reversed(conversations):
            history.append({"role": conv.role, "content": conv.content})
        
        return history
    
    async def _save_conversation(
        self,
        student_id: str,
        user_message: str,
        assistant_response: str
    ) -> None:
        """Save conversation to database"""
        user_conv = Conversation(
            student_id=student_id,
            role="user",
            content=user_message
        )
        assistant_conv = Conversation(
            student_id=student_id,
            role="assistant",
            content=assistant_response
        )
        
        self.db.add(user_conv)
        self.db.add(assistant_conv)
        await self.db.commit()