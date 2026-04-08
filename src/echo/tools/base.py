"""Base tool classes and directory confinement logic."""

import logging
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

# File types that can be safely read/edited as text
TEXT_EXTENSIONS = {
    ".txt",
    ".py",
    ".c",
    ".cpp",
    ".h",
    ".hpp",
    ".java",
    ".js",
    ".jsx",
    ".ts",
    ".tsx",
    ".html",
    ".htm",
    ".css",
    ".scss",
    ".sass",
    ".less",
    ".json",
    ".xml",
    ".yaml",
    ".yml",
    ".md",
    ".rst",
    ".tex",
    ".log",
    ".cfg",
    ".ini",
    ".toml",
    ".env",
    ".conf",
    ".sh",
    ".bash",
    ".bat",
    ".ps1",
    ".sql",
    ".csv",
    ".tsv",
    ".php",
    ".rb",
    ".go",
    ".rs",
    ".swift",
    ".kt",
    ".scala",
    ".pl",
    ".pm",
    ".lua",
    ".r",
    ".R",
    ".m",
    ".mm",
    ".asm",
    ".s",
    ".dockerfile",
    ".makefile",
    ".cmake",
    ".gitignore",
    ".gitattributes",
    ".editorconfig",
    "",  # Files without extension
}


@dataclass
class ToolResult:
    """Result from tool execution."""

    success: bool
    content: str = ""
    error: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)


class DirectoryConfinedTools:
    """Main toolkit with comprehensive directory-confined tools."""

    def __init__(self, base_dir: Path | None = None):
        """Initialize toolkit with directory confinement.

        Args:
            base_dir: Base directory for confinement (defaults to cwd)
        """
        self.base_dir = (base_dir or Path.cwd()).resolve()
        self.history: list[dict[str, Any]] = []
        self._validate_base_dir()
        logger.info("AI Toolkit initialized with base dir: %s", self.base_dir)

    def _validate_base_dir(self):
        """Ensure we're confined to the base directory."""
        if not self.base_dir.is_absolute():
            self.base_dir = self.base_dir.resolve()
        if not self.base_dir.exists():
            raise ValueError(f"Base directory does not exist: {self.base_dir}")

    def _is_allowed_path(self, path: Path) -> bool:
        """Strict path validation - only allow paths within base_dir."""
        try:
            resolved = path.resolve()
            return resolved.is_relative_to(self.base_dir.resolve())
        except (ValueError, OSError):
            return False

    def _sanitize_path(self, path_str: str) -> Path | None:
        """Convert string to safe Path object within base_dir."""
        try:
            path = Path(path_str)
            if not path.is_absolute():
                path = self.base_dir / path
            resolved = path.resolve()

            if self._is_allowed_path(resolved):
                return resolved
            logger.warning("Path escape attempt blocked: %s", path_str)
            return None
        except (ValueError, OSError) as e:
            logger.error("Path sanitization error: %s", e)
            return None

    def _is_text_file(self, path: Path) -> bool:
        """Determine if file can be safely read as text."""
        ext = path.suffix.lower()
        return ext in TEXT_EXTENSIONS

    def _log_tool_execution(self, tool_name: str, args: dict[str, Any], result: ToolResult):
        """Log tool execution for history."""
        self.history.append(
            {
                "tool": tool_name,
                "args": args,
                "success": result.success,
                "timestamp": datetime.now().isoformat(),
            }
        )
