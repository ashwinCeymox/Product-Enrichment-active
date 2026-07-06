# agent/image_prompts.py
"""
Image Prompt Agent — Generates two types of prompts via LLM:
  1. Lifestyle prompts (person using the product, 3 different viewing angles)
  2. Feature prompts (one per key_feature, visually demonstrating the feature)

Uses litellm.acompletion to stay async-compatible with the existing pipeline.
"""

import json
from litellm import acompletion
from config import LLM_MODEL

# ─────────────────────────────────────────────────────────────
# Environment Detection
# ─────────────────────────────────────────────────────────────

INDOOR_KEYWORDS = [
    "treadmill", "rowing machine", "stationary bike", "weight bench",
    "dumbbell", "barbell", "resistance band", "yoga mat", "gym machine",
    "table tennis", "boxing bag", "gymnastics", "elliptical", "spin bike",
    "exercise bike", "indoor cycle", "power rack", "smith machine"
]

OUTDOOR_KEYWORDS = [
    "pickleball", "paddle", "tennis racket", "golf club", "outdoor bike",
    "surfboard", "skateboard", "badminton", "squash racket", "cricket bat",
    "baseball bat", "soccer ball", "football", "basketball"
]

BOTH_KEYWORDS = [
    "running shoe", "jump rope", "kettlebell", "water bottle",
    "sports apparel", "sports bag", "fitness tracker", "sports eyewear",
    "court shoe", "training shoe"
]

# ─────────────────────────────────────────────────────────────
# Product Size Classification
# ─────────────────────────────────────────────────────────────

SMALL_KEYWORDS = [
    "water bottle", "resistance band", "jump rope", "fitness tracker",
    "sports eyewear", "wristband", "grip tape", "ball", "shuttlecock",
    "edge guard"
]

MEDIUM_KEYWORDS = [
    "paddle", "racket", "racquet", "dumbbell", "kettlebell", "yoga mat",
    "boxing glove", "shin guard", "helmet", "sports bag", "bat"
]

LARGE_KEYWORDS = [
    "treadmill", "elliptical", "exercise bike", "stationary bike",
    "rowing machine", "weight bench", "power rack", "smith machine",
    "table tennis table", "gym machine", "trampoline"
]


def _detect_environment(text: str) -> str:
    text = text.lower()
    for kw in OUTDOOR_KEYWORDS:
        if kw in text:
            return "OUTDOOR"
    for kw in INDOOR_KEYWORDS:
        if kw in text:
            return "INDOOR"
    for kw in BOTH_KEYWORDS:
        if kw in text:
            return "BOTH"
    return "INDOOR"


def _detect_product_size(text: str) -> str:
    text = text.lower()
    for kw in LARGE_KEYWORDS:
        if kw in text:
            return "LARGE"
    for kw in MEDIUM_KEYWORDS:
        if kw in text:
            return "MEDIUM"
    for kw in SMALL_KEYWORDS:
        if kw in text:
            return "SMALL"
    return "MEDIUM"


# ─────────────────────────────────────────────────────────────
# Viewing Angle Strategies — one per lifestyle iteration
# ─────────────────────────────────────────────────────────────

ANGLE_STRATEGIES = [
    {
        "name": "wide_action",
        "instruction": (
            "Wide shot showing the full body of a person actively using the product. "
            "Camera at a 3/4 angle, capturing the environment and person mid-action. "
            "Dynamic pose, aspirational feel. Product clearly visible."
        ),
    },
    {
        "name": "medium_side",
        "instruction": (
            "Medium shot from a side angle, waist-up view of a person using the product. "
            "Focus split between the person's engagement and the product. "
            "Intimate framing showing natural grip and interaction. "
            "Shallow depth of field with background slightly blurred."
        ),
    },
    {
        "name": "close_detail",
        "instruction": (
            "Close-up action detail shot focusing on the moment of product interaction. "
            "Tight crop on hands, contact point, or the product in active use. "
            "Person partially visible, emphasis on product in motion. "
            "Cinematic depth of field, frozen action moment."
        ),
    },
]


