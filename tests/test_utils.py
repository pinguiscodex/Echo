"""Tests for Echo utilities."""

import json
import logging
from pathlib import Path

import pytest

from echo.utils.helpers import (
    cleanup_temp_files,
    ensure_directories,
    format_timestamp,
    load_chat_history,
    save_chat_history,
)
from echo.utils.logging import setup_logging


class TestSetupLogging:
    """Tests for setup_logging."""

    def test_setup_logging_creates_file(self, tmp_path):
        """Test that logging creates a log file."""
        log_file = tmp_path / "test.log"
        setup_logging(log_level="DEBUG", log_file=log_file, console_output=False)

        # Log something
        logging.info("Test message")

        assert log_file.exists()
        content = log_file.read_text()
        assert "Test message" in content

    def test_setup_logging_default_path(self, tmp_path):
        """Test logging with default path."""
        import os

        os.chdir(tmp_path)
        setup_logging(log_level="INFO", console_output=False)
        assert (tmp_path / "logs" / "echo.log").exists()


class TestLoadChatHistory:
    """Tests for load_chat_history."""

    def test_load_existing_history(self, tmp_path):
        """Test loading existing chat history."""
        history_file = tmp_path / "chat_history.json"
        messages = [
            {"role": "system", "content": "You are a test assistant."},
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there!"},
        ]
        history_file.write_text(json.dumps(messages))

        loaded = load_chat_history(history_file)
        assert len(loaded) == 3
        assert loaded[1]["role"] == "user"

    def test_load_nonexistent_history(self, tmp_path):
        """Test loading nonexistent history returns empty list."""
        history_file = tmp_path / "nonexistent.json"
        loaded = load_chat_history(history_file)
        assert loaded == []


class TestSaveChatHistory:
    """Tests for save_chat_history."""

    def test_save_history(self, tmp_path):
        """Test saving chat history."""
        history_file = tmp_path / "chat_history.json"
        messages = [
            {"role": "user", "content": "Test"},
        ]

        saved_path = save_chat_history(messages, history_file)
        assert saved_path == history_file
        assert history_file.exists()

        # Verify content
        loaded = json.loads(history_file.read_text())
        assert len(loaded) == 1


class TestFormatTimestamp:
    """Tests for format_timestamp."""

    def test_format_valid_timestamp(self):
        """Test formatting valid timestamp."""
        result = format_timestamp("2024-01-01T12:30:45")
        assert result == "12:30:45"

    def test_format_invalid_timestamp(self):
        """Test formatting invalid timestamp."""
        result = format_timestamp("not-a-timestamp")
        assert result == "??:??:??"

    def test_format_current_time(self):
        """Test formatting current time."""
        result = format_timestamp()
        assert len(result) == 8  # HH:MM:SS


class TestCleanupTempFiles:
    """Tests for cleanup_temp_files."""

    def test_cleanup_removes_files(self, tmp_path):
        """Test cleanup removes matching files."""
        (tmp_path / "rec_001.wav").touch()
        (tmp_path / "rec_002.wav").touch()
        (tmp_path / "keep.txt").touch()

        removed = cleanup_temp_files(tmp_path, "rec_*.wav")
        assert removed == 2
        assert (tmp_path / "keep.txt").exists()
        assert not (tmp_path / "rec_001.wav").exists()

    def test_cleanup_empty_directory(self, tmp_path):
        """Test cleanup on empty directory."""
        removed = cleanup_temp_files(tmp_path)
        assert removed == 0


class TestEnsureDirectories:
    """Tests for ensure_directories."""

    def test_ensure_existing_dirs(self, tmp_path):
        """Test ensure with existing directories."""
        data_dir = tmp_path / "data"
        data_dir.mkdir()

        import os

        os.chdir(tmp_path)

        created = ensure_directories()
        # data already exists, logs should be created
        assert len(created) >= 1

    def test_ensure_creates_dirs(self, tmp_path):
        """Test that ensure creates missing directories."""
        import os

        os.chdir(tmp_path)

        ensure_directories()

        assert (tmp_path / "data").exists()
        assert (tmp_path / "logs").exists()
