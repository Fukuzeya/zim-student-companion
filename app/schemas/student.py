# ============================================================================
# Student Schemas
# ============================================================================
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime, date
from uuid import UUID
from enum import Enum

class EducationLevelEnum(str, Enum):
    PRIMARY = "primary"
    SECONDARY = "secondary"
    A_LEVEL = "a_level"

class StudentBase(BaseModel):
    first_name: str = Field(..., min_length=2, max_length=100)
    last_name: str = Field("", max_length=100)
    education_level: EducationLevelEnum
    grade: str
    school_name: Optional[str] = None
    district: Optional[str] = None
    province: Optional[str] = None
    subjects: List[str] = []
    preferred_language: str = "english"
    daily_goal_minutes: int = 30

class StudentCreate(StudentBase):
    user_id: UUID

class StudentUpdate(BaseModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    school_name: Optional[str] = None
    district: Optional[str] = None
    province: Optional[str] = None
    grade: Optional[str] = None
    subjects: Optional[List[str]] = None
    preferred_language: Optional[str] = None
    daily_goal_minutes: Optional[int] = None

class StudentResponse(StudentBase):
    id: UUID
    user_id: UUID
    total_xp: int
    level: int
    created_at: datetime
    
    class Config:
        from_attributes = True

class StudentStats(BaseModel):
    total_xp: int
    level: int
    level_title: str
    xp_for_next_level: int
    progress_percent: float
    current_streak: int
    longest_streak: int
    total_questions_answered: int
    accuracy_percent: float
    total_study_time_minutes: int

class StudentProgress(BaseModel):
    topic_id: UUID
    topic_name: str
    subject_name: str
    mastery_level: float
    questions_attempted: int
    questions_correct: int
    last_practiced: Optional[datetime]

class ParentLinkRequest(BaseModel):
    verification_code: str = Field(..., min_length=6, max_length=6)

class ParentLinkResponse(BaseModel):
    student_id: UUID
    student_name: str
    relationship: Optional[str]
    verified: bool