# ─────────────────────────────────────────────────────────────
# System Prompts
# ─────────────────────────────────────────────────────────────

LIFESTYLE_SYSTEM_PROMPT = """You are an expert visual marketing prompt engineer specializing in photorealistic product and lifestyle imagery for sports and fitness products.

Your job: take the inputs and generate ONE detailed image generation prompt for a lifestyle photo.

CRITICAL RULES:
1. You must respond ONLY with a valid JSON object: {"PROMPT": "your prompt text here"}
2. The PROMPT value rules:
   - Use ONLY single quotes if quoting is needed, never double quotes inside the prompt
   - No backslashes, no line breaks, no markdown, no arrows, no emoji
   - One single continuous sentence
3. NEVER describe the product appearance — the reference image handles that entirely.
4. Focus ONLY on: scene, environment, person action, camera angle, lighting, mood.
5. The person must be NATURALLY using the product, not posing.
6. Consider the PRODUCT SIZE when framing — a small handheld item needs close framing, a large machine needs wide framing.
7. If you cannot generate a valid response, return: {"PROMPT": "GENERATION FAILED"}
8. NEVER add any text outside the JSON object."""

FEATURE_SYSTEM_PROMPT = """You are an expert visual marketing prompt engineer specializing in photorealistic product feature imagery for sports and fitness products.

Your job: take a product feature title and description, then generate ONE detailed image generation prompt that visually communicates that specific feature.

CRITICAL RULES:
1. You must respond ONLY with a valid JSON object: {"PROMPT": "your prompt text here"}
2. The PROMPT value rules:
   - Use ONLY single quotes if quoting is needed, never double quotes inside the prompt
   - No backslashes, no line breaks, no markdown, no arrows, no emoji
   - One single continuous sentence
3. NEVER describe the product appearance — the reference image handles that entirely.
4. The image should visually DEMONSTRATE the feature being described, not just show the product.
5. Show the product in a real-world context where the feature benefit is obvious.
6. Style: high-end marketing photography, warm lighting, lifestyle-meets-feature.
7. If you cannot generate a valid response, return: {"PROMPT": "GENERATION FAILED"}
8. NEVER add any text outside the JSON object."""


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

async def create_lifestyle_prompts(
    description: str,
    category: str,
    count: int = 3
) -> list[str]:
    """
    Generate 'count' lifestyle image prompts, each with a different viewing angle.

    Args:
        description: Full product description text.
        category: Product category (e.g., "PICKLEBALL PADDLE").
        count: Number of prompts to generate (default 3).

    Returns:
        List of prompt strings ready for the image generator.
    """
    combined_text = f"{description} {category}"
    environment = _detect_environment(combined_text)
    product_size = _detect_product_size(combined_text)

    # Build environment context string
    env_map = {
        "OUTDOOR": "outdoor setting appropriate for the sport (court, field, park, trail)",
        "INDOOR": "modern indoor setting (home gym, fitness studio, gym floor)",
        "BOTH": "versatile setting that could be indoor or outdoor based on natural use",
    }
    env_context = env_map.get(environment, env_map["INDOOR"])

    # Build size context string
    size_map = {
        "SMALL": (
            "The product is small and handheld. Ensure it is clearly visible "
            "in the person's hand or being directly interacted with at close range."
        ),
        "MEDIUM": (
            "The product is medium-sized and handheld or body-mounted. "
            "Show the person gripping, wearing, or actively swinging/using it."
        ),
        "LARGE": (
            "The product is a large piece of equipment. The person should be "
            "standing on, sitting in, or actively operating the full-size machine."
        ),
    }
    size_context = size_map.get(product_size, size_map["MEDIUM"])

    prompts = []

    for i in range(count):
        angle = ANGLE_STRATEGIES[i % len(ANGLE_STRATEGIES)]

        user_message = (
            f"product_description: {description}\n"
            f"product_category: {category}\n"
            f"environment: {environment} — {env_context}\n"
            f"product_size: {product_size} — {size_context}\n"
            f"viewing_angle_strategy: {angle['name']} — {angle['instruction']}\n\n"
            f"Generate a photorealistic lifestyle image prompt showing a real person "
            f"actively using this product. The reference image will be provided "
            f"separately — do NOT describe the product appearance."
        )

        print(f"  [image_prompts] generating lifestyle prompt {i+1}/{count} ({angle['name']})...")

        try:
            response = await acompletion(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": LIFESTYLE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.8,
                max_tokens=800,
            )

            prompt_text = _parse_prompt_response(response.choices[0].message.content)
            if prompt_text:
                prompts.append(prompt_text)
                print(f"  [image_prompts] ✓ lifestyle {i+1}: {prompt_text[:80]}...")
            else:
                print(f"  [image_prompts] ✗ lifestyle {i+1}: failed to parse")

        except Exception as e:
            print(f"  [image_prompts] ✗ lifestyle {i+1} error: {e}")

    return prompts


