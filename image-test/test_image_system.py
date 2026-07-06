# test_image_system.py
"""
Standalone test for the image generation system.
Reads the saved ProductOutput JSON directly.
Runs img_prompt.py + image_generator.py independently.

Run:
    python test_image_system.py
"""

import asyncio
import json
import os
import re
import shutil
import zipfile
import httpx
from src.tools.img_prompt import generate_all_prompts
from src.tools.image_generator import generate_product_images

# ── Config ────────────────────────────────────────────────────
PRODUCT_JSON_PATH = "joola_magnus_output.json"
REFERENCE_IMAGE_CACHE = "output/reference_cache"


# ─────────────────────────────────────────────────────────────
# Reference image helper
# Downloads scraped_images[0]["url"] to a local file
# so image_generator.py can attach it as base64
# ─────────────────────────────────────────────────────────────

async def download_reference_image(product: dict) -> str | None:
    """
    Pulls the first scraped image URL from the new schema:
        product["images"]["scraped_images"][0]["url"]

    Downloads it locally and returns the file path.
    Returns None if no scraped images exist or download fails.
    """
    try:
        scraped = product.get("images", {}).get("scraped_images", [])

        if not scraped:
            print("[test] no scraped_images found in schema — skipping reference")
            return None

        # always use index [0] — front/hero view
        hero = scraped[0]
        url  = hero.get("url", "")
        alt  = hero.get("alt", "reference")

        if not url:
            print("[test] scraped_images[0] has no url — skipping reference")
            return None

        print(f"[test] reference image url : {url}")
        print(f"[test] reference image alt : {alt}")

        # build local save path
        os.makedirs(REFERENCE_IMAGE_CACHE, exist_ok=True)
        ext       = os.path.splitext(url.split("?")[0])[1] or ".jpg"
        save_path = os.path.join(REFERENCE_IMAGE_CACHE, f"hero{ext}")

        # download
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()

        with open(save_path, "wb") as f:
            f.write(response.content)

        size_kb = len(response.content) // 1024
        print(f"[test] reference saved     : {save_path} ({size_kb} KB)")
        return save_path

    except Exception as e:
        print(f"[test] reference image download failed: {e}")
        return None


# ─────────────────────────────────────────────────────────────
# Exchange rate helper
# ─────────────────────────────────────────────────────────────

async def get_exchange_rates() -> dict:
    url = "https://api.exchangerate-api.com/v4/latest/USD"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()
            return {
                "USD": 1.0,
                "INR": data["rates"]["INR"],
                "AED": data["rates"]["AED"],
            }
    except Exception as e:
        print(f"[test] failed to fetch exchange rates: {e}")
        return {"USD": 1.0, "INR": 0.0, "AED": 0.0}


# ─────────────────────────────────────────────────────────────
# Main test
# ─────────────────────────────────────────────────────────────

