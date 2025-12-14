# ============================================================================
# Conversation Flows
# ============================================================================
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
import random
import string

from app.services.whatsapp.client import WhatsAppClient, WhatsAppMessage
from app.models.user import EducationLevel, ParentStudentLink, Student, SubscriptionTier, User, UserRole
from app.core.redis import cache

@dataclass
class FlowState:
    """Represents current conversation flow state"""
    flow_name: str
    step: str
    data: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return {
            "flow_name": self.flow_name,
            "step": self.step,
            "data": self.data
        }

class ConversationFlow:
    """Manages multi-step conversation flows"""
    
    SUBJECTS_BY_LEVEL = {
        "primary": [
            {"id": "math_p", "title": "Mathematics", "description": "Numbers, shapes, and problem solving"},
            {"id": "eng_p", "title": "English", "description": "Reading, writing, and comprehension"},
            {"id": "shona", "title": "Shona", "description": "ChiShona language"},
            {"id": "science_p", "title": "Science", "description": "General science"},
            {"id": "social_p", "title": "Social Studies", "description": "History and geography"},
        ],
        "secondary": [
            {"id": "math_s", "title": "Mathematics", "description": "Algebra, geometry, statistics"},
            {"id": "eng_s", "title": "English Language", "description": "Language and literature"},
            {"id": "physics", "title": "Physics", "description": "Matter, energy, and forces"},
            {"id": "chemistry", "title": "Chemistry", "description": "Elements and reactions"},
            {"id": "biology", "title": "Biology", "description": "Living organisms"},
            {"id": "geography", "title": "Geography", "description": "Physical and human geography"},
            {"id": "history", "title": "History", "description": "Zimbabwe and world history"},
            {"id": "accounts", "title": "Accounting", "description": "Financial accounting"},
            {"id": "commerce", "title": "Commerce", "description": "Business studies"},
        ],
        "a_level": [
            {"id": "math_a", "title": "Mathematics", "description": "Pure and applied maths"},
            {"id": "physics_a", "title": "Physics", "description": "Advanced physics"},
            {"id": "chemistry_a", "title": "Chemistry", "description": "Advanced chemistry"},
            {"id": "biology_a", "title": "Biology", "description": "Advanced biology"},
            {"id": "accounts_a", "title": "Accounting", "description": "Advanced accounting"},
            {"id": "economics", "title": "Economics", "description": "Micro and macroeconomics"},
            {"id": "business", "title": "Business Studies", "description": "Advanced business"},
            {"id": "computing", "title": "Computer Science", "description": "Programming and theory"},
        ]
    }
    
    GRADES_BY_LEVEL = {
        "primary": ["Grade 1", "Grade 2", "Grade 3", "Grade 4", "Grade 5", "Grade 6", "Grade 7"],
        "secondary": ["Form 1", "Form 2", "Form 3", "Form 4"],
        "a_level": ["Lower 6", "Upper 6"]
    }
    
    def __init__(self, wa_client: WhatsAppClient, db: AsyncSession):
        self.wa = wa_client
        self.db = db
    
    async def start_onboarding(self, phone: str) -> None:
        """Start the onboarding flow for new users"""
        # Initialize flow state
        state = FlowState(
            flow_name="onboarding",
            step="welcome",
            data={"phone": phone}
        )
        await cache.set_json(f"flow_state:{phone}", state.to_dict(), ttl=3600)
        
        # Send welcome message with role selection
        await self.wa.send_buttons(
            to=phone,
            header="🎓 Welcome to Zim Student Companion!",
            body="I'm your AI study buddy for ZIMSEC exams. I'll help you practice, "
                 "understand difficult topics, and prepare for success!\n\n"
                 "First, tell me who you are:",
            buttons=[
                {"id": "role_student", "title": "📚 I'm a Student"},
                {"id": "role_parent", "title": "👨‍👩‍👧 I'm a Parent"},
                {"id": "role_teacher", "title": "👩‍🏫 I'm a Teacher"}
            ],
            footer="Let's get started! 🚀"
        )
    
    async def handle_onboarding(
        self,
        phone: str,
        message: WhatsAppMessage,
        state: FlowState
    ) -> None:
        """Handle onboarding flow steps"""
        text = message.text or ""
        if message.button_reply:
            text = message.button_reply.get("id", "")
        if message.list_reply:
            text = message.list_reply.get("id", "")
        
        step = state.step
        
        if step == "welcome":
            await self._handle_role_selection(phone, text, state)
        elif step == "get_name":
            await self._handle_name(phone, text, state)
        elif step == "get_level":
            await self._handle_level(phone, text, state)
        elif step == "get_grade":
            await self._handle_grade(phone, text, state)
        elif step == "get_subjects":
            await self._handle_subjects(phone, text, state)
        elif step == "get_school":
            await self._handle_school(phone, text, state)
        elif step == "confirm":
            await self._handle_confirmation(phone, text, state)
        elif step == "parent_get_name":
            await self._handle_parent_name(phone, text, state)
        elif step == "parent_link_child":
            await self._handle_parent_link(phone, text, state)
    
    async def _handle_role_selection(
        self,
        phone: str,
        text: str,
        state: FlowState
    ) -> None:
        """Handle role selection"""
        if text == "role_student":
            state.data["role"] = "student"
            state.step = "get_name"
            await cache.set_json(f"flow_state:{phone}", state.to_dict())
            
            await self.wa.send_text(
                phone,
                "Awesome! Let's set up your student profile. 📝\n\n"
                "What's your first name?"
            )
        
        elif text == "role_parent":
            state.data["role"] = "parent"
            state.step = "parent_get_name"
            await cache.set_json(f"flow_state:{phone}", state.to_dict())
            
            await self.wa.send_text(
                phone,
                "Welcome, parent! 👋\n\n"
                "I'll help you track your child's learning progress.\n\n"
                "What's your name?"
            )
        
        elif text == "role_teacher":
            state.data["role"] = "teacher"
            await cache.delete(f"flow_state:{phone}")
            
            await self.wa.send_text(
                phone,
                "Hello, Teacher! 👋\n\n"
                "Teacher accounts are set up through our web dashboard.\n\n"
                "Please visit: https://zimstudent.com/teachers\n\n"
                "Or contact us for school partnerships: partners@zimstudent.com"
            )
        else:
            await self.wa.send_buttons(
                to=phone,
                body="Please select your role:",
                buttons=[
                    {"id": "role_student", "title": "📚 I'm a Student"},
                    {"id": "role_parent", "title": "👨‍👩‍👧 I'm a Parent"},
                    {"id": "role_teacher", "title": "👩‍🏫 I'm a Teacher"}
                ]
            )
    
    async def _handle_name(self, phone: str, text: str, state: FlowState) -> None:
        """Handle name input"""
        if len(text) < 2 or len(text) > 50:
            await self.wa.send_text(phone, "Please enter a valid name (2-50 characters):")
            return
        
        state.data["first_name"] = text.strip().title()
        state.step = "get_level"
        await cache.set_json(f"flow_state:{phone}", state.to_dict())
        
        await self.wa.send_buttons(
            to=phone,
            body=f"Nice to meet you, {state.data['first_name']}! 🎉\n\n"
                 f"What level are you studying?",
            buttons=[
                {"id": "level_primary", "title": "📗 Primary (Gr 1-7)"},
                {"id": "level_secondary", "title": "📘 Secondary (F1-4)"},
                {"id": "level_a_level", "title": "📕 A-Level (F5-6)"}
            ]
        )
    
    async def _handle_level(self, phone: str, text: str, state: FlowState) -> None:
        """Handle education level selection"""
        level_map = {
            "level_primary": "primary",
            "level_secondary": "secondary",
            "level_a_level": "a_level"
        }
        
        if text not in level_map:
            await self.wa.send_buttons(
                to=phone,
                body="Please select your education level:",
                buttons=[
                    {"id": "level_primary", "title": "📗 Primary"},
                    {"id": "level_secondary", "title": "📘 Secondary"},
                    {"id": "level_a_level", "title": "📕 A-Level"}
                ]
            )
            return
        
        level = level_map[text]
        state.data["education_level"] = level
        state.step = "get_grade"
        await cache.set_json(f"flow_state:{phone}", state.to_dict())
        
        # Create grade selection list
        grades = self.GRADES_BY_LEVEL[level]
        sections = [{
            "title": "Select Your Grade",
            "rows": [
                {"id": f"grade_{g.replace(' ', '_')}", "title": g}
                for g in grades
            ]
        }]
        
        await self.wa.send_list(
            to=phone,
            body=f"Great! Which grade/form are you in?",
            button_text="Select Grade",
            sections=sections
        )
    
    async def _handle_grade(self, phone: str, text: str, state: FlowState) -> None:
        """Handle grade selection"""
        if not text.startswith("grade_"):
            await self.wa.send_text(phone, "Please select your grade from the list.")
            return
        
        grade = text.replace("grade_", "").replace("_", " ")
        state.data["grade"] = grade
        state.step = "get_subjects"
        await cache.set_json(f"flow_state:{phone}", state.to_dict())
        
        # Create subject selection list
        level = state.data["education_level"]
        subjects = self.SUBJECTS_BY_LEVEL.get(level, [])
        
        sections = [{
            "title": "Choose Your Subjects",
            "rows": [
                {
                    "id": f"subj_{s['id']}",
                    "title": s["title"],
                    "description": s["description"][:72]
                }
                for s in subjects
            ]
        }]
        
        state.data["selected_subjects"] = []
        await cache.set_json(f"flow_state:{phone}", state.to_dict())
        
        await self.wa.send_list(
            to=phone,
            header="📚 Subject Selection",
            body=f"Which subjects do you want to practice?\n\n"
                 f"Select one subject now. You can add more later.\n\n"
                 f"Tip: Start with the subject you find most challenging!",
            button_text="Choose Subject",
            sections=sections,
            footer="You can change this anytime"
        )
    
    async def _handle_subjects(self, phone: str, text: str, state: FlowState) -> None:
        """Handle subject selection"""
        if text.startswith("subj_"):
            subject_id = text.replace("subj_", "")
            level = state.data["education_level"]
            subjects = self.SUBJECTS_BY_LEVEL.get(level, [])
            
            selected = next((s for s in subjects if s["id"] == subject_id), None)
            if selected:
                state.data["selected_subjects"] = [selected["title"]]
        
        if not state.data.get("selected_subjects"):
            await self.wa.send_text(phone, "Please select at least one subject.")
            return
        
        state.step = "get_school"
        await cache.set_json(f"flow_state:{phone}", state.to_dict())
        
        await self.wa.send_text(
            phone,
            f"Excellent choice! 👍\n\n"
            f"What's the name of your school?\n\n"
            f"(Type 'skip' if you prefer not to share)"
        )
    
    async def _handle_school(self, phone: str, text: str, state: FlowState) -> None:
        """Handle school name input"""
        if text.lower() != "skip":
            state.data["school_name"] = text.strip()
        else:
            state.data["school_name"] = None
        
        state.step = "confirm"
        await cache.set_json(f"flow_state:{phone}", state.to_dict())
        
        # Show confirmation
        school_text = state.data.get("school_name") or "Not specified"
        subjects_text = ", ".join(state.data.get("selected_subjects", []))
        
        await self.wa.send_buttons(
            to=phone,
            header="✅ Confirm Your Profile",
            body=f"Please confirm your details:\n\n"
                 f"👤 Name: {state.data['first_name']}\n"
                 f"📚 Level: {state.data['education_level'].replace('_', ' ').title()}\n"
                 f"📖 Grade: {state.data['grade']}\n"
                 f"📝 Subjects: {subjects_text}\n"
                 f"🏫 School: {school_text}\n\n"
                 f"Is this correct?",
            buttons=[
                {"id": "confirm_yes", "title": "✅ Yes, looks good!"},
                {"id": "confirm_no", "title": "🔄 Start over"}
            ]
        )
    
    async def _handle_confirmation(self, phone: str, text: str, state: FlowState) -> None:
        """Handle profile confirmation"""
        if text == "confirm_no":
            await self.start_onboarding(phone)
            return
        
        if text != "confirm_yes":
            await self.wa.send_buttons(
                to=phone,
                body="Please confirm your profile:",
                buttons=[
                    {"id": "confirm_yes", "title": "✅ Yes, looks good!"},
                    {"id": "confirm_no", "title": "🔄 Start over"}
                ]
            )
            return
        
        # Create user and student in database
        try:
            user = User(
                phone_number=phone,
                whatsapp_id=phone,
                role=UserRole.STUDENT,
                subscription_tier=SubscriptionTier.FREE
            )
            self.db.add(user)
            await self.db.flush()
            
            student = Student(
                user_id=user.id,
                first_name=state.data["first_name"],
                last_name="",  # Can be updated later
                education_level=EducationLevel(state.data["education_level"]),
                grade=state.data["grade"],
                subjects=state.data.get("selected_subjects", []),
                school_name=state.data.get("school_name"),
                preferred_language="english"
            )
            self.db.add(student)
            
            # Create streak record
            from app.models.gamification import StudentStreak
            streak = StudentStreak(student_id=student.id)
            self.db.add(streak)
            
            await self.db.commit()
            
            # Clear flow state
            await cache.delete(f"flow_state:{phone}")
            
            # Send success message
            await self.wa.send_text(
                phone,
                f"🎉 Welcome aboard, {state.data['first_name']}!\n\n"
                f"Your account is all set up. Here's what you can do:\n\n"
                f"📚 *Ask me anything* - I'll help you understand\n"
                f"🎯 *Daily Practice* - Build your skills\n"
                f"🏆 *Competitions* - Compete with others\n"
                f"📊 *Progress* - Track your improvement\n\n"
                f"Type *menu* anytime to see options.\n\n"
                f"Ready to start learning? Ask me a question or type *practice* to begin!"
            )
            
            # Show main menu
            await self.show_main_menu(phone, user)
            
        except Exception as e:
            await self.wa.send_text(
                phone,
                "Sorry, there was an error creating your account. Please try again later."
            )
            raise
    
    async def _handle_parent_name(self, phone: str, text: str, state: FlowState) -> None:
        """Handle parent name input"""
        if len(text) < 2:
            await self.wa.send_text(phone, "Please enter your name:")
            return
        
        state.data["parent_name"] = text.strip().title()
        state.step = "parent_link_child"
        await cache.set_json(f"flow_state:{phone}", state.to_dict())
        
        await self.wa.send_text(
            phone,
            f"Hello {state.data['parent_name']}! 👋\n\n"
            f"To link with your child's account, please ask them for their "
            f"*6-digit parent code*.\n\n"
            f"Your child can get this code by typing 'parent code' in their chat.\n\n"
            f"Once you have the code, type it here:"
        )
    
    async def _handle_parent_link(self, phone: str, text: str, state: FlowState) -> None:
        """Handle parent-child linking"""
        code = text.strip().upper()
        
        if len(code) != 6:
            await self.wa.send_text(
                phone,
                "Please enter a valid 6-digit code:"
            )
            return
        
        # Look up the code
        from sqlalchemy import select
        result = await self.db.execute(
            select(ParentStudentLink)
            .where(ParentStudentLink.verification_code == code)
            .where(ParentStudentLink.verified == False)
        )
        link = result.scalar_one_or_none()
        
        if not link:
            await self.wa.send_text(
                phone,
                "Invalid or expired code. Please check with your child and try again."
            )
            return
        
        # Create parent user
        parent_user = User(
            phone_number=phone,
            whatsapp_id=phone,
            role=UserRole.PARENT,
            subscription_tier=SubscriptionTier.FREE
        )
        self.db.add(parent_user)
        await self.db.flush()
        
        # Update link
        link.parent_user_id = parent_user.id
        link.verified = True
        
        await self.db.commit()
        
        # Get student name
        student_result = await self.db.execute(
            select(Student).where(Student.id == link.student_id)
        )
        student = student_result.scalar_one_or_none()
        
        await cache.delete(f"flow_state:{phone}")
        
        await self.wa.send_text(
            phone,
            f"✅ Successfully linked to {student.first_name}'s account!\n\n"
            f"You'll now receive:\n"
            f"📊 Weekly progress reports\n"
            f"🏆 Achievement notifications\n"
            f"📈 Performance insights\n\n"
            f"Type *report* anytime to see your child's latest progress."
        )
    
    async def show_main_menu(self, phone: str, user: User) -> None:
        """Show the main menu"""
        if user.role == UserRole.STUDENT:
            await self.wa.send_list(
                to=phone,
                header="📚 Zim Student Companion",
                body="What would you like to do today?",
                button_text="Choose Option",
                sections=[
                    {
                        "title": "Learning",
                        "rows": [
                            {"id": "menu_practice", "title": "🎯 Daily Practice", "description": "Practice questions for your subjects"},
                            {"id": "menu_ask", "title": "❓ Ask a Question", "description": "Get help understanding a topic"},
                            {"id": "menu_quiz", "title": "📝 Quick Quiz", "description": "Test your knowledge"},
                        ]
                    },
                    {
                        "title": "Progress & Fun",
                        "rows": [
                            {"id": "menu_progress", "title": "📊 My Progress", "description": "View your learning stats"},
                            {"id": "menu_compete", "title": "🏆 Competitions", "description": "Join challenges and win"},
                            {"id": "menu_achievements", "title": "🎖️ Achievements", "description": "View your badges"},
                        ]
                    },
                    {
                        "title": "Account",
                        "rows": [
                            {"id": "menu_parent_code", "title": "👨‍👩‍👧 Parent Code", "description": "Link parent to your account"},
                            {"id": "menu_subscription", "title": "💎 Upgrade", "description": "Get unlimited access"},
                            {"id": "menu_settings", "title": "⚙️ Settings", "description": "Update your profile"},
                        ]
                    }
                ],
                footer=f"🔥 Keep learning, keep growing!"
            )
        
        elif user.role == UserRole.PARENT:
            await self.wa.send_list(
                to=phone,
                header="👨‍👩‍👧 Parent Dashboard",
                body="Monitor your child's learning journey",
                button_text="Choose Option",
                sections=[
                    {
                        "title": "Reports",
                        "rows": [
                            {"id": "parent_daily", "title": "📊 Daily Summary", "description": "Today's learning activity"},
                            {"id": "parent_weekly", "title": "📈 Weekly Report", "description": "This week's progress"},
                            {"id": "parent_subjects", "title": "📚 Subject Breakdown", "description": "Performance by subject"},
                        ]
                    },
                    {
                        "title": "Settings",
                        "rows": [
                            {"id": "parent_notifications", "title": "🔔 Notifications", "description": "Manage alerts"},
                            {"id": "parent_subscription", "title": "💎 Subscription", "description": "Manage plan"},
                        ]
                    }
                ]
            )