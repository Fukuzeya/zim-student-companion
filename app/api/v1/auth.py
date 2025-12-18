# ============================================================================
# Authentication Endpoints
# ============================================================================
"""
Authentication and authorization endpoints for the EduBot application.

Provides:
- Phone/OTP based authentication (primary for WhatsApp users)
- Email/password authentication (for dashboard access)
- JWT token management (access + refresh tokens)
- Session management and logout
- Current user profile retrieval
"""
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, Field, EmailStr
from typing import Optional, List
from datetime import datetime, timedelta
from uuid import UUID
import secrets

from app.core.database import get_db
from app.core.security import (
    create_access_token,
    create_refresh_token,
    verify_password,
    get_password_hash,
    decode_access_token,
    decode_refresh_token,
    get_current_active_user
)
from app.models.user import User, Student, UserRole, SubscriptionTier
from app.config import get_settings

settings = get_settings()
router = APIRouter(prefix="/auth", tags=["authentication"])
security = HTTPBearer(auto_error=False)


# ============================================================================
# Request/Response Schemas
# ============================================================================
class PhoneLoginRequest(BaseModel):
    """Request OTP for phone-based login"""
    phone_number: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")

class OTPVerifyRequest(BaseModel):
    """Verify OTP and complete phone login"""
    phone_number: str = Field(..., pattern=r"^\+?[0-9]{10,15}$")
    otp: str = Field(..., min_length=6, max_length=6)

class EmailLoginRequest(BaseModel):
    """Email/password login request"""
    email: EmailStr
    password: str = Field(..., min_length=1)

class RegisterRequest(BaseModel):
    """User registration request"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    phone_number: Optional[str] = Field(None, pattern=r"^\+?[0-9]{10,15}$")
    role: UserRole = UserRole.STUDENT

class RefreshTokenRequest(BaseModel):
    """Refresh token request"""
    refresh_token: str

class TokenResponse(BaseModel):
    """Authentication token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds until access token expires
    user_id: str
    role: str

class UserProfileResponse(BaseModel):
    """Current user profile response"""
    id: UUID
    phone_number: str
    email: Optional[str]
    role: str
    subscription_tier: str
    subscription_expires_at: Optional[datetime]
    is_active: bool
    is_verified: bool
    created_at: datetime
    last_active: Optional[datetime]
    # Student profile (if applicable)
    student: Optional[dict] = None

class MessageResponse(BaseModel):
    """Generic message response"""
    message: str
    success: bool = True
    
class ChangePasswordRequest(BaseModel):
    current_password: str = Field(..., min_length=1)
    new_password: str = Field(..., min_length=8)
    
class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(..., min_length=8)


