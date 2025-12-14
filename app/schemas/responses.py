# ============================================================================
# Common Response Schemas
# ============================================================================
from uuid import UUID
from pydantic import BaseModel
from typing import Optional, List, Dict, Any, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')

class BaseResponse(BaseModel):
    success: bool = True
    message: Optional[str] = None

class ErrorResponse(BaseModel):
    success: bool = False
    error: str
    error_code: Optional[str] = None
    details: Optional[Dict[str, Any]] = None

class PaginatedResponse(BaseModel):
    items: List[Any]
    total: int
    page: int
    page_size: int
    total_pages: int

class HealthCheckResponse(BaseModel):
    status: str
    app: str
    version: str
    timestamp: datetime

class LeaderboardEntry(BaseModel):
    rank: int
    student_id: str
    name: str
    school: Optional[str]
    grade: str
    score: float
    metric: str

class LeaderboardResponse(BaseModel):
    leaderboard: List[LeaderboardEntry]
    type: str
    updated_at: datetime

class AchievementResponse(BaseModel):
    name: str
    description: str
    icon: str
    points: int
    earned_at: datetime

class NotificationResponse(BaseModel):
    id: UUID
    title: str
    message: str
    type: str
    is_read: bool
    created_at: datetime

class DailyStatsResponse(BaseModel):
    date: str
    questions_answered: int
    correct_answers: int
    accuracy: float
    xp_earned: int
    time_spent_minutes: int
    streak_maintained: bool

class WeeklyReportResponse(BaseModel):
    week_start: str
    week_end: str
    total_questions: int
    total_correct: int
    accuracy: float
    total_xp: int
    total_time_minutes: int
    subjects_practiced: List[str]
    strongest_topic: Optional[str]
    weakest_topic: Optional[str]
    recommendations: List[str]