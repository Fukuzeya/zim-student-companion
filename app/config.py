import secrets
import hashlib
from pydantic_settings import BaseSettings
from pydantic import Field, model_validator
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Zim Student Companion"
    DEBUG: bool = True  # CHANGED: Default to True for development
    SECRET_KEY: str = "dev-secret-key-change-in-production"  # Default for dev
    API_V1_PREFIX: str = "/v1"
    
    # Database - with defaults for local Docker setup
    DATABASE_URL: str = "postgresql://postgres:12345@localhost:5432/zsc_db"
    REDIS_URL: str = "redis://localhost:6379/0"
    
    # Gemini AI - Optional with empty default
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    GEMINI_EMBEDDING_MODEL: str = "text-embedding-004"
    
    # Qdrant
    QDRANT_HOST: str = "localhost"
    QDRANT_PORT: int = 6333
    QDRANT_COLLECTION: str = "zimsec_documents"
    
    # WhatsApp - Optional with empty defaults
    WHATSAPP_TOKEN: str = Field(..., env="WHATSAPP_TOKEN")
    WHATSAPP_PHONE_NUMBER_ID: str = Field(..., env="WHATSAPP_PHONE_NUMBER_ID")
    WHATSAPP_VERIFY_TOKEN: str = "RaphaelIsAwesome"
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v24.0"
    WHATSAPP_BUSINESS_ACCOUNT_ID: Optional[str] = Field(..., env="WHATSAPP_BUSINESS_ACCOUNT_ID")
    WHATSAPP_APP_SECRET : Optional[str] = Field(None, env="WHATSAPP_APP_SECRET")
    
    # Paynow - Optional with empty defaults
    PAYNOW_INTEGRATION_ID: str = ""
    PAYNOW_INTEGRATION_KEY: str = ""
    PAYNOW_RESULT_URL: str = "http://localhost:8000/api/v1/payments/webhook/paynow"
    PAYNOW_RETURN_URL: str = "http://localhost:8000/payment/success"
    
    # JWT
    JWT_ALGORITHM: str = "HS256"
    # Token expiration times
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30  # 30 minutes
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7  # 7 days
    # Secret key for JWT signing (generate with: openssl rand -hex 32)
    # If not set, will be derived from SECRET_KEY for consistency across restarts
    JWT_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Secret key for JWT access tokens. If not set, derived from SECRET_KEY."
    )

    # Separate secret for refresh tokens (additional security layer)
    # If not set, will be derived from SECRET_KEY for consistency across restarts
    REFRESH_SECRET_KEY: Optional[str] = Field(
        default=None,
        description="Secret key for JWT refresh tokens. If not set, derived from SECRET_KEY."
    )

    @model_validator(mode='after')
    def derive_jwt_secrets(self) -> 'Settings':
        """
        Derive JWT secrets from SECRET_KEY if not explicitly set.
        This ensures tokens remain valid across application restarts.

        IMPORTANT: In production, set SECRET_KEY to a strong random value in .env
        Generate with: openssl rand -hex 32
        """
        if not self.JWT_SECRET_KEY:
            # Derive JWT secret from SECRET_KEY using HMAC-SHA256
            self.JWT_SECRET_KEY = hashlib.sha256(
                f"{self.SECRET_KEY}:jwt:access".encode()
            ).hexdigest()

        if not self.REFRESH_SECRET_KEY:
            # Derive refresh secret from SECRET_KEY using HMAC-SHA256
            self.REFRESH_SECRET_KEY = hashlib.sha256(
                f"{self.SECRET_KEY}:jwt:refresh".encode()
            ).hexdigest()

        # Warn if using default SECRET_KEY in non-debug mode
        if not self.DEBUG and self.SECRET_KEY == "dev-secret-key-change-in-production":
            import warnings
            warnings.warn(
                "WARNING: Using default SECRET_KEY in production! "
                "Set a secure SECRET_KEY in your .env file. "
                "Generate one with: openssl rand -hex 32",
                UserWarning
            )

        return self

    # Password requirements
    MIN_PASSWORD_LENGTH: int = 8
    
    # Rate Limits
    FREE_DAILY_QUESTIONS: int = 5
    BASIC_DAILY_QUESTIONS: int = 50
    PREMIUM_DAILY_QUESTIONS: int = 1000
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # Ignore extra fields in .env

@lru_cache()
def get_settings() -> Settings:
    return Settings()