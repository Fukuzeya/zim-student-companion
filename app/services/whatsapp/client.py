# ============================================================================
# WhatsApp API Client
# ============================================================================
import httpx
from typing import Optional, Dict, Any, List
from dataclasses import dataclass
from enum import Enum
import logging

from app.config import get_settings

settings = get_settings()
logger = logging.getLogger(__name__)

class MessageType(str, Enum):
    TEXT = "text"
    INTERACTIVE = "interactive"
    TEMPLATE = "template"
    IMAGE = "image"
    DOCUMENT = "document"

@dataclass
class WhatsAppMessage:
    """Represents an incoming WhatsApp message"""
    message_id: str
    from_number: str
    timestamp: str
    message_type: str
    text: Optional[str] = None
    button_reply: Optional[Dict] = None
    list_reply: Optional[Dict] = None
    interactive_reply: Optional[Dict] = None

class WhatsAppClient:
    """WhatsApp Cloud API Client"""
    
    def __init__(self):
        self.api_url = settings.WHATSAPP_API_URL
        self.phone_number_id = settings.WHATSAPP_PHONE_NUMBER_ID
        self.token = settings.WHATSAPP_TOKEN
        self.headers = {
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        }
    
    async def send_text(self, to: str, text: str, preview_url: bool = False) -> Dict:
        """Send a text message"""
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "text",
            "text": {
                "preview_url": preview_url,
                "body": text
            }
        }
        return await self._send_message(payload)
    
    async def send_buttons(
        self,
        to: str,
        body: str,
        buttons: List[Dict[str, str]],
        header: Optional[str] = None,
        footer: Optional[str] = None
    ) -> Dict:
        """Send interactive buttons (max 3 buttons)"""
        interactive = {
            "type": "button",
            "body": {"text": body},
            "action": {
                "buttons": [
                    {
                        "type": "reply",
                        "reply": {
                            "id": btn["id"],
                            "title": btn["title"][:20]  # Max 20 chars
                        }
                    }
                    for btn in buttons[:3]  # Max 3 buttons
                ]
            }
        }
        
        if header:
            interactive["header"] = {"type": "text", "text": header}
        if footer:
            interactive["footer"] = {"text": footer}
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive
        }
        return await self._send_message(payload)
    
    async def send_list(
        self,
        to: str,
        body: str,
        button_text: str,
        sections: List[Dict],
        header: Optional[str] = None,
        footer: Optional[str] = None
    ) -> Dict:
        """Send interactive list menu"""
        interactive = {
            "type": "list",
            "body": {"text": body},
            "action": {
                "button": button_text[:20],
                "sections": sections
            }
        }
        
        if header:
            interactive["header"] = {"type": "text", "text": header}
        if footer:
            interactive["footer"] = {"text": footer}
        
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": to,
            "type": "interactive",
            "interactive": interactive
        }
        return await self._send_message(payload)
    
    async def send_template(
        self,
        to: str,
        template_name: str,
        language_code: str = "en",
        components: Optional[List[Dict]] = None
    ) -> Dict:
        """Send a pre-approved template message"""
        template = {
            "name": template_name,
            "language": {"code": language_code}
        }
        if components:
            template["components"] = components
        
        payload = {
            "messaging_product": "whatsapp",
            "to": to,
            "type": "template",
            "template": template
        }
        return await self._send_message(payload)
    
    async def mark_as_read(self, message_id: str) -> Dict:
        """Mark a message as read"""
        payload = {
            "messaging_product": "whatsapp",
            "status": "read",
            "message_id": message_id
        }
        return await self._send_message(payload)
    
    async def _send_message(self, payload: Dict) -> Dict:
        """Internal method to send messages"""
        url = f"{self.api_url}/{self.phone_number_id}/messages"
        recipient = payload.get("to", "unknown")
        msg_type = payload.get("type", "unknown")

        logger.info("=" * 40)
        logger.info(f"📤 SENDING MESSAGE TO WHATSAPP")
        logger.info("=" * 40)
        logger.info(f"📍 URL: {url}")
        logger.info(f"👤 Recipient: {recipient}")
        logger.info(f"📝 Type: {msg_type}")
        logger.info(f"🔑 Token present: {bool(self.token)}")
        logger.info(f"🔑 Token length: {len(self.token) if self.token else 0}")

        # Log payload (but truncate long text bodies)
        log_payload = payload.copy()
        if log_payload.get("text", {}).get("body"):
            body = log_payload["text"]["body"]
            if len(body) > 100:
                log_payload["text"]["body"] = body[:100] + "...[truncated]"
        logger.info(f"📦 Payload: {log_payload}")

        async with httpx.AsyncClient() as client:
            try:
                logger.info("🚀 Making HTTP POST request...")
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                )
                logger.info(f"📬 Response status: {response.status_code}")
                logger.info(f"📬 Response headers: {dict(response.headers)}")

                response.raise_for_status()
                result = response.json()
                logger.info(f"✅ Message sent successfully!")
                logger.info(f"✅ Response: {result}")
                return result
            except httpx.HTTPStatusError as e:
                error_body = e.response.text if e.response else "No response body"
                logger.error("=" * 40)
                logger.error(f"❌ WHATSAPP API HTTP ERROR")
                logger.error("=" * 40)
                logger.error(f"❌ Status code: {e.response.status_code if e.response else 'N/A'}")
                logger.error(f"❌ Response body: {error_body}")
                logger.error(f"❌ URL: {url}")
                logger.error(f"❌ Payload sent: {log_payload}")
                raise
            except httpx.HTTPError as e:
                logger.error("=" * 40)
                logger.error(f"❌ WHATSAPP API CONNECTION ERROR")
                logger.error("=" * 40)
                logger.error(f"❌ Error type: {type(e).__name__}")
                logger.error(f"❌ Error message: {e}")
                raise
    
    @staticmethod
    def parse_webhook(data: Dict) -> Optional[WhatsAppMessage]:
        """Parse incoming webhook data"""
        logger.info("=" * 40)
        logger.info("🔍 PARSING WEBHOOK DATA")
        logger.info("=" * 40)

        try:
            logger.info(f"📥 Raw webhook data keys: {list(data.keys())}")

            entry = data.get("entry", [{}])[0]
            logger.info(f"📋 Entry keys: {list(entry.keys()) if entry else 'EMPTY'}")

            changes = entry.get("changes", [{}])[0]
            logger.info(f"📋 Changes keys: {list(changes.keys()) if changes else 'EMPTY'}")

            value = changes.get("value", {})
            logger.info(f"📋 Value keys: {list(value.keys()) if value else 'EMPTY'}")

            messages = value.get("messages", [])
            logger.info(f"📬 Messages count: {len(messages)}")

            if not messages:
                logger.warning("⚠️ No messages found in webhook data")
                logger.warning(f"⚠️ Full value object: {value}")
                return None

            msg = messages[0]
            logger.info(f"📩 First message: {msg}")

            message = WhatsAppMessage(
                message_id=msg.get("id"),
                from_number=msg.get("from"),
                timestamp=msg.get("timestamp"),
                message_type=msg.get("type")
            )

            if msg.get("type") == "text":
                message.text = msg.get("text", {}).get("body")
                logger.info(f"📝 Text message: '{message.text}'")
            elif msg.get("type") == "interactive":
                interactive = msg.get("interactive", {})
                logger.info(f"🔘 Interactive type: {interactive.get('type')}")
                if interactive.get("type") == "button_reply":
                    message.button_reply = interactive.get("button_reply")
                    logger.info(f"🔘 Button reply: {message.button_reply}")
                elif interactive.get("type") == "list_reply":
                    message.list_reply = interactive.get("list_reply")
                    logger.info(f"📋 List reply: {message.list_reply}")
                message.interactive_reply = interactive

            logger.info(f"✅ Parsed message: id={message.message_id}, from={message.from_number}, type={message.message_type}")
            return message
        except Exception as e:
            logger.exception(f"❌ Error parsing webhook: {e}")
            logger.error(f"❌ Failed data: {data}")
            return None