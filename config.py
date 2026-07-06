# config.py
"""
Configuration for the product enrichment pipeline.

Add these new variables to your existing config.py.
If you use .env, add them there too.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── Existing (keep as-is) ──
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek/deepseek-chat")
LLM_API_KEY = os.getenv("LLM_API_KEY", "")


# ══════════════════════════════════════════════════════════
# NEW — Image Pipeline Config
# ══════════════════════════════════════════════════════════

# OpenRouter API key (for Gemini image generation)
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")

# Google Drive (for uploading generated images)
GDRIVE_SERVICE_ACCOUNT_FILE = os.getenv("GDRIVE_SERVICE_ACCOUNT_FILE", "service-account.json")
GDRIVE_FOLDER_ID = os.getenv("GDRIVE_FOLDER_ID", "")

# Image generation defaults
LIFESTYLE_IMAGE_COUNT = int(os.getenv("LIFESTYLE_IMAGE_COUNT", "3"))
MAX_SCRAPED_IMAGES = int(os.getenv("MAX_SCRAPED_IMAGES", "6"))

# ── Legacy (can remove after migration) ──
NANO_BANANA_API_KEY = os.getenv("NANO_BANANA_API_KEY", "")
DEFAULT_IMAGE_COUNT = int(os.getenv("DEFAULT_IMAGE_COUNT", "5"))
