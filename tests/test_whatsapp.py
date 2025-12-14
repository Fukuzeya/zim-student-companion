# ============================================================================
# WhatsApp Integration Tests
# ============================================================================
import pytest
from app.services.whatsapp.client import WhatsAppClient, WhatsAppMessage

class TestWhatsAppClient:
    """Tests for WhatsApp client"""
    
    def test_parse_text_message(self):
        """Test parsing text message webhook"""
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg123",
                            "from": "263771234567",
                            "timestamp": "1234567890",
                            "type": "text",
                            "text": {"body": "Hello"}
                        }]
                    }
                }]
            }]
        }
        
        message = WhatsAppClient.parse_webhook(webhook_data)
        
        assert message is not None
        assert message.message_id == "msg123"
        assert message.from_number == "263771234567"
        assert message.text == "Hello"
        assert message.message_type == "text"
    
    def test_parse_button_reply(self):
        """Test parsing button reply webhook"""
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": [{
                            "id": "msg456",
                            "from": "263771234567",
                            "timestamp": "1234567890",
                            "type": "interactive",
                            "interactive": {
                                "type": "button_reply",
                                "button_reply": {
                                    "id": "btn_practice",
                                    "title": "Start Practice"
                                }
                            }
                        }]
                    }
                }]
            }]
        }
        
        message = WhatsAppClient.parse_webhook(webhook_data)
        
        assert message is not None
        assert message.button_reply is not None
        assert message.button_reply["id"] == "btn_practice"
    
    def test_parse_empty_webhook(self):
        """Test parsing webhook with no messages"""
        webhook_data = {
            "entry": [{
                "changes": [{
                    "value": {
                        "messages": []
                    }
                }]
            }]
        }
        
        message = WhatsAppClient.parse_webhook(webhook_data)
        assert message is None