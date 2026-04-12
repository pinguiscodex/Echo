"""Tests for Echo chatbot functionality."""

import json
from unittest.mock import MagicMock, patch

import pytest


class TestChatResponse:
    """Tests for ChatResponse class."""

    def test_empty_response(self):
        """Test empty chat response."""
        from echo.core.chatbot import ChatResponse

        response = ChatResponse()
        assert response.content == ""
        assert not response.has_tool_calls()
        assert not response

    def test_response_with_content(self):
        """Test response with content."""
        from echo.core.chatbot import ChatResponse

        response = ChatResponse(content="Hello!")
        assert response.content == "Hello!"
        assert not response.has_tool_calls()
        assert bool(response)

    def test_response_with_tool_calls(self):
        """Test response with tool calls."""
        from echo.core.chatbot import ChatResponse

        tool_calls = [{"id": "1", "function": {"name": "test", "arguments": "{}"}}]
        response = ChatResponse(content="Using tool", tool_calls=tool_calls)
        assert response.has_tool_calls()
        assert bool(response)


class TestEchoChatbot:
    """Tests for EchoChatbot class."""

    @patch("echo.core.chatbot.get_settings")
    def test_initialization(self, mock_get_settings, mock_settings):
        """Test chatbot initialization."""
        from echo.core.chatbot import EchoChatbot

        mock_get_settings.return_value = mock_settings
        chatbot = EchoChatbot()

        assert len(chatbot.messages) == 1
        assert chatbot.messages[0]["role"] == "system"
        assert chatbot.api_provider == "openrouter"

    @patch("echo.core.chatbot.get_settings")
    def test_add_message(self, mock_get_settings, mock_settings):
        """Test adding messages to conversation."""
        from echo.core.chatbot import EchoChatbot

        mock_get_settings.return_value = mock_settings
        chatbot = EchoChatbot()
        chatbot.add_message("user", "Hello")

        assert len(chatbot.messages) == 2
        assert chatbot.messages[1]["role"] == "user"
        assert chatbot.messages[1]["content"] == "Hello"

    @patch("echo.core.chatbot.get_settings")
    def test_clear_history(self, mock_get_settings, mock_settings):
        """Test clearing conversation history."""
        from echo.core.chatbot import EchoChatbot

        mock_get_settings.return_value = mock_settings
        chatbot = EchoChatbot()
        chatbot.add_message("user", "Hello")
        chatbot.add_message("assistant", "Hi there")

        chatbot.clear_history()
        assert len(chatbot.messages) == 1
        assert chatbot.messages[0]["role"] == "system"

    @patch("echo.core.chatbot.get_settings")
    def test_get_history(self, mock_get_settings, mock_settings):
        """Test getting conversation history."""
        from echo.core.chatbot import EchoChatbot

        mock_get_settings.return_value = mock_settings
        chatbot = EchoChatbot()
        chatbot.add_message("user", "Test")

        history = chatbot.get_history()
        assert len(history) == 2
        assert isinstance(history, list)

    @patch("echo.core.chatbot.get_settings")
    def test_save_and_load_history(self, mock_get_settings, mock_settings, tmp_path):
        """Test saving and loading conversation history."""
        from echo.core.chatbot import EchoChatbot

        mock_get_settings.return_value = mock_settings
        chatbot = EchoChatbot()
        chatbot.add_message("user", "Test message")

        history_path = tmp_path / "chat_history.json"
        chatbot.save_history(history_path)
        assert history_path.exists()

        chatbot.clear_history()
        chatbot.load_history(history_path)
        assert len(chatbot.messages) == 2

    @patch("echo.core.chatbot.get_settings")
    def test_tool_call_message_format(self, mock_get_settings, mock_settings):
        """Test that assistant messages with tool_calls have correct format."""
        from echo.core.chatbot import EchoChatbot

        mock_get_settings.return_value = mock_settings
        chatbot = EchoChatbot()

        # Simulate adding an assistant message with tool calls (as chat_continue would)
        tool_calls = [
            {
                "id": "call_abc123",
                "type": "function",
                "function": {"name": "test_tool", "arguments": '{"key": "value"}'},
            }
        ]
        assistant_message = {
            "role": "assistant",
            "content": None,
            "tool_calls": tool_calls,
        }
        chatbot.messages.append(assistant_message)

        last_msg = chatbot.messages[-1]
        assert last_msg["role"] == "assistant"
        assert last_msg["content"] is None
        assert "tool_calls" in last_msg
        assert last_msg["tool_calls"][0]["type"] == "function"
