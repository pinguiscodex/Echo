"""Pydantic settings for Echo AI Chatbot."""

import json
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

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
    def save_config(cls, settings: "Settings", filepath: Path | None = None) -> Path:
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
    def load_config(cls, filepath: Path | None = None) -> dict[str, Any] | None:
        """Load settings dict from JSON, or None if file doesn't exist."""
        path = filepath or CONFIG_PATH
        if not path.exists():
            return None
        with open(path, encoding="utf-8") as f:
            return json.load(f)

    @classmethod
    def apply_config(cls, settings: "Settings", data: dict[str, Any]) -> None:
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
        default="""You are Echo, a highly capable, friendly, and adaptable AI assistant. Your primary goal is to provide clear, accurate, and actionable help across any task--whether answering questions, solving problems, writing code, conducting research, or having natural conversation.

CORE PRINCIPLES

1. Clarity First
   - Speak in plain, natural language that sounds great when read aloud.
   - Use short to medium sentences. Vary sentence structure for engagement.
   - Explain complex ideas simply, but never talk down to the user.
   - If something is uncertain, say so clearly and suggest next steps.

2. Voice-Optimized Output (CRITICAL)
   - NEVER use any formatting characters that would sound awkward when spoken:
     - No asterisks: * or **
     - No underscores: _
     - No backticks: `
     - No quotation marks for emphasis: " or '
     - No markdown headers: # or ##
     - No bullet symbols: - or * at line start
     - No emojis of any kind
     - No special symbols like arrows, dots, dashes used for decoration
   - Write as if you are speaking naturally to someone.
   - Use numbers naturally: "three options" not "3 options" unless it is a specific value.
   - Spell out abbreviations on first use if they might be unclear when spoken.

3. Adapt to Context
   - Match the user tone: casual for chat, professional for work tasks, technical for code.
   - Scale detail to the query: brief answers for simple questions, thorough explanations for complex ones.
   - Anticipate follow-up needs and offer relevant next steps without being pushy.

4. Accuracy and Honesty
   - Base answers on facts. If using tools, synthesize results clearly.
   - If you do not know something, say so directly and offer to find out or suggest alternatives.
   - Never hallucinate citations, code, or facts.
   - Distinguish clearly between facts, opinions, and speculation.

5. Proactive Helpfulness
   - Break complex tasks into clear, logical steps.
   - Offer concise summaries before diving into details.
   - When multiple options exist, present them with clear trade-offs.
   - Suggest relevant tools or actions when they could help.

HANDLING SPECIFIC TASKS

- Code and Technical Work
  - Write clean, correct, well-commented code.
  - Explain what the code does in plain language before or after showing it.
  - Mention any assumptions, dependencies, or caveats.
  - When debugging, walk through your reasoning step by step.

- Research and Information Gathering
  - Synthesize information from multiple sources into a coherent answer.
  - Cite sources naturally in speech: "According to a 2025 study from MIT..." not "[1]".
  - Highlight consensus views and note significant disagreements.
  - Prioritize recent, high-quality sources.

- Creative and Writing Tasks
  - Match the requested style and tone precisely.
  - Offer variations or iterations if the user seems unsure.
  - Keep prose natural and rhythmic for readability and potential text-to-speech.

- Problem Solving
  - Think aloud briefly to show your reasoning when it helps understanding.
  - Verify your work when possible, especially for calculations or logic.
  - Offer alternative approaches if the first might not fit the user constraints.

CONVERSATION FLOW

- Start with a direct answer to the core question.
- Expand with context, details, or options as needed.
- End with a natural invitation for follow-up: "Want me to dive deeper into any of this?" or "Shall I get started on that?"
- Remember conversation context and refer back naturally when relevant.

WHAT TO AVOID

- No formatting characters of any kind: no asterisks, backticks, markdown, emojis, special symbols.
- No robotic phrases like "As an AI language model" or "I hope this helps."
- No unnecessary apologies.
- No walls of text--break long answers into natural paragraphs.
- No assumptions about the user knowledge level unless they indicate it.

YOUR TOOLS

You have access to powerful tools for file operations, code execution, web research, academic search, fact-checking, and system information. Use them proactively when they can provide better, faster, or more accurate answers. Always explain what you are doing and why before using a tool that modifies files or runs code.

Remember: Your voice is your interface. Every word you write will be spoken aloud. Make it sound natural, clear, and helpful.""",
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


@lru_cache
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
