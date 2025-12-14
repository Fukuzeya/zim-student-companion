# ============================================================================
# User & Student Models
# ============================================================================
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy import Text, Enum, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
import enum
from app.core.database import Base

class UserRole(str, enum.Enum):
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"
    ADMIN = "admin"

class EducationLevel(str, enum.Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    A_LEVEL = "a_level"

class SubscriptionTier(str, enum.Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    FAMILY = "family"
    SCHOOL = "school"

class User(Base):
    __tablename__ = "users"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    phone_number = Column(String(20), unique=True, nullable=False, index=True)
    whatsapp_id = Column(String(50), unique=True)
    email = Column(String(255), unique=True, nullable=True)
    password_hash = Column(String(255), nullable=True)  # For dashboard login
    role = Column(Enum(UserRole), nullable=False, default=UserRole.STUDENT)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    last_active = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True)
    is_verified = Column(Boolean, default=False)
    subscription_tier = Column(Enum(SubscriptionTier), default=SubscriptionTier.FREE)
    subscription_expires_at = Column(DateTime(timezone=True))
    
    # Relationships
    student = relationship("Student", back_populates="user", uselist=False, cascade="all, delete-orphan")
    parent_links = relationship("ParentStudentLink", back_populates="parent", foreign_keys="ParentStudentLink.parent_user_id")
    payments = relationship("Payment", back_populates="user")
    
    def __repr__(self):
        return f"<User {self.phone_number} ({self.role.value})>"

class Student(Base):
    __tablename__ = "students"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True)
    first_name = Column(String(100), nullable=False)
    last_name = Column(String(100), default="")
    date_of_birth = Column(DateTime, nullable=True)
    school_name = Column(String(200))
    school_id = Column(UUID(as_uuid=True), nullable=True)  # For school accounts
    district = Column(String(100))
    province = Column(String(100))
    education_level = Column(Enum(EducationLevel), nullable=False)
    grade = Column(String(20), nullable=False)
    subjects = Column(JSON, default=list)  # List of subject names
    preferred_language = Column(String(20), default="english")
    daily_goal_minutes = Column(Integer, default=30)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Gamification stats
    total_xp = Column(Integer, default=0)
    level = Column(Integer, default=1)
    
    # Relationships
    user = relationship("User", back_populates="student")
    sessions = relationship("PracticeSession", back_populates="student", cascade="all, delete-orphan")
    progress = relationship("StudentTopicProgress", back_populates="student", cascade="all, delete-orphan")
    streak = relationship("StudentStreak", back_populates="student", uselist=False, cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="student", cascade="all, delete-orphan")
    achievements = relationship("StudentAchievement", back_populates="student", cascade="all, delete-orphan")
    competition_entries = relationship("CompetitionParticipant", back_populates="student")
    
    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}".strip()
    
    def __repr__(self):
        return f"<Student {self.first_name} ({self.grade})>"

class ParentStudentLink(Base):
    __tablename__ = "parent_student_links"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    parent_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=True)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    relationship_type = Column(String(20))  # mother, father, guardian
    verified = Column(Boolean, default=False)
    verification_code = Column(String(6))
    notifications_enabled = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    parent = relationship("User", back_populates="parent_links", foreign_keys=[parent_user_id])
    student = relationship("Student")
    
    __table_args__ = (
        UniqueConstraint('parent_user_id', 'student_id', name='unique_parent_student'),
    )