# ============================================================================
# Phone/OTP Authentication
# ============================================================================
@router.post("/phone/request-otp", response_model=MessageResponse)
async def request_otp(
    request: PhoneLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Request OTP for phone-based login.
    
    Generates a 6-digit OTP and stores it in Redis with 5-minute expiry.
    In production, sends OTP via SMS gateway.
    
    Rate limited to prevent abuse.
    """
    import random
    from app.core.redis import cache
    
    # Check rate limiting (max 3 OTP requests per phone per 15 minutes)
    rate_key = f"otp_rate:{request.phone_number}"
    rate_count = await cache.get(rate_key)
    
    if rate_count and int(rate_count) >= 3:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many OTP requests. Please wait 15 minutes."
        )
    
    # Generate 6-digit OTP
    otp = str(random.randint(100000, 999999))
    
    # Store OTP in Redis (5 min expiry)
    await cache.set(f"otp:{request.phone_number}", otp, ttl=300)
    
    # Update rate limit counter
    if rate_count:
        await cache.set(rate_key, str(int(rate_count) + 1), ttl=900)
    else:
        await cache.set(rate_key, "1", ttl=900)
    
    # In production, send OTP via SMS gateway (e.g., Twilio, Africa's Talking)
    # await send_sms(request.phone_number, f"Your EduBot verification code is: {otp}")
    
    response = {"message": "OTP sent to your phone", "success": True}
    
    # Include OTP in response only in debug mode (REMOVE IN PRODUCTION)
    if settings.DEBUG:
        response["debug_otp"] = otp
    
    return response


@router.post("/phone/verify", response_model=TokenResponse)
async def verify_otp(
    request: OTPVerifyRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify OTP and complete phone-based login.
    
    If user exists, returns tokens. If new user, creates account first.
    Updates last_active timestamp on successful login.
    """
    from app.core.redis import cache
    
    # Retrieve stored OTP
    stored_otp = await cache.get(f"otp:{request.phone_number}")
    
    if not stored_otp or stored_otp != request.otp:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired OTP"
        )
    
    # Delete used OTP
    await cache.delete(f"otp:{request.phone_number}")
    
    # Find existing user
    result = await db.execute(
        select(User).where(User.phone_number == request.phone_number)
    )
    user = result.scalar_one_or_none()
    
    # If user doesn't exist, create a basic account
    if not user:
        user = User(
            phone_number=request.phone_number,
            role=UserRole.STUDENT,
            is_verified=True,  # Phone verified via OTP
            is_active=True,
            subscription_tier=SubscriptionTier.FREE
        )
        db.add(user)
        await db.commit()
        await db.refresh(user)
    
    # Update last active
    user.last_active = datetime.utcnow()
    await db.commit()
    
    # Generate tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=refresh_token_expires
    )
    
    # Store refresh token in Redis for validation
    await cache.set(
        f"refresh_token:{user.id}",
        refresh_token,
        ttl=int(refresh_token_expires.total_seconds())
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        role=user.role.value
    )


# ============================================================================
# Email/Password Authentication
# ============================================================================
@router.post("/login", response_model=TokenResponse)
async def login(
    request: EmailLoginRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Login with email and password.
    
    Primarily used for admin dashboard and web portal access.
    Returns access and refresh tokens on success.
    """
    from app.core.redis import cache
    
    # Find user by email
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    user = result.scalar_one_or_none()
    
    # Validate credentials
    if not user or not user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not verify_password(request.password, user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Update last active
    user.last_active = datetime.utcnow()
    await db.commit()
    
    # Generate tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=refresh_token_expires
    )
    
    # Store refresh token
    await cache.set(
        f"refresh_token:{user.id}",
        refresh_token,
        ttl=int(refresh_token_expires.total_seconds())
    )
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        role=user.role.value
    )


@router.post("/register", response_model=TokenResponse)
async def register(
    request: RegisterRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Register new user with email and password.
    
    Creates a new user account and returns authentication tokens.
    Email must be unique across all users.
    """
    from app.core.redis import cache
    
    # Check if email already exists
    result = await db.execute(
        select(User).where(User.email == request.email)
    )
    if result.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered"
        )
    
    # Check phone number if provided
    if request.phone_number:
        result = await db.execute(
            select(User).where(User.phone_number == request.phone_number)
        )
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already registered"
            )
    
    # Create user
    user = User(
        email=request.email,
        password_hash=get_password_hash(request.password),
        phone_number=request.phone_number or f"pending_{secrets.token_hex(8)}",
        role=request.role,
        is_active=True,
        is_verified=False,  # Email verification pending
        subscription_tier=SubscriptionTier.FREE
    )
    
    db.add(user)
    await db.commit()
    await db.refresh(user)
    
    # Generate tokens
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        expires_delta=access_token_expires
    )
    refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=refresh_token_expires
    )
    
    # Store refresh token
    await cache.set(
        f"refresh_token:{user.id}",
        refresh_token,
        ttl=int(refresh_token_expires.total_seconds())
    )
    
    # TODO: Send verification email
    # await send_verification_email(user.email, user.id)
    
    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        role=user.role.value
    )


