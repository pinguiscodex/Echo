"""Tests for Echo tools package."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from tests.factories import ToolResultFactory


class TestToolResult:
    """Tests for ToolResult dataclass."""

    def test_success_result(self):
        """Test successful tool result creation."""
        from echo.tools.base import ToolResult

        result = ToolResult(success=True, content="File written", metadata={"size": 100})
        assert result.success is True
        assert result.content == "File written"
        assert result.metadata == {"size": 100}
        assert result.error == ""

    def test_failure_result(self):
        """Test failed tool result creation."""
        from echo.tools.base import ToolResult

        result = ToolResult(success=False, error="Permission denied")
        assert result.success is False
        assert result.error == "Permission denied"
        assert result.content == ""

    def test_factory_success(self):
        """Test ToolResultFactory success method."""
        result = ToolResultFactory.success(content="Test output")
        assert result.success is True
        assert result.content == "Test output"

    def test_factory_failure(self):
        """Test ToolResultFactory failure method."""
        result = ToolResultFactory.failure(error="Test error")
        assert result.success is False
        assert result.error == "Test error"


class TestDirectoryConfinedTools:
    """Tests for directory confinement logic."""

    def test_base_dir_is_cwd(self, tmp_path):
        """Test base directory defaults to cwd."""
        from echo.tools.base import DirectoryConfinedTools

        confined = DirectoryConfinedTools(tmp_path)
        assert confined.base_dir == tmp_path.resolve()

    def test_sanitize_path_relative(self, tmp_path):
        """Test sanitizing relative paths."""
        from echo.tools.base import DirectoryConfinedTools

        confined = DirectoryConfinedTools(tmp_path)
        result = confined._sanitize_path("test.txt")
        assert result is not None
        assert result.is_relative_to(tmp_path.resolve())

    def test_sanitize_path_escape(self, tmp_path):
        """Test blocking path escape attempts."""
        from echo.tools.base import DirectoryConfinedTools

        confined = DirectoryConfinedTools(tmp_path)
        # Try to escape to parent
        result = confined._sanitize_path("../../etc/passwd")
        # Should either be None or still within base_dir
        if result is not None:
            assert result.is_relative_to(tmp_path.resolve())

    def test_is_text_file(self, tmp_path):
        """Test text file detection."""
        from echo.tools.base import DirectoryConfinedTools

        confined = DirectoryConfinedTools(tmp_path)
        assert confined._is_text_file(Path("test.py")) is True
        assert confined._is_text_file(Path("readme.md")) is True
        assert confined._is_text_file(Path("config.json")) is True
        assert confined._is_text_file(Path("image.png")) is False
        assert confined._is_text_file(Path("binary.exe")) is False

    def test_log_tool_execution(self, tmp_path):
        """Test tool execution logging."""
        from echo.tools.base import DirectoryConfinedTools, ToolResult

        confined = DirectoryConfinedTools(tmp_path)
        result = ToolResult(success=True, content="Done")
        confined._log_tool_execution("test_tool", {"arg": "value"}, result)

        assert len(confined.history) == 1
        assert confined.history[0]["tool"] == "test_tool"
        assert confined.history[0]["success"] is True


class TestFileSystemTools:
    """Tests for file system tools."""

    def test_list_directory(self, tmp_path):
        """Test listing directory contents."""
        from echo.tools.base import DirectoryConfinedTools
        from echo.tools.filesystem import FileSystemTools

        # Create some files
        (tmp_path / "file1.txt").write_text("hello")
        (tmp_path / "file2.py").write_text("print('hi')")
        (tmp_path / "subdir").mkdir()

        confined = DirectoryConfinedTools(tmp_path)
        fs = FileSystemTools(confined)
        result = fs.list_directory(".")

        assert result.success is True
        assert "file1.txt" in result.content
        assert "file2.py" in result.content

    def test_write_and_read_file(self, tmp_path):
        """Test writing and reading files."""
        from echo.tools.base import DirectoryConfinedTools
        from echo.tools.filesystem import FileSystemTools

        confined = DirectoryConfinedTools(tmp_path)
        fs = FileSystemTools(confined)

        # Write
        write_result = fs.write_file("test.txt", "Hello, World!")
        assert write_result.success is True
        assert (tmp_path / "test.txt").exists()

        # Read
        read_result = fs.read_file("test.txt")
        assert read_result.success is True
        assert "Hello, World!" in read_result.content

    def test_create_directory(self, tmp_path):
        """Test directory creation."""
        from echo.tools.base import DirectoryConfinedTools
        from echo.tools.filesystem import FileSystemTools

        confined = DirectoryConfinedTools(tmp_path)
        fs = FileSystemTools(confined)

        result = fs.create_directory("nested/deep/dir")
        assert result.success is True
        assert (tmp_path / "nested" / "deep" / "dir").exists()

    def test_edit_file(self, tmp_path):
        """Test file editing."""
        from echo.tools.base import DirectoryConfinedTools
        from echo.tools.filesystem import FileSystemTools

        confined = DirectoryConfinedTools(tmp_path)
        fs = FileSystemTools(confined)

        # Create file
        fs.write_file("test.py", "x = 1\ny = 2\n")

        # Edit
        result = fs.edit_file("test.py", "x = 1", "x = 10")
        assert result.success is True
        assert "1 occurrence" in result.content

        # Verify edit
        content = (tmp_path / "test.py").read_text()
        assert "x = 10" in content
        assert "x = 1\n" not in content

    def test_search_files(self, tmp_path):
        """Test file searching."""
        from echo.tools.base import DirectoryConfinedTools
        from echo.tools.filesystem import FileSystemTools

        confined = DirectoryConfinedTools(tmp_path)
        fs = FileSystemTools(confined)

        # Create files
        fs.write_file("main.py", "")
        fs.write_file("test.py", "")
        fs.write_file("readme.md", "")

        result = fs.search_files(".*\\.py$")
        assert result.success is True
        assert "main.py" in result.content
        assert "test.py" in result.content
        assert "readme.md" not in result.content


class TestCommandTools:
    """Tests for command execution tools."""

    def test_run_command(self, tmp_path):
        """Test running a shell command."""
        from echo.tools.base import DirectoryConfinedTools
        from echo.tools.command import CommandExecutionTools

        confined = DirectoryConfinedTools(tmp_path)
        cmd = CommandExecutionTools(confined)

        result = cmd.run_command("echo 'hello world'")
        assert result.success is True
        assert "hello world" in result.content

    def test_run_command_timeout(self, tmp_path):
        """Test command timeout."""
        from echo.tools.base import DirectoryConfinedTools
        from echo.tools.command import CommandExecutionTools

        confined = DirectoryConfinedTools(tmp_path)
        cmd = CommandExecutionTools(confined)

        result = cmd.run_command("sleep 10", timeout=1)
        assert result.success is False
        assert "timed out" in result.error.lower()


class TestCodeTools:
    """Tests for code execution tools."""

    def test_execute_python(self, tmp_path):
        """Test Python code execution."""
        from echo.tools.base import DirectoryConfinedTools
        from echo.tools.code import CodeExecutionTools

        confined = DirectoryConfinedTools(tmp_path)
        code = CodeExecutionTools(confined)

        result = code.execute_python("print('Hello from Python!')")
        assert result.success is True
        assert "Hello from Python!" in result.content

    def test_validate_python_valid(self, tmp_path):
        """Test validating valid Python code."""
        from echo.tools.base import DirectoryConfinedTools
        from echo.tools.code import CodeExecutionTools

        confined = DirectoryConfinedTools(tmp_path)
        code = CodeExecutionTools(confined)

        result = code.validate_python("def foo():\n    return 42")
        assert result.success is True
        assert "valid" in result.content.lower()

    def test_validate_python_invalid(self, tmp_path):
        """Test validating invalid Python code."""
        from echo.tools.base import DirectoryConfinedTools
        from echo.tools.code import CodeExecutionTools

        confined = DirectoryConfinedTools(tmp_path)
        code = CodeExecutionTools(confined)

        result = code.validate_python("def foo(\n    return")
        assert result.success is False
        assert "Syntax error" in result.error


class TestSystemTools:
    """Tests for system information tools."""

    def test_get_system_info(self, tmp_path):
        """Test getting system information."""
        from echo.tools.base import DirectoryConfinedTools
        from echo.tools.system import SystemInfoTools

        confined = DirectoryConfinedTools(tmp_path)
        sys_info = SystemInfoTools(confined)

        result = sys_info.get_system_info()
        assert result.success is True
        assert "operating_system" in result.content
        assert "python_version" in result.content

    def test_get_directory_structure(self, tmp_path):
        """Test getting directory structure."""
        from echo.tools.base import DirectoryConfinedTools
        from echo.tools.system import SystemInfoTools

        confined = DirectoryConfinedTools(tmp_path)
        sys_info = SystemInfoTools(confined)

        result = sys_info.get_directory_structure()
        assert result.success is True


class TestAIToolkit:
    """Tests for AIToolkit integration."""

    def test_toolkit_initialization(self, tmp_path):
        """Test AIToolkit initializes with tools."""
        from echo.tools import AIToolkit

        toolkit = AIToolkit(tmp_path)
        assert len(toolkit.tool_map) > 0
        assert "list_directory" in toolkit.tool_map
        assert "read_file" in toolkit.tool_map

    def test_call_tool(self, tmp_path):
        """Test calling a tool through AIToolkit."""
        from echo.tools import AIToolkit

        toolkit = AIToolkit(tmp_path)
        result = toolkit.call_tool("get_system_info")
        assert result.success is True

    def test_call_unknown_tool(self, tmp_path):
        """Test calling unknown tool returns error."""
        from echo.tools import AIToolkit

        toolkit = AIToolkit(tmp_path)
        result = toolkit.call_tool("nonexistent_tool")
        assert result.success is False
        assert "Unknown tool" in result.error

    def test_tool_usage_history(self, tmp_path):
        """Test tool usage history tracking."""
        from echo.tools import AIToolkit

        toolkit = AIToolkit(tmp_path)
        toolkit.call_tool("get_system_info")

        history = toolkit.get_tool_usage_history()
        assert len(history) == 1
        assert history[0]["tool"] == "get_system_info"

    def test_tool_definitions(self, tmp_path):
        """Test tool definitions are valid."""
        from echo.tools import AIToolkit

        toolkit = AIToolkit(tmp_path)
        assert len(toolkit.tool_definitions) > 0

        for tool_def in toolkit.tool_definitions:
            assert "type" in tool_def
            assert "function" in tool_def
            assert "name" in tool_def["function"]
            assert "parameters" in tool_def["function"]