async def create_feature_prompts(
    key_features: list[dict],
    category: str
) -> list[dict]:
    """
    Generate one image prompt per key feature.

    Args:
        key_features: List of dicts with "title" and "description".
        category: Product category string.

    Returns:
        List of dicts: [{"title": "...", "description": "...", "prompt": "..."}]
    """
    results = []

    for i, feature in enumerate(key_features):
        title = feature.get("title", f"Feature {i+1}")
        desc = feature.get("description", "")

        if not desc:
            print(f"  [image_prompts] ✗ feature '{title}': no description — skipping")
            continue

        user_message = (
            f"product_category: {category}\n"
            f"feature_title: {title}\n"
            f"feature_description: {desc}\n\n"
            f"Generate a photorealistic feature-highlight marketing image prompt "
            f"that visually demonstrates the feature '{title}'. The image should "
            f"show the product in a real-world context where this feature's benefit "
            f"is obvious. The reference image will be provided separately — "
            f"do NOT describe the product appearance."
        )

        print(f"  [image_prompts] generating feature prompt {i+1}/{len(key_features)} ({title})...")

        try:
            response = await acompletion(
                model=LLM_MODEL,
                messages=[
                    {"role": "system", "content": FEATURE_SYSTEM_PROMPT},
                    {"role": "user", "content": user_message},
                ],
                temperature=0.7,
                max_tokens=800,
            )

            prompt_text = _parse_prompt_response(response.choices[0].message.content)
            if prompt_text:
                results.append({
                    "title": title,
                    "description": desc,
                    "prompt": prompt_text,
                })
                print(f"  [image_prompts] ✓ feature '{title}': {prompt_text[:80]}...")
            else:
                print(f"  [image_prompts] ✗ feature '{title}': failed to parse")

        except Exception as e:
            print(f"  [image_prompts] ✗ feature '{title}' error: {e}")

    return results


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────

def _parse_prompt_response(raw_text: str) -> str:
    """Parse the LLM response to extract the PROMPT value from JSON."""
    if not raw_text:
        return ""

    text = raw_text.strip()

    # Strip markdown code fences if present
    if text.startswith("```"):
        lines = text.split("\n")
        text = "\n".join(lines[1:-1]).strip()
        if text.startswith("json"):
            text = text[4:].strip()

    try:
        parsed = json.loads(text)
        prompt = parsed.get("PROMPT", "")
        if prompt and prompt != "GENERATION FAILED":
            return prompt
    except json.JSONDecodeError:
        # Try regex fallback
        import re
        match = re.search(r'"PROMPT"\s*:\s*"((?:[^"\\]|\\.)*)"', text)
        if match:
            result = match.group(1)
            if result != "GENERATION FAILED":
                return result

    return ""
