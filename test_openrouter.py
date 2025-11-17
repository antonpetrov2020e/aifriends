#!/usr/bin/env python3
"""
Quick test script to verify OpenRouter API is working
"""
import asyncio
from openai import AsyncOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

async def test_openrouter():
    api_key = os.getenv("OPENROUTER_API_KEY")
    model = os.getenv("LLM_MODEL", "google/gemini-2.0-flash-exp:free")

    print(f"Testing OpenRouter API...")
    print(f"API Key: {api_key[:20]}..." if api_key else "API Key: NOT FOUND")
    print(f"Model: {model}")
    print("-" * 50)

    client = AsyncOpenAI(
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
    )

    try:
        print("Sending test request...")
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "Привет! Скажи 'Работаю!' одним словом."}
            ],
            max_tokens=50,
        )

        result = response.choices[0].message.content
        print(f"✅ SUCCESS! Response: {result}")
        return True

    except Exception as e:
        print(f"❌ ERROR: {type(e).__name__}")
        print(f"Message: {e}")

        # Try to get more details
        if hasattr(e, 'response'):
            print(f"Response status: {e.response.status_code if hasattr(e.response, 'status_code') else 'N/A'}")
            print(f"Response text: {e.response.text if hasattr(e.response, 'text') else 'N/A'}")

        import traceback
        print("\nFull traceback:")
        print(traceback.format_exc())
        return False

if __name__ == "__main__":
    success = asyncio.run(test_openrouter())
    exit(0 if success else 1)
