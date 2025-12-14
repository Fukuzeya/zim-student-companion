# ============================================================================
# Custom Exceptions
# ============================================================================
from typing import Optional

class ZSCException(Exception):
    """Base exception for Zim Student Companion"""
    def __init__(
        self,
        detail: str,
        status_code: int = 400,
        error_code: Optional[str] = None
    ):
        self.detail = detail
        self.status_code = status_code
        self.error_code = error_code or "ZSC_ERROR"
        super().__init__(self.detail)

class RateLimitExceeded(ZSCException):
    def __init__(self, remaining_time: int = 0):
        super().__init__(
            detail=f"Daily question limit reached. Upgrade for more!",
            status_code=429,
            error_code="RATE_LIMIT_EXCEEDED"
        )
        self.remaining_time = remaining_time

class SubscriptionRequired(ZSCException):
    def __init__(self, feature: str):
        super().__init__(
            detail=f"'{feature}' requires a premium subscription",
            status_code=403,
            error_code="SUBSCRIPTION_REQUIRED"
        )

class DocumentNotFound(ZSCException):
    def __init__(self, doc_id: str):
        super().__init__(
            detail=f"Document not found: {doc_id}",
            status_code=404,
            error_code="DOCUMENT_NOT_FOUND"
        )

class InvalidAnswer(ZSCException):
    def __init__(self, message: str = "Invalid answer format"):
        super().__init__(
            detail=message,
            status_code=400,
            error_code="INVALID_ANSWER"
        )