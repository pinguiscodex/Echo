"""Input validation and type guards for Echo."""

from pathlib import Path


def is_valid_api_key(key: str) -> bool:
    """Check if an API key looks valid (non-empty, not placeholder)."""
    if not key or not key.strip():
        return False
    placeholders = [
        "your_openrouter_api_key_here",
        "your_mistral_api_key_here",
        "your_api_key_here",
    ]
    return key.strip() not in placeholders


def is_valid_audio_path(path: Path) -> bool:
    """Check if a path is a valid audio file."""
    if not path.exists():
        return False
    valid_extensions = {".wav", ".mp3", ".ogg", ".flac", ".m4a"}
    return path.suffix.lower() in valid_extensions


def sanitize_input(text: str, max_length: int = 4096) -> str:
    """Sanitize user input text."""
    if not text:
        return ""
    text = text.strip()
    if len(text) > max_length:
        text = text[:max_length]
    return text


def validate_sample_rate(rate: int) -> bool:
    """Validate audio sample rate."""
    valid_rates = {8000, 11025, 16000, 22050, 44100, 48000}
    return rate in valid_rates


def validate_temperature(temp: float) -> bool:
    """Validate temperature value."""
    return 0.0 <= temp <= 2.0


def validate_max_tokens(tokens: int) -> bool:
    """Validate max tokens value."""
    return 64 <= tokens <= 4096
