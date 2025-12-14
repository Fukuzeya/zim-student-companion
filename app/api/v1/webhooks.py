# ============================================================================
# WhatsApp Webhook Endpoints
# ============================================================================
from fastapi import APIRouter, Depends, HTTPException, Request, Response, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession
import logging

from app.core.database import get_db
from app.config import get_settings
from app.services.whatsapp.client import WhatsAppClient
from app.services.whatsapp.handlers import MessageHandler
from app.services.rag.rag_engine import RAGEngine
from app.api.deps import get_rag_engine

settings = get_settings()
logger = logging.getLogger(__name__)
router = APIRouter(prefix="/webhooks", tags=["webhooks"])

@router.get("/whatsapp")
async def verify_webhook(
    request: Request
):
    """Verify WhatsApp webhook (required by Meta)"""
    params = request.query_params
    
    mode = params.get("hub.mode")
    token = params.get("hub.verify_token")
    challenge = params.get("hub.challenge")
    
    if mode == "subscribe" and token == settings.WHATSAPP_VERIFY_TOKEN:
        logger.info("WhatsApp webhook verified")
        return Response(content=challenge, media_type="text/plain")
    
    raise HTTPException(status_code=403, detail="Verification failed")

@router.post("/whatsapp")
async def receive_whatsapp_message(
    request: Request,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db)
):
    """Receive WhatsApp messages"""
    try:
        data = await request.json()
        logger.info(f"Received WhatsApp webhook: {data}")
        
        # Parse the webhook
        wa_client = WhatsAppClient()
        message = wa_client.parse_webhook(data)
        
        if message:
            # Process message in background to respond quickly
            background_tasks.add_task(
                process_whatsapp_message,
                message,
                db
            )
        
        return {"status": "received"}
    
    except Exception as e:
        logger.error(f"WhatsApp webhook error: {e}")
        # Always return 200 to WhatsApp
        return {"status": "error", "message": str(e)}

async def process_whatsapp_message(message, db: AsyncSession):
    """Process WhatsApp message in background"""
    try:
        from app.services.whatsapp.client import WhatsAppClient
        from app.services.whatsapp.handlers import MessageHandler
        from app.services.rag.vector_store import VectorStore
        from app.services.rag.rag_engine import RAGEngine
        
        wa_client = WhatsAppClient()
        vector_store = VectorStore(settings)
        rag_engine = RAGEngine(vector_store, settings)
        
        handler = MessageHandler(wa_client, rag_engine, db)
        await handler.handle_message(message)
        
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        # Try to send error message
        try:
            wa_client = WhatsAppClient()
            await wa_client.send_text(
                message.from_number,
                "Sorry, I encountered an error. Please try again in a moment. 🙏"
            )
        except:
            pass

@router.post("/whatsapp/status")
async def whatsapp_status_update(request: Request):
    """Handle WhatsApp message status updates"""
    try:
        data = await request.json()
        logger.debug(f"WhatsApp status update: {data}")
        return {"status": "received"}
    except Exception as e:
        logger.error(f"Status update error: {e}")
        return {"status": "error"}