"""Pure utility functions for Echo AI Chatbot."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


def load_chat_history(filepath: Optional[Path] = None) -> List[Dict]:
    """Load chat history from JSON file."""
    if filepath is None:
        filepath = Path("data/chat_history.json")

    if not filepath.exists():
        return []

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            messages = json.load(f)
        logging.info("Loaded %d messages from %s", len(messages), filepath)
        return messages
    except Exception as e:
        logging.error("Failed to load chat history: %s", e)
        return []


def save_chat_history(messages: List[Dict], filepath: Optional[Path] = None) -> Path:
    """Save chat history to JSON file."""
    if filepath is None:
        filepath = Path("data/chat_history.json")

    filepath.parent.mkdir(parents=True, exist_ok=True)

    try:
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)
        logging.info("Saved %d messages to %s", len(messages), filepath)
        return filepath
    except Exception as e:
        logging.error("Failed to save chat history: %s", e)
        raise


def format_timestamp(timestamp: Optional[str] = None) -> str:
    """Format a timestamp for display."""
    if timestamp:
        try:
            dt = datetime.fromisoformat(timestamp)
            return dt.strftime("%H:%M:%S")
        except ValueError:
            return "??:??:??"
    return datetime.now().strftime("%H:%M:%S")


def cleanup_temp_files(directory: Path = Path("data"), pattern: str = "rec_*.wav") -> int:
    """Clean up temporary audio files."""
    if not directory.exists():
        return 0

    removed = 0
    for filepath in directory.glob(pattern):
        try:
            filepath.unlink()
            removed += 1
        except Exception as e:
            logging.warning("Failed to remove %s: %s", filepath, e)

    if removed > 0:
        logging.info("Cleaned up %d temporary files", removed)

    return removed


def ensure_directories() -> List[Path]:
    """Ensure all required directories exist."""
    directories = [
        Path("data"),
        Path("logs"),
    ]

    created = []
    for directory in directories:
        if not directory.exists():
            directory.mkdir(parents=True, exist_ok=True)
            created.append(directory)
            logging.info("Created directory: %s", directory)

    return created
