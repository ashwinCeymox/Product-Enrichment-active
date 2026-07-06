# config.py
"""
Standalone config for the image generation test.
Reads all settings from environment variables or .env file.
"""

import os
from dotenv import load_dotenv

load_dotenv()

# ── OpenRouter (Image Generation) ──
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "")
IMAGE_MODEL = os.getenv("IMAGE_MODEL", "google/gemini-2.5-flash-image")

# ── LLM for prompt generation (via litellm → DeepSeek direct) ──
DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")
LLM_MODEL = os.getenv("LLM_MODEL", "deepseek/deepseek-chat")

# litellm reads DEEPSEEK_API_KEY from env automatically,
# but ensure it's set in case .env was loaded after litellm import
if DEEPSEEK_API_KEY:
    os.environ["DEEPSEEK_API_KEY"] = DEEPSEEK_API_KEY

# ── Output ──
IMAGE_OUTPUT_DIR = os.getenv("IMAGE_OUTPUT_DIR", "output/images")
