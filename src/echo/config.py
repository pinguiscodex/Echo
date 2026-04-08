"""Pydantic settings for Echo AI Chatbot."""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Literal, Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Load .env file from project root (parent of src/echo/)
env_path = Path(__file__).parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

# Config JSON path
CONFIG_PATH = Path(__file__).parent.parent.parent / "data" / "config.json"


class ConfigStore:
    """Save and load Echo settings from a JSON config file."""

    # All keys that are persisted to config.json
    KEYS = [
        "api_provider",
        "openrouter_model",
        "mistral_model",
        "whisper_model",
        "tts_voice",
        "temperature",
        "max_tokens",
        "system_prompt",
        "input_mode",
        "output_mode",
        "sample_rate",
        "enable_tools",
        "python_execution_timeout",
        "command_execution_timeout",
    ]

    @classmethod
    def save_config(cls, settings: "Settings", filepath: Optional[Path] = None) -> Path:
        """Serialise all user-editable settings to JSON."""
        path = filepath or CONFIG_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        data = {}
        for key in cls.KEYS:
            data[key] = getattr(settings, key)
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        return path

    @classmethod
    def load_config(cls, filepath: Optional[Path] = None) -> Optional[Dict[str, Any]]:
        """Load settings dict from JSON, or None if file doesn't exist."""
        path = filepath or CONFIG_PATH
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def apply_config(cls, settings: "Settings", data: Dict[str, Any]) -> None:
        """Apply loaded config values to the live Settings instance."""
        for key in cls.KEYS:
            if key in data:
                try:
                    object.__setattr__(settings, key, data[key])
                except Exception:
                    pass  # skip invalid values silently

    @classmethod
    def sync_to_env(cls, settings: "Settings") -> None:
        """Update os.environ so pydantic-settings picks up config.json values."""
        env_map = {
            "API_PROVIDER": settings.api_provider,
            "OPENROUTER_MODEL": settings.openrouter_model,
            "MISTRAL_MODEL": settings.mistral_model,
            "WHISPER_MODEL": settings.whisper_model,
            "TTS_VOICE": settings.tts_voice,
            "TEMPERATURE": str(settings.temperature),
            "MAX_TOKENS": str(settings.max_tokens),
            "SYSTEM_PROMPT": settings.system_prompt,
            "INPUT_MODE": settings.input_mode,
            "OUTPUT_MODE": settings.output_mode,
            "SAMPLE_RATE": str(settings.sample_rate),
            "ENABLE_TOOLS": str(settings.enable_tools).lower(),
            "PYTHON_EXECUTION_TIMEOUT": str(settings.python_execution_timeout),
            "COMMAND_EXECUTION_TIMEOUT": str(settings.command_execution_timeout),
        }
        for k, v in env_map.items():
            os.environ[k] = v


class Settings(BaseSettings):
    """Echo AI Chatbot settings loaded from environment variables."""

    # Pydantic V2 config (replaces class Config)
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    # API Configuration
    openrouter_api_key: str = Field(
        default="", description="OpenRouter API key for chat completions"
    )
    mistral_api_key: str = Field(default="", description="Mistral API key for chat completions")

    # API Provider Selection
    api_provider: Literal["openrouter", "mistral"] = Field(
        default="openrouter", description="API provider to use: openrouter or mistral"
    )

    # Model Configuration
    openrouter_model: str = Field(
        default="openai/gpt-oss-120b:free", description="OpenRouter model identifier"
    )
    mistral_model: str = Field(
        default="mistral-small-latest", description="Mistral model identifier"
    )

    # Whisper Configuration
    whisper_model: Literal[
        "tiny",
        "tiny.en",
        "base",
        "base.en",
        "small",
        "small.en",
        "medium",
        "medium.en",
        "large-v1",
        "large-v2",
        "large-v3",
        "distil-large-v3",
        "distil-medium.en",
        "distil-small.en",
        "distil-large-v2",
    ] = Field(default="base", description="Whisper speech-to-text model size (faster-whisper)")

    # TTS Configuration
    tts_voice: str = Field(default="en-US-JennyNeural", description="Edge TTS voice identifier")

    # Chat Configuration
    temperature: float = Field(
        default=0.7, ge=0.0, le=2.0, description="AI response temperature (0.0-2.0)"
    )
    max_tokens: int = Field(default=1024, ge=64, le=4096, description="Maximum tokens per response")
    system_prompt: str = Field(
        default="You are Echo, a helpful and friendly AI assistant. Provide clear, concise answers.",
        description="System prompt for the AI",
    )

    # Input/Output Configuration
    input_mode: Literal["text", "speech", "both"] = Field(
        default="both", description="Input mode: text, speech, or both"
    )
    output_mode: Literal["text", "speech", "both"] = Field(
        default="both", description="Output mode: text, speech, or both"
    )

    # Audio Configuration
    sample_rate: int = Field(default=16000, description="Audio sample rate for recording")

    # AI Agent Tools Configuration
    enable_tools: bool = Field(
        default=True, description="Enable AI agent tool calling capabilities"
    )
    python_execution_timeout: int = Field(
        default=30, ge=5, le=120, description="Timeout for Python code execution in seconds"
    )
    command_execution_timeout: int = Field(
        default=30, ge=5, le=120, description="Timeout for shell command execution in seconds"
    )


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance (singleton pattern)."""
    return Settings()


def reload_settings() -> Settings:
    """Reload settings: apply config.json → sync os.environ → reload from .env/envvars."""
    get_settings.cache_clear()
    s = Settings()
    # If config.json exists, apply it on top of defaults/.env
    data = ConfigStore.load_config()
    if data:
        ConfigStore.apply_config(s, data)
        ConfigStore.sync_to_env(s)
    return s
