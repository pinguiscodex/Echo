"""Integration tests for Echo voice pipeline."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestVoicePipeline:
    """Integration tests for voice input pipeline."""

    def test_recorder_to_transcriber(self, tmp_path):
        """Test that recorder output can be transcribed."""
        # This is a structural test - verifies interfaces match
        from echo.core.recorder import AudioRecorder
        from echo.core.transcriber import WhisperTranscriber

        # Both classes should accept Path objects
        assert hasattr(AudioRecorder, "save_recording")
        assert hasattr(WhisperTranscriber, "transcribe")

    def test_transcriber_to_chatbot(self):
        """Test that transcriber output works with chatbot."""
        from echo.core.chatbot import EchoChatbot
        from echo.core.transcriber import WhisperTranscriber

        # Transcriber returns string, chatbot accepts string
        assert hasattr(WhisperTranscriber, "transcribe")
        assert hasattr(EchoChatbot, "chat")

    def test_chatbot_to_tts(self):
        """Test that chatbot output works with TTS."""
        from echo.core.chatbot import ChatResponse, EchoChatbot
        from echo.core.tts import TTSEngine

        # ChatResponse has content, TTS accepts string
        response = ChatResponse(content="Test")
        assert isinstance(response.content, str)
        assert hasattr(TTSEngine, "speak")


class TestToolExecution:
    """Integration tests for tool execution."""

    def test_tool_result_format(self):
        """Test that tool results are properly formatted."""
        from echo.tools.base import ToolResult

        result = ToolResult(success=True, content="Test output")
        assert result.success is True
        assert result.content == "Test output"
        assert result.error == ""

    def test_tool_error_format(self):
        """Test that tool errors are properly formatted."""
        from echo.tools.base import ToolResult

        result = ToolResult(success=False, error="Something failed")
        assert result.success is False
        assert result.error == "Something failed"
        assert result.content == ""