# ============================================================================
# Token Management
# ============================================================================
@router.post("/refresh", response_model=TokenResponse)
async def refresh_token(
    request: RefreshTokenRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Refresh access token using refresh token.
    
    Validates the refresh token, checks it hasn't been revoked,
    and issues new access and refresh tokens.
    
    The old refresh token is invalidated (rotation).
    """
    from app.core.redis import cache
    
    # Decode refresh token
    try:
        payload = decode_refresh_token(request.refresh_token)
        user_id = payload.get("sub")
        
        if not user_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid refresh token"
            )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    
    # Verify refresh token is still valid (not revoked)
    stored_token = await cache.get(f"refresh_token:{user_id}")
    if not stored_token or stored_token != request.refresh_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Refresh token has been revoked"
        )
    
    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found"
        )
    
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is deactivated"
        )
    
    # Generate new tokens (token rotation)
    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    refresh_token_expires = timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    
    new_access_token = create_access_token(
        data={"sub": str(user.id), "role": user.role.value},
        expires_delta=access_token_expires
    )
    new_refresh_token = create_refresh_token(
        data={"sub": str(user.id)},
        expires_delta=refresh_token_expires
    )
    
    # Replace old refresh token with new one
    await cache.set(
        f"refresh_token:{user.id}",
        new_refresh_token,
        ttl=int(refresh_token_expires.total_seconds())
    )
    
    # Update last active
    user.last_active = datetime.utcnow()
    await db.commit()
    
    return TokenResponse(
        access_token=new_access_token,
        refresh_token=new_refresh_token,
        token_type="bearer",
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user_id=str(user.id),
        role=user.role.value
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Logout current user.
    
    Revokes the refresh token, effectively logging out the user.
    The access token will remain valid until it expires, but
    cannot be refreshed.
    
    For immediate invalidation, implement token blacklisting.
    """
    from app.core.redis import cache
    
    # Delete refresh token from Redis (revoke it)
    await cache.delete(f"refresh_token:{current_user.id}")
    
    # Optionally: Add current access token to blacklist
    # This requires checking blacklist on every request
    # await cache.set(f"blacklist:{access_token}", "1", ttl=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    
    return MessageResponse(
        message="Successfully logged out",
        success=True
    )


# ============================================================================
# Current User Profile
# ============================================================================
@router.get("/me", response_model=UserProfileResponse)
async def get_current_user_profile(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Get current authenticated user's profile.
    
    Returns complete user information including:
    - Basic user data (phone, email, role)
    - Subscription information
    - Student profile (if applicable)
    
    Requires valid access token in Authorization header.
    """
    # Build response
    profile = {
        "id": current_user.id,
        "phone_number": current_user.phone_number,
        "email": current_user.email,
        "role": current_user.role.value,
        "subscription_tier": current_user.subscription_tier.value,
        "subscription_expires_at": current_user.subscription_expires_at,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at,
        "last_active": current_user.last_active,
        "student": None
    }
    
    # Get student profile if exists
    result = await db.execute(
        select(Student).where(Student.user_id == current_user.id)
    )
    student = result.scalar_one_or_none()
    
    if student:
        profile["student"] = {
            "id": str(student.id),
            "first_name": student.first_name,
            "last_name": student.last_name,
            "full_name": student.full_name,
            "grade": student.grade,
            "education_level": student.education_level.value,
            "school_name": student.school_name,
            "district": student.district,
            "province": student.province,
            "subjects": student.subjects,
            "total_xp": student.total_xp,
            "level": student.level,
            "daily_goal_minutes": student.daily_goal_minutes,
            "preferred_language": student.preferred_language
        }
    
    return profile


@router.put("/me", response_model=UserProfileResponse)
async def update_current_user_profile(
    email: Optional[str] = None,
    phone_number: Optional[str] = None,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Update current user's profile.
    
    Allows updating email and phone number.
    Email changes may require re-verification.
    """
    if email and email != current_user.email:
        # Check if email is already taken
        result = await db.execute(select(User).where(User.email == email))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email already in use"
            )
        current_user.email = email
        current_user.is_verified = False  # Require re-verification
    
    if phone_number and phone_number != current_user.phone_number:
        # Check if phone is already taken
        result = await db.execute(select(User).where(User.phone_number == phone_number))
        if result.scalar_one_or_none():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Phone number already in use"
            )
        current_user.phone_number = phone_number
    
    await db.commit()
    await db.refresh(current_user)
    
    # Return updated profile
    return await get_current_user_profile(current_user, db)


