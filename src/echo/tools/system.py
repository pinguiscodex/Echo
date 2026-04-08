"""System information tools."""

import json
import logging
import os
import platform
import shutil
import sys

from echo.tools.base import DirectoryConfinedTools, ToolResult

logger = logging.getLogger(__name__)


class SystemInfoTools:
    """System and environment information tools."""

    def __init__(self, agent: DirectoryConfinedTools):
        self.agent = agent

    def get_system_info(self) -> ToolResult:
        """Get comprehensive system information."""
        try:
            import cpuinfo

            cpu_info = cpuinfo.get_cpu_info()
            cpu_name = cpu_info.get("brand_raw", "Unknown")
        except Exception:
            cpu_name = "Unknown"

        # Memory info (cross-platform)
        try:
            import psutil

            memory = psutil.virtual_memory()
            memory_total = f"{memory.total / (1024**3):.1f} GB"
            memory_available = f"{memory.available / (1024**3):.1f} GB"
        except Exception:
            memory_total = "Unknown"
            memory_available = "Unknown"

        info = {
            "operating_system": f"{platform.system()} {platform.release()}",
            "platform": sys.platform,
            "python_version": platform.python_version(),
            "python_implementation": platform.python_implementation(),
            "machine": platform.machine(),
            "processor": cpu_name,
            "memory_total": memory_total,
            "memory_available": memory_available,
            "working_directory": str(self.agent.base_dir),
            "current_user": os.getenv("USER") or os.getenv("USERNAME") or "Unknown",
            "shell": os.environ.get("SHELL", "Unknown"),
            "terminal_size": {
                "columns": shutil.get_terminal_size().columns,
                "lines": shutil.get_terminal_size().lines,
            },
        }

        return ToolResult(True, content=json.dumps(info, indent=2), metadata=info)

    def get_directory_structure(self) -> ToolResult:
        """Get overview of current directory structure."""
        try:
            from echo.tools.filesystem import FileSystemTools

            fs_tools = FileSystemTools(self.agent)
            return fs_tools.list_directory(".")
        except Exception as e:
            return ToolResult(False, error=str(e))
