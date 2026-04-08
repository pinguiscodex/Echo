"""Chat history persistence service for Echo."""

import json
import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class ChatHistoryService:
    """Service for managing chat history persistence."""

    DEFAULT_PATH = Path("data/chat_history.json")

    def __init__(self, filepath: Optional[Path] = None):
        """Initialize the history service.

        Args:
            filepath: Path to the chat history file
        """
        self.filepath = filepath or self.DEFAULT_PATH

    def save(self, messages: List[Dict]) -> Path:
        """Save conversation history to file.

        Args:
            messages: List of message dictionaries

        Returns:
            Path to saved file
        """
        self.filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(messages, f, indent=2, ensure_ascii=False)

        logger.info("Chat history saved to: %s", self.filepath)
        return self.filepath

    def load(self) -> List[Dict]:
        """Load conversation history from file.

        Returns:
            List of message dictionaries, or empty list if file doesn't exist
        """
        if not self.filepath.exists():
            logger.info("No chat history found at: %s", self.filepath)
            return []

        try:
            with open(self.filepath, "r", encoding="utf-8") as f:
                messages = json.load(f)
            logger.info("Chat history loaded from: %s", self.filepath)
            return messages
        except Exception as e:
            logger.error("Failed to load chat history: %s", e)
            return []

    def exists(self) -> bool:
        """Check if chat history file exists."""
        return self.filepath.exists()

    def clear(self) -> None:
        """Delete the chat history file if it exists."""
        if self.filepath.exists():
            self.filepath.unlink()
            logger.info("Chat history file deleted: %s", self.filepath)

    def get_message_count(self, messages: List[Dict]) -> int:
        """Count user and assistant messages (excluding system)."""
        return len([m for m in messages if m.get("role") in ("user", "assistant")])
