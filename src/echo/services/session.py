"""Chat session management -- per-session history persistence."""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

SESSIONS_DIR = Path("data/chat_sessions")


class ChatSession:
    """Represents a single chat session."""

    def __init__(
        self,
        session_id: str,
        timestamp: str,
        messages: list[dict[str, Any]] | None = None,
    ):
        self.session_id = session_id
        self.timestamp = timestamp
        self.messages = messages or []

    @property
    def message_count(self) -> int:
        """Count user and assistant messages (excluding system)."""
        return len([m for m in self.messages if m.get("role") in ("user", "assistant")])

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "session_id": self.session_id,
            "timestamp": self.timestamp,
            "messages": self.messages,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ChatSession":
        """Deserialize from dict."""
        return cls(
            session_id=data["session_id"],
            timestamp=data["timestamp"],
            messages=data.get("messages", []),
        )


class ChatSessionManager:
    """Manages per-session chat history in data/chat_sessions/."""

    def __init__(self, sessions_dir: Path | None = None):
        self.sessions_dir = sessions_dir or SESSIONS_DIR
        self.sessions_dir.mkdir(parents=True, exist_ok=True)
        self.current_session: ChatSession | None = None

    def create_session(
        self,
        timestamp: str | None = None,
        system_prompt: str | None = None,
    ) -> ChatSession:
        """Create a new chat session.

        Args:
            timestamp: ISO timestamp string (auto-generated if None).
            system_prompt: System prompt to seed the session with.

        Returns:
            The new ChatSession instance.
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        self.current_session = ChatSession(
            session_id=timestamp, timestamp=timestamp, messages=messages
        )
        self._save_session(self.current_session)
        logger.info("New chat session created: %s", timestamp)
        return self.current_session

    def get_session_file(self, session: ChatSession) -> Path:
        """Get the file path for a session."""
        return self.sessions_dir / f"{session.session_id}.json"

    def _save_session(self, session: ChatSession) -> Path:
        """Save a session to disk."""
        filepath = self.get_session_file(session)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(session.to_dict(), f, indent=2, ensure_ascii=False)
        return filepath

    def save_current_session(self) -> Path | None:
        """Save the current active session."""
        if self.current_session is None:
            return None
        return self._save_session(self.current_session)

    def add_message(self, role: str, content: str) -> None:
        """Add a message to the current session."""
        if self.current_session is None:
            return
        self.current_session.messages.append({"role": role, "content": content})
        self._save_session(self.current_session)

    def list_sessions(self) -> list[ChatSession]:
        """List all saved sessions, sorted newest first."""
        sessions = []
        if not self.sessions_dir.exists():
            return sessions
        for filepath in sorted(self.sessions_dir.glob("*.json"), reverse=True):
            try:
                with open(filepath, encoding="utf-8") as f:
                    data = json.load(f)
                sessions.append(ChatSession.from_dict(data))
            except (json.JSONDecodeError, KeyError, ValueError):
                continue
        return sessions

    def load_session(self, session_id: str) -> ChatSession | None:
        """Load a specific session by ID.

        Args:
            session_id: The session timestamp/ID to load.

        Returns:
            The loaded ChatSession, or None if not found.
        """
        filepath = self.sessions_dir / f"{session_id}.json"
        if not filepath.exists():
            logger.warning("Session file not found: %s", filepath)
            return None
        try:
            with open(filepath, encoding="utf-8") as f:
                data = json.load(f)
            self.current_session = ChatSession.from_dict(data)
            logger.info("Session loaded: %s", session_id)
            return self.current_session
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.error("Failed to load session %s: %s", session_id, e)
            return None

    def delete_session(self, session_id: str) -> bool:
        """Delete a session file.

        Args:
            session_id: The session timestamp/ID to delete.

        Returns:
            True if deleted, False if not found.
        """
        filepath = self.sessions_dir / f"{session_id}.json"
        if filepath.exists():
            filepath.unlink()
            logger.info("Session deleted: %s", session_id)
            return True
        return False

    def get_messages(self) -> list[dict[str, Any]]:
        """Get messages from the current session."""
        if self.current_session is None:
            return []
        return self.current_session.messages.copy()

    def set_messages(self, messages: list[dict[str, Any]]) -> None:
        """Replace messages in the current session."""
        if self.current_session is None:
            return
        self.current_session.messages = messages
        self._save_session(self.current_session)
