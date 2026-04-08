"""Code execution tools with directory confinement."""

import ast
import logging
import subprocess
import sys
import tempfile
from pathlib import Path

from echo.tools.base import DirectoryConfinedTools, ToolResult

logger = logging.getLogger(__name__)


class CodeExecutionTools:
    """Safe code execution with directory confinement."""

    def __init__(self, agent: DirectoryConfinedTools):
        self.agent = agent

    def execute_python(self, code: str, timeout: int = 30) -> ToolResult:
        """Execute Python code safely in confined directory."""
        temp_path = None
        try:
            # Create temporary file in base directory
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False, dir=self.agent.base_dir
            ) as temp:
                temp.write(code)
                temp_path = Path(temp.name)

            result = subprocess.run(
                [sys.executable, str(temp_path)],
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

            return ToolResult(True, content=output_text, metadata={"returncode": result.returncode})
        except subprocess.TimeoutExpired:
            return ToolResult(False, error=f"Python execution timed out after {timeout}s")
        except Exception as e:
            return ToolResult(False, error=str(e))
        finally:
            # Clean up temp file
            if temp_path and temp_path.exists():
                try:
                    temp_path.unlink()
                except Exception:
                    pass

    def validate_python(self, code: str) -> ToolResult:
        """Validate Python syntax without execution."""
        try:
            ast.parse(code)
            return ToolResult(True, content="Python code is syntactically valid")
        except SyntaxError as e:
            return ToolResult(
                False, error=f"Syntax error at line {e.lineno}, col {e.offset}: {e.msg}"
            )
