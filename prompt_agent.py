"""
Prompt Agent — LLM-based image prompt generator.

Generates two types of prompts:
  1. Lifestyle prompts: Person actively using the product (3 different angles)
  2. Feature prompts: Product in context highlighting a specific feature

The prompt agent NEVER describes the product appearance — the reference image
handles that entirely. Prompts focus only on scene, environment, person action,
camera angle, and lighting.
"""

import json
import requests
import config


# ─────────────────────────────────────────────────────────────
# Environment Detection — determines indoor vs outdoor setting
# ─────────────────────────────────────────────────────────────

INDOOR_PRODUCTS = [
    "treadmill", "rowing machine", "stationary bike", "weight bench",
    "dumbbell", "barbell", "resistance band", "yoga mat", "gym machine",
    "table tennis", "boxing bag", "gymnastics", "elliptical", "spin bike",
    "exercise bike", "indoor cycle", "power rack", "smith machine"
]

OUTDOOR_PRODUCTS = [
    "pickleball", "paddle", "tennis racket", "golf club", "outdoor bike",
    "surfboard", "skateboard", "badminton", "squash racket", "cricket bat",
    "baseball bat", "soccer ball", "football", "basketball"
]

BOTH_PRODUCTS = [
    "running shoe", "jump rope", "kettlebell", "water bottle",
    "sports apparel", "sports bag", "fitness tracker", "sports eyewear",
    "court shoe", "training shoe"
]

# ─────────────────────────────────────────────────────────────
# Product size classification — determines framing and scale
# ─────────────────────────────────────────────────────────────

SMALL_PRODUCTS = [
    "water bottle", "resistance band", "jump rope", "fitness tracker",
    "sports eyewear", "wristband", "grip tape", "ball", "shuttlecock",
    "edge guard"
]

MEDIUM_PRODUCTS = [
    "paddle", "racket", "racquet", "dumbbell", "kettlebell", "yoga mat",
    "boxing glove", "shin guard", "helmet", "sports bag", "bat"
]

LARGE_PRODUCTS = [
    "treadmill", "elliptical", "exercise bike", "stationary bike",
    "rowing machine", "weight bench", "power rack", "smith machine",
    "table tennis table", "gym machine", "trampoline"
]


def _detect_environment(description: str, category: str) -> str:
    """Classify product environment as INDOOR, OUTDOOR, or BOTH."""
    text = f"{description} {category}".lower()

    for keyword in OUTDOOR_PRODUCTS:
        if keyword in text:
            return "OUTDOOR"

    for keyword in INDOOR_PRODUCTS:
        if keyword in text:
            return "INDOOR"

    for keyword in BOTH_PRODUCTS:
        if keyword in text:
            return "BOTH"

    return "INDOOR"  # safe default


def _detect_product_size(description: str, category: str) -> str:
    """Classify product as SMALL, MEDIUM, or LARGE for framing decisions."""
    text = f"{description} {category}".lower()

    for keyword in LARGE_PRODUCTS:
        if keyword in text:
            return "LARGE"

    for keyword in MEDIUM_PRODUCTS:
        if keyword in text:
            return "MEDIUM"

    for keyword in SMALL_PRODUCTS:
        if keyword in text:
            return "SMALL"

    return "MEDIUM"  # safe default


# ─────────────────────────────────────────────────────────────
# Lifestyle prompt — viewing angle strategies per iteration
# ─────────────────────────────────────────────────────────────

