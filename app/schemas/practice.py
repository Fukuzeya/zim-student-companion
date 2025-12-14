# ============================================================================
# Practice Schemas
# ============================================================================
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
from uuid import UUID
from enum import Enum

class QuestionTypeEnum(str, Enum):
    MULTIPLE_CHOICE = "multiple_choice"
    SHORT_ANSWER = "short_answer"
    LONG_ANSWER = "long_answer"
    CALCULATION = "calculation"
    DIAGRAM = "diagram"
    ESSAY = "essay"

class DifficultyEnum(str, Enum):
    EASY = "easy"
    MEDIUM = "medium"
    HARD = "hard"

class SessionTypeEnum(str, Enum):
    DAILY_PRACTICE = "daily_practice"
    TOPIC_PRACTICE = "topic_practice"
    MOCK_EXAM = "mock_exam"
    COMPETITION = "competition"
    REVISION = "revision"
    HOMEWORK = "homework"

class QuestionBase(BaseModel):
    question_text: str
    question_type: QuestionTypeEnum
    options: Optional[List[str]] = None
    marks: int = 1
    difficulty: DifficultyEnum = DifficultyEnum.MEDIUM

class QuestionCreate(QuestionBase):
    subject_id: UUID
    topic_id: Optional[UUID] = None
    correct_answer: str
    marking_scheme: Optional[str] = None
    explanation: Optional[str] = None
    source: str = "manual"
    source_year: Optional[int] = None

class QuestionResponse(QuestionBase):
    id: UUID
    subject_id: UUID
    topic_id: Optional[UUID]
    source: Optional[str]
    source_year: Optional[int]
    times_attempted: int
    success_rate: float
    
    class Config:
        from_attributes = True

class QuestionWithAnswer(QuestionResponse):
    correct_answer: str
    marking_scheme: Optional[str]
    explanation: Optional[str]

class StartSessionRequest(BaseModel):
    subject_id: Optional[UUID] = None
    topic_id: Optional[UUID] = None
    session_type: SessionTypeEnum = SessionTypeEnum.DAILY_PRACTICE
    num_questions: int = Field(5, ge=1, le=50)
    difficulty: Optional[DifficultyEnum] = None

class SessionQuestionResponse(BaseModel):
    id: UUID
    question_text: str
    question_type: QuestionTypeEnum
    options: Optional[List[str]]
    marks: int
    difficulty: DifficultyEnum
    index: int
    total: int

class AnswerSubmission(BaseModel):
    question_id: UUID
    answer: str

class AnswerEvaluation(BaseModel):
    is_correct: bool
    feedback: str
    marks_earned: float
    marks_possible: float
    xp_earned: int
    correct_answer: Optional[str] = None  # Only shown after attempt

class SessionSummary(BaseModel):
    session_id: UUID
    total_questions: int
    correct_answers: int
    score_percentage: float
    time_spent_seconds: int
    xp_earned: int
    achievements_unlocked: List[str]

class HintResponse(BaseModel):
    hint: str
    hint_number: int
    hints_remaining: int

class AskQuestionRequest(BaseModel):
    question: str = Field(..., min_length=3, max_length=1000)
    subject: Optional[str] = None
    topic: Optional[str] = None

class AskQuestionResponse(BaseModel):
    response: str
    sources_used: int
    follow_up_suggestions: Optional[List[str]] = None
