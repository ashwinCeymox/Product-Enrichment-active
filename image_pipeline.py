"""
Image Pipeline — Main orchestrator for product image generation.

Coordinates:
  1. Scraped image selection (from input HTML)
  2. Lifestyle image generation (3x, different viewing angles)
  3. Feature image generation (4-5x, one per key feature)

Usage:
    from image_pipeline import ImagePipeline

    pipeline = ImagePipeline()
    result = pipeline.generate_all_images(product_data)
    # result = {
    #     "scraped_images": [...],
    #     "lifestyle_images": [...],
    #     "feature_images": [...]
    # }
"""

import re
import prompt_agent
from image_generator import ImageGenerator
from gdrive_uploader import GDriveUploader
import config


class ImagePipeline:
    """End-to-end image generation pipeline for product enrichment."""

    def __init__(
        self,
        openrouter_api_key: str = None,
        gdrive_service_account: str = None,
        gdrive_folder_id: str = None,
    ):
        self.image_gen = ImageGenerator(api_key=openrouter_api_key)
        self.uploader = GDriveUploader(
            service_account_file=gdrive_service_account,
            folder_id=gdrive_folder_id,
        )

    # ─────────────────────────────────────────────────────
    # Main entry point
    # ─────────────────────────────────────────────────────

    def generate_all_images(self, product_data: dict) -> dict:
        """
        Generate all image arrays for a product.

        Args:
            product_data: The enriched product JSON from Phase 5.
                Must contain: product_identity, images (scraped), long_description,
                key_features.

        Returns:
            {
                "scraped_images": [...],
                "lifestyle_images": [...],
                "feature_images": [...],
                "generation_status": {
                    "lifestyle_status": "success" | "partial" | "failed",
                    "feature_status": "success" | "partial" | "failed",
                    "lifestyle_generated": int,
                    "feature_generated": int,
                    "lifestyle_failed": int,
                    "feature_failed": int,
                }
            }
        """
        print("\n" + "=" * 60)
        print("IMAGE PIPELINE — Starting")
        print("=" * 60)

        # ── Step 1: Extract and select scraped images ──
        scraped_images = self._select_scraped_images(product_data)
        print(f"\n[Pipeline] Selected {len(scraped_images)} scraped images")

        # ── Step 2: Select best reference image ──
        reference_url = self._select_reference_image(scraped_images)
        if not reference_url:
            print("[Pipeline] WARNING: No reference image found — skipping generation")
            return {
                "scraped_images": scraped_images,
                "lifestyle_images": [],
                "feature_images": [],
                "generation_status": {
                    "lifestyle_status": "failed",
                    "feature_status": "failed",
                    "lifestyle_generated": 0,
                    "feature_generated": 0,
                    "lifestyle_failed": 0,
                    "feature_failed": 0,
                },
            }

        print(f"[Pipeline] Reference image: {reference_url[:80]}...")

        # ── Step 3: Get product context ──
        description = self._get_description(product_data)
        category = self._get_category(product_data)
        key_features = self._get_key_features(product_data)

        print(f"[Pipeline] Category: {category}")
        print(f"[Pipeline] Key features: {len(key_features)}")

        # ── Step 4: Generate lifestyle images ──
        print(f"\n{'─' * 40}")
        print(f"GENERATING LIFESTYLE IMAGES ({config.LIFESTYLE_IMAGE_COUNT}x)")
        print(f"{'─' * 40}")

        lifestyle_images, lifestyle_stats = self._generate_lifestyle_images(
            reference_url=reference_url,
            description=description,
            category=category,
            count=config.LIFESTYLE_IMAGE_COUNT,
        )

        # ── Step 5: Generate feature images ──
        print(f"\n{'─' * 40}")
        print(f"GENERATING FEATURE IMAGES ({len(key_features)}x)")
        print(f"{'─' * 40}")

        feature_images, feature_stats = self._generate_feature_images(
            reference_url=reference_url,
            key_features=key_features,
            category=category,
        )

        # ── Step 6: Assemble final result ──
        result = {
            "scraped_images": scraped_images,
            "lifestyle_images": lifestyle_images,
            "feature_images": feature_images,
            "generation_status": {
                "lifestyle_status": self._compute_status(
                    lifestyle_stats["generated"],
                    lifestyle_stats["failed"],
                    config.LIFESTYLE_IMAGE_COUNT
                ),
                "feature_status": self._compute_status(
                    feature_stats["generated"],
                    feature_stats["failed"],
                    len(key_features)
                ),
                "lifestyle_generated": lifestyle_stats["generated"],
                "feature_generated": feature_stats["generated"],
                "lifestyle_failed": lifestyle_stats["failed"],
                "feature_failed": feature_stats["failed"],
            },
        }

        total = len(scraped_images) + len(lifestyle_images) + len(feature_images)
        print(f"\n{'=' * 60}")
        print(f"IMAGE PIPELINE — Complete")
        print(f"  Scraped: {len(scraped_images)}")
        print(f"  Lifestyle: {len(lifestyle_images)}/{config.LIFESTYLE_IMAGE_COUNT}")
        print(f"  Feature: {len(feature_images)}/{len(key_features)}")
        print(f"  Total: {total}")
        print(f"{'=' * 60}\n")

        return result

    # ─────────────────────────────────────────────────────
    # Scraped image selection
    # ─────────────────────────────────────────────────────

    def _select_scraped_images(self, product_data: dict) -> list:
        """
        Extract and filter scraped images from the product data.
        Keeps only genuine product images, filters out icons/logos/banners.
        """
        raw_images = product_data.get("images", [])

        # If images is a flat list of URLs (strings)
        if raw_images and isinstance(raw_images[0], str):
            raw_images = [
                {"url": url, "alt": f"Product Image {i+1}", "type": "product"}
                for i, url in enumerate(raw_images)
            ]

        # Filter out non-product images
        filtered = []
        skip_patterns = [
            r"logo", r"icon", r"badge", r"banner", r"footer",
            r"sprite", r"placeholder", r"loading", r"arrow",
            r"1x1", r"pixel", r"tracking", r"favicon"
        ]

        for img in raw_images:
            url = img.get("url", "")
            alt = img.get("alt", "")
            img_type = img.get("type", "")

            # Skip marketing images (those are generated, not scraped)
            if img_type == "marketing":
                continue

            # Skip tiny/tracking images
            text_to_check = f"{url} {alt}".lower()
            if any(re.search(p, text_to_check) for p in skip_patterns):
                continue

            # Skip very short URLs (likely broken)
            if len(url) < 20:
                continue

            filtered.append({
                "url": url,
                "alt": alt or f"Product Image",
                "type": "product",
            })

        # Cap at max scraped images
        return filtered[:config.MAX_SCRAPED_IMAGES]

    def _select_reference_image(self, scraped_images: list) -> str:
        """
        Select the best product image to use as reference for image generation.
        Prefers the first image (usually the hero/primary product shot).
        """
        if not scraped_images:
            return ""

        # Use the first scraped image (typically the hero shot)
        return scraped_images[0].get("url", "")

    # ─────────────────────────────────────────────────────
    # Lifestyle image generation
    # ─────────────────────────────────────────────────────

    def _generate_lifestyle_images(
        self,
        reference_url: str,
        description: str,
        category: str,
        count: int = 3,
    ) -> tuple:
        """
        Generate N lifestyle images with different viewing angles.

        Returns:
            (list_of_image_dicts, stats_dict)
        """
        images = []
        stats = {"generated": 0, "failed": 0}

        for i in range(count):
            print(f"\n  [Lifestyle {i+1}/{count}]")

            # Step 1: Generate prompt via agent
            print(f"  → Generating prompt (angle: {prompt_agent.LIFESTYLE_ANGLE_STRATEGIES[i % 3]['name']})...")
            image_prompt = prompt_agent.generate_lifestyle_prompt(
                description=description,
                category=category,
                iteration_index=i,
            )

            if not image_prompt:
                print(f"  ✗ Prompt generation failed — skipping")
                stats["failed"] += 1
                continue

            print(f"  → Prompt: {image_prompt[:100]}...")

            # Step 2: Generate image via Gemini
            gen_result = self.image_gen.generate(
                reference_image_url=reference_url,
                prompt=image_prompt,
            )

            if not gen_result["success"]:
                print(f"  ✗ Image generation failed: {gen_result['error']}")
                stats["failed"] += 1
                continue

            # Step 3: Upload to Google Drive
            upload_result = self.uploader.upload_base64_image(
                base64_data=gen_result["image_data"],
                filename=None,  # auto-generated
                mime_type=gen_result["mime_type"],
            )

            if not upload_result["success"]:
                print(f"  ✗ Upload failed: {upload_result['error']}")
                stats["failed"] += 1
                continue

            # Success
            angle_name = prompt_agent.LIFESTYLE_ANGLE_STRATEGIES[i % 3]["name"]
            images.append({
                "url": upload_result["url"],
                "drive_url": upload_result["drive_url"],
                "file_id": upload_result["file_id"],
                "alt": f"Lifestyle {angle_name.replace('_', ' ').title()} Shot",
                "type": "lifestyle",
                "prompt_used": image_prompt,
            })
            stats["generated"] += 1
            print(f"  ✓ Done — {upload_result['url'][:60]}...")

        return images, stats

    # ─────────────────────────────────────────────────────
    # Feature image generation
    # ─────────────────────────────────────────────────────

    def _generate_feature_images(
        self,
        reference_url: str,
        key_features: list,
        category: str,
    ) -> tuple:
        """
        Generate one image per key feature.

        Args:
            reference_url: URL of the reference product image.
            key_features: List of dicts with "title" and "description".
            category: Product category string.

        Returns:
            (list_of_image_dicts, stats_dict)
        """
        images = []
        stats = {"generated": 0, "failed": 0}

        if not key_features:
            print("  [Feature] No key features found — skipping")
            return images, stats

        for i, feature in enumerate(key_features):
            title = feature.get("title", f"Feature {i+1}")
            description = feature.get("description", "")

            print(f"\n  [Feature {i+1}/{len(key_features)}] {title}")

            if not description:
                print(f"  ✗ No description for feature — skipping")
                stats["failed"] += 1
                continue

            # Step 1: Generate prompt via agent
            print(f"  → Generating feature prompt...")
            image_prompt = prompt_agent.generate_feature_prompt(
                feature_title=title,
                feature_description=description,
                category=category,
            )

            if not image_prompt:
                print(f"  ✗ Prompt generation failed — skipping")
                stats["failed"] += 1
                continue

            print(f"  → Prompt: {image_prompt[:100]}...")

            # Step 2: Generate image via Gemini
            gen_result = self.image_gen.generate(
                reference_image_url=reference_url,
                prompt=image_prompt,
            )

            if not gen_result["success"]:
                print(f"  ✗ Image generation failed: {gen_result['error']}")
                stats["failed"] += 1
                continue

            # Step 3: Upload to Google Drive
            upload_result = self.uploader.upload_base64_image(
                base64_data=gen_result["image_data"],
                filename=None,
                mime_type=gen_result["mime_type"],
            )

            if not upload_result["success"]:
                print(f"  ✗ Upload failed: {upload_result['error']}")
                stats["failed"] += 1
                continue

            # Success
            images.append({
                "url": upload_result["url"],
                "drive_url": upload_result["drive_url"],
                "file_id": upload_result["file_id"],
                "alt": f"{title} — Feature Highlight",
                "type": "feature",
                "feature_title": title,
                "feature_description": description,
                "prompt_used": image_prompt,
            })
            stats["generated"] += 1
            print(f"  ✓ Done — {upload_result['url'][:60]}...")

        return images, stats

    # ─────────────────────────────────────────────────────
    # Helpers
    # ─────────────────────────────────────────────────────

    def _get_description(self, product_data: dict) -> str:
        """Extract the best description from product data."""
        # Priority: long_description > about_this_item joined > short_description
        desc = product_data.get("long_description", "")
        if desc:
            return desc

        about = product_data.get("about_this_item", [])
        if about:
            return " ".join(about)

        return product_data.get("short_description", "")

    def _get_category(self, product_data: dict) -> str:
        """Extract product category."""
        identity = product_data.get("product_identity", {})
        return identity.get("product_category", "GENERAL FITNESS EQUIPMENT")

    def _get_key_features(self, product_data: dict) -> list:
        """Extract key features list."""
        features = product_data.get("key_features", [])
        if not features:
            return []

        # Ensure each feature has title and description
        valid = []
        for f in features:
            if isinstance(f, dict) and f.get("title") and f.get("description"):
                valid.append(f)

        return valid

    @staticmethod
    def _compute_status(generated: int, failed: int, total: int) -> str:
        """Compute generation status string."""
        if generated == total:
            return "success"
        elif generated > 0:
            return "partial"
        else:
            return "failed"


