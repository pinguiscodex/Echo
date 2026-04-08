"""Pytest fixtures and mocks for Echo tests."""

import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from faker import Faker


@pytest.fixture
def fake():
    """Provide a Faker instance."""
    return Faker()


@pytest.fixture
def temp_dir():
    """Create a temporary directory for test operations."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def mock_settings():
    """Mock settings object with default values."""
    settings = MagicMock()
    settings.api_provider = "openrouter"
    settings.openrouter_model = "test-model"
    settings.mistral_model = "mistral-small-latest"
    settings.openrouter_api_key = "test-api-key"
    settings.mistral_api_key = ""
    settings.whisper_model = "tiny"
    settings.tts_voice = "en-US-JennyNeural"
    settings.temperature = 0.7
    settings.max_tokens = 1024
    settings.system_prompt = "You are a test assistant."
    settings.input_mode = "text"
    settings.output_mode = "text"
    settings.sample_rate = 16000
    settings.enable_tools = False
    settings.python_execution_timeout = 30
    settings.command_execution_timeout = 30
    return settings


@pytest.fixture
def mock_audio_recorder():
    """Mock audio recorder that doesn't actually record."""
    with patch("echo.core.recorder.AudioRecorder") as mock:
        instance = MagicMock()
        instance.is_recording = False
        instance.is_listening = False
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_transcriber():
    """Mock transcriber that returns fixed text."""
    with patch("echo.core.transcriber.WhisperTranscriber") as mock:
        instance = MagicMock()
        instance.transcribe.return_value = "Hello, this is a test."
        mock.return_value = instance
        yield mock


@pytest.fixture
def mock_tts():
    """Mock TTS engine that doesn't actually speak."""
    with patch("echo.core.tts.TTSEngine") as mock:
        instance = MagicMock()
        mock.return_value = instance
        yield mock


@pytest.fixture
def data_dir(tmp_path):
    """Create data directory in temp path."""
    data_path = tmp_path / "data"
    data_path.mkdir()
    return data_path


@pytest.fixture
def logs_dir(tmp_path):
    """Create logs directory in temp path."""
    logs_path = tmp_path / "logs"
    logs_path.mkdir()
    return logs_path


@pytest.fixture
def mock_httpx_client():
    """Mock httpx client for testing."""
    with patch("httpx.Client") as mock:
        instance = MagicMock()
        instance.get.return_value.status_code = 200
        instance.get.return_value.json.return_value = {"status": "ok"}
        instance.post.return_value.status_code = 200
        instance.post.return_value.json.return_value = {"status": "ok"}
        mock.return_value = instance
        yield mock


# Factory-boy fixtures
@pytest.fixture
def message_factory():
    """Provide message factory."""
    from tests.factories import MessageFactory

    return MessageFactory


@pytest.fixture
def conversation_factory():
    """Provide conversation factory."""
    from tests.factories import ConversationFactory

    return ConversationFactory


@pytest.fixture
def tool_result_factory():
    """Provide tool result factory."""
    from tests.factories import ToolResultFactory

    return ToolResultFactory


@pytest.fixture
def sample_conversation(message_factory):
    """Create a sample conversation."""
    return [
        message_factory.system(),
        message_factory.user_message(content="Hello, how are you?"),
        message_factory.assistant_message(content="I'm doing well, thank you!"),
    ]


@pytest.fixture
def tool_call_fixture():
    """Create a sample tool call."""
    from tests.factories import ToolCallFactory

    return ToolCallFactory(
        function={
            "name": "list_directory",
            "arguments": '{"path": "."}',
        }
    )
