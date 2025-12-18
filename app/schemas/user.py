# ============================================================================
# User Schemas
# ============================================================================
from pydantic import BaseModel, Field, validator
from typing import Optional, List
from datetime import datetime
from uuid import UUID
from enum import Enum

class UserRoleEnum(str, Enum):
    STUDENT = "student"
    PARENT = "parent"
    TEACHER = "teacher"
    ADMIN = "admin"

class SubscriptionTierEnum(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PREMIUM = "premium"
    FAMILY = "family"
    SCHOOL = "school"

class UserBase(BaseModel):
    phone_number: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    email: Optional[str] = None
    role: UserRoleEnum = UserRoleEnum.STUDENT

class UserCreate(UserBase):
    password: Optional[str] = Field(None, min_length=8)

class UserUpdate(BaseModel):
    email: Optional[str] = None
    phone_number: Optional[str] = None
    is_active: Optional[bool] = None

class UserResponse(UserBase):
    id: UUID
    is_active: bool
    is_verified: bool
    subscription_tier: SubscriptionTierEnum
    subscription_expires_at: Optional[datetime]
    created_at: datetime
    last_active: Optional[datetime]
    
    class Config:
        from_attributes = True

class UserInDB(UserResponse):
    password_hash: Optional[str]