LIFESTYLE_ANGLE_STRATEGIES = [
    {
        "name": "wide_action",
        "description": (
            "Wide shot showing the full body of a person actively using the product. "
            "Camera is at a 3/4 angle, capturing the environment and the person mid-action. "
            "Dynamic pose, aspirational feel. The product should be clearly visible in the "
            "person's hands or being used naturally."
        ),
    },
    {
        "name": "medium_side",
        "description": (
            "Medium shot from a side angle, waist-up view of a person using the product. "
            "Focus is split between the person's expression/engagement and the product. "
            "More intimate framing, showing the natural grip and interaction with the product. "
            "Shallow depth of field with the background slightly blurred."
        ),
    },
    {
        "name": "close_detail",
        "description": (
            "Close-up action detail shot focusing on the moment of product interaction. "
            "Tight crop on the hands, contact point, or the product in active use. "
            "The person is partially visible but the emphasis is on the product in motion. "
            "Cinematic depth of field, frozen action moment."
        ),
    },
]


# ─────────────────────────────────────────────────────────────
# System prompts for the LLM agent
# ─────────────────────────────────────────────────────────────

LIFESTYLE_SYSTEM_PROMPT = """You are an expert visual marketing prompt engineer specializing in photorealistic product and lifestyle imagery for sports and fitness products.

Your job: take the inputs and generate ONE detailed image generation prompt for a lifestyle photo.

CRITICAL RULES:
1. You must respond ONLY with a valid JSON object: {"PROMPT": "your prompt text here"}
2. The PROMPT value must follow these strict rules:
   - Use ONLY single quotes if quoting is needed, never double quotes inside the prompt text
   - No backslashes anywhere inside the prompt text
   - No line breaks or newline characters, keep it as one single continuous sentence
   - No markdown formatting, no bold, no bullet points, no headers, no asterisks
   - No arrows of any kind, replace with 'pointing to' or 'near'
   - No special unicode characters, emoji, or symbols
   - No curly brackets or square brackets inside the prompt text
3. NEVER describe the product appearance. The reference image is the sole source of truth for product visuals.
4. Focus ONLY on: scene, environment, person action, camera angle, lighting, mood.
5. The person in the image must be NATURALLY using the product, not posing.
6. If you cannot generate a valid response, return: {"PROMPT": "GENERATION FAILED"}
7. NEVER add any text outside the JSON object."""


FEATURE_SYSTEM_PROMPT = """You are an expert visual marketing prompt engineer specializing in photorealistic product feature imagery for sports and fitness products.

Your job: take a product feature title and description, then generate ONE detailed image generation prompt that visually communicates that specific feature.

CRITICAL RULES:
1. You must respond ONLY with a valid JSON object: {"PROMPT": "your prompt text here"}
2. The PROMPT value must follow these strict rules:
   - Use ONLY single quotes if quoting is needed, never double quotes inside the prompt text
   - No backslashes anywhere inside the prompt text
   - No line breaks or newline characters, keep it as one single continuous sentence
   - No markdown formatting, no bold, no bullet points, no headers, no asterisks
   - No arrows of any kind, replace with 'pointing to' or 'near'
   - No special unicode characters, emoji, or symbols
   - No curly brackets or square brackets inside the prompt text
3. NEVER describe the product appearance. The reference image is the sole source of truth for product visuals.
4. The image should visually DEMONSTRATE the feature being described, not just show the product.
5. Show the product in a real-world context where the feature's benefit is obvious.
6. Style: high-end marketing photography, warm lighting, lifestyle-meets-feature.
7. If you cannot generate a valid response, return: {"PROMPT": "GENERATION FAILED"}
8. NEVER add any text outside the JSON object."""


# ─────────────────────────────────────────────────────────────
# LLM API call helper
# ─────────────────────────────────────────────────────────────

