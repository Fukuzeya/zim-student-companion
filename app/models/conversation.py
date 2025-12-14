# ============================================================================
# Conversation History Model
# ============================================================================
from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.core.database import Base

class Conversation(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    student_id = Column(UUID(as_uuid=True), ForeignKey("students.id", ondelete="CASCADE"), nullable=False)
    
    whatsapp_message_id = Column(String(100))
    role = Column(String(20), nullable=False)  # user, assistant, system
    content = Column(Text, nullable=False)
    
    # Context
    context_type = Column(String(30))  # question, explanation, practice, general, feedback
    subject_id = Column(UUID(as_uuid=True), ForeignKey("subjects.id"), nullable=True)
    topic_id = Column(UUID(as_uuid=True), ForeignKey("topics.id"), nullable=True)
    session_id = Column(UUID(as_uuid=True), ForeignKey("practice_sessions.id"), nullable=True)
    
    # Metadata
    tokens_used = Column(Integer)
    response_time_ms = Column(Integer)
    
    # RAG metadata
    sources_used = Column(Integer, default=0)
    retrieval_score = Column(String(10))  # high, medium, low
    
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    student = relationship("Student", back_populates="conversations")
    
    def __repr__(self):
        return f"<Conversation {self.role}: {self.content[:50]}...>"