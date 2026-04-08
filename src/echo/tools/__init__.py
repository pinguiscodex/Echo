"""Echo AI Toolkit - Comprehensive tool package for file, system, code, and research operations."""

from echo.tools.base import DirectoryConfinedTools, ToolResult
from echo.tools.code import CodeExecutionTools
from echo.tools.command import CommandExecutionTools
from echo.tools.filesystem import FileSystemTools
from echo.tools.research import ResearchOrchestrator
from echo.tools.system import SystemInfoTools

__all__ = [
    "ToolResult",
    "DirectoryConfinedTools",
    "FileSystemTools",
    "CommandExecutionTools",
    "CodeExecutionTools",
    "SystemInfoTools",
    "ResearchOrchestrator",
    "AIToolkit",
]

# Import AIToolkit last since it depends on all others
from echo.tools._toolkit import AIToolkit
