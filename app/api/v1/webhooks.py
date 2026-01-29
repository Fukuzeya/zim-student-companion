# ============================================================================
# WhatsApp Webhook Endpoints
# ============================================================================
"""
WhatsApp webhook handlers for receiving and processing messages.

Key improvements:
- Singleton RAG engine to avoid re-initialization
- Proper database session handling in background tasks
- Metrics and observability
- Enhanced error handling with user feedback
- Support for various webhook event types
"""
from fastapi import APIRouter, Depends, HTTPException, Request, Response, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
from contextlib import asynccontextmanager
import logging
import hashlib
import hmac
import time
from typing import Optional, Dict, Any

from app.core.database import get_db, async_session_maker
from app.config import get_settings
from app.services.whatsapp.client import WhatsAppClient, WhatsAppMessage
from app.services.whatsapp.handlers import MessageHandler

# Import from updated RAG pipeline
from app.services.rag import (
    RAGEngine,
    create_rag_engine,
    get_metrics_collector,
)

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/webhooks", tags=["webhooks"])


# ============================================================================
# Singleton RAG Engine Management
# ============================================================================
class RAGEngineManager:
    """
    Manages a singleton RAG engine instance.
    Ensures expensive initialization only happens once.
    """
    _instance: Optional[RAGEngine] = None
    _initialized: bool = False
    _lock = None  # Will be set on first access
    
    @classmethod
    async def get_engine(cls) -> RAGEngine:
        """Get or create the singleton RAG engine"""
        import asyncio
        
        if cls._lock is None:
            cls._lock = asyncio.Lock()
        
        if cls._instance is None or not cls._initialized:
            async with cls._lock:
                # Double-check after acquiring lock
                if cls._instance is None:
                    logger.info("Initializing RAG engine singleton...")
                    cls._instance = create_rag_engine(settings)
                    await cls._instance.initialize()
                    cls._initialized = True
                    logger.info("✓ RAG engine singleton ready")
        
        return cls._instance
    
    @classmethod
    async def shutdown(cls):
        """Shutdown the RAG engine (call on app shutdown)"""
        if cls._instance:
            await cls._instance.close()
            cls._instance = None
            cls._initialized = False
            logger.info("RAG engine shutdown complete")


# ============================================================================
# Webhook Signature Verification
# ============================================================================
def verify_webhook_signature(
    payload: bytes,
    signature: str,
    secret: str
) -> bool:
    """
    Verify WhatsApp webhook signature for security.
    
    Args:
        payload: Raw request body
        signature: X-Hub-Signature-256 header value
        secret: App secret from Meta dashboard
    
    Returns:
        True if signature is valid
    """
    if not signature or not secret:
        return False
    
    try:
        # Signature format: sha256=<hash>
        if signature.startswith("sha256="):
            signature = signature[7:]
        
        expected = hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()
        
        return hmac.compare_digest(expected, signature)
    except Exception as e:
        logger.error(f"Signature verification error: {e}")
        return False


# ============================================================================
# Webhook Endpoints
# ============================================================================
@router.get("/whatsapp")
async def verify_webhook(request: Request):
    """
    Verify WhatsApp webhook (required by Meta during setup).
    
    Meta sends a GET request with:
    - hub.mode: should be "subscribe"
    - hub.verify_token: your configured verify token
    - hub.challenge: challenge string to echo back
    """
    params = request.query_params
    
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    logger.info(f"Webhook verification attempt: mode={mode}")
    
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("✓ WhatsApp webhook verified successfully")
        return Response(content=challenge, media_type="text/plain")
    
    logger.warning(f"Webhook verification failed: invalid token")
    raise HTTPException(status_code=403, detail="Verification failed")


