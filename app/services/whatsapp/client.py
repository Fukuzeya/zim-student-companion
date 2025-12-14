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
        
        async with httpx.AsyncClient() as client:
            try:
                response = await client.post(
                    url,
                    json=payload,
                    headers=self.headers,
                    timeout=30.0
                )
                response.raise_for_status()
                return response.json()
            except httpx.HTTPError as e:
                logger.error(f"WhatsApp API error: {e}")
                raise
    
    @staticmethod
    def parse_webhook(data: Dict) -> Optional[WhatsAppMessage]:
        """Parse incoming webhook data"""
        try:
            entry = data.get("entry", [{}])[0]
            changes = entry.get("changes", [{}])[0]
            value = changes.get("value", {})
            messages = value.get("messages", [])
            
            if not messages:
                return None
            
            msg = messages[0]
            message = WhatsAppMessage(
                message_id=msg.get("id"),
                from_number=msg.get("from"),
                timestamp=msg.get("timestamp"),
                message_type=msg.get("type")
            )
            
            if msg.get("type") == "text":
                message.text = msg.get("text", {}).get("body")
            elif msg.get("type") == "interactive":
                interactive = msg.get("interactive", {})
                if interactive.get("type") == "button_reply":
                    message.button_reply = interactive.get("button_reply")
                elif interactive.get("type") == "list_reply":
                    message.list_reply = interactive.get("list_reply")
                message.interactive_reply = interactive
            
            return message
        except Exception as e:
            logger.error(f"Error parsing webhook: {e}")
            return None