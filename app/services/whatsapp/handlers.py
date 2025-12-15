# ============================================================================
# Message Handlers
# ============================================================================
"""
WhatsApp message handlers with intelligent routing and RAG integration.

Key improvements:
- Automatic mode detection based on query intent
- Metrics recording for monitoring
- Conversation caching for faster history retrieval
- Subject/topic detection for better context
- Enhanced error handling and user feedback
"""
from typing import Optional, Dict, Any, Tuple
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import logging
import uuid
from datetime import datetime

from app.services.whatsapp.client import WhatsAppClient, WhatsAppMessage
from app.services.whatsapp.flows import ConversationFlow, FlowState
from app.models.user import User, Student
from app.models.conversation import Conversation
from app.core.redis import cache

# Import from updated RAG pipeline
from app.services.rag import (
    RAGEngine,
    RAGResponse,
    QueryProcessor,
    QueryIntent,
    ResponseMode,
    ConversationCache,
    record_rag_query,
    get_metrics_collector,
)

logger = logging.getLogger(__name__)


# ============================================================================
# Command Definitions
# ============================================================================
class Commands:
    """User command definitions"""
    MENU = {"menu", "help", "start", "home"}
    PRACTICE = {"practice", "quiz", "test", "questions"}
    EXPLAIN = {"explain", "teach", "learn"}
    SUMMARY = {"summary", "summarize", "recap", "review"}
    HINT = {"hint", "clue", "help me"}
    SKIP = {"skip", "next", "pass"}
    QUIT = {"quit", "exit", "stop", "end", "done"}
    UPGRADE = {"upgrade", "premium", "subscribe", "plan", "plans"}
    PROGRESS = {"progress", "stats", "score", "performance"}
    SUBJECT = {"subject", "change subject", "switch subject"}


# ============================================================================
# Intent to Mode Mapping
# ============================================================================
INTENT_MODE_MAP: Dict[QueryIntent, ResponseMode] = {
    QueryIntent.EXPLAIN: ResponseMode.EXPLAIN,
    QueryIntent.DEFINE: ResponseMode.EXPLAIN,
    QueryIntent.CALCULATE: ResponseMode.SOCRATIC,
    QueryIntent.COMPARE: ResponseMode.EXPLAIN,
    QueryIntent.EXAMPLE: ResponseMode.EXPLAIN,
    QueryIntent.PRACTICE: ResponseMode.PRACTICE,
    QueryIntent.HELP: ResponseMode.SOCRATIC,
    QueryIntent.CLARIFY: ResponseMode.EXPLAIN,
    QueryIntent.GREETING: ResponseMode.SOCRATIC,
    QueryIntent.UNKNOWN: ResponseMode.SOCRATIC,
}


