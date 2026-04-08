"""Tests for Echo services."""

import json
from pathlib import Path

import pytest

from echo.services.history import ChatHistoryService


class TestChatHistoryService:
    """Tests for ChatHistoryService."""

    def test_save_history(self, tmp_path):
        """Test saving chat history."""
        history_file = tmp_path / "chat_history.json"
        service = ChatHistoryService(history_file)

        messages = [
            {"role": "system", "content": "You are a test assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi!"},
        ]

        saved_path = service.save(messages)
        assert saved_path == history_file
        assert history_file.exists()

        content = json.loads(history_file.read_text())
        assert len(content) == 3

    def test_load_history(self, tmp_path):
        """Test loading chat history."""
        history_file = tmp_path / "chat_history.json"
        messages = [
            {"role": "user", "content": "Test"},
        ]
        history_file.write_text(json.dumps(messages))

        service = ChatHistoryService(history_file)
        loaded = service.load()
        assert len(loaded) == 1
        assert loaded[0]["content"] == "Test"

    def test_load_nonexistent(self, tmp_path):
        """Test loading nonexistent history."""
        history_file = tmp_path / "nonexistent.json"
        service = ChatHistoryService(history_file)
        loaded = service.load()
        assert loaded == []

    def test_exists(self, tmp_path):
        """Test exists method."""
        history_file = tmp_path / "chat_history.json"
        service = ChatHistoryService(history_file)

        assert service.exists() is False
        history_file.touch()
        assert service.exists() is True

    def test_clear(self, tmp_path):
        """Test clear method."""
        history_file = tmp_path / "chat_history.json"
        history_file.write_text("[]")

        service = ChatHistoryService(history_file)
        service.clear()
        assert not history_file.exists()

    def test_get_message_count(self, tmp_path):
        """Test message counting."""
        service = ChatHistoryService(tmp_path / "dummy.json")

        messages = [
            {"role": "system", "content": "System"},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi"},
            {"role": "user", "content": "How are you?"},
            {"role": "assistant", "content": "Good!"},
        ]

        count = service.get_message_count(messages)
        assert count == 4  # Excludes system message

    def test_default_path(self):
        """Test default path is set."""
        service = ChatHistoryService()
        assert service.filepath == ChatHistoryService.DEFAULT_PATH
