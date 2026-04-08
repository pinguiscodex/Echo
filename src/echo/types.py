"""Shared type aliases, TypedDicts, and Protocols for Echo."""

from pathlib import Path
from typing import Any, Dict, List, Optional, TypedDict


class MessageDict(TypedDict, total=False):
    """Type for chat message dictionaries."""

    role: str
    content: Optional[str]
    reasoning_details: Optional[str]
    tool_calls: List[Dict[str, Any]]


class ToolCallDict(TypedDict, total=False):
    """Type for tool call dictionaries."""

    id: str
    function: Dict[str, str]


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
    language: Optional[str]
    language_probability: float


# Type aliases
FilePath = Path
AudioPath = Path
HistoryList = List[MessageDict]
ToolMap = Dict[str, Any]