# ============================================================================
# Main Message Handler
# ============================================================================
class MessageHandler:
    """
    Handles incoming WhatsApp messages with intelligent routing.
    
    Features:
    - Automatic response mode detection based on query intent
    - Conversation history caching
    - Metrics recording for monitoring
    - Rate limiting with user feedback
    - Multi-command support
    """
    
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
        
        # Initialize query processor for intent detection
        self.query_processor = QueryProcessor()
        
        # Conversation cache for faster history retrieval
        self._conv_cache = ConversationCache(cache, max_history=10)
    
    # ==================== Main Entry Point ====================
    
    async def handle_message(self, message: WhatsAppMessage) -> None:
        """
        Main message handler - routes to appropriate handler.
        
        Flow:
        1. Mark message as read
        2. Get/create user
        3. Check flow state
        4. Route based on command or flow state
        """
        phone = message.from_number
        
        try:
            # Mark as read immediately
            await self.wa.mark_as_read(message.message_id)
            
            # Get or create user
            user = await self._get_or_create_user(phone)
            if not user:
                return  # Onboarding started
            
            # Get current flow state
            state = await self._get_flow_state(phone)
            
            # Extract message text
            text = self._get_message_text(message)
            
            if not text:
                await self.wa.send_text(
                    phone,
                    "I can only understand text messages right now. "
                    "Please type your question! 📝"
                )
                return
            
            # Check for global commands first
            command_handled = await self._handle_commands(phone, text, user, state)
            if command_handled:
                return
            
            # Route based on flow state
            if state:
                await self._route_by_state(phone, message, text, user, state)
            else:
                # General conversation - use RAG
                await self._handle_general_query(phone, text, user)
                
        except Exception as e:
            logger.exception(f"Error handling message from {phone}: {e}")
            await self.wa.send_text(
                phone,
                "Oops! Something went wrong 🙈 Please try again in a moment."
            )
            get_metrics_collector().record_error()
    
    # ==================== Command Handling ====================
    
    async def _handle_commands(
        self,
        phone: str,
        text: str,
        user: User,
        state: Optional[FlowState]
    ) -> bool:
        """
        Handle global commands. Returns True if command was handled.
        """
        text_lower = text.lower().strip()
        
        # Menu/Help
        if text_lower in Commands.MENU:
            await self.flow.show_main_menu(phone, user)
            return True
        
        # Upgrade
        if text_lower in Commands.UPGRADE:
            await self._show_upgrade_options(phone, user)
            return True
        
        # Progress
        if text_lower in Commands.PROGRESS:
            await self._show_progress(phone, user)
            return True
        
        # Subject change
        if text_lower in Commands.SUBJECT:
            await self._start_subject_selection(phone, user)
            return True
        
        # Start practice (when not in practice flow)
        if text_lower in Commands.PRACTICE and (not state or state.flow_name != "practice"):
            await self._start_practice_session(phone, user)
            return True
        
        return False
    
    # ==================== Flow Routing ====================
    
    async def _route_by_state(
        self,
        phone: str,
        message: WhatsAppMessage,
        text: str,
        user: User,
        state: FlowState
    ) -> None:
        """Route message based on current flow state"""
        
        if state.flow_name == "onboarding":
            await self.flow.handle_onboarding(phone, message, state)
        
        elif state.flow_name == "practice":
            await self._handle_practice(phone, message, user, state)
        
        elif state.flow_name == "parent_link":
            await self.flow.handle_parent_linking(phone, message, state)
        
        elif state.flow_name == "subject_selection":
            await self._handle_subject_selection(phone, text, user, state)
        
        else:
            # Unknown state, clear and handle as general query
            await cache.delete(f"flow_state:{phone}")
            await self._handle_general_query(phone, text, user)
    
    # ==================== General Query Handling ====================
    
    async def _handle_general_query(
        self,
        phone: str,
        text: str,
        user: User
    ) -> None:
        """
        Handle general questions using the RAG pipeline.
        
        Features:
        - Automatic mode detection
        - Subject/topic context
        - Metrics recording
        - Rate limiting
        """
        # Get student profile
        student = await self._get_student(user.id)
        if not student:
            await self.wa.send_text(
                phone,
                "Please complete your profile first. Type 'start' to begin setup."
            )
            return
        
        # Check rate limit
        allowed, remaining = await self._check_rate_limit(user)
        if not allowed:
            await self._send_rate_limit_message(phone)
            return
        
        # Process query to detect intent and subject
        query_context = {
            "subject": student.subjects[0] if student.subjects else None,
            "grade": student.grade,
        }
        processed = self.query_processor.process(text, query_context)
        
        # Determine response mode based on intent
        mode = self._determine_mode(processed.intent, text)
        
        # Build student context
        student_context = self._build_student_context(student, processed)
        
        # Get conversation history (from cache or DB)
        history = await self._get_conversation_history(student.id)
        
        # Generate query ID for tracking
        query_id = str(uuid.uuid4())[:8]
        
        # Query RAG with detected mode
        response = await self.rag.query_with_metadata(
            question=text,
            student_context=student_context,
            conversation_history=history,
            mode=mode.value
        )
        
        # Record metrics
        record_rag_query(
            query_id=query_id,
            query_text=text,
            response=response,
            subject=processed.subject,
            grade=student.grade
        )
        
        # Save conversation to DB and cache
        await self._save_conversation(student.id, text, response.response_text)
        
        # Send response
        await self.wa.send_text(phone, response.response_text)
        
        # Show remaining questions for free users
        if self._is_free_user(user) and remaining <= 3:
            await self._send_remaining_questions_notice(phone, remaining)
        
        # Log for debugging
        logger.info(
            f"Query processed: mode={mode.value}, intent={processed.intent.value}, "
            f"subject={processed.subject}, confidence={response.confidence_score:.2f}, "
            f"time={response.total_time_ms:.0f}ms"
        )
    
    def _determine_mode(self, intent: QueryIntent, text: str) -> ResponseMode:
        """
        Determine response mode based on intent and text patterns.
        """
        text_lower = text.lower()
        
        # Explicit mode requests in text
        if any(word in text_lower for word in ["explain", "what is", "describe", "define"]):
            return ResponseMode.EXPLAIN
        
        if any(word in text_lower for word in ["summarize", "summary", "recap"]):
            return ResponseMode.SUMMARY
        
        if any(word in text_lower for word in ["quiz", "test me", "practice"]):
            return ResponseMode.QUIZ
        
        if any(word in text_lower for word in ["hint", "clue", "help me with"]):
            return ResponseMode.HINT
        
        # Use intent mapping
        return INTENT_MODE_MAP.get(intent, ResponseMode.SOCRATIC)
    
    def _build_student_context(
        self,
        student: Student,
        processed: Any  # ProcessedQuery
    ) -> Dict[str, Any]:
        """Build comprehensive student context for RAG"""
        return {
            "first_name": student.first_name,
            "education_level": student.education_level.value,
            "grade": student.grade,
            "current_subject": processed.subject or (
                student.subjects[0] if student.subjects else None
            ),
            "topic": processed.topic,
            "preferred_language": student.preferred_language,
            "detected_intent": processed.intent.value,
            "query_keywords": processed.keywords[:5],  # Top keywords
        }
    
    # ==================== Practice Session Handling ====================
    
    async def _handle_practice(
        self,
        phone: str,
        message: WhatsAppMessage,
        user: User,
        state: FlowState
    ) -> None:
        """Handle practice session responses with improved flow"""
        from app.services.practice.session_manager import PracticeSessionManager
        
        text = self._get_message_text(message)
        text_lower = text.lower().strip()
        
        # Get student
        student = await self._get_student(user.id)
        if not student:
            return
        
        # Initialize session manager with RAG engine
        session_manager = PracticeSessionManager(self.db, self.rag)
        
        # Handle practice commands
        if text_lower in Commands.QUIT:
            await self._end_practice_session(phone, session_manager, state, student)
            return
        
        if text_lower in Commands.HINT:
            await self._provide_hint(phone, session_manager, state)
            return
        
        if text_lower in Commands.SKIP:
            await self._skip_question(phone, session_manager, state, student)
            return
        
        # Evaluate answer
        await self._evaluate_practice_answer(
            phone, text, session_manager, state, student
        )
    
    async def _end_practice_session(
        self,
        phone: str,
        session_manager,
        state: FlowState,
        student: Student
    ) -> None:
        """End practice session and show summary"""
        summary = await session_manager.end_session(
            state.data.get("session_id"),
            student.id
        )
        await self.wa.send_text(phone, summary)
        await cache.delete(f"flow_state:{phone}")
        
        # Offer next actions
        await self.wa.send_text(
            phone,
            "What would you like to do next?\n"
            "• Type 'practice' for more questions\n"
            "• Type 'menu' for main menu\n"
            "• Or ask me anything! 📚"
        )
    
    async def _provide_hint(
        self,
        phone: str,
        session_manager,
        state: FlowState
    ) -> None:
        """Provide hint for current question"""
        hints_used = state.data.get("hints_used", 0)
        max_hints = 3
        
        if hints_used >= max_hints:
            await self.wa.send_text(
                phone,
                f"You've used all {max_hints} hints for this question! 🤔\n\n"
                "Try your best answer, or type 'skip' to move on."
            )
            return
        
        hint = await session_manager.get_hint(
            state.data.get("current_question_id"),
            hints_used
        )
        
        state.data["hints_used"] = hints_used + 1
        await cache.set_json(f"flow_state:{phone}", state.__dict__)
        
        remaining_hints = max_hints - hints_used - 1
        hint_msg = f"💡 Hint {hints_used + 1}:\n{hint}"
        if remaining_hints > 0:
            hint_msg += f"\n\n({remaining_hints} hint{'s' if remaining_hints > 1 else ''} remaining)"
        
        await self.wa.send_text(phone, hint_msg)
    
    async def _skip_question(
        self,
        phone: str,
        session_manager,
        state: FlowState,
        student: Student
    ) -> None:
        """Skip current question and get next"""
        next_q = await session_manager.skip_question(
            state.data.get("session_id"),
            state.data.get("current_question_id")
        )
        
        if next_q:
            state.data["current_question_id"] = str(next_q.id)
            state.data["hints_used"] = 0
            await cache.set_json(f"flow_state:{phone}", state.__dict__)
            await self.wa.send_text(phone, "⏭️ Moving on...\n\n" + next_q.formatted_text)
        else:
            await self._end_practice_session(phone, session_manager, state, student)
    
    async def _evaluate_practice_answer(
        self,
        phone: str,
        answer: str,
        session_manager,
        state: FlowState,
        student: Student
    ) -> None:
        """Evaluate student's practice answer"""
        result = await session_manager.evaluate_answer(
            session_id=state.data.get("session_id"),
            question_id=state.data.get("current_question_id"),
            student_answer=answer,
            student_id=student.id,
            hints_used=state.data.get("hints_used", 0)
        )
        
        # Send feedback
        await self.wa.send_text(phone, result["feedback"])
        
        # Handle next question
        if result.get("next_question"):
            state.data["current_question_id"] = str(result["next_question"].id)
            state.data["hints_used"] = 0
            state.data["questions_answered"] = state.data.get("questions_answered", 0) + 1
            await cache.set_json(f"flow_state:{phone}", state.__dict__)
            
            # Small delay before next question
            await self.wa.send_text(
                phone,
                f"📝 Question {state.data['questions_answered'] + 1}:\n\n"
                f"{result['next_question'].formatted_text}"
            )
        else:
            await self._end_practice_session(phone, session_manager, state, student)
    
    async def _start_practice_session(self, phone: str, user: User) -> None:
        """Start a new practice session"""
        student = await self._get_student(user.id)
        if not student:
            await self.wa.send_text(
                phone,
                "Please complete your profile first. Type 'start' to begin."
            )
            return
        
        # Set flow state
        state = FlowState(
            flow_name="practice",
            step="topic_selection",
            data={"student_id": str(student.id)}
        )
        await cache.set_json(f"flow_state:{phone}", state.__dict__)
        
        # Ask for subject/topic
        subjects = student.subjects or ["Mathematics", "English", "Science"]
        subject_list = "\n".join(f"• {s}" for s in subjects)
        
        await self.wa.send_text(
            phone,
            f"📚 Let's practice!\n\n"
            f"Which subject would you like to practice?\n{subject_list}\n\n"
            f"Or type a specific topic (e.g., 'quadratic equations')"
        )
    
    # ==================== Helper Methods ====================
    
    async def _get_or_create_user(self, phone: str) -> Optional[User]:
        """Get existing user or start onboarding"""
        result = await self.db.execute(
            select(User).where(User.phone_number == phone)
        )
        user = result.scalar_one_or_none()
        
        if not user:
            await self.flow.start_onboarding(phone)
            return None
        
        return user
    
    async def _get_student(self, user_id: str) -> Optional[Student]:
        """Get student profile"""
        result = await self.db.execute(
            select(Student).where(Student.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
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
    
    async def _check_rate_limit(self, user: User) -> Tuple[bool, int]:
        """Check rate limit and return (allowed, remaining)"""
        rate_key = f"questions:{user.id}:{user.subscription_tier}"
        limit = self._get_question_limit(user.subscription_tier)
        return await cache.check_rate_limit(rate_key, limit)
    
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
    
    def _is_free_user(self, user: User) -> bool:
        """Check if user is on free tier"""
        return user.subscription_tier.value == "free"
    
    async def _get_conversation_history(
        self,
        student_id: str,
        limit: int = 10
    ) -> list:
        """Get recent conversation history from cache or DB"""
        # Try cache first
        cached_history = await self._conv_cache.get_history(student_id)
        if cached_history:
            return cached_history
        
        # Fall back to database
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
        """Save conversation to database and cache"""
        # Save to database
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
        
        # Update cache
        await self._conv_cache.add_message(student_id, "user", user_message)
        await self._conv_cache.add_message(student_id, "assistant", assistant_response)
    
    # ==================== User Feedback Messages ====================
    
    async def _send_rate_limit_message(self, phone: str) -> None:
        """Send rate limit exceeded message"""
        await self.wa.send_text(
            phone,
            "🚫 You've reached your daily question limit!\n\n"
            "Upgrade to Premium for unlimited questions and more features.\n\n"
            "Type 'upgrade' to see plans."
        )
    
    async def _send_remaining_questions_notice(
        self,
        phone: str,
        remaining: int
    ) -> None:
        """Send remaining questions notice for free users"""
        if remaining == 0:
            return
        
        emoji = "⚠️" if remaining == 1 else "💡"
        await self.wa.send_text(
            phone,
            f"{emoji} You have {remaining} question{'s' if remaining > 1 else ''} "
            f"left today.\n"
            f"Type 'upgrade' for unlimited learning!"
        )
    
    async def _show_upgrade_options(self, phone: str, user: User) -> None:
        """Show subscription upgrade options"""
        await self.wa.send_text(
            phone,
            "🚀 *Upgrade Your Learning*\n\n"
            "*Basic Plan* - $2/month\n"
            "• 50 questions/day\n"
            "• Practice sessions\n\n"
            "*Premium Plan* - $5/month\n"
            "• Unlimited questions\n"
            "• All subjects\n"
            "• Priority support\n"
            "• Progress reports\n\n"
            "*Family Plan* - $8/month\n"
            "• Up to 4 students\n"
            "• All Premium features\n"
            "• Parent dashboard\n\n"
            "Reply with the plan name to subscribe!"
        )
    
    async def _show_progress(self, phone: str, user: User) -> None:
        """Show user's learning progress"""
        student = await self._get_student(user.id)
        if not student:
            await self.wa.send_text(phone, "Complete your profile first! Type 'start'.")
            return
        
        # TODO: Get actual stats from database
        await self.wa.send_text(
            phone,
            f"📊 *Your Progress, {student.first_name}*\n\n"
            f"🔥 Current streak: 5 days\n"
            f"📝 Questions answered: 127\n"
            f"✅ Accuracy: 78%\n"
            f"⭐ XP earned: 2,450\n\n"
            f"Keep up the great work! 🌟"
        )
    
    async def _start_subject_selection(self, phone: str, user: User) -> None:
        """Start subject selection flow"""
        await self.wa.send_text(
            phone,
            "📚 Which subject would you like to focus on?\n\n"
            "• Mathematics\n"
            "• English\n"
            "• Physics\n"
            "• Chemistry\n"
            "• Biology\n"
            "• Geography\n"
            "• History\n\n"
            "Type the subject name to select it."
        )
        
        state = FlowState(
            flow_name="subject_selection",
            step="selecting",
            data={"user_id": str(user.id)}
        )
        await cache.set_json(f"flow_state:{phone}", state.__dict__)
    
    async def _handle_subject_selection(
        self,
        phone: str,
        text: str,
        user: User,
        state: FlowState
    ) -> None:
        """Handle subject selection"""
        subjects = [
            "mathematics", "english", "physics", "chemistry",
            "biology", "geography", "history", "commerce", "accounting"
        ]
        
        text_lower = text.lower().strip()
        
        if text_lower in subjects:
            # Update student's current subject
            student = await self._get_student(user.id)
            if student and student.subjects:
                # Move selected subject to front
                if text_lower.title() in student.subjects:
                    student.subjects.remove(text_lower.title())
                student.subjects.insert(0, text_lower.title())
                await self.db.commit()
            
            await cache.delete(f"flow_state:{phone}")
            await self.wa.send_text(
                phone,
                f"✅ Great! You're now focused on *{text_lower.title()}*.\n\n"
                f"Ask me anything about {text_lower.title()}, or type 'practice' "
                f"for some questions!"
            )
        else:
            await self.wa.send_text(
                phone,
                f"I don't recognize '{text}' as a subject. "
                f"Please choose from the list above, or type 'menu' to go back."
            )