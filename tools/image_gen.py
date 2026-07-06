# tools/image_gen.py
"""
Image Generation Tool — Calls OpenRouter (Gemini) with a reference image + prompt.

This replaces nano_banana for reference-image-aware generation.
Supports all known response formats from OpenRouter/Gemini.
"""

import json
import re
import aiohttp

DEFAULT_MODEL = "google/gemini-2.5-flash-preview-image-generation"
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"


async def generate_image_with_reference(
    prompt: str,
    reference_image_url: str,
    api_key: str,
    model: str = DEFAULT_MODEL,
    timeout: int = 120,
) -> dict:
    """
    Generate an image using OpenRouter/Gemini with a reference product image.

    Args:
        prompt: The image generation prompt (from the prompt agent).
        reference_image_url: URL of the product reference image.
        api_key: OpenRouter API key.
        model: Model identifier (default: Gemini flash image).
        timeout: Request timeout in seconds.

    Returns:
        dict with:
          - success (bool)
          - image_data (str): base64 image data
          - mime_type (str): e.g. "image/png"
          - error (str): error message if failed
    """
    if not prompt:
        return _error("No prompt provided")
    if not api_key:
        return _error("No API key provided")

    # ── Build message content ──
    content = []

    if reference_image_url:
        content.append({
            "type": "image_url",
            "image_url": {"url": reference_image_url},
        })

    content.append({
        "type": "text",
        "text": prompt,
    })

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model,
        "messages": [
            {"role": "user", "content": content}
        ],
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(
                OPENROUTER_URL,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as resp:
                if resp.status != 200:
                    body = await resp.text()
                    return _error(f"API returned {resp.status}: {body[:300]}")

                api_response = await resp.json()

    except aiohttp.ClientError as e:
        return _error(f"HTTP error: {e}")
    except Exception as e:
        return _error(f"Request failed: {e}")

    # ── Check for API-level errors ──
    if "error" in api_response:
        err = api_response["error"]
        msg = err.get("message", json.dumps(err)) if isinstance(err, dict) else str(err)
        return _error(f"API error: {msg}")

    # ── Extract image from response ──
    return _extract_image(api_response)


def _extract_image(api_response: dict) -> dict:
    """
    Extract image data from OpenRouter/Gemini response.
    Handles ALL known response formats.
    """
    choices = api_response.get("choices", [])
    images = []

    for choice in choices:
        msg_content = choice.get("message", {}).get("content")

        if isinstance(msg_content, str):
            # Check for inline base64 data URIs in text
            matches = re.findall(
                r"data:image/[a-zA-Z]+;base64,[A-Za-z0-9+/=]+",
                msg_content
            )
            for match in matches:
                mime, data = _parse_data_uri(match)
                images.append({"data": data, "mime_type": mime})

        elif isinstance(msg_content, list):
            for part in msg_content:
                ptype = part.get("type", "")

                # Format 1: OpenAI — { type: "image_url", image_url: { url } }
                if ptype == "image_url" and "image_url" in part:
                    url = part["image_url"].get("url", "")
                    if url.startswith("data:"):
                        mime, data = _parse_data_uri(url)
                        images.append({"data": data, "mime_type": mime})

                # Format 2: { type: "image", url }
                elif ptype == "image" and "url" in part:
                    url = part["url"]
                    if url.startswith("data:"):
                        mime, data = _parse_data_uri(url)
                        images.append({"data": data, "mime_type": mime})

                # Format 3: { type: "image", image: { url } }
                elif ptype == "image" and "image" in part:
                    url = part["image"].get("url", "")
                    if url.startswith("data:"):
                        mime, data = _parse_data_uri(url)
                        images.append({"data": data, "mime_type": mime})

                # Format 4: Gemini native — { type: "inline_data", inline_data: { mime_type, data } }
                elif ptype == "inline_data" and "inline_data" in part:
                    mime = part["inline_data"].get("mime_type", "image/png")
                    data = part["inline_data"].get("data", "")
                    if data:
                        images.append({"data": data, "mime_type": mime})

                # Format 5: Gemini alt — { inline_data: { data } } (no type field)
                elif "inline_data" in part and "data" in part.get("inline_data", {}):
                    mime = part["inline_data"].get("mime_type", "image/png")
                    data = part["inline_data"]["data"]
                    images.append({"data": data, "mime_type": mime})

                # Format 6: Anthropic — { type: "image", source: { data } }
                elif ptype == "image" and "source" in part:
                    mime = part["source"].get("media_type", "image/png")
                    data = part["source"].get("data", "")
                    if data:
                        images.append({"data": data, "mime_type": mime})

                # Format 7: { b64_json }
                elif "b64_json" in part:
                    images.append({"data": part["b64_json"], "mime_type": "image/png"})

    if not images:
        return _error("No image found in API response")

    first = images[0]
    return {
        "success": True,
        "image_data": first["data"],
        "mime_type": first["mime_type"],
        "error": "",
    }


def _parse_data_uri(uri: str) -> tuple:
    match = re.match(r"data:(image/[a-zA-Z]+);base64,(.+)", uri)
    if match:
        return match.group(1), match.group(2)
    return "image/png", uri


def _error(msg: str) -> dict:
    print(f"  [image_gen] ERROR: {msg}")
    return {"success": False, "image_data": "", "mime_type": "", "error": msg}
