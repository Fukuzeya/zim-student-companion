from pydantic_settings import BaseSettings
from pydantic import Field
from functools import lru_cache
from typing import Optional

class Settings(BaseSettings):
    # Application
    APP_NAME: str = "Zim Student Companion"
    DEBUG: bool = True  # CHANGED: Default to True for development
    SECRET_KEY: str = "dev-secret-key-change-in-production"  # Default for dev
    API_V1_PREFIX: str = "/api/v1"
    
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
    WHATSAPP_TOKEN: str = ""
    WHATSAPP_PHONE_NUMBER_ID: str = ""
    WHATSAPP_VERIFY_TOKEN: str = "dev-verify-token"
    WHATSAPP_API_URL: str = "https://graph.facebook.com/v18.0"
    WHATSAPP_BUSINESS_ACCOUNT_ID: str = Field(..., env="WHATSAPP_BUSINESS_ACCOUNT_ID")
    
    # Paynow - Optional with empty defaults
    PAYNOW_INTEGRATION_ID: str = ""
    PAYNOW_INTEGRATION_KEY: str = ""
    PAYNOW_RESULT_URL: str = "http://localhost:8000/api/v1/payments/webhook/paynow"
    PAYNOW_RETURN_URL: str = "http://localhost:8000/payment/success"
    
    # JWT
    JWT_SECRET_KEY: str = "dev-jwt-secret-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    
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