async def main():

    # ── Step 1: Load ProductOutput JSON ──────────────────────
    print(f"\n[test] ── LOADING JSON ──────────────────────────────")
    print(f"[test] file: {PRODUCT_JSON_PATH}")

    if not os.path.exists(PRODUCT_JSON_PATH):
        print(f"[test] ERROR — file not found: {PRODUCT_JSON_PATH}")
        return

    with open(PRODUCT_JSON_PATH, "r") as f:
        product = json.load(f)

    identity = product.get("product_identity", {})
    print(f"[test] product  : {identity.get('product_name', 'unknown')}")
    print(f"[test] sku      : {identity.get('sku', 'unknown')}")
    print(f"[test] category : {identity.get('product_category', 'unknown')}")
    print(f"[test] features : {len(product.get('key_features', []))}")
    print(f"[test] scraped  : {len(product.get('images', {}).get('scraped_images', []))} images")

    # ── Step 2: Download reference image ─────────────────────
    print(f"\n[test] ── DOWNLOADING REFERENCE IMAGE ───────────────")
    reference_image_path = await download_reference_image(product)

    # ── Step 3: Generate image prompts ────────────────────────
    print(f"\n[test] ── STEP 1: GENERATING IMAGE PROMPTS ──────────")
    prompt_results = await generate_all_prompts(product)

    print(f"\n[test] lifestyle prompts : {prompt_results['meta']['lifestyle_count']}")
    print(f"[test] feature prompts   : {prompt_results['meta']['feature_count']}")
    print(f"[test] environment       : {prompt_results['meta']['environment']}")
    print(f"[test] product size      : {prompt_results['meta']['product_size']}")

    print(f"\n[test] ── lifestyle prompts ─────────────────────────")
    for i, p in enumerate(prompt_results["lifestyle"]):
        print(f"  [{i+1}] {p[:120]}...")

    print(f"\n[test] ── feature prompts ───────────────────────────")
    for i, feat in enumerate(prompt_results["features"]):
        print(f"  [{i+1}] title      : {feat['title']}")
        print(f"       description: {feat['description'][:80]}...")
        print(f"       prompt     : {feat['prompt'][:100]}...")
        print()

    # ── Step 4: Generate images via OpenRouter (Gemini) ───────
    print(f"[test] ── STEP 2: GENERATING IMAGES (OpenRouter) ────")

    sku = (
        identity.get("sku")
        or identity.get("model")
        or "test-product"
    )

    image_results = await generate_product_images(
        lifestyle_prompts=prompt_results["lifestyle"],
        feature_prompts=prompt_results["features"],
        product_sku=sku,
        reference_image_path=reference_image_path,
    )

    # ── Step 5: Print file results ────────────────────────────
    print(f"\n[test] ── RESULTS ───────────────────────────────────")
    print(f"[test] folder          : {image_results['folder']}")
    print(f"[test] total generated : {image_results['total_generated']}")
    print(f"[test] total failed    : {image_results['total_failed']}")

    print(f"\n[test] lifestyle images:")
    for item in image_results["lifestyle"]:
        exists = "✓" if os.path.exists(item["path"]) else "✗ MISSING"
        print(f"  {exists}  {item['path']}")

    print(f"\n[test] feature images:")
    for item in image_results["features"]:
        exists = "✓" if os.path.exists(item["path"]) else "✗ MISSING"
        print(f"  {exists}  {item['path']}")
        print(f"         title      : {item['title']}")
        print(f"         description: {item.get('description','')[:80]}...")

    # ── Step 6: Build image entries for appending to input JSON ─
    print(f"\n[test] ── FETCHING EXCHANGE RATES ───────────────────")
    rates = await get_exchange_rates()
    print(f"[test] USD: 1.0 | INR: {rates['INR']} | AED: {rates['AED']}")

    def format_costs(cost_usd: float) -> dict:
        return {
            "USD": round(cost_usd, 6),
            "INR": round(cost_usd * rates["INR"], 6),
            "AED": round(cost_usd * rates["AED"], 6),
        }

    print(f"\n[test] ── FINAL SCHEMA images[] PREVIEW ─────────────")

    lifestyle_images = [
        {
            "url":  item["path"],
            "alt":  item["alt"],
            "type": "marketing",
            "cost": format_costs(item.get("cost", 0.0))
        }
        for item in image_results["lifestyle"]
    ]

    feature_images = [
        {
            "url":         item["path"],
            "alt":         item["alt"],
            "description": item.get("description", ""),
            "type":        "marketing",
            "cost":        format_costs(item.get("cost", 0.0))
        }
        for item in image_results["features"]
    ]

    # ── Step 7: Append generated images into the original product JSON ─
    if "images" not in product:
        product["images"] = {}

    product["images"]["lifestyle_images"] = lifestyle_images
    product["images"]["feature_images"]   = feature_images

    print(json.dumps(product["images"], indent=2))

    # ── Step 8: Update enrichment_metadata counters ───────────
    product["enrichment_metadata"] = {
        **product.get("enrichment_metadata", {}),
        "image_generation_status": (
            "success" if image_results["total_failed"] == 0
            else "partial" if image_results["total_generated"] > 0
            else "failed"
        ),
        "lifestyle_images_generated": len(image_results["lifestyle"]),
        "feature_images_generated":   len(image_results["features"]),
        "lifestyle_images_failed":    image_results["total_failed"],
        "feature_images_failed":      0,
    }

    print(f"\n[test] ── ENRICHMENT METADATA ───────────────────────")
    print(json.dumps(product["enrichment_metadata"], indent=2))

    # ── Step 9: Save enriched product JSON (original + generated images) ─
    output_path = "test_image_output.json"
    with open(output_path, "w") as f:
        json.dump(product, f, indent=2)

    print(f"\n[test] output saved → {output_path}")

    # ── Step 10: Zip output images folder as product_name.zip ─
    product_name = product.get("product_identity", {}).get("product_name", "product")
    safe_name = re.sub(r'[^\w\-]', '-', product_name).strip('-')
    safe_name = re.sub(r'-+', '-', safe_name)  # collapse multiple dashes
    zip_filename = f"{safe_name}.zip"
    images_folder = image_results["folder"]  # e.g. output/images/17022

    if os.path.isdir(images_folder):
        with zipfile.ZipFile(zip_filename, 'w', zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(images_folder):
                for file in files:
                    file_path = os.path.join(root, file)
                    arcname = os.path.relpath(file_path, os.path.dirname(images_folder))
                    zf.write(file_path, arcname)
        zip_size_mb = os.path.getsize(zip_filename) / (1024 * 1024)
        print(f"\n[test] ── ZIP CREATED ───────────────────────────────")
        print(f"[test] zip file : {zip_filename} ({zip_size_mb:.1f} MB)")
    else:
        print(f"\n[test] ⚠ images folder not found: {images_folder} — skipping zip")

    # ── Step 11: Clean up — permanently delete output/images & reference_cache ─
    for cleanup_dir in ["output/images", REFERENCE_IMAGE_CACHE]:
        if os.path.isdir(cleanup_dir):
            shutil.rmtree(cleanup_dir)
            print(f"[test] ✓ deleted: {cleanup_dir}/")

    print(f"[test] ── DONE ──────────────────────────────────────")


if __name__ == "__main__":
    asyncio.run(main())
