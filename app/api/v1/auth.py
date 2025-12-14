# ============================================================================
# Authentication Endpoints
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, Field
from typing import Optional
from datetime import timedelta

from app.core.database import get_db
from app.core.security import create_access_token, verify_password, get_password_hash
from app.models.user import User, UserRole
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["authentication"])

class PhoneLoginRequest(BaseModel):
    phone_number: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")

class OTPVerifyRequest(BaseModel):
    phone_number: str
    otp: str = Field(..., min_length=6, max_length=6)

class EmailLoginRequest(BaseModel):
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user_id: str
    role: str

class RegisterRequest(BaseModel):
    email: str
    password: str = Field(..., min_length=8)
    phone_number: Optional[str] = None
    role: UserRole = UserRole.STUDENT

@router.post("/phone/request-otp")
async def request_otp(
    request: PhoneLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Request OTP for phone login"""
    import random
    from app.core.redis import cache
    
    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    
    # Store OTP in Redis (5 min expiry)
    await cache.set(f"otp:{request.phone_number}", otp, ttl=300)
    
    # In production, send OTP via SMS gateway
    # For now, return it (REMOVE IN PRODUCTION)
    return {
        "message": "OTP sent to your phone",
        "debug_otp": otp if settings.DEBUG else None
    }

@router.post("/phone/verify", response_model=TokenResponse)
async def verify_otp(
    request: OTPVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """Verify OTP and login"""
    from app.core.redis import cache
    
    # Verify OTP
    stored_otp = await cache.get(f"otp:{request.phone_number}")
    
    if not stored_otp or stored_otp != request.otp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP"
        )
    
    # Delete used OTP
    await cache.delete(f"otp:{request.phone_number}")
    
    # Find or create user
    result = await db.execute(
        select(User).where(User.phone_number == request.phone_number)
    )
    user = result.scalar_one_or_none()
    
    if not user:
        # Return indication that user needs to register
        return {
            "access_token": "",
            "token_type": "bearer",
            "user_id": "",
            "role": "new_user"
        }
    
    # Create token
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "role": user.role.value
    }

@router.post("/login", response_model=TokenResponse)
async def login(
    request: EmailLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """Login with email and password"""
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()
    
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials"
        )
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "role": user.role.value
    }

@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """Register new user with email"""
    # Check if email exists
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Create user
    user = User(
        email=request.email,
        password_hash=get_password_hash(request.password),
        phone_number=request.phone_number or f"temp_{request.email}",
        role=request.role
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    access_token = create_access_token(
        data={"sub": str(user.id)},
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "user_id": str(user.id),
        "role": user.role.value
    }