# ─────────────────────────────────────────────────────
# Standalone test / CLI usage
# ─────────────────────────────────────────────────────

if __name__ == "__main__":
    # Example: Test with JOOLA Magnus CAS 14mm product data
    test_product = {
        "product_identity": {
            "brand": "JOOLA",
            "product_name": "JOOLA Tyson McGuffin Magnus CAS 14mm Pickleball Paddle",
            "model": "Magnus CAS 14mm",
            "product_category": "PICKLEBALL PADDLE",
        },
        "images": [
            {
                "url": "https://joola.com/cdn/shop/files/3_0008_2R1A5206-19_07b51b87-2025-4943-8ffd-3d5aac432b79.jpg?v=1768589884",
                "alt": "Magnus CAS Front View",
                "type": "product",
            },
            {
                "url": "https://joola.com/cdn/shop/files/magnus-cas-back.jpg",
                "alt": "Magnus CAS Back View",
                "type": "product",
            },
        ],
        "long_description": (
            "Emblazoned with an eye-catching lion graphic on its paddle face, "
            "the JOOLA Magnus CAS 14mm Pickleball Paddle was designed to highlight "
            "the distinctive roar of pickleball's most electrifying man, Tyson McGuffin. "
            "Engineered with JOOLA's first edgeless design, the Magnus CAS uses double "
            "frame carbon fiber construction to increase performance and stability while "
            "removing the edge guard for a larger hitting area. The 14mm core provides a "
            "balanced blend of power and control, while the Carbon Abrasion Surface (CAS) "
            "technology creates a unique textured surface for increased spin. This lightweight "
            "elongated paddle features a 5-inch Feel-Tec Pure grip and an average weight of "
            "7.8oz, making it ideal for advanced players seeking swifter swings and an "
            "enlarged sweet spot."
        ),
        "key_features": [
            {
                "title": "Carbon Abrasion Surface (CAS)",
                "description": (
                    "Our CAS technology utilizes a multi-step, abrasion sand-blasted "
                    "process, creating a unique, textured surface for increased spin."
                ),
            },
            {
                "title": "Edgeless Design",
                "description": (
                    "Engineered with a double frame to increase durability and strength "
                    "while allowing for no edge guard and a larger hitting area. Stays "
                    "lightweight for faster swings."
                ),
            },
            {
                "title": "Elongated Shape",
                "description": (
                    "A longer hitting surface combined with a shorter handle for added "
                    "power and reach, ideal for cross-over tennis players."
                ),
            },
            {
                "title": "NFC Chip Accessible",
                "description": (
                    "Unlock the JOOLA experience with NFC chip-enabled technology. "
                    "Tap your phone to the handle to authenticate your paddle and "
                    "unlock an extended 12-month warranty through JOOLA Connect."
                ),
            },
        ],
    }

    pipeline = ImagePipeline()
    result = pipeline.generate_all_images(test_product)

    # Pretty print the result
    import json
    print("\n\nFINAL OUTPUT:")
    print(json.dumps(result, indent=2))
