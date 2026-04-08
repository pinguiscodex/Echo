"""File system tools for directory-confined operations."""

import json
import logging
import os
import re
import shutil
from datetime import datetime
from pathlib import Path

from echo.tools.base import DirectoryConfinedTools, ToolResult

logger = logging.getLogger(__name__)


class FileSystemTools:
    """Complete file system operations with directory confinement."""

    def __init__(self, agent: DirectoryConfinedTools):
        self.agent = agent

    def list_directory(self, path: str = ".") -> ToolResult:
        """List files and directories in a path with tree view."""
        path_obj = self.agent._sanitize_path(path)
        if not path_obj:
            return ToolResult(False, error="Path outside allowed directory")

        if not path_obj.is_dir():
            return ToolResult(False, error=f"Not a directory: {path}")

        try:
            items = []
            for item in sorted(path_obj.iterdir()):
                try:
                    item_path = item.relative_to(self.agent.base_dir)
                    item_type = "DIR" if item.is_dir() else "FILE"
                    size = item.stat().st_size if item.is_file() else 0
                    modified = datetime.fromtimestamp(item.stat().st_mtime).strftime(
                        "%Y-%m-%d %H:%M"
                    )

                    items.append(
                        {
                            "name": str(item_path),
                            "type": item_type,
                            "size": f"{size:,}" if size > 0 else "-",
                            "modified": modified,
                        }
                    )
                except (PermissionError, OSError) as e:
                    items.append(
                        {"name": item.name, "type": "ERROR", "size": "-", "modified": str(e)}
                    )

            tree = self._generate_tree(path_obj, max_depth=2)
            return ToolResult(
                True,
                content=json.dumps({"items": items, "tree": tree}, indent=2),
                metadata={"path": str(path_obj), "item_count": len(items)},
            )
        except Exception as e:
            return ToolResult(False, error=str(e))

    def _generate_tree(
        self, path: Path, prefix: str = "", max_depth: int = 2, current_depth: int = 0
    ) -> str:
        """Generate a tree view of directory structure."""
        if current_depth > max_depth:
            return ""

        try:
            items = sorted(path.iterdir())
            dirs = [p for p in items if p.is_dir()]
            files = [p for p in items if p.is_file()]
        except (PermissionError, OSError):
            return ""

        lines = []
        all_items = dirs + files
        for i, item in enumerate(all_items):
            connector = "└── " if i == len(all_items) - 1 else "├── "
            item_name = item.name + "/" if item.is_dir() else item.name
            lines.append(f"{prefix}{connector}{item_name}")

            if item.is_dir() and current_depth < max_depth:
                extension = "│   " if i < len(all_items) - 1 else "    "
                subtree = self._generate_tree(
                    item, prefix + extension, max_depth, current_depth + 1
                )
                if subtree:
                    lines.append(subtree)

        return "\n".join(lines)

    def read_file(self, path: str, max_lines: int | None = None) -> ToolResult:
        """Read file content (text files only)."""
        path_obj = self.agent._sanitize_path(path)
        if not path_obj:
            return ToolResult(False, error="Path outside allowed directory")

        if not path_obj.is_file():
            return ToolResult(False, error=f"Not a file: {path}")

        if not self.agent._is_text_file(path_obj):
            return ToolResult(
                False, error=f"Binary file not supported for reading: {path_obj.suffix}"
            )

        try:
            with open(path_obj, encoding="utf-8", errors="replace") as f:
                if max_lines:
                    lines = []
                    for i, line in enumerate(f):
                        if i >= max_lines:
                            lines.append(f"\n... (truncated, showing first {max_lines} lines)")
                            break
                        lines.append(line)
                    content = "".join(lines)
                else:
                    content = f.read()

            return ToolResult(
                True,
                content=content,
                metadata={
                    "size": len(content),
                    "path": str(path_obj.relative_to(self.agent.base_dir)),
                    "lines": content.count("\n") + 1,
                },
            )
        except Exception as e:
            return ToolResult(False, error=str(e))

    def write_file(self, path: str, content: str) -> ToolResult:
        """Write or create file content."""
        path_obj = self.agent._sanitize_path(path)
        if not path_obj:
            return ToolResult(False, error="Path outside allowed directory")

        try:
            path_obj.parent.mkdir(parents=True, exist_ok=True)
            with open(path_obj, "w", encoding="utf-8") as f:
                f.write(content)

            self.agent._log_tool_execution("write_file", {"path": str(path)}, ToolResult(True))
            return ToolResult(
                True,
                content=f"File written successfully: {path_obj.relative_to(self.agent.base_dir)}",
                metadata={"path": str(path_obj), "size": len(content)},
            )
        except Exception as e:
            return ToolResult(False, error=str(e))

    def edit_file(self, path: str, old_text: str, new_text: str) -> ToolResult:
        """Find and replace text in file."""
        path_obj = self.agent._sanitize_path(path)
        if not path_obj:
            return ToolResult(False, error="Path outside allowed directory")

        if not path_obj.is_file():
            return ToolResult(False, error=f"File not found: {path}")

        if not self.agent._is_text_file(path_obj):
            return ToolResult(False, error="Cannot edit binary files")

        try:
            with open(path_obj, encoding="utf-8") as f:
                content = f.read()

            if old_text not in content:
                return ToolResult(False, error=f"Text not found in file: {old_text[:50]}...")

            occurrences = content.count(old_text)
            new_content = content.replace(old_text, new_text)

            with open(path_obj, "w", encoding="utf-8") as f:
                f.write(new_content)

            self.agent._log_tool_execution("edit_file", {"path": str(path)}, ToolResult(True))
            return ToolResult(
                True,
                content=f"Replaced {occurrences} occurrence(s) in {path_obj.relative_to(self.agent.base_dir)}",
                metadata={"path": str(path_obj), "occurrences": occurrences},
            )
        except Exception as e:
            return ToolResult(False, error=str(e))

    def create_directory(self, path: str) -> ToolResult:
        """Create directory (and parents if needed)."""
        path_obj = self.agent._sanitize_path(path)
        if not path_obj:
            return ToolResult(False, error="Path outside allowed directory")

        try:
            path_obj.mkdir(parents=True, exist_ok=True)
            return ToolResult(
                True,
                content=f"Directory created: {path_obj.relative_to(self.agent.base_dir)}",
                metadata={"path": str(path_obj)},
            )
        except Exception as e:
            return ToolResult(False, error=str(e))

    def delete_path(self, path: str, recursive: bool = False) -> ToolResult:
        """Delete file or directory."""
        path_obj = self.agent._sanitize_path(path)
        if not path_obj:
            return ToolResult(False, error="Path outside allowed directory")

        try:
            if path_obj.is_file():
                path_obj.unlink()
                return ToolResult(
                    True, content=f"File deleted: {path_obj.relative_to(self.agent.base_dir)}"
                )
            if path_obj.is_dir():
                if recursive:
                    shutil.rmtree(path_obj)
                    return ToolResult(
                        True,
                        content=f"Directory deleted: {path_obj.relative_to(self.agent.base_dir)}",
                    )
                return ToolResult(False, error="Use recursive=True to delete directories")
            return ToolResult(False, error="Path not found")
        except Exception as e:
            return ToolResult(False, error=str(e))

    def search_files(self, pattern: str, path: str = ".") -> ToolResult:
        """Search for files matching regex pattern."""
        path_obj = self.agent._sanitize_path(path)
        if not path_obj or not path_obj.is_dir():
            return ToolResult(False, error="Invalid directory path")

        try:
            matches = []
            for root, dirs, files in os.walk(path_obj):
                for file in files:
                    if re.search(pattern, file, re.IGNORECASE):
                        rel_path = Path(root) / file
                        try:
                            matches.append(str(rel_path.relative_to(self.agent.base_dir)))
                        except ValueError:
                            pass

            if not matches:
                return ToolResult(True, content="No files found matching pattern")

            return ToolResult(
                True, content=json.dumps(matches, indent=2), metadata={"count": len(matches)}
            )
        except Exception as e:
            return ToolResult(False, error=str(e))
