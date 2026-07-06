# pipeline/image_pipeline.py
"""
Image Pipeline — Orchestrates two-array image generation.

Array 1: lifestyle_images (3x) — person using the product, different viewing angles
Array 2: feature_images  (4-5x) — one per key feature, demonstrating that feature

Flow per image:
  1. Prompt Agent (LLM) generates a text prompt
  2. Image Generator (Gemini via OpenRouter) creates image from prompt + reference
  3. GDrive Uploader stores the image and returns a public URL
"""

import asyncio
from agent.image_prompts import create_lifestyle_prompts, create_feature_prompts, ANGLE_STRATEGIES
from tools.image_gen import generate_image_with_reference
from tools.gdrive_upload import upload_image
from config import (
    OPENROUTER_API_KEY,
    GDRIVE_FOLDER_ID,
    GDRIVE_SERVICE_ACCOUNT_FILE,
    LIFESTYLE_IMAGE_COUNT,
)


async def run_image_generation(
    description: str,
    category: str,
    key_features: list[dict],
    reference_image_url: str,
    scraped_images: list[dict],
) -> dict:
    """
    Main entry point — generates both lifestyle and feature image arrays.

    Args:
        description: Product long_description text.
        category: Product category (e.g., "PICKLEBALL PADDLE").
        key_features: List of {"title": "...", "description": "..."} dicts.
        reference_image_url: Best product image URL to use as reference.
        scraped_images: List of {"url": "...", "alt": "...", "type": "product"} dicts.

    Returns:
        {
            "scraped_images": [...],
            "lifestyle_images": [...],
            "feature_images": [...],
            "generation_status": {
                "lifestyle_generated": int,
                "feature_generated": int,
                "lifestyle_failed": int,
                "feature_failed": int,
            }
        }
    """
    print(f"\n{'=' * 60}")
    print("IMAGE PIPELINE — Starting")
    print(f"  Reference: {reference_image_url[:80]}..." if reference_image_url else "  Reference: NONE")
    print(f"  Category: {category}")
    print(f"  Key features: {len(key_features)}")
    print(f"{'=' * 60}")

    # ── PHASE 1: Generate lifestyle images ──
    print(f"\n{'─' * 40}")
    print(f"PHASE 1 — LIFESTYLE IMAGES ({LIFESTYLE_IMAGE_COUNT}x)")
    print(f"{'─' * 40}")

    lifestyle_images, ls_stats = await _generate_lifestyle_array(
        description=description,
        category=category,
        reference_url=reference_image_url,
        count=LIFESTYLE_IMAGE_COUNT,
    )

    # ── PHASE 2: Generate feature images ──
    print(f"\n{'─' * 40}")
    print(f"PHASE 2 — FEATURE IMAGES ({len(key_features)}x)")
    print(f"{'─' * 40}")

    feature_images, ft_stats = await _generate_feature_array(
        key_features=key_features,
        category=category,
        reference_url=reference_image_url,
    )

    # ── Assemble result ──
    total = len(scraped_images) + len(lifestyle_images) + len(feature_images)

    print(f"\n{'=' * 60}")
    print(f"IMAGE PIPELINE — Complete")
    print(f"  Scraped:   {len(scraped_images)}")
    print(f"  Lifestyle: {len(lifestyle_images)}/{LIFESTYLE_IMAGE_COUNT}")
    print(f"  Feature:   {len(feature_images)}/{len(key_features)}")
    print(f"  Total:     {total}")
    print(f"{'=' * 60}\n")

    return {
        "scraped_images": scraped_images,
        "lifestyle_images": lifestyle_images,
        "feature_images": feature_images,
        "generation_status": {
            "lifestyle_generated": ls_stats["generated"],
            "feature_generated": ft_stats["generated"],
            "lifestyle_failed": ls_stats["failed"],
            "feature_failed": ft_stats["failed"],
        },
    }


# ─────────────────────────────────────────────────────────────
# Lifestyle Array Generation
# ─────────────────────────────────────────────────────────────