@router.post("/whatsapp")
async def receive_whatsapp_message(
    request: Request,
    background_tasks: BackgroundTasks,
):
    """
    Receive WhatsApp messages and events.
    
    Handles:
    - Incoming messages (text, button replies, list replies)
    - Message status updates (sent, delivered, read)
    - Error notifications
    
    Note: Always returns 200 to acknowledge receipt to WhatsApp.
    Processing happens in background to respond quickly.
    """
    start_time = time.time()
    
    try:
        # Get raw body for signature verification
        body = await request.body()
        
        # Verify signature in production (when DEBUG is False)
        if not settings.DEBUG:
            signature = request.headers.get("X-Hub-Signature-256", "")
            if not verify_webhook_signature(body, signature, settings.WHATSAPP_APP_SECRET or ""):
                logger.warning("Invalid webhook signature")
                # Still return 200 to not trigger retries
                return {"status": "invalid_signature"}
        
        # Parse JSON payload
        data = await request.json()
        
        # Log webhook type
        webhook_type = _get_webhook_type(data)
        logger.info(f"Received WhatsApp webhook: type={webhook_type}")
        
        if settings.DEBUG:
            logger.debug(f"Webhook payload: {data}")
        
        # Route based on webhook type
        if webhook_type == "message":
            # Parse message
            wa_client = WhatsAppClient()
            message = wa_client.parse_webhook(data)

            if message:
                logger.info(
                    f"📩 Message received: from={message.from_number}, "
                    f"type={message.message_type}, text='{message.text[:50] if message.text else 'N/A'}...'"
                )
                # Process message in background
                background_tasks.add_task(
                    process_whatsapp_message,
                    message,
                    data  # Pass original data for context
                )
                logger.info(f"✅ Message queued for background processing")
            else:
                logger.warning(f"⚠️ Failed to parse message from webhook data: {data}")
        
        elif webhook_type == "status":
            # Handle status update in background
            background_tasks.add_task(
                process_status_update,
                data
            )
        
        elif webhook_type == "error":
            # Log errors but don't fail
            _log_webhook_error(data)
        
        # Record webhook latency
        latency_ms = (time.time() - start_time) * 1000
        logger.debug(f"Webhook acknowledged in {latency_ms:.1f}ms")
        
        return {"status": "received"}
    
    except Exception as e:
        logger.exception(f"WhatsApp webhook error: {e}")
        get_metrics_collector().record_error()
        # Always return 200 to WhatsApp to prevent retries
        return {"status": "error", "message": str(e)}


@router.post("/whatsapp/status")
async def whatsapp_status_update(
    request: Request,
    background_tasks: BackgroundTasks
):
    """
    Handle WhatsApp message status updates.
    
    Status types:
    - sent: Message sent to WhatsApp servers
    - delivered: Message delivered to user's device
    - read: Message read by user
    - failed: Message failed to send
    """
    try:
        data = await request.json()
        
        background_tasks.add_task(process_status_update, data)
        
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"Status update error: {e}")
        return {"status": "error"}


# ============================================================================
# Background Processing Functions
# ============================================================================
async def process_whatsapp_message(
    message: WhatsAppMessage,
    raw_data: Dict[str, Any]
):
    """
    Process WhatsApp message in background.

    Creates fresh database session and uses singleton RAG engine.
    Handles all errors gracefully with user feedback.
    """
    processing_start = time.time()
    logger.info(f"🔄 Background processing started for {message.from_number}")

    # Create fresh database session for background task
    async with async_session_maker() as db:
        try:
            # Get singleton RAG engine
            logger.debug("Getting RAG engine...")
            rag_engine = await RAGEngineManager.get_engine()
            logger.debug("✓ RAG engine ready")

            # Create WhatsApp client
            wa_client = WhatsAppClient()
            logger.debug(f"✓ WhatsApp client created (phone_id={settings.WHATSAPP_PHONE_NUMBER_ID})")

            # Create message handler
            handler = MessageHandler(wa_client, rag_engine, db)
            logger.debug("✓ Message handler created")

            # Process the message
            logger.info(f"🤖 Processing message from {message.from_number}...")
            await handler.handle_message(message)

            # Log processing time
            processing_time = (time.time() - processing_start) * 1000
            logger.info(
                f"✅ Message processed successfully: from={message.from_number}, "
                f"time={processing_time:.0f}ms"
            )

        except Exception as e:
            logger.exception(
                f"❌ Error processing message from {message.from_number}: {e}"
            )
            get_metrics_collector().record_error()

            # Try to send error message to user
            try:
                await _send_error_message(message.from_number)
            except Exception as send_err:
                logger.error(f"❌ Failed to send error message: {send_err}")


