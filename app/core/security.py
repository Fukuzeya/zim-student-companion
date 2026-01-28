# ============================================================================
# Security Module
# ============================================================================
"""
Security utilities for authentication and authorization.

Provides:
- Password hashing and verification (bcrypt)
- JWT access token creation and validation
- JWT refresh token creation and validation
- Current user dependency for protected routes
"""
from datetime import datetime, timedelta
from typing import Optional, Any, Dict
from uuid import UUID

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.config import get_settings
from app.models.user import User

settings = get_settings()

# ============================================================================
# Password Hashing
# ============================================================================
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verify a plain password against a hashed password.
    
    Args:
        plain_password: The plain text password to verify
        hashed_password: The bcrypt hashed password to compare against
        
    Returns:
        True if password matches, False otherwise
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Hash a password using bcrypt.
    
    Args:
        password: Plain text password to hash
        
    Returns:
        Bcrypt hashed password string
    """
    return pwd_context.hash(password)


# ============================================================================
# JWT Token Configuration
# ============================================================================
# Token types for different purposes
ACCESS_TOKEN_TYPE = "access"
REFRESH_TOKEN_TYPE = "refresh"

# Security scheme for API documentation
security_scheme = HTTPBearer(auto_error=False)


# ============================================================================
# Access Token Functions
# ============================================================================
def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT access token.
    
    Args:
        data: Dictionary of claims to encode in the token
              Should include 'sub' (subject/user_id) at minimum
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT token string
    """
    to_encode = data.copy()
    
    # Set expiration
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": ACCESS_TOKEN_TYPE
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.JWT_SECRET_KEY,  # Use dedicated JWT secret
        algorithm=settings.JWT_ALGORITHM
    )

    return encoded_jwt


