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
- Full menu item routing for interactive buttons/lists
- Real progress stats from database
- Parent report integration
"""
from typing import Optional, Dict, Any, Tuple, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc, Integer
import logging
import uuid
import random
import string
from datetime import datetime, date, timedelta

from app.services.whatsapp.client import WhatsAppClient, WhatsAppMessage
from app.services.whatsapp.flows import ConversationFlow, FlowState
from app.models.user import User, Student, ParentStudentLink, UserRole
from app.models.conversation import Conversation
from app.models.practice import PracticeSession, QuestionAttempt
from app.models.gamification import StudentStreak, StudentAchievement, Achievement
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

# Import services for real stats
from app.services.gamification.xp_system import XPSystem
from app.services.notifications.parent_reports import ParentReportService

logger = logging.getLogger(__name__)


# ============================================================================
# Command Definitions
# ============================================================================
class Commands:
    """User command definitions"""
    GREETING = {"hi", "hello", "hey", "hie", "howzit", "good morning", "good afternoon", "good evening", "yo", "sup"}
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
    ACHIEVEMENTS = {"achievements", "badges", "trophies"}
    LEADERBOARD = {"leaderboard", "ranking", "rankings", "top"}
    PARENT_CODE = {"parent code", "parentcode", "link parent", "parent link"}
    REPORT = {"report", "reports", "my report"}

    # Menu item IDs (from interactive buttons/lists)
    MENU_ITEMS = {
        # Student menu items
        "menu_practice", "menu_ask", "menu_quiz",
        "menu_progress", "menu_compete", "menu_achievements",
        "menu_parent_code", "menu_subscription", "menu_settings",
        # Parent menu items
        "parent_daily", "parent_weekly", "parent_subjects",
        "parent_notifications", "parent_subscription",
        # Notification toggles
        "notif_enable", "notif_disable",
        # Settings items
        "setting_subject", "setting_name", "setting_grade"
    }

    # Dynamic menu items that need pattern matching
    DYNAMIC_PREFIXES = {"quiz_"}


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
            user, is_first_message_today = await self._get_or_create_user(phone)
            if not user:
                return  # Onboarding started

            # Send welcome back message for returning users (first message of the day)
            if is_first_message_today and user.role == UserRole.STUDENT:
                student = await self._get_student(user.id)
                if student:
                    await self._send_welcome_back(phone, user, student)
            
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
        Handle global commands and menu item callbacks. Returns True if command was handled.
        """
        text_lower = text.lower().strip()

        # ===== Menu Item Callbacks (from interactive buttons/lists) =====
        if text_lower in Commands.MENU_ITEMS:
            return await self._handle_menu_item(phone, text_lower, user)

        # Check for dynamic menu items (like quiz_mathematics)
        for prefix in Commands.DYNAMIC_PREFIXES:
            if text_lower.startswith(prefix):
                return await self._handle_menu_item(phone, text_lower, user)

        # ===== Text Commands =====

        # Greeting - respond directly without RAG
        if text_lower in Commands.GREETING:
            name = user.first_name or "there"
            await self.wa.send_text(
                phone,
                f"Hey {name}! 👋 How can I help you today?\n\n"
                "Type *menu* to see what I can do, or just ask me a question!"
            )
            return True

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

        # Achievements
        if text_lower in Commands.ACHIEVEMENTS:
            await self._show_achievements(phone, user)
            return True

        # Leaderboard
        if text_lower in Commands.LEADERBOARD:
            await self._show_leaderboard(phone, user)
            return True

        # Parent code generation
        if text_lower in Commands.PARENT_CODE:
            await self._generate_parent_code(phone, user)
            return True

        # Report (for parents)
        if text_lower in Commands.REPORT:
            await self._show_report(phone, user)
            return True

        # Start practice (when not in practice flow)
        if text_lower in Commands.PRACTICE and (not state or state.flow_name != "practice"):
            await self._start_practice_session(phone, user)
            return True

        return False

    async def _handle_menu_item(self, phone: str, menu_id: str, user: User) -> bool:
        """
        Handle menu item callbacks from interactive buttons/lists.
        Routes menu_* and parent_* IDs to appropriate handlers.
        """
        # Student menu items
        if menu_id == "menu_practice":
            await self._start_practice_session(phone, user)
            return True

        elif menu_id == "menu_ask":
            await self.wa.send_text(
                phone,
                "❓ *Ask me anything!*\n\n"
                "Just type your question and I'll help you understand.\n\n"
                "Examples:\n"
                "• Explain photosynthesis\n"
                "• How do I solve quadratic equations?\n"
                "• What caused World War 1?\n"
                "• Calculate the area of a circle with radius 5cm"
            )
            return True

        elif menu_id == "menu_quiz":
            await self._start_quick_quiz(phone, user)
            return True

        elif menu_id == "menu_progress":
            await self._show_progress(phone, user)
            return True

        elif menu_id == "menu_compete":
            await self._show_competitions(phone, user)
            return True

        elif menu_id == "menu_achievements":
            await self._show_achievements(phone, user)
            return True

        elif menu_id == "menu_parent_code":
            await self._generate_parent_code(phone, user)
            return True

        elif menu_id == "menu_subscription":
            await self._show_upgrade_options(phone, user)
            return True

        elif menu_id == "menu_settings":
            await self._show_settings(phone, user)
            return True

        # Parent menu items
        elif menu_id == "parent_daily":
            await self._show_parent_daily_report(phone, user)
            return True

        elif menu_id == "parent_weekly":
            await self._show_parent_weekly_report(phone, user)
            return True

        elif menu_id == "parent_subjects":
            await self._show_parent_subject_breakdown(phone, user)
            return True

        elif menu_id == "parent_notifications":
            await self._show_parent_notification_settings(phone, user)
            return True

        elif menu_id == "parent_subscription":
            await self._show_upgrade_options(phone, user)
            return True

        # Notification toggles
        elif menu_id == "notif_enable":
            await self._toggle_notifications(phone, user, enable=True)
            return True

        elif menu_id == "notif_disable":
            await self._toggle_notifications(phone, user, enable=False)
            return True

        # Settings items
        elif menu_id == "setting_subject":
            await self._start_subject_selection(phone, user)
            return True

        elif menu_id == "setting_name":
            await self._start_name_change(phone, user)
            return True

        elif menu_id == "setting_grade":
            await self._start_grade_change(phone, user)
            return True

        # Dynamic quiz subject selection
        elif menu_id.startswith("quiz_"):
            subject = menu_id.replace("quiz_", "").title()
            await self._start_quiz_with_subject(phone, user, subject)
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

        elif state.flow_name == "settings":
            await self._handle_settings_flow(phone, text, user, state)

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
    
    async def _get_or_create_user(self, phone: str) -> Tuple[Optional[User], bool]:
        """
        Get existing user or start onboarding.
        Returns (user, is_returning_today) tuple.
        is_returning_today is True if this is the first message of the day.
        """
        result = await self.db.execute(
            select(User).where(User.phone_number == phone)
        )
        user = result.scalar_one_or_none()

        if not user:
            await self.flow.start_onboarding(phone)
            return None, False

        # Check if this is the first message today (for welcome back)
        welcome_key = f"welcomed_today:{phone}"
        already_welcomed = await cache.get(welcome_key)

        if not already_welcomed:
            # Mark as welcomed for today (expires at midnight)
            await cache.set(welcome_key, "1", ttl=self._seconds_until_midnight())
            return user, True  # First message today

        return user, False

    def _seconds_until_midnight(self) -> int:
        """Calculate seconds until midnight for cache TTL"""
        now = datetime.now()
        midnight = datetime(now.year, now.month, now.day) + timedelta(days=1)
        return int((midnight - now).total_seconds())
    
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
        """Show user's learning progress with real data from database"""
        student = await self._get_student(user.id)
        if not student:
            await self.wa.send_text(phone, "Complete your profile first! Type 'start'.")
            return

        # Get real stats from XP system
        xp_system = XPSystem(self.db)
        stats = await xp_system.get_student_stats(student.id)

        # Get practice stats
        practice_stats = await self._get_practice_stats(student.id)

        # Build progress message with real data
        level_info = xp_system.get_level_info(student.total_xp or 0)

        # Progress bar for level
        progress_pct = level_info.get("progress_percent", 0)
        filled = int(progress_pct / 10)
        progress_bar = "█" * filled + "░" * (10 - filled)

        message = f"""📊 *Your Progress, {student.first_name}!*

━━━━━━━━━━━━━━━━━━━━━
🎮 *Level & XP*
━━━━━━━━━━━━━━━━━━━━━
⭐ Level {level_info['level']}: {level_info['title']}
💎 Total XP: {student.total_xp or 0:,}
📈 Progress: [{progress_bar}] {progress_pct:.0f}%
   {level_info['xp_in_level']}/{level_info['xp_for_next_level']} XP to next level

━━━━━━━━━━━━━━━━━━━━━
🔥 *Streaks*
━━━━━━━━━━━━━━━━━━━━━
🔥 Current streak: {stats.get('current_streak', 0)} days
🏆 Longest streak: {stats.get('longest_streak', 0)} days
📅 Total active days: {stats.get('total_active_days', 0)}

━━━━━━━━━━━━━━━━━━━━━
📝 *Practice Stats*
━━━━━━━━━━━━━━━━━━━━━
📚 Questions answered: {practice_stats['total_questions']:,}
✅ Correct answers: {practice_stats['correct_answers']:,}
📈 Accuracy: {practice_stats['accuracy']:.1f}%
🎯 Sessions completed: {practice_stats['sessions_completed']}

━━━━━━━━━━━━━━━━━━━━━
{self._get_encouragement_message(practice_stats['accuracy'], stats.get('current_streak', 0))}
"""
        await self.wa.send_text(phone, message)

    async def _get_practice_stats(self, student_id) -> Dict[str, Any]:
        """Get comprehensive practice statistics for a student"""
        # Total questions attempted
        result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .where(QuestionAttempt.student_id == student_id)
            .where(QuestionAttempt.student_answer != "[SKIPPED]")
        )
        total_questions = result.scalar() or 0

        # Correct answers
        result = await self.db.execute(
            select(func.count(QuestionAttempt.id))
            .where(QuestionAttempt.student_id == student_id)
            .where(QuestionAttempt.is_correct == True)
        )
        correct_answers = result.scalar() or 0

        # Sessions completed
        result = await self.db.execute(
            select(func.count(PracticeSession.id))
            .where(PracticeSession.student_id == student_id)
            .where(PracticeSession.status == "completed")
        )
        sessions_completed = result.scalar() or 0

        accuracy = (correct_answers / total_questions * 100) if total_questions > 0 else 0

        return {
            "total_questions": total_questions,
            "correct_answers": correct_answers,
            "accuracy": accuracy,
            "sessions_completed": sessions_completed
        }

    def _get_encouragement_message(self, accuracy: float, streak: int) -> str:
        """Generate personalized encouragement message"""
        if streak >= 30:
            return "🏆 *AMAZING!* 30+ day streak! You're a true champion! 🌟"
        elif streak >= 14:
            return "🔥 *Incredible!* Two weeks strong! Keep the momentum! 💪"
        elif streak >= 7:
            return "⭐ *Fantastic!* A whole week of learning! You're on fire! 🔥"
        elif accuracy >= 90:
            return "🌟 *Outstanding accuracy!* You're mastering this! 🎯"
        elif accuracy >= 75:
            return "👏 *Great work!* Keep practicing to reach excellence! 📚"
        elif accuracy >= 50:
            return "💪 *Good progress!* Every question makes you stronger! 📈"
        else:
            return "🚀 *Keep going!* Practice makes perfect! You've got this! 💪"
    
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

    # ==================== Achievement & Leaderboard Handlers ====================

    async def _show_achievements(self, phone: str, user: User) -> None:
        """Show student's earned achievements"""
        student = await self._get_student(user.id)
        if not student:
            await self.wa.send_text(phone, "Complete your profile first! Type 'start'.")
            return

        # Get earned achievements
        result = await self.db.execute(
            select(Achievement, StudentAchievement.earned_at)
            .join(StudentAchievement, Achievement.id == StudentAchievement.achievement_id)
            .where(StudentAchievement.student_id == student.id)
            .order_by(StudentAchievement.earned_at.desc())
            .limit(10)
        )
        achievements = result.all()

        if not achievements:
            await self.wa.send_text(
                phone,
                "🎖️ *Your Achievements*\n\n"
                "You haven't earned any badges yet!\n\n"
                "Keep practicing to unlock achievements:\n"
                "• 🔥 First Flame - 3 day streak\n"
                "• 📚 Bookworm - Answer 50 questions\n"
                "• 🎯 Sharp Shooter - 90% accuracy in a session\n"
                "• 🏆 Champion - Win a competition\n\n"
                "Type *practice* to start earning! 💪"
            )
            return

        # Build achievements message
        achievements_text = ""
        for achievement, earned_at in achievements:
            icon = achievement.icon or "🏅"
            earned_date = earned_at.strftime("%b %d")
            achievements_text += f"{icon} *{achievement.name}*\n"
            achievements_text += f"   {achievement.description}\n"
            achievements_text += f"   Earned: {earned_date}\n\n"

        # Count total achievements
        total_result = await self.db.execute(
            select(func.count(StudentAchievement.id))
            .where(StudentAchievement.student_id == student.id)
        )
        total_earned = total_result.scalar() or 0

        # Get total possible achievements
        total_possible_result = await self.db.execute(select(func.count(Achievement.id)))
        total_possible = total_possible_result.scalar() or 0

        message = f"""🎖️ *Your Achievements*

You've earned *{total_earned}/{total_possible}* badges! 🌟

━━━━━━━━━━━━━━━━━━━━━
{achievements_text}
━━━━━━━━━━━━━━━━━━━━━
Keep practicing to unlock more! 💪
"""
        await self.wa.send_text(phone, message)

    async def _show_leaderboard(self, phone: str, user: User) -> None:
        """Show leaderboard rankings"""
        student = await self._get_student(user.id)
        if not student:
            await self.wa.send_text(phone, "Complete your profile first! Type 'start'.")
            return

        # Get top 10 students by XP
        result = await self.db.execute(
            select(Student)
            .where(Student.total_xp > 0)
            .order_by(desc(Student.total_xp))
            .limit(10)
        )
        top_students = result.scalars().all()

        # Find current student's rank
        rank_result = await self.db.execute(
            select(func.count(Student.id))
            .where(Student.total_xp > (student.total_xp or 0))
        )
        user_rank = (rank_result.scalar() or 0) + 1

        # Build leaderboard
        leaderboard_text = ""
        medals = ["🥇", "🥈", "🥉"]

        for i, s in enumerate(top_students):
            rank = i + 1
            medal = medals[i] if i < 3 else f"{rank}."
            name = s.first_name[:12]  # Truncate long names
            is_you = " ← You!" if s.id == student.id else ""

            if rank <= 3:
                leaderboard_text += f"{medal} *{name}* - {s.total_xp or 0:,} XP{is_you}\n"
            else:
                leaderboard_text += f"{medal} {name} - {s.total_xp or 0:,} XP{is_you}\n"

        # Add user's position if not in top 10
        user_in_top = any(s.id == student.id for s in top_students)

        message = f"""🏆 *Leaderboard - Top Students*

━━━━━━━━━━━━━━━━━━━━━
{leaderboard_text}
━━━━━━━━━━━━━━━━━━━━━
"""
        if not user_in_top:
            message += f"\n📍 *Your Rank:* #{user_rank} with {student.total_xp or 0:,} XP\n"
            message += f"   Keep practicing to climb higher! 📈\n"

        message += "\n💡 Earn XP by answering questions correctly!"

        await self.wa.send_text(phone, message)

    # ==================== Parent Code Generation ====================

    async def _generate_parent_code(self, phone: str, user: User) -> None:
        """Generate a 6-digit code for parent linking"""
        if user.role != UserRole.STUDENT:
            await self.wa.send_text(
                phone,
                "This feature is only for students.\n\n"
                "If you're a parent, ask your child for their parent code!"
            )
            return

        student = await self._get_student(user.id)
        if not student:
            await self.wa.send_text(phone, "Complete your profile first! Type 'start'.")
            return

        # Check for existing unexpired code
        result = await self.db.execute(
            select(ParentStudentLink)
            .where(ParentStudentLink.student_id == student.id)
            .where(ParentStudentLink.verified == False)
            .where(ParentStudentLink.created_at > datetime.utcnow() - timedelta(hours=24))
        )
        existing_link = result.scalar_one_or_none()

        if existing_link:
            code = existing_link.verification_code
        else:
            # Generate new 6-digit code
            code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=6))

            # Create new link record
            new_link = ParentStudentLink(
                student_id=student.id,
                verification_code=code,
                verified=False
            )
            self.db.add(new_link)
            await self.db.commit()

        await self.wa.send_text(
            phone,
            f"👨‍👩‍👧 *Parent Linking Code*\n\n"
            f"Share this code with your parent:\n\n"
            f"🔑 *{code}*\n\n"
            f"Instructions for your parent:\n"
            f"1. Save this number to contacts\n"
            f"2. Send a message saying 'Hi'\n"
            f"3. Select 'I'm a Parent'\n"
            f"4. Enter the code above\n\n"
            f"⏰ This code expires in 24 hours.\n"
            f"🔒 Only share with your parent/guardian!"
        )

    # ==================== Parent Report Handlers ====================

    async def _show_report(self, phone: str, user: User) -> None:
        """Show report - routes to appropriate report based on user role"""
        if user.role == UserRole.PARENT:
            await self._show_parent_weekly_report(phone, user)
        else:
            await self._show_progress(phone, user)

    async def _get_linked_student(self, parent_user_id) -> Optional[Student]:
        """Get the student linked to a parent"""
        result = await self.db.execute(
            select(Student)
            .join(ParentStudentLink, ParentStudentLink.student_id == Student.id)
            .where(ParentStudentLink.parent_user_id == parent_user_id)
            .where(ParentStudentLink.verified == True)
        )
        return result.scalar_one_or_none()

    async def _show_parent_daily_report(self, phone: str, user: User) -> None:
        """Show parent's daily report for their child"""
        if user.role != UserRole.PARENT:
            await self.wa.send_text(phone, "This feature is only for parents.")
            return

        student = await self._get_linked_student(user.id)
        if not student:
            await self.wa.send_text(
                phone,
                "You haven't linked to a student account yet.\n\n"
                "Ask your child for their 6-digit parent code, "
                "then send it here to link accounts."
            )
            return

        # Generate daily report
        report_service = ParentReportService(self.db)
        report = await report_service.generate_report(student.id, "daily")

        if "error" in report:
            await self.wa.send_text(phone, f"Sorry, couldn't generate report: {report['error']}")
            return

        summary = report.get("summary", {})

        message = f"""📊 *Daily Report for {student.first_name}*

📅 {report.get('date', 'Today')}

━━━━━━━━━━━━━━━━━━━━━
📈 *Today's Activity*
━━━━━━━━━━━━━━━━━━━━━
📝 Questions attempted: {summary.get('questions_attempted', 0)}
✅ Correct answers: {summary.get('correct_answers', 0)}
📊 Accuracy: {summary.get('accuracy_percentage', 0):.1f}%
⏱️ Time spent: {summary.get('time_spent_minutes', 0)} minutes
🔥 Current streak: {summary.get('current_streak', 0)} days

━━━━━━━━━━━━━━━━━━━━━
{report.get('status', '')}

{report.get('message', '')}
"""
        await self.wa.send_text(phone, message)

    async def _show_parent_weekly_report(self, phone: str, user: User) -> None:
        """Show parent's weekly report for their child"""
        if user.role != UserRole.PARENT:
            await self.wa.send_text(phone, "This feature is only for parents.")
            return

        student = await self._get_linked_student(user.id)
        if not student:
            await self.wa.send_text(
                phone,
                "You haven't linked to a student account yet.\n\n"
                "Ask your child for their 6-digit parent code, "
                "then send it here to link accounts."
            )
            return

        # Generate weekly report
        report_service = ParentReportService(self.db)
        report = await report_service.generate_report(student.id, "weekly")

        if "error" in report:
            await self.wa.send_text(phone, f"Sorry, couldn't generate report: {report['error']}")
            return

        summary = report.get("summary", {})
        strongest = report.get("strongest_area", {})
        weakest = report.get("needs_attention", {})
        comparison = report.get("comparison", {})
        recommendations = report.get("recommendations", [])

        # Build recommendations text
        rec_text = ""
        for i, rec in enumerate(recommendations[:3], 1):
            rec_text += f"{i}. {rec}\n"

        if not rec_text:
            rec_text = "Keep up the great work! 🌟"

        # Calculate trend emoji
        change = comparison.get("change_percentage", 0)
        trend_emoji = "📈" if change > 0 else "📉" if change < 0 else "➡️"

        message = f"""📊 *Weekly Report for {student.first_name}*

📅 {report.get('week_start', '')} - {report.get('week_end', '')}

━━━━━━━━━━━━━━━━━━━━━
📈 *Summary*
━━━━━━━━━━━━━━━━━━━━━
📝 Total questions: {summary.get('total_questions', 0)}
✅ Correct: {summary.get('correct_answers', 0)}
📊 Accuracy: {summary.get('accuracy_percentage', 0):.1f}%
📅 Active days: {summary.get('active_days', 0)}/7
🔥 Current streak: {summary.get('current_streak', 0)} days

━━━━━━━━━━━━━━━━━━━━━
💪 *Strongest Area*
━━━━━━━━━━━━━━━━━━━━━
{strongest.get('topic', 'N/A')} ({strongest.get('mastery', 0):.0f}% mastery)

━━━━━━━━━━━━━━━━━━━━━
📚 *Needs Practice*
━━━━━━━━━━━━━━━━━━━━━
{weakest.get('topic', 'N/A')} ({weakest.get('mastery', 0):.0f}% mastery)

━━━━━━━━━━━━━━━━━━━━━
{trend_emoji} *vs Last Week*
━━━━━━━━━━━━━━━━━━━━━
{comparison.get('previous_week_questions', 0)} → {comparison.get('current_week_questions', 0)} questions
Change: {change:+.1f}%

━━━━━━━━━━━━━━━━━━━━━
💡 *Recommendations*
━━━━━━━━━━━━━━━━━━━━━
{rec_text}
"""
        await self.wa.send_text(phone, message)

    async def _show_parent_subject_breakdown(self, phone: str, user: User) -> None:
        """Show subject-wise performance breakdown for parent"""
        if user.role != UserRole.PARENT:
            await self.wa.send_text(phone, "This feature is only for parents.")
            return

        student = await self._get_linked_student(user.id)
        if not student:
            await self.wa.send_text(
                phone,
                "You haven't linked to a student account yet.\n\n"
                "Ask your child for their 6-digit parent code."
            )
            return

        # Get subject-wise stats from question attempts
        from app.models.curriculum import Question, Subject

        # Get attempts grouped by subject
        result = await self.db.execute(
            select(
                Subject.name,
                func.count(QuestionAttempt.id).label('total'),
                func.sum(QuestionAttempt.is_correct.cast(Integer)).label('correct')
            )
            .select_from(QuestionAttempt)
            .join(Question, QuestionAttempt.question_id == Question.id)
            .join(Subject, Question.subject_id == Subject.id)
            .where(QuestionAttempt.student_id == student.id)
            .group_by(Subject.name)
            .order_by(desc('total'))
        )
        subject_stats = result.all()

        if not subject_stats:
            await self.wa.send_text(
                phone,
                f"📚 *Subject Breakdown for {student.first_name}*\n\n"
                f"No practice data available yet.\n\n"
                f"Encourage your child to start practicing! 📖"
            )
            return

        # Build subject breakdown
        breakdown_text = ""
        for subject_name, total, correct in subject_stats:
            correct = correct or 0
            accuracy = (correct / total * 100) if total > 0 else 0

            # Performance indicator
            if accuracy >= 80:
                indicator = "🟢"
            elif accuracy >= 60:
                indicator = "🟡"
            else:
                indicator = "🔴"

            breakdown_text += f"{indicator} *{subject_name}*\n"
            breakdown_text += f"   Questions: {total} | Correct: {correct} | Accuracy: {accuracy:.0f}%\n\n"

        message = f"""📚 *Subject Breakdown for {student.first_name}*

━━━━━━━━━━━━━━━━━━━━━
{breakdown_text}
━━━━━━━━━━━━━━━━━━━━━
Legend:
🟢 Strong (80%+)
🟡 Developing (60-79%)
🔴 Needs attention (<60%)
"""
        await self.wa.send_text(phone, message)

    async def _show_parent_notification_settings(self, phone: str, user: User) -> None:
        """Show and manage parent notification settings"""
        if user.role != UserRole.PARENT:
            await self.wa.send_text(phone, "This feature is only for parents.")
            return

        # Get current notification settings from link
        result = await self.db.execute(
            select(ParentStudentLink)
            .where(ParentStudentLink.parent_user_id == user.id)
            .where(ParentStudentLink.verified == True)
        )
        link = result.scalar_one_or_none()

        if not link:
            await self.wa.send_text(
                phone,
                "You haven't linked to a student account yet."
            )
            return

        notifications_enabled = link.notifications_enabled if hasattr(link, 'notifications_enabled') else True

        status = "✅ ON" if notifications_enabled else "❌ OFF"

        await self.wa.send_buttons(
            to=phone,
            header="🔔 Notification Settings",
            body=f"Current status: {status}\n\n"
                 f"When enabled, you'll receive:\n"
                 f"• 📊 Weekly progress reports\n"
                 f"• 🏆 Achievement notifications\n"
                 f"• ⚠️ Streak warnings\n"
                 f"• 📅 Activity reminders",
            buttons=[
                {"id": "notif_enable", "title": "✅ Enable"},
                {"id": "notif_disable", "title": "❌ Disable"}
            ]
        )

    # ==================== Additional Feature Handlers ====================

    async def _start_quick_quiz(self, phone: str, user: User) -> None:
        """Start a quick 5-question quiz"""
        student = await self._get_student(user.id)
        if not student:
            await self.wa.send_text(phone, "Complete your profile first! Type 'start'.")
            return

        # Set up quick quiz flow state
        state = FlowState(
            flow_name="practice",
            step="topic_selection",
            data={
                "student_id": str(student.id),
                "quiz_type": "quick",
                "num_questions": 5
            }
        )
        await cache.set_json(f"flow_state:{phone}", state.__dict__)

        subjects = student.subjects or ["Mathematics", "English", "Science"]

        await self.wa.send_list(
            to=phone,
            header="⚡ Quick Quiz",
            body="Choose a subject for your 5-question quiz!\n\n"
                 "Answer quickly for bonus XP! ⏱️",
            button_text="Select Subject",
            sections=[{
                "title": "Subjects",
                "rows": [
                    {"id": f"quiz_{s.lower()}", "title": s, "description": f"5 quick questions on {s}"}
                    for s in subjects[:10]  # WhatsApp limit
                ]
            }]
        )

    async def _show_competitions(self, phone: str, user: User) -> None:
        """Show available and upcoming competitions"""
        student = await self._get_student(user.id)
        if not student:
            await self.wa.send_text(phone, "Complete your profile first! Type 'start'.")
            return

        # Check for active competitions
        # For now, show a coming soon message with engaging content
        await self.wa.send_text(
            phone,
            "🏆 *Competitions*\n\n"
            "━━━━━━━━━━━━━━━━━━━━━\n"
            "🔜 *Coming Soon!*\n"
            "━━━━━━━━━━━━━━━━━━━━━\n\n"
            "Weekly competitions are being prepared!\n\n"
            "*What to expect:*\n"
            "• 📊 Subject-based challenges\n"
            "• ⏱️ Timed quiz battles\n"
            "• 🏅 Leaderboards and prizes\n"
            "• 🎁 XP bonuses for winners\n\n"
            "*Prepare by:*\n"
            "1. Practice daily to improve\n"
            "2. Build your streak 🔥\n"
            "3. Check back soon!\n\n"
            "Type *leaderboard* to see current rankings!"
        )

    async def _show_settings(self, phone: str, user: User) -> None:
        """Show user settings and options"""
        student = await self._get_student(user.id)
        if not student:
            await self.wa.send_text(phone, "Complete your profile first! Type 'start'.")
            return

        subjects_text = ", ".join(student.subjects[:3]) if student.subjects else "Not set"
        if student.subjects and len(student.subjects) > 3:
            subjects_text += f" +{len(student.subjects) - 3} more"

        await self.wa.send_list(
            to=phone,
            header="⚙️ Settings",
            body=f"*Current Profile:*\n"
                 f"👤 Name: {student.first_name}\n"
                 f"📚 Level: {student.education_level.value.replace('_', ' ').title()}\n"
                 f"📖 Grade: {student.grade}\n"
                 f"📝 Subjects: {subjects_text}\n"
                 f"🏫 School: {student.school_name or 'Not set'}\n\n"
                 f"What would you like to update?",
            button_text="Change Setting",
            sections=[{
                "title": "Profile Settings",
                "rows": [
                    {"id": "setting_subject", "title": "📚 Change Subject", "description": "Switch your primary subject"},
                    {"id": "setting_name", "title": "👤 Update Name", "description": "Change your display name"},
                    {"id": "setting_grade", "title": "📖 Change Grade", "description": "Update your grade/form"},
                ]
            }]
        )

    # ==================== Welcome Back Handler ====================

    async def _send_welcome_back(self, phone: str, user: User, student: Student) -> None:
        """Send personalized welcome back message for returning users"""
        xp_system = XPSystem(self.db)
        stats = await xp_system.get_student_stats(student.id)
        level_info = xp_system.get_level_info(student.total_xp or 0)

        # Check last activity
        streak_result = await self.db.execute(
            select(StudentStreak).where(StudentStreak.student_id == student.id)
        )
        streak = streak_result.scalar_one_or_none()

        streak_days = streak.current_streak if streak else 0
        streak_emoji = "🔥" if streak_days > 0 else "💪"

        # Personalized greeting based on time of day
        hour = datetime.now().hour
        if hour < 12:
            greeting = "Good morning"
        elif hour < 17:
            greeting = "Good afternoon"
        else:
            greeting = "Good evening"

        message = f"""👋 *{greeting}, {student.first_name}!*

{streak_emoji} Streak: {streak_days} days
⭐ Level {level_info['level']}: {level_info['title']}
💎 {student.total_xp or 0:,} XP

Ready to learn something new? 📚

Type *practice* to start a session, or ask me anything!
"""
        await self.wa.send_text(phone, message)

    # ==================== Notification & Settings Handlers ====================

    async def _toggle_notifications(self, phone: str, user: User, enable: bool) -> None:
        """Toggle notification settings for parent"""
        if user.role != UserRole.PARENT:
            await self.wa.send_text(phone, "This feature is only for parents.")
            return

        # Update notification setting in link
        result = await self.db.execute(
            select(ParentStudentLink)
            .where(ParentStudentLink.parent_user_id == user.id)
            .where(ParentStudentLink.verified == True)
        )
        link = result.scalar_one_or_none()

        if not link:
            await self.wa.send_text(phone, "You haven't linked to a student account yet.")
            return

        # Update if the column exists
        if hasattr(link, 'notifications_enabled'):
            link.notifications_enabled = enable
            await self.db.commit()

        status = "enabled ✅" if enable else "disabled ❌"
        await self.wa.send_text(
            phone,
            f"🔔 Notifications have been *{status}*\n\n"
            f"{'You will now receive progress reports and updates.' if enable else 'You will no longer receive automatic notifications.'}\n\n"
            f"Type *menu* to go back to the main menu."
        )

    async def _start_name_change(self, phone: str, user: User) -> None:
        """Start the name change flow"""
        student = await self._get_student(user.id)
        if not student:
            await self.wa.send_text(phone, "Complete your profile first! Type 'start'.")
            return

        # Set flow state for name change
        state = FlowState(
            flow_name="settings",
            step="change_name",
            data={"user_id": str(user.id), "student_id": str(student.id)}
        )
        await cache.set_json(f"flow_state:{phone}", state.__dict__)

        await self.wa.send_text(
            phone,
            f"👤 *Change Name*\n\n"
            f"Current name: *{student.first_name}*\n\n"
            f"Please type your new name:\n\n"
            f"(Type 'cancel' to go back)"
        )

    async def _start_grade_change(self, phone: str, user: User) -> None:
        """Start the grade change flow"""
        student = await self._get_student(user.id)
        if not student:
            await self.wa.send_text(phone, "Complete your profile first! Type 'start'.")
            return

        # Set flow state for grade change
        state = FlowState(
            flow_name="settings",
            step="change_grade",
            data={"user_id": str(user.id), "student_id": str(student.id)}
        )
        await cache.set_json(f"flow_state:{phone}", state.__dict__)

        # Show grade options based on education level
        level = student.education_level.value
        grades = {
            "primary": ["Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7"],
            "secondary": ["Form 1", "Form 2", "Form 3", "Form 4"],
            "a_level": ["Lower 6", "Upper 6"]
        }

        grade_list = grades.get(level, grades["secondary"])
        grade_options = "\n".join(f"• {g}" for g in grade_list)

        await self.wa.send_text(
            phone,
            f"📖 *Change Grade*\n\n"
            f"Current: *{student.grade}*\n"
            f"Level: *{level.replace('_', ' ').title()}*\n\n"
            f"Select your new grade:\n{grade_options}\n\n"
            f"(Type 'cancel' to go back)"
        )

    async def _start_quiz_with_subject(self, phone: str, user: User, subject: str) -> None:
        """Start a quick quiz with a specific subject"""
        student = await self._get_student(user.id)
        if not student:
            await self.wa.send_text(phone, "Complete your profile first! Type 'start'.")
            return

        # Import practice session manager
        from app.services.practice.session_manager import PracticeSessionManager

        # Get subject ID from database
        from app.models.curriculum import Subject as SubjectModel
        result = await self.db.execute(
            select(SubjectModel).where(SubjectModel.name.ilike(f"%{subject}%"))
        )
        subject_record = result.scalar_one_or_none()

        # Initialize session manager with RAG engine
        session_manager = PracticeSessionManager(self.db, self.rag)

        try:
            # Start the session
            session, first_question = await session_manager.start_session(
                student_id=student.id,
                subject_id=subject_record.id if subject_record else None,
                topic_name=subject,
                session_type="quick_quiz",
                num_questions=5
            )

            # Set up practice flow state
            state = FlowState(
                flow_name="practice",
                step="answering",
                data={
                    "student_id": str(student.id),
                    "session_id": str(session.id),
                    "current_question_id": str(first_question.id),
                    "hints_used": 0,
                    "questions_answered": 0,
                    "quiz_type": "quick"
                }
            )
            await cache.set_json(f"flow_state:{phone}", state.__dict__)

            await self.wa.send_text(
                phone,
                f"⚡ *Quick Quiz: {subject}*\n\n"
                f"📝 5 questions | ⏱️ Answer quickly for bonus XP!\n\n"
                f"Let's go! 🚀\n\n"
                f"━━━━━━━━━━━━━━━━━━━━━\n\n"
                f"{first_question.formatted_text}"
            )

        except Exception as e:
            logger.error(f"Error starting quiz: {e}")
            await self.wa.send_text(
                phone,
                f"Sorry, I couldn't start a quiz for {subject} right now.\n\n"
                f"Try typing 'practice' to start a regular practice session instead!"
            )

    # ==================== Settings Flow Handler ====================

    async def _handle_settings_flow(
        self,
        phone: str,
        text: str,
        user: User,
        state: FlowState
    ) -> None:
        """Handle settings flow steps"""
        step = state.step
        text_lower = text.lower().strip()

        # Allow cancellation
        if text_lower == "cancel":
            await cache.delete(f"flow_state:{phone}")
            await self.wa.send_text(phone, "Cancelled. Type *menu* to see options.")
            return

        if step == "change_name":
            await self._process_name_change(phone, text, user, state)
        elif step == "change_grade":
            await self._process_grade_change(phone, text, user, state)

    async def _process_name_change(
        self,
        phone: str,
        text: str,
        user: User,
        state: FlowState
    ) -> None:
        """Process name change input"""
        new_name = text.strip().title()

        # Validate name
        if len(new_name) < 2 or len(new_name) > 50:
            await self.wa.send_text(
                phone,
                "Please enter a valid name (2-50 characters).\n"
                "Type 'cancel' to go back."
            )
            return

        # Update student name
        student = await self._get_student(user.id)
        if student:
            old_name = student.first_name
            student.first_name = new_name
            await self.db.commit()

            await cache.delete(f"flow_state:{phone}")
            await self.wa.send_text(
                phone,
                f"✅ *Name Updated!*\n\n"
                f"Changed from *{old_name}* to *{new_name}*\n\n"
                f"Type *menu* to continue."
            )

    async def _process_grade_change(
        self,
        phone: str,
        text: str,
        user: User,
        state: FlowState
    ) -> None:
        """Process grade change input"""
        new_grade = text.strip()

        # Valid grades
        valid_grades = {
            "grade 1", "grade 2", "grade 3", "grade 4", "grade 5", "grade 6", "grade 7",
            "form 1", "form 2", "form 3", "form 4",
            "lower 6", "upper 6"
        }

        if new_grade.lower() not in valid_grades:
            await self.wa.send_text(
                phone,
                f"Invalid grade. Please select from the list.\n"
                f"Type 'cancel' to go back."
            )
            return

        # Update student grade
        student = await self._get_student(user.id)
        if student:
            old_grade = student.grade
            student.grade = new_grade.title()
            await self.db.commit()

            await cache.delete(f"flow_state:{phone}")
            await self.wa.send_text(
                phone,
                f"✅ *Grade Updated!*\n\n"
                f"Changed from *{old_grade}* to *{new_grade.title()}*\n\n"
                f"Your questions will now match your new level! 📚\n\n"
                f"Type *menu* to continue."
            )