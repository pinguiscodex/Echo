"""Shared type aliases, TypedDicts, and Protocols for Echo."""

from pathlib import Path
from typing import Any, TypedDict


class MessageDict(TypedDict, total=False):
    """Type for chat message dictionaries."""

    role: str
    content: str | None
    reasoning_details: str | None
    tool_calls: list[dict[str, Any]]


class ToolCallDict(TypedDict, total=False):
    """Type for tool call dictionaries."""

    id: str
    function: dict[str, str]


class ToolResultDict(TypedDict):
    """Type for tool result dictionaries."""

    role: str
    tool_call_id: str
    content: str


class AudioConfig(TypedDict):
    """Type for audio configuration."""

    sample_rate: int
    channels: int
    dtype: str


class TranscriptionResult(TypedDict):
    """Type for transcription results."""

    text: str
    language: str | None
    language_probability: float


# Type aliases
FilePath = Path
AudioPath = Path
HistoryList = list[MessageDict]
ToolMap = dict[str, Any]
