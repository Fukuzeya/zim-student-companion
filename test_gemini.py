#!/usr/bin/env python3
"""Quick test to verify Gemini API connectivity"""
import os
import sys

# Load from .env
from dotenv import load_dotenv
load_dotenv()

api_key = os.getenv("GEMINI_API_KEY")
model_name = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

print(f"API Key: {'Set (' + str(len(api_key)) + ' chars)' if api_key else 'NOT SET'}")
print(f"Model: {model_name}")

if not api_key:
    print("ERROR: GEMINI_API_KEY not set in .env")
    sys.exit(1)

try:
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel(model_name)

    print(f"\nTesting model '{model_name}'...")
    response = model.generate_content("Say 'Hello World'")

    print("\nResponse object:")
    print(f"  - candidates: {len(response.candidates) if response.candidates else 0}")

    if response.candidates:
        candidate = response.candidates[0]
        print(f"  - finish_reason: {candidate.finish_reason}")
        print(f"  - safety_ratings: {candidate.safety_ratings}")

        if candidate.content and candidate.content.parts:
            print(f"\n✅ SUCCESS! Response: {candidate.content.parts[0].text}")
        else:
            print(f"\n❌ No content in response")
    else:
        print("\n❌ No candidates in response")

except Exception as e:
    print(f"\n❌ ERROR: {e}")
    import traceback
    traceback.print_exc()
