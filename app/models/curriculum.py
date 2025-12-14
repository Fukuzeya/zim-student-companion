# ============================================================================
# Curriculum Models
# ============================================================================
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey
from sqlalchemy import Text, Enum, JSON, Numeric
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class Subject(Base):
    __tablename__ = "subjects"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), nullable=False)
    code = Column(String(20), unique=True, nullable=False)  # ZIMSEC code
    education_level = Column(String(20), nullable=False)  # primary, secondary, a_level
    description = Column(Text)
    icon = Column(String(50))  # emoji or icon name
    color = Column(String(7))  # hex color
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    topics = relationship("Topic", back_populates="subject", cascade="all, delete-orphan")
    questions = relationship("Question", back_populates="subject")
    
    def __repr__(self):
        return f"<Subject {self.name} ({self.code})>"

class Topic(Base):
    __tablename__ = "topics"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id", ondelete="CASCADE"), nullable=False)
    parent_topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=True)  # For sub-topics
    name = Column(String(200), nullable=False)
    description = Column(Text)
    grade = Column(String(20), nullable=False)
    syllabus_reference = Column(String(100))  # ZIMSEC syllabus section
    order_index = Column(Integer, default=0)
    estimated_hours = Column(Numeric(4, 1))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    subject = relationship("Subject", back_populates="topics")
    parent_topic = relationship("Topic", remote_side=[id], backref="sub_topics")
    questions = relationship("Question", back_populates="topic")
    learning_objectives = relationship("LearningObjective", back_populates="topic", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Topic {self.name}>"

class LearningObjective(Base):
    __tablename__ = "learning_objectives"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id", ondelete="CASCADE"), nullable=False)
    description = Column(Text, nullable=False)
    bloom_level = Column(String(20))  # remember, understand, apply, analyze, evaluate, create
    order_index = Column(Integer, default=0)
    
    topic = relationship("Topic", back_populates="learning_objectives")

class Question(Base):
    __tablename__ = "questions"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=True)
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=True)
    
    question_text = Column(Text, nullable=False)
    question_type = Column(String(30), nullable=False)  # multiple_choice, short_answer, long_answer, calculation, diagram, essay
    options = Column(JSON, nullable=True)  # For MCQ: ["option1", "option2", ...]
    correct_answer = Column(Text, nullable=False)
    marking_scheme = Column(Text)  # Detailed marking criteria
    explanation = Column(Text)  # Explanation of the answer
    marks = Column(Integer, default=1)
    difficulty = Column(String(20), default="medium")  # easy, medium, hard
    
    # Source information
    source = Column(String(50))  # past_paper, generated, teacher_submitted
    source_year = Column(Integer)
    source_paper = Column(String(50))  # Paper 1, Paper 2, etc.
    source_question_number = Column(String(20))
    
    # Statistics
    times_attempted = Column(Integer, default=0)
    times_correct = Column(Integer, default=0)
    avg_time_seconds = Column(Integer)
    
    # Vector store reference
    vector_id = Column(String(100))
    
    # Metadata
    tags = Column(JSON, default=list)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    created_by = Column(UUID(as_uuid=True), nullable=True)  # Teacher who created it
    
    topic = relationship("Topic", back_populates="questions")
    subject = relationship("Subject", back_populates="questions")
    
    @property
    def success_rate(self) -> float:
        if self.times_attempted == 0:
            return 0.0
        return (self.times_correct / self.times_attempted) * 100
    
    def __repr__(self):
        return f"<Question {self.id} ({self.difficulty})>"