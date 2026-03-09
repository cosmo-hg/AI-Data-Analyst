"""
Configuration Module
Stores model configurations and environment settings.
Only Gemini models are available.
"""

import os
from dataclasses import dataclass
from typing import Optional, List


@dataclass
class ModelConfig:
    """Configuration for an LLM model."""
    name: str           # Internal name (used in API)
    display_name: str   # Name shown in UI
    provider: str       # 'gemini'
    size: str           # Model size for display
    description: str    # Brief description


# Available models - Gemini 2026 models
AVAILABLE_MODELS = [
    ModelConfig(
        name="gemini-2.5-flash",
        display_name="Gemini 2.5 Flash",
        provider="gemini",
        size="Cloud",
        description="Best for most use cases - fast and efficient"
    ),
    ModelConfig(
        name="gemini-3-flash-preview",
        display_name="Gemini 3 Flash (Preview)",
        provider="gemini",
        size="Cloud",
        description="Most intelligent Flash model - newest preview"
    ),
    ModelConfig(
        name="gemini-2.5-pro",
        display_name="Gemini 2.5 Pro",
        provider="gemini",
        size="Cloud",
        description="More powerful - lower rate limits on free tier"
    ),
]


def get_model_by_name(name: str) -> Optional[ModelConfig]:
    """Get a model configuration by its internal name."""
    for model in AVAILABLE_MODELS:
        if model.name == name:
            return model
    return None


def get_all_models() -> List[ModelConfig]:
    """Get all available models."""
    return AVAILABLE_MODELS


def get_gemini_api_key() -> Optional[str]:
    """Get the Gemini API key from environment."""
    return os.environ.get("GEMINI_API_KEY")


def has_gemini_api_key() -> bool:
    """Check if Gemini API key is configured."""
    key = get_gemini_api_key()
    return key is not None and len(key) > 0


# Default model - Gemini 2.5 Flash
DEFAULT_MODEL = "gemini-2.5-flash"
