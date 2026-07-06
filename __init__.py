"""
Product Enrichment — Image Generation Pipeline

Modules:
  - config: Credentials and configuration management
  - prompt_agent: LLM-based image prompt generator
  - image_generator: OpenRouter/Gemini image generation
  - gdrive_uploader: Google Drive image upload and link generation
  - image_pipeline: Main orchestrator (entry point)
"""

from .image_pipeline import ImagePipeline
from .prompt_agent import generate_lifestyle_prompt, generate_feature_prompt
from .image_generator import ImageGenerator
from .gdrive_uploader import GDriveUploader

__all__ = [
    "ImagePipeline",
    "generate_lifestyle_prompt",
    "generate_feature_prompt",
    "ImageGenerator",
    "GDriveUploader",
]