def decode_access_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT access token.

    Args:
        token: The JWT token string to decode

    Returns:
        Dictionary of decoded claims

    Raises:
        JWTError: If token is invalid or expired
    """
    payload = jwt.decode(
        token,
        settings.JWT_SECRET_KEY,  # Use dedicated JWT secret
        algorithms=[settings.JWT_ALGORITHM]
    )
    
    # Verify token type
    if payload.get("type") != ACCESS_TOKEN_TYPE:
        raise JWTError("Invalid token type")
    
    return payload


# ============================================================================
# Refresh Token Functions
# ============================================================================
def create_refresh_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    """
    Create a JWT refresh token.
    
    Refresh tokens have longer expiration and are used to obtain
    new access tokens without re-authentication.
    
    Args:
        data: Dictionary of claims (typically just 'sub' for user_id)
        expires_delta: Optional custom expiration time
        
    Returns:
        Encoded JWT refresh token string
    """
    to_encode = data.copy()
    
    # Set expiration (longer than access token)
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(
            days=settings.REFRESH_TOKEN_EXPIRE_DAYS
        )
    
    to_encode.update({
        "exp": expire,
        "iat": datetime.utcnow(),
        "type": REFRESH_TOKEN_TYPE
    })
    
    encoded_jwt = jwt.encode(
        to_encode,
        settings.REFRESH_SECRET_KEY,  # Use different secret for refresh tokens
        algorithm=settings.JWT_ALGORITHM
    )
    
    return encoded_jwt


def decode_refresh_token(token: str) -> Dict[str, Any]:
    """
    Decode and validate a JWT refresh token.
    
    Args:
        token: The refresh token string to decode
        
    Returns:
        Dictionary of decoded claims
        
    Raises:
        JWTError: If token is invalid or expired
    """
    payload = jwt.decode(
        token,
        settings.REFRESH_SECRET_KEY,
        algorithms=[settings.JWT_ALGORITHM]
    )
    
    # Verify token type
    if payload.get("type") != REFRESH_TOKEN_TYPE:
        raise JWTError("Invalid token type")
    
    return payload


# ============================================================================
# Authentication Dependencies
# ============================================================================
async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
    db: AsyncSession = Depends(None)  # Will be overridden
) -> User:
    """
    Dependency to get the current authenticated user from JWT token.
    
    Extracts the Bearer token from Authorization header, validates it,
    and returns the associated user.
    
    Args:
        credentials: HTTP Authorization credentials (Bearer token)
        db: Database session
        
    Returns:
        User object for the authenticated user
        
    Raises:
        HTTPException: 401 if token is missing, invalid, or user not found
    """
    from app.models.user import User
    from app.core.database import get_db
    
    # Get db session if not provided
    if db is None:
        async for session in get_db():
            db = session
            break
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    result = await db.execute(
        select(User).where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    
    if user is None:
        raise credentials_exception
    
    return user


async def get_current_active_user(
    credentials: HTTPAuthorizationCredentials = Depends(security_scheme),
) -> "User":
    """
    Dependency to get the current active authenticated user.
    
    Extends get_current_user to also verify the user account is active.
    
    Args:
        credentials: HTTP Authorization credentials
        
    Returns:
        Active User object
        
    Raises:
        HTTPException: 401 if not authenticated, 403 if account inactive
    """
    from app.models.user import User
    from app.core.database import get_db
    
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    if not credentials:
        raise credentials_exception
    
    try:
        token = credentials.credentials
        payload = decode_access_token(token)
        user_id: str = payload.get("sub")
        
        if user_id is None:
            raise credentials_exception
            
    except JWTError:
        raise credentials_exception
    
    # Get user from database
    async for db in get_db():
        result = await db.execute(
            select(User).where(User.id == user_id)
        )
        user = result.scalar_one_or_none()
        
        if user is None:
            raise credentials_exception
        
        if not user.is_active:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Account is deactivated"
            )
        
        return user


def get_optional_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
) -> Optional["User"]:
    """
    Dependency that optionally returns the current user.
    
    Unlike get_current_user, this doesn't raise an exception if
    no valid token is provided. Useful for endpoints that have
    different behavior for authenticated vs anonymous users.
    
    Returns:
        User object if authenticated, None otherwise
    """
    if not credentials:
        return None
    
    try:
        # This is a simplified version - in production, 
        # you'd want to do the full validation
        return None  # Implement as needed
    except Exception:
        return None


# ============================================================================
# Permission Checking Utilities
# ============================================================================
def require_role(*allowed_roles: str):
    """
    Dependency factory for role-based access control.
    
    Usage:
        @router.get("/admin-only")
        async def admin_endpoint(user: User = Depends(require_role("admin"))):
            ...
    
    Args:
        allowed_roles: Role names that are allowed to access the endpoint
        
    Returns:
        Dependency function that validates user role
    """
    async def role_checker(
        user: "User" = Depends(get_current_active_user)
    ) -> "User":
        if user.role.value not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access denied. Required role: {', '.join(allowed_roles)}"
            )
        return user
    
    return role_checker


def require_subscription(*allowed_tiers: str):
    """
    Dependency factory for subscription-based access control.
    
    Usage:
        @router.get("/premium-feature")
        async def premium_endpoint(user: User = Depends(require_subscription("premium", "family"))):
            ...
    
    Args:
        allowed_tiers: Subscription tiers allowed to access the endpoint
        
    Returns:
        Dependency function that validates subscription
    """
    async def subscription_checker(
        user: "User" = Depends(get_current_active_user)
    ) -> "User":
        from datetime import datetime
        
        # Check if subscription is active
        if user.subscription_expires_at and user.subscription_expires_at < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Subscription has expired"
            )
        
        if user.subscription_tier.value not in allowed_tiers:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"This feature requires: {', '.join(allowed_tiers)} subscription"
            )
        
        return user
    
    return subscription_checker


# ============================================================================
# Token Blacklist Utilities (Optional)
# ============================================================================
async def is_token_blacklisted(token: str) -> bool:
    """
    Check if a token has been blacklisted (revoked).
    
    Used for immediate token invalidation on logout.
    Requires Redis for storage.
    
    Args:
        token: The JWT token to check
        
    Returns:
        True if token is blacklisted, False otherwise
    """
    from app.core.redis import cache
    
    # Create a hash of the token for storage efficiency
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
    
    result = await cache.get(f"blacklist:{token_hash}")
    return result is not None


async def blacklist_token(token: str, expires_in: int) -> None:
    """
    Add a token to the blacklist.
    
    Args:
        token: The JWT token to blacklist
        expires_in: Seconds until the blacklist entry expires
                   (should match token expiration)
    """
    from app.core.redis import cache
    
    import hashlib
    token_hash = hashlib.sha256(token.encode()).hexdigest()[:16]
    
    await cache.set(f"blacklist:{token_hash}", "1", ttl=expires_in)