def _call_prompt_llm(system_prompt: str, user_message: str) -> str:
    """Call the prompt agent LLM and return the generated prompt string."""
    headers = {
        "Authorization": f"Bearer {config.PROMPT_AGENT_API_KEY}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": config.PROMPT_AGENT_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_message},
        ],
        "temperature": 0.8,
        "max_tokens": 1000,
    }

    try:
        response = requests.post(
            config.PROMPT_AGENT_BASE_URL,
            headers=headers,
            json=payload,
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()

        # Extract content from response
        content = data["choices"][0]["message"]["content"].strip()

        # Parse JSON from response — handle markdown-wrapped JSON
        if content.startswith("```"):
            content = content.split("```")[1]
            if content.startswith("json"):
                content = content[4:]
            content = content.strip()

        parsed = json.loads(content)
        prompt_text = parsed.get("PROMPT", "")

        if not prompt_text or prompt_text == "GENERATION FAILED":
            print(f"[PromptAgent] WARNING: LLM returned failed/empty prompt")
            return ""

        return prompt_text

    except requests.exceptions.RequestException as e:
        print(f"[PromptAgent] ERROR: API call failed — {e}")
        return ""
    except (json.JSONDecodeError, KeyError, IndexError) as e:
        print(f"[PromptAgent] ERROR: Failed to parse LLM response — {e}")
        return ""


# ─────────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────────

def generate_lifestyle_prompt(
    description: str,
    category: str,
    iteration_index: int
) -> str:
    """
    Generate a lifestyle image prompt for iteration N.

    Args:
        description: Full product description text.
        category: Product category (e.g., "PICKLEBALL PADDLE").
        iteration_index: 0, 1, or 2 — determines viewing angle strategy.

    Returns:
        A prompt string ready for the image generator, or empty string on failure.
    """
    environment = _detect_environment(description, category)
    product_size = _detect_product_size(description, category)
    angle_strategy = LIFESTYLE_ANGLE_STRATEGIES[
        iteration_index % len(LIFESTYLE_ANGLE_STRATEGIES)
    ]

    # Build environment context
    if environment == "OUTDOOR":
        env_context = "outdoor setting appropriate for the sport (court, field, park, trail)"
    elif environment == "INDOOR":
        env_context = "modern indoor setting (home gym, fitness studio, gym floor)"
    else:
        env_context = "versatile setting that could be indoor or outdoor, based on natural use"

    # Build size-aware framing guidance
    if product_size == "SMALL":
        size_context = (
            "The product is small and handheld. Ensure it is clearly visible "
            "in the person's hand or being directly interacted with at close range."
        )
    elif product_size == "LARGE":
        size_context = (
            "The product is a large piece of equipment. The person should be "
            "standing on, sitting in, or actively operating the full-size machine."
        )
    else:
        size_context = (
            "The product is medium-sized and handheld or body-mounted. "
            "Show the person gripping, wearing, or actively swinging/using it."
        )

    user_message = f"""product_description: {description}
product_category: {category}
environment: {environment} — {env_context}
product_size: {product_size} — {size_context}
viewing_angle_strategy: {angle_strategy['name']} — {angle_strategy['description']}

Generate a photorealistic lifestyle image prompt showing a real person actively using this product. The reference image will be provided separately to the image generator — do NOT describe the product appearance."""

    return _call_prompt_llm(LIFESTYLE_SYSTEM_PROMPT, user_message)


def generate_feature_prompt(
    feature_title: str,
    feature_description: str,
    category: str
) -> str:
    """
    Generate a feature-highlight image prompt.

    Args:
        feature_title: Short feature name (e.g., "Carbon Abrasion Surface").
        feature_description: 1-2 sentence explanation of the feature.
        category: Product category.

    Returns:
        A prompt string ready for the image generator, or empty string on failure.
    """
    environment = _detect_environment(feature_description, category)
    product_size = _detect_product_size(feature_description, category)

    user_message = f"""product_category: {category}
feature_title: {feature_title}
feature_description: {feature_description}
environment: {environment}
product_size: {product_size}

Generate a photorealistic feature-highlight marketing image prompt that visually demonstrates the feature '{feature_title}'. The image should show the product in a real-world context where this specific feature's benefit is obvious and impactful. The reference image will be provided separately — do NOT describe the product appearance."""

    return _call_prompt_llm(FEATURE_SYSTEM_PROMPT, user_message)