async def _generate_lifestyle_array(
    description: str,
    category: str,
    reference_url: str,
    count: int,
) -> tuple[list, dict]:
    """
    Generate N lifestyle images sequentially.
    Each iteration uses a different viewing angle strategy.
    Same description + reference, different prompt each time.
    """
    stats = {"generated": 0, "failed": 0}

    if not reference_url:
        print("  [lifestyle] No reference image — skipping")
        return [], stats

    # Step 1: Generate all prompts (one per iteration)
    prompts = await create_lifestyle_prompts(
        description=description,
        category=category,
        count=count,
    )

    if not prompts:
        print("  [lifestyle] No prompts generated — skipping")
        stats["failed"] = count
        return [], stats

    # Step 2: Generate images + upload (sequential to avoid rate limits)
    images = []

    for i, prompt in enumerate(prompts):
        print(f"\n  [lifestyle {i+1}/{len(prompts)}] Generating image...")

        # Generate image via Gemini
        gen_result = await generate_image_with_reference(
            prompt=prompt,
            reference_image_url=reference_url,
            api_key=OPENROUTER_API_KEY,
        )

        if not gen_result["success"]:
            print(f"  [lifestyle {i+1}] ✗ generation failed: {gen_result['error']}")
            stats["failed"] += 1
            continue

        # Upload to Google Drive
        upload_result = await upload_image(
            base64_data=gen_result["image_data"],
            mime_type=gen_result["mime_type"],
            folder_id=GDRIVE_FOLDER_ID,
            service_account_file=GDRIVE_SERVICE_ACCOUNT_FILE,
        )

        if not upload_result["success"]:
            print(f"  [lifestyle {i+1}] ✗ upload failed: {upload_result['error']}")
            stats["failed"] += 1
            continue

        angle_name = ANGLE_STRATEGIES[i % len(ANGLE_STRATEGIES)]["name"]
        images.append({
            "url": upload_result["url"],
            "drive_url": upload_result["drive_url"],
            "alt": f"Lifestyle {angle_name.replace('_', ' ').title()} Shot",
            "type": "lifestyle",
        })
        stats["generated"] += 1
        print(f"  [lifestyle {i+1}] ✓ {upload_result['url'][:60]}...")

    return images, stats


# ─────────────────────────────────────────────────────────────
# Feature Array Generation
# ─────────────────────────────────────────────────────────────

async def _generate_feature_array(
    key_features: list[dict],
    category: str,
    reference_url: str,
) -> tuple[list, dict]:
    """
    Generate one image per key feature.
    Each feature description is the input to the prompt agent.
    """
    stats = {"generated": 0, "failed": 0}

    if not key_features:
        print("  [feature] No key features — skipping")
        return [], stats

    if not reference_url:
        print("  [feature] No reference image — skipping")
        stats["failed"] = len(key_features)
        return [], stats

    # Step 1: Generate all feature prompts
    feature_prompts = await create_feature_prompts(
        key_features=key_features,
        category=category,
    )

    if not feature_prompts:
        print("  [feature] No prompts generated — skipping")
        stats["failed"] = len(key_features)
        return [], stats

    # Step 2: Generate images + upload (sequential)
    images = []

    for i, fp in enumerate(feature_prompts):
        title = fp["title"]
        prompt = fp["prompt"]

        print(f"\n  [feature {i+1}/{len(feature_prompts)}] '{title}' — generating image...")

        gen_result = await generate_image_with_reference(
            prompt=prompt,
            reference_image_url=reference_url,
            api_key=OPENROUTER_API_KEY,
        )

        if not gen_result["success"]:
            print(f"  [feature {i+1}] ✗ generation failed: {gen_result['error']}")
            stats["failed"] += 1
            continue

        upload_result = await upload_image(
            base64_data=gen_result["image_data"],
            mime_type=gen_result["mime_type"],
            folder_id=GDRIVE_FOLDER_ID,
            service_account_file=GDRIVE_SERVICE_ACCOUNT_FILE,
        )

        if not upload_result["success"]:
            print(f"  [feature {i+1}] ✗ upload failed: {upload_result['error']}")
            stats["failed"] += 1
            continue

        images.append({
            "url": upload_result["url"],
            "drive_url": upload_result["drive_url"],
            "alt": f"{title} — Feature Highlight",
            "type": "feature",
            "feature_title": title,
            "feature_description": fp["description"],
        })
        stats["generated"] += 1
        print(f"  [feature {i+1}] ✓ {upload_result['url'][:60]}...")

    return images, stats
