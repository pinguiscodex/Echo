"""Command execution tools with directory confinement."""

import logging
import platform
import subprocess

from echo.tools.base import DirectoryConfinedTools, ToolResult

logger = logging.getLogger(__name__)


class CommandExecutionTools:
    """Cross-platform command execution with confinement."""

    def __init__(self, agent: DirectoryConfinedTools):
        self.agent = agent
        self.os_name = platform.system().lower()

    def run_command(self, command: str, timeout: int = 30, shell: bool = True) -> ToolResult:
        """Execute a shell command in the base directory."""
        try:
            result = subprocess.run(
                command,
                shell=shell,
                cwd=str(self.agent.base_dir),
                capture_output=True,
                text=True,
                timeout=timeout,
                stdin=subprocess.DEVNULL,
            )

            output = []
            if result.stdout:
                output.append(result.stdout)
            if result.stderr:
                output.append(f"STDERR: {result.stderr}")

            output_text = "\n".join(output) if output else "(no output)"

            return ToolResult(
                True,
                content=output_text,
                metadata={"returncode": result.returncode, "command": command, "timeout": timeout},
            )
        except subprocess.TimeoutExpired:
            return ToolResult(False, error=f"Command timed out after {timeout}s")
        except Exception as e:
            return ToolResult(False, error=str(e))
