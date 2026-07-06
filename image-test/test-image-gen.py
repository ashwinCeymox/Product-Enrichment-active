import asyncio
import aiohttp
import ssl
import json
import certifi
from config import OPENROUTER_API_KEY,IMAGE_MODEL



OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"

async def test_cost_extraction():
    payload = {
        "model": IMAGE_MODEL,
        "messages": [
            {"role": "user", "content": "Say hello in one word."}  # cheap test prompt
        ],
    }

    headers = {
        "Authorization": f"Bearer {OPENROUTER_API_KEY}",
        "Content-Type":  "application/json",
    }

    ssl_ctx = ssl.create_default_context(cafile=certifi.where())
    conn = aiohttp.TCPConnector(ssl=ssl_ctx)

    async with aiohttp.ClientSession(connector=conn) as session:
        async with session.post(
            OPENROUTER_URL,
            headers=headers,
            json=payload,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as resp:
            print(f"Status: {resp.status}")
            api_response = await resp.json()

    # ── Dump everything ──────────────────────────────────────
    print("\n=== FULL RESPONSE ===")
    print(json.dumps(api_response, indent=2, default=str))

    # ── Show top-level keys ──────────────────────────────────
    print("\n=== TOP-LEVEL KEYS ===")
    print(list(api_response.keys()))

    # ── Show usage block ─────────────────────────────────────
    print("\n=== USAGE BLOCK ===")
    usage = api_response.get("usage", {})
    print(json.dumps(usage, indent=2, default=str))

    # ── Try extracting cost ──────────────────────────────────
    print("\n=== COST EXTRACTION ===")
    cost = (
        usage.get("total_cost")
        or usage.get("cost")
        or usage.get("cost_usd")
        or api_response.get("total_cost")
        or 0.0
    )
    print(f"Extracted cost : ${cost}")
    print(f"Prompt tokens  : {usage.get('prompt_tokens', 'N/A')}")
    print(f"Output tokens  : {usage.get('completion_tokens', 'N/A')}")

asyncio.run(test_cost_extraction())