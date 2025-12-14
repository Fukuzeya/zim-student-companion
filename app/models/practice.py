# ============================================================================
# Practice Session Models
# ============================================================================
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy import Text, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class PracticeSession(Base):
    __tablename__ = "practice_sessions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=True)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=True)
    competition_id = Column(UUID(as_uuid=True), ForeignKey("competitions.id"), nullable=True)
    
    session_type = Column(String(30), nullable=False)  # daily_practice, topic_practice, mock_exam, competition, revision, homework
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True))
    
    total_questions = Column(Integer, default=0)
    correct_answers = Column(Integer, default=0)
    score_percentage = Column(Numeric(5, 2))
    total_marks_earned = Column(Numeric(6, 1), default=0)
    total_marks_possible = Column(Numeric(6, 1), default=0)
    time_spent_seconds = Column(Integer)
    
    difficulty_level = Column(String(20))
    status = Column(String(20), default="in_progress")  # in_progress, completed, abandoned
    
    # XP earned in this session
    xp_earned = Column(Integer, default=0)
    
    student = relationship("Student", back_populates="sessions")
    attempts = relationship("QuestionAttempt", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<PracticeSession {self.id} ({self.status})>"

class QuestionAttempt(Base):
    __tablename__ = "question_attempts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey("practice_sessions.id", ondelete="CASCADE"), nullable=False)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    question_id = Column(UUID(as_uuid=True), ForeignKey("questions.id"), nullable=False)
    
    student_answer = Column(Text)
    is_correct = Column(Boolean)
    marks_earned = Column(Numeric(4, 1), default=0)
    marks_possible = Column(Numeric(4, 1), default=1)
    
    time_spent_seconds = Column(Integer)
    hints_used = Column(Integer, default=0)
    attempts_count = Column(Integer, default=1)  # How many tries before getting it right
    
    ai_feedback = Column(Text)
    attempted_at = Column(DateTime(timezone=True), server_default=func.now())
    
    session = relationship("PracticeSession", back_populates="attempts")
    question = relationship("Question")
    
    def __repr__(self):
        return f"<QuestionAttempt {self.id} ({'✓' if self.is_correct else '✗'})>"