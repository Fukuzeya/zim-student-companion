#!/usr/bin/env python3
"""
WhatsApp Webhook Configuration Test Script
Run this to diagnose webhook issues.
"""
import asyncio
import httpx
import sys
from app.config import get_settings

settings = get_settings()

def print_header(title: str):
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60)

async def main():
    print_header("WhatsApp Webhook Configuration Check")

    # 1. Check Configuration
    print("\n📋 Configuration Values:")
    print(f"  WHATSAPP_TOKEN: {'✅ Set' if settings.WHATSAPP_TOKEN else '❌ Missing'} (length: {len(settings.WHATSAPP_TOKEN) if settings.WHATSAPP_TOKEN else 0})")
    print(f"  WHATSAPP_PHONE_NUMBER_ID: {settings.WHATSAPP_PHONE_NUMBER_ID or '❌ Missing'}")
    print(f"  WHATSAPP_VERIFY_TOKEN: {settings.WHATSAPP_VERIFY_TOKEN or '❌ Missing'}")
    print(f"  WHATSAPP_API_URL: {settings.WHATSAPP_API_URL}")
    print(f"  WHATSAPP_APP_SECRET: {'✅ Set' if settings.WHATSAPP_APP_SECRET else '⚠️ Not set (signature verification disabled)'}")
    print(f"  DEBUG: {settings.DEBUG} {'⚠️ Signature verification skipped!' if settings.DEBUG else ''}")

    # 2. Test WhatsApp API Connection
    print_header("Testing WhatsApp API Connection")

    api_url = f"{settings.WHATSAPP_API_URL}/{settings.WHATSAPP_PHONE_NUMBER_ID}"
    headers = {"Authorization": f"Bearer {settings.WHATSAPP_TOKEN}"}

    async with httpx.AsyncClient() as client:
        try:
            # Test getting phone number details
            response = await client.get(api_url, headers=headers, timeout=10.0)
            if response.status_code == 200:
                data = response.json()
                print(f"  ✅ WhatsApp API connected!")
                print(f"  Phone Number: {data.get('display_phone_number', 'N/A')}")
                print(f"  Verified Name: {data.get('verified_name', 'N/A')}")
                print(f"  Quality Rating: {data.get('quality_rating', 'N/A')}")
            else:
                print(f"  ❌ WhatsApp API error: {response.status_code}")
                print(f"  Response: {response.text}")
        except Exception as e:
            print(f"  ❌ Connection error: {e}")

    # 3. Check Database Connection
    print_header("Testing Database Connection")
    try:
        from app.core.database import async_session_maker
        from sqlalchemy import text
        async with async_session_maker() as db:
            result = await db.execute(text("SELECT 1"))
            print("  ✅ Database connected!")
    except Exception as e:
        print(f"  ❌ Database error: {e}")

    # 4. Check Redis Connection
    print_header("Testing Redis Connection")
    try:
        from app.core.redis import redis_client
        await redis_client.ping()
        print("  ✅ Redis connected!")
    except Exception as e:
        print(f"  ⚠️ Redis error (optional): {e}")

    # 5. Print Expected Webhook URLs
    print_header("Expected Webhook URLs")
    base_url = "https://edu.sawaratech.co.zw"

    print(f"\n  Your current Facebook callback URL:")
    print(f"  ➡️  {base_url}/api/v1/webhooks/whatsapp")

    print(f"\n  ⚠️ But your app expects (no /api prefix):")
    print(f"  ➡️  {base_url}/v1/webhooks/whatsapp")

    print(f"\n  🔧 FIX: Update Facebook callback URL to remove '/api' prefix")
    print(f"     OR configure your reverse proxy to handle /api/ → /")

    # 6. Webhook Verification Test URL
    print_header("Test Verification URL")
    verify_url = f"{base_url}/v1/webhooks/whatsapp?hub.mode=subscribe&hub.verify_token={settings.WHATSAPP_VERIFY_TOKEN}&hub.challenge=test123"
    print(f"\n  Test with curl:")
    print(f"  curl -v \"{verify_url}\"")
    print(f"\n  Expected response: test123")

    print("\n" + "=" * 60)
    print("  Done!")
    print("=" * 60 + "\n")

if __name__ == "__main__":
    asyncio.run(main())
