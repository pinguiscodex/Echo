"""Test factories for Echo AI Chatbot using factory-boy and Faker."""

from pathlib import Path
from typing import Any, Dict, List

import factory
from factory import Faker, LazyAttribute, Sequence

from echo.types import MessageDict, ToolCallDict


class MessageFactory(factory.Factory):
    """Factory for chat message dictionaries."""

    class Meta:
        model = dict

    role = Faker("random_element", elements=["user", "assistant", "system"])
    content = Faker("text", max_nb_chars=200)

    class Params:
        user_message = factory.Trait(
            role="user",
            content=Faker("sentence"),
        )
        assistant_message = factory.Trait(
            role="assistant",
            content=Faker("paragraph"),
        )
        system_message = factory.Trait(
            role="system",
            content=Faker("text", max_nb_chars=500),
        )
        with_tool_calls = factory.Trait(
            role="assistant",
            content=Faker("paragraph"),
            tool_calls=factory.List([factory.SubFactory("tests.factories.ToolCallFactory")]),
        )

    @classmethod
    def user(cls, **kwargs) -> MessageDict:
        """Create a user message."""
        return cls(
            role="user", content=Faker("sentence").evaluate(None, None, {"locale": None}), **kwargs
        )

    @classmethod
    def assistant(cls, **kwargs) -> MessageDict:
        """Create an assistant message."""
        return cls(
            role="assistant",
            content=Faker("paragraph").evaluate(None, None, {"locale": None}),
            **kwargs,
        )

    @classmethod
    def system(cls, **kwargs) -> MessageDict:
        """Create a system message."""
        return cls(
            role="system",
            content=Faker("text", max_nb_chars=500).evaluate(None, None, {"locale": None}),
            **kwargs,
        )


class ToolCallFactory(factory.Factory):
    """Factory for tool call dictionaries."""

    class Meta:
        model = dict

    id = factory.Sequence(lambda n: f"call_{n:04d}")
    function = factory.Dict(
        {
            "name": Faker(
                "random_element",
                elements=[
                    "list_directory",
                    "read_file",
                    "write_file",
                    "run_command",
                    "execute_python",
                    "web_search",
                    "wikipedia_summary",
                ],
            ),
            "arguments": "{}",
        }
    )


class ConversationFactory(factory.Factory):
    """Factory for a full conversation (list of messages)."""

    class Meta:
        model = list

    class Params:
        short = factory.Trait(
            messages=factory.List(
                [
                    factory.SubFactory(MessageFactory, role="system"),
                    factory.SubFactory(MessageFactory, role="user"),
                    factory.SubFactory(MessageFactory, role="assistant"),
                ]
            )
        )
        long = factory.Trait(
            messages=factory.List(
                [
                    factory.SubFactory(MessageFactory, role="system"),
                    factory.SubFactory(MessageFactory, role="user"),
                    factory.SubFactory(MessageFactory, role="assistant"),
                    factory.SubFactory(MessageFactory, role="user"),
                    factory.SubFactory(MessageFactory, role="assistant"),
                    factory.SubFactory(MessageFactory, role="user"),
                    factory.SubFactory(MessageFactory, role="assistant"),
                ]
            )
        )

    @classmethod
    def create(cls, turn_count: int = 1, **kwargs) -> List[Dict[str, Any]]:
        """Create a conversation with N user/assistant turns."""
        messages = [MessageFactory.system()]
        for _ in range(turn_count):
            messages.append(MessageFactory.user_message())
            messages.append(MessageFactory.assistant_message())
        return messages


class SettingsFactory(factory.Factory):
    """Factory for mock settings objects."""

    class Meta:
        model = dict

    api_provider = Faker("random_element", elements=["openrouter", "mistral"])
    openrouter_model = Faker(
        "random_element",
        elements=[
            "openai/gpt-oss-120b:free",
            "google/gemma-3-27b-it:free",
            "meta-llama/llama-3.3-70b-instruct:free",
        ],
    )
    mistral_model = Faker(
        "random_element",
        elements=[
            "mistral-small-latest",
            "mistral-medium-latest",
        ],
    )
    openrouter_api_key = LazyAttribute(lambda _: f"sk-{Faker('uuid4')()}")
    mistral_api_key = ""
    whisper_model = Faker("random_element", elements=["tiny", "base", "small"])
    tts_voice = Faker(
        "random_element",
        elements=[
            "en-US-JennyNeural",
            "en-US-GuyNeural",
            "en-GB-SoniaNeural",
        ],
    )
    temperature = Faker("pyfloat", min_value=0.0, max_value=2.0, right_digits=1)
    max_tokens = Faker("random_element", elements=[256, 512, 1024, 2048])
    system_prompt = Faker("sentence")
    input_mode = Faker("random_element", elements=["text", "speech", "both"])
    output_mode = Faker("random_element", elements=["text", "speech", "both"])
    sample_rate = Faker("random_element", elements=[16000, 44100])
    enable_tools = Faker("pybool")
    python_execution_timeout = 30
    command_execution_timeout = 30


class ToolResultFactory:
    """Factory for tool result objects (simple wrapper, not factory-boy)."""

    @staticmethod
    def success(content: str = None, **kwargs) -> Dict[str, Any]:
        """Create a successful tool result."""
        from echo.tools.base import ToolResult

        return ToolResult(
            success=True,
            content=content or Faker().paragraph(),
            **kwargs,
        )

    @staticmethod
    def failure(error: str = None, **kwargs) -> Dict[str, Any]:
        """Create a failed tool result."""
        from echo.tools.base import ToolResult

        return ToolResult(
            success=False,
            error=error or Faker().sentence(),
            **kwargs,
        )


class AudioPathFactory(factory.Factory):
    """Factory for temporary audio file paths."""

    class Meta:
        model = Path

    class Params:
        wav = factory.Trait(
            _path=LazyAttribute(lambda _: Path(f"/tmp/test_audio_{Faker('uuid4')()}.wav")),
        )
        mp3 = factory.Trait(
            _path=LazyAttribute(lambda _: Path(f"/tmp/test_audio_{Faker('uuid4')()}.mp3")),
        )

    @classmethod
    def create(cls, tmp_path: Path, extension: str = ".wav") -> Path:
        """Create a temporary audio file path."""
        return (
            tmp_path
            / f"test_audio_{Faker('uuid4').evaluate(None, None, {'locale': None})}{extension}"
        )
