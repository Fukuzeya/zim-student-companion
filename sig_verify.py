import hmac
import hashlib
import json

app_secret = "49500de18f6648b89cc2405e8a7f2a84"

payload = {
  "object": "whatsapp_business_account",
  "entry": [
    {
      "id": "2065792750850834",
      "changes": [
        {
          "value": {
            "messaging_product": "whatsapp",
            "metadata": {
              "display_phone_number": "263787869209",
              "phone_number_id": "926838607178124"
            },
            "contacts": [
              {
                "profile": {
                  "name": "Test User"
                },
                "wa_id": "263778081286"
              }
            ],
            "messages": [
              {
                "from": "263778081286",
                "id": "wamid.HBgLMjYzNzc4MDgxMjg2FQIAEhggQTJCM0M0RDVFNkY3RzhIOUkwSjFLMkwzTTRONU82AA==",
                "timestamp": "1738821600",
                "type": "text",
                "text": {
                  "body": "hi"
                }
              }
            ]
          },
          "field": "messages"
        }
      ]
    }
  ]
}

body = json.dumps(payload, separators=(',', ':'))
signature = hmac.new(
    app_secret.encode(),
    body.encode(),
    hashlib.sha256
).hexdigest()

print(f"sha256={signature}")