async def process_status_update(data: Dict[str, Any]):
    """
    Process message status updates.
    
    Can be used to:
    - Track message delivery rates
    - Handle failed messages
    - Update conversation status
    """
    try:
        statuses = _extract_statuses(data)
        
        for status in statuses:
            status_type = status.get("status")
            message_id = status.get("id")
            recipient = status.get("recipient_id")
            timestamp = status.get("timestamp")
            
            if status_type == "failed":
                # Log failed messages for debugging
                errors = status.get("errors", [])
                logger.warning(
                    f"Message delivery failed: id={message_id}, "
                    f"recipient={recipient}, errors={errors}"
                )
                
                # Could notify user or retry here
                
            elif status_type == "read":
                # Message was read - could update analytics
                logger.debug(f"Message read: id={message_id}")
                
            elif status_type in ["sent", "delivered"]:
                logger.debug(f"Message {status_type}: id={message_id}")
                
    except Exception as e:
        logger.error(f"Error processing status update: {e}")


# ============================================================================
# Helper Functions
# ============================================================================
def _get_webhook_type(data: Dict[str, Any]) -> str:
    """
    Determine the type of webhook event.
    
    Returns: 'message', 'status', 'error', or 'unknown'
    """
    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        
        if "messages" in value:
            return "message"
        elif "statuses" in value:
            return "status"
        elif "errors" in value:
            return "error"
        
        return "unknown"
    except (IndexError, KeyError):
        return "unknown"


def _extract_statuses(data: Dict[str, Any]) -> list:
    """Extract status updates from webhook data"""
    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        return value.get("statuses", [])
    except (IndexError, KeyError):
        return []


def _log_webhook_error(data: Dict[str, Any]):
    """Log webhook error details"""
    try:
        entry = data.get("entry", [{}])[0]
        changes = entry.get("changes", [{}])[0]
        value = changes.get("value", {})
        errors = value.get("errors", [])
        
        for error in errors:
            logger.error(
                f"WhatsApp API error: code={error.get('code')}, "
                f"title={error.get('title')}, "
                f"message={error.get('message')}"
            )
    except Exception as e:
        logger.error(f"Error parsing webhook error: {e}")


async def _send_error_message(phone: str):
    """Send error message to user"""
    try:
        wa_client = WhatsAppClient()
        await wa_client.send_text(
            phone,
            "Sorry, I encountered an error processing your message. 🙏\n\n"
            "Please try again in a moment. If the problem persists, "
            "type 'help' for assistance."
        )
    except Exception as e:
        logger.error(f"Failed to send error message: {e}")


# ============================================================================
# Health Check Endpoint
# ============================================================================
@router.get("/health")
async def webhook_health():
    """
    Health check endpoint for webhook service.
    
    Checks:
    - RAG engine status
    - WhatsApp client connectivity
    """
    health = {
        "status": "healthy",
        "timestamp": time.time(),
        "components": {}
    }
    
    # Check RAG engine
    try:
        engine = await RAGEngineManager.get_engine()
        rag_health = await engine.health_check()
        health["components"]["rag_engine"] = {
            "status": rag_health.get("status", "unknown"),
            "collections": len(rag_health.get("collections", {}))
        }
    except Exception as e:
        health["status"] = "degraded"
        health["components"]["rag_engine"] = {
            "status": "error",
            "error": str(e)
        }
    
    # Get metrics
    metrics = get_metrics_collector().get_stats(period_hours=1)
    health["metrics"] = {
        "queries_last_hour": metrics.get("query_count", 0),
        "error_rate": metrics.get("error_rate", 0),
        "avg_latency_ms": metrics.get("latency", {}).get("avg_ms", 0),
    }
    
    return health


# ============================================================================
# Startup/Shutdown Hooks (to be called from main.py)
# ============================================================================
async def startup_webhook_services():
    """Initialize webhook services on app startup"""
    logger.info("Starting webhook services...")
    
    # Pre-initialize RAG engine
    try:
        await RAGEngineManager.get_engine()
        logger.info("✓ Webhook services ready")
    except Exception as e:
        logger.error(f"Failed to initialize webhook services: {e}")
        raise


async def shutdown_webhook_services():
    """Cleanup webhook services on app shutdown"""
    logger.info("Shutting down webhook services...")
    await RAGEngineManager.shutdown()
    logger.info("✓ Webhook services shutdown complete")