# ============================================================================
# Password Management
# ============================================================================
@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    payload: ChangePasswordRequest,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Change current user's password.
    """
    if not current_user.password_hash:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No password set. Use forgot password to set one."
        )

    if not verify_password(payload.current_password, current_user.password_hash):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Current password is incorrect"
        )

    current_user.password_hash = get_password_hash(payload.new_password)
    await db.commit()

    return MessageResponse(
        message="Password changed successfully",
        success=True
    )

@router.post("/forgot-password", response_model=MessageResponse)
async def forgot_password(
    email: EmailStr,
    db: AsyncSession = Depends(get_db)
):
    """
    Request password reset.
    
    Sends a password reset link to the user's email.
    Link expires in 1 hour.
    """
    from app.core.redis import cache
    
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()
    
    # Always return success to prevent email enumeration
    if not user:
        return MessageResponse(
            message="If an account exists with this email, a reset link has been sent.",
            success=True
        )
    
    # Generate reset token
    reset_token = secrets.token_urlsafe(32)
    
    # Store reset token (1 hour expiry)
    await cache.set(f"password_reset:{reset_token}", str(user.id), ttl=3600)
    
    # TODO: Send reset email
    # reset_url = f"{settings.FRONTEND_URL}/reset-password?token={reset_token}"
    # await send_password_reset_email(user.email, reset_url)
    
    return MessageResponse(
        message="If an account exists with this email, a reset link has been sent.",
        success=True
    )


@router.post("/reset-password", response_model=MessageResponse)
async def reset_password(
    payload: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db),
):
    """
    Reset password using reset token.
    """
    from app.core.redis import cache

    # Validate reset token
    user_id = await cache.get(f"password_reset:{payload.token}")

    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token"
        )

    # Get user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )

    # Update password
    user.password_hash = get_password_hash(payload.new_password)
    await db.commit()

    # Cleanup
    await cache.delete(f"password_reset:{payload.token}")
    await cache.delete(f"refresh_token:{user.id}")

    return MessageResponse(
        message="Password reset successfully. Please login with your new password.",
        success=True
    )



# ============================================================================
# Email Verification
# ============================================================================
@router.post("/send-verification", response_model=MessageResponse)
async def send_verification_email(
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_db)
):
    """
    Send email verification link.
    
    Sends a verification link to the user's registered email.
    """
    from app.core.redis import cache
    
    if not current_user.email:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No email address registered"
        )
    
    if current_user.is_verified:
        return MessageResponse(
            message="Email is already verified",
            success=True
        )
    
    # Generate verification token
    verification_token = secrets.token_urlsafe(32)
    
    # Store token (24 hour expiry)
    await cache.set(
        f"email_verify:{verification_token}",
        str(current_user.id),
        ttl=86400
    )
    
    # TODO: Send verification email
    # verify_url = f"{settings.FRONTEND_URL}/verify-email?token={verification_token}"
    # await send_verification_email(current_user.email, verify_url)
    
    return MessageResponse(
        message="Verification email sent",
        success=True
    )


@router.post("/verify-email", response_model=MessageResponse)
async def verify_email(
    token: str,
    db: AsyncSession = Depends(get_db)
):
    """
    Verify email using verification token.
    """
    from app.core.redis import cache
    
    # Validate token
    user_id = await cache.get(f"email_verify:{token}")
    
    if not user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token"
        )
    
    # Update user
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="User not found"
        )
    
    user.is_verified = True
    await db.commit()
    
    # Delete used token
    await cache.delete(f"email_verify:{token}")
    
    return MessageResponse(
        message="Email verified successfully",
        success=True
    )