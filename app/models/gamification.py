# ============================================================================
# Gamification Models
# ============================================================================
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, Date
from sqlalchemy import Text, Numeric, JSON, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class Achievement(Base):
    __tablename__ = "achievements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False, unique=True)
    description = Column(Text)
    icon = Column(String(50))  # emoji or icon name
    badge_image_url = Column(String(500))
    points = Column(Integer, default=0)
    
    achievement_type = Column(String(30))  # streak, mastery, competition, milestone, special
    criteria = Column(JSON)  # JSON defining how to earn
    is_secret = Column(Boolean, default=False)  # Hidden until earned
    is_active = Column(Boolean, default=True)
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    student_achievements = relationship("StudentAchievement", back_populates="achievement")
    
    def __repr__(self):
        return f"<Achievement {self.name}>"

class StudentAchievement(Base):
    __tablename__ = "student_achievements"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    achievement_id = Column(UUID(as_uuid=True), ForeignKey("achievements.id"), nullable=False)
    earned_at = Column(DateTime(timezone=True), server_default=func.now())
    
    student = relationship("Student", back_populates="achievements")
    achievement = relationship("Achievement", back_populates="student_achievements")
    
    __table_args__ = (
        UniqueConstraint('student_id', 'achievement_id', name='unique_student_achievement'),
    )

class StudentStreak(Base):
    __tablename__ = "student_streaks"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False, unique=True)
    
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    last_activity_date = Column(Date)
    total_active_days = Column(Integer, default=0)
    
    # Weekly stats
    questions_this_week = Column(Integer, default=0)
    correct_this_week = Column(Integer, default=0)
    time_this_week_minutes = Column(Integer, default=0)
    week_start_date = Column(Date)
    
    student = relationship("Student", back_populates="streak")
    
    def __repr__(self):
        return f"<StudentStreak {self.current_streak} days>"

class StudentTopicProgress(Base):
    __tablename__ = "student_topic_progress"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    
    mastery_level = Column(Numeric(5, 2), default=0)  # 0-100
    questions_attempted = Column(Integer, default=0)
    questions_correct = Column(Integer, default=0)
    time_spent_minutes = Column(Integer, default=0)
    
    last_practiced = Column(DateTime(timezone=True))
    next_review_date = Column(Date)  # For spaced repetition
    
    # Difficulty progression
    current_difficulty = Column(String(20), default="easy")
    
    student = relationship("Student", back_populates="progress")
    topic = relationship("Topic")
    
    __table_args__ = (
        UniqueConstraint('student_id', 'topic_id', name='unique_student_topic'),
    )

class Competition(Base):
    __tablename__ = "competitions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=True)
    education_level = Column(String(20))
    grade = Column(String(20))
    
    competition_type = Column(String(30))  # individual, school, district, national
    
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    
    max_participants = Column(Integer)
    entry_fee = Column(Numeric(10, 2), default=0)
    
    prizes = Column(JSON)  # {"1st": "...", "2nd": "...", etc.}
    rules = Column(JSON)  # Competition rules
    
    num_questions = Column(Integer, default=10)
    time_limit_minutes = Column(Integer, default=30)
    difficulty = Column(String(20), default="medium")
    
    status = Column(String(20), default="upcoming")  # upcoming, active, completed, cancelled
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(UUID(as_uuid=True))
    
    participants = relationship("CompetitionParticipant", back_populates="competition", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Competition {self.name}>"

class CompetitionParticipant(Base):
    __tablename__ = "competition_participants"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    
    score = Column(Numeric(10, 2), default=0)
    time_taken_seconds = Column(Integer)
    questions_correct = Column(Integer, default=0)
    questions_attempted = Column(Integer, default=0)
    
    rank = Column(Integer)
    prize_won = Column(String(200))
    
    joined_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    status = Column(String(20), default="registered")  # registered, in_progress, completed, disqualified
    
    competition = relationship("Competition", back_populates="participants")
    student = relationship("Student", back_populates="competition_entries")
    
    __table_args__ = (
        UniqueConstraint('competition_id', 'student_id', name='unique_competition_student'),
    )