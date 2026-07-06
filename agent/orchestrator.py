# agent/orchestrator.py
"""
Core Agent Loop — Product enrichment + two-array image generation.

Flow:
  1. Tool-calling loop (scrape → serp search → merge JSON)
  2. Parse final product JSON
  3. Extract reference image + description + key_features
  4. Run image pipeline → lifestyle_images[] + feature_images[]
  5. Merge image arrays into final product JSON
"""

import json
import os
import re
import asyncio
from litellm import completion
from src.prompts import SYSTEM_PROMPT, build_user_message
from src.tool_definitions import TOOL_DEFINITIONS
from src.tools.tools import TOOL_MAP
from config import LLM_MODEL, LLM_API_KEY, OPENROUTER_API_KEY, MAX_SCRAPED_IMAGES

# Import the updated image pipeline
from pipeline.image_pipeline import run_image_generation


def run_agent(cleaned_html: str, source_url: str) -> dict:
    """
    Core agent loop.
    Receives cleaned HTML, runs tool-calling loop,
    generates images (lifestyle + feature arrays), and returns final product JSON.
    """

    os.environ["DEEPSEEK_API_KEY"] = LLM_API_KEY

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": build_user_message(cleaned_html, source_url)}
    ]

    MAX_ITERATIONS = 6
    iteration = 0
    final_product_data = {}

    print(f"\n[agent] starting loop — model: {LLM_MODEL}")

    while iteration < MAX_ITERATIONS:
        iteration += 1
        print(f"[agent] iteration {iteration}")

        response = completion(
            model=LLM_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice="auto"
        )

        message = response.choices[0].message

        # ── no tool calls → LLM is done, parse JSON and BREAK ──
        if not message.tool_calls:
            print("[agent] no tool calls — extracting final JSON")
            final_product_data = _parse_output(message.content)
            break

        print(f"[agent] {len(message.tool_calls)} tool call(s) requested")

        messages.append({
            "role": "assistant",
            "content": message.content or "",
            "tool_calls": [
                {
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": tc.function.arguments
                    }
                }
                for tc in message.tool_calls
            ]
        })

        for tool_call in message.tool_calls:
            fn_name = tool_call.function.name
            fn_args = json.loads(tool_call.function.arguments)
            print(f"  [tool] {fn_name}({fn_args})")

            try:
                tool_fn = TOOL_MAP[fn_name]
                result = tool_fn(fn_args)
                result_str = json.dumps(result) if isinstance(result, dict) else str(result)
            except Exception as e:
                result_str = f"ERROR: {str(e)}"
                print(f"  [tool] ERROR: {e}")

            messages.append({
                "role": "tool",
                "tool_call_id": tool_call.id,
                "name": fn_name,
                "content": result_str
            })

    # ── max iterations fallback ──
    if not final_product_data:
        print("[agent] max iterations reached — requesting best-effort output")
        messages.append({
            "role": "user",
            "content": "Return the best JSON output you have so far. Output only valid JSON."
        })
        response = completion(model=LLM_MODEL, messages=messages)
        final_product_data = _parse_output(response.choices[0].message.content)

    # ══════════════════════════════════════════════════════════
    # IMAGE GENERATION PHASE
    # ══════════════════════════════════════════════════════════
    #
    # Extract inputs from the agent-generated product JSON:
    #   - description → drives lifestyle prompt generation
    #   - key_features → each one drives a feature prompt
    #   - scraped images → select best as reference, keep rest for gallery
    #
    # Output structure:
    #   images.scraped_images[]   — original product photos
    #   images.lifestyle_images[] — AI lifestyle shots (3x, different angles)
    #   images.feature_images[]   — AI feature shots (1 per key_feature)
    # ══════════════════════════════════════════════════════════

    description = _extract_description(final_product_data)
    category = _extract_category(final_product_data)
    key_features = _extract_key_features(final_product_data)
    scraped_images = _extract_scraped_images(final_product_data)
    reference_url = _select_reference_image(scraped_images)

    if description and reference_url:
        print(f"\n[agent] starting image pipeline...")
        print(f"  description: {description[:80]}...")
        print(f"  category: {category}")
        print(f"  key_features: {len(key_features)}")
        print(f"  reference: {reference_url[:60]}...")

        try:
            image_result = asyncio.run(
                run_image_generation(
                    description=description,
                    category=category,
                    key_features=key_features,
                    reference_image_url=reference_url,
                    scraped_images=scraped_images,
                )
            )

            # Merge image arrays into the final product data
            final_product_data["images"] = {
                "scraped_images": image_result["scraped_images"],
                "lifestyle_images": image_result["lifestyle_images"],
                "feature_images": image_result["feature_images"],
            }

            # Update enrichment metadata
            metadata = final_product_data.get("enrichment_metadata", {})
            gen_status = image_result["generation_status"]

            metadata["scraped_images_kept"] = len(scraped_images)
            metadata["lifestyle_images_generated"] = gen_status["lifestyle_generated"]
            metadata["feature_images_generated"] = gen_status["feature_generated"]
            metadata["lifestyle_images_failed"] = gen_status["lifestyle_failed"]
            metadata["feature_images_failed"] = gen_status["feature_failed"]

            total_gen = gen_status["lifestyle_generated"] + gen_status["feature_generated"]
            total_fail = gen_status["lifestyle_failed"] + gen_status["feature_failed"]

            if total_fail == 0 and total_gen > 0:
                metadata["image_generation_status"] = "success"
            elif total_gen > 0:
                metadata["image_generation_status"] = "partial"
            else:
                metadata["image_generation_status"] = "failed"

            final_product_data["enrichment_metadata"] = metadata

        except Exception as e:
            print(f"[agent] ERROR during image generation: {e}")
            final_product_data["images"] = {
                "scraped_images": scraped_images,
                "lifestyle_images": [],
                "feature_images": [],
            }
            metadata = final_product_data.get("enrichment_metadata", {})
            metadata["image_generation_status"] = "failed"
            metadata["image_generation_error"] = str(e)
            final_product_data["enrichment_metadata"] = metadata

    else:
        reasons = []
        if not description:
            reasons.append("no description")
        if not reference_url:
            reasons.append("no reference image")
        print(f"[agent] Skipping image generation: {', '.join(reasons)}")

        final_product_data["images"] = {
            "scraped_images": scraped_images,
            "lifestyle_images": [],
            "feature_images": [],
        }

    return final_product_data


# ─────────────────────────────────────────────────────────────
# Extraction helpers — pull data from the agent-generated JSON
# ─────────────────────────────────────────────────────────────

def _extract_description(data: dict) -> str:
    """Get the best description for prompt generation."""
    # Priority: long_description > about_this_item joined > short_description
    desc = data.get("long_description", "")
    if desc:
        return desc

    about = data.get("about_this_item", [])
    if about and isinstance(about, list):
        return " ".join(about)

    return data.get("short_description", "")


def _extract_category(data: dict) -> str:
    """Get product category."""
    identity = data.get("product_identity", {})
    return identity.get("product_category", "GENERAL FITNESS EQUIPMENT")


def _extract_key_features(data: dict) -> list:
    """Get key features (must have title + description)."""
    features = data.get("key_features", [])
    if not features or not isinstance(features, list):
        return []
    return [
        f for f in features
        if isinstance(f, dict) and f.get("title") and f.get("description")
    ]


def _extract_scraped_images(data: dict) -> list:
    """
    Extract scraped product images from the agent's output.
    Filters out non-product images and caps at MAX_SCRAPED_IMAGES.
    """
    raw_images = data.get("images", [])

    # Handle case where images is already the new dict format (re-run safety)
    if isinstance(raw_images, dict):
        return raw_images.get("scraped_images", [])

    # Handle flat URL list
    if raw_images and isinstance(raw_images[0], str):
        raw_images = [
            {"url": url, "alt": f"Product Image {i+1}", "type": "product"}
            for i, url in enumerate(raw_images)
        ]

    # Filter out junk images
    skip_patterns = [
        r"logo", r"icon", r"badge", r"banner", r"footer",
        r"sprite", r"placeholder", r"loading", r"arrow",
        r"1x1", r"pixel", r"tracking", r"favicon"
    ]

    filtered = []
    for img in raw_images:
        if not isinstance(img, dict):
            continue

        url = img.get("url", "")
        alt = img.get("alt", "")
        img_type = img.get("type", "")

        # Skip marketing images (those are AI-generated, not scraped)
        if img_type == "marketing":
            continue

        text = f"{url} {alt}".lower()
        if any(re.search(p, text) for p in skip_patterns):
            continue

        if len(url) < 20:
            continue

        filtered.append({
            "url": url,
            "alt": alt or "Product Image",
            "type": "product",
        })

    return filtered[:MAX_SCRAPED_IMAGES]


def _select_reference_image(scraped_images: list) -> str:
    """Pick the best image to use as reference for Gemini generation."""
    if not scraped_images:
        return ""
    # First image is typically the hero/primary product shot
    return scraped_images[0].get("url", "")


# ─────────────────────────────────────────────────────────────
# JSON output parser
# ─────────────────────────────────────────────────────────────

def _parse_output(text: str) -> dict:
    if not text:
        return {}
    text = text.strip()
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1])
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r'\{.*\}', text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError:
                pass
    print("[agent] WARNING: could not parse JSON from response")
    return {"raw_response": text}
