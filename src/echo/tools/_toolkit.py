"""Main AIToolkit class that aggregates all tools."""

import logging
import platform
import sys
from pathlib import Path
from typing import Any

from echo.tools.base import DirectoryConfinedTools, ToolResult
from echo.tools.code import CodeExecutionTools
from echo.tools.command import CommandExecutionTools
from echo.tools.filesystem import FileSystemTools
from echo.tools.research import ResearchOrchestrator
from echo.tools.system import SystemInfoTools

logger = logging.getLogger(__name__)


class AIToolkit:
    """Complete AI toolkit with all tools accessible."""

    def __init__(self, base_dir: Path | None = None):
        """Initialize toolkit.

        Args:
            base_dir: Base directory for confinement
        """
        self.agent = DirectoryConfinedTools(base_dir)
        self.fs = FileSystemTools(self.agent)
        self.commands = CommandExecutionTools(self.agent)
        self.code = CodeExecutionTools(self.agent)
        self.system = SystemInfoTools(self.agent)

        # Research tools
        try:
            self.research = ResearchOrchestrator()
            self.research_enabled = True
        except Exception as e:
            logger.warning("Research tools disabled: %s", e)
            self.research = None
            self.research_enabled = False

        # Tool registry
        self.tool_map = {
            "list_directory": self.fs.list_directory,
            "read_file": self.fs.read_file,
            "write_file": self.fs.write_file,
            "edit_file": self.fs.edit_file,
            "create_directory": self.fs.create_directory,
            "delete_path": self.fs.delete_path,
            "search_files": self.fs.search_files,
            "run_command": self.commands.run_command,
            "execute_python": self.code.execute_python,
            "validate_python": self.code.validate_python,
            "get_system_info": self.system.get_system_info,
            "get_directory_structure": self.system.get_directory_structure,
        }

        # Add research tools if available
        if self.research_enabled and self.research:
            self.tool_map.update(
                {
                    "wikipedia_search": self.research.wiki.wikipedia_search,
                    "wikipedia_summary": self.research.wiki.wikipedia_summary,
                    "wikipedia_full_article": self.research.wiki.wikipedia_full_article,
                    "wikipedia_random": self.research.wiki.wikipedia_random,
                    "web_search": self.research.ddg.web_search,
                    "news_search": self.research.ddg.news_search,
                    "dork_search": self.research.ddg.dork_search,
                    "academic_search": self.research.ddg.academic_search,
                    "code_search": self.research.ddg.code_search,
                    "smart_research": self.research.smart_research,
                    "fact_check": self.research.fact_check,
                }
            )

        # Tool definitions for AI
        self.tool_definitions = self._get_tool_definitions()

        logger.info("AI Toolkit ready with %d tools", len(self.tool_map))

    def _get_tool_definitions(self) -> list[dict[str, Any]]:
        """Get JSON schema definitions for all tools."""
        return [
            {
                "type": "function",
                "function": {
                    "name": "list_directory",
                    "description": "List files and directories with tree view showing structure",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {
                                "type": "string",
                                "description": "Directory path to list (default: current directory)",
                                "default": ".",
                            }
                        },
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "read_file",
                    "description": "Read the contents of a text file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the file to read"},
                            "max_lines": {
                                "type": "integer",
                                "description": "Maximum number of lines to read (optional)",
                                "default": None,
                            },
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "write_file",
                    "description": "Write content to a file, creating it if it doesn't exist",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the file to write"},
                            "content": {
                                "type": "string",
                                "description": "Content to write to the file",
                            },
                        },
                        "required": ["path", "content"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "edit_file",
                    "description": "Find and replace text in an existing file",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to the file to edit"},
                            "old_text": {
                                "type": "string",
                                "description": "Text to find and replace",
                            },
                            "new_text": {"type": "string", "description": "Text to replace with"},
                        },
                        "required": ["path", "old_text", "new_text"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "create_directory",
                    "description": "Create a new directory (and parent directories if needed)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path of directory to create"}
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_path",
                    "description": "Delete a file or directory",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "path": {"type": "string", "description": "Path to delete"},
                            "recursive": {
                                "type": "boolean",
                                "description": "Whether to delete directories recursively",
                                "default": False,
                            },
                        },
                        "required": ["path"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "search_files",
                    "description": "Search for files matching a regex pattern in their names",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "pattern": {
                                "type": "string",
                                "description": "Regex pattern to match filenames",
                            },
                            "path": {
                                "type": "string",
                                "description": "Directory to search in (default: current)",
                                "default": ".",
                            },
                        },
                        "required": ["pattern"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "run_command",
                    "description": f"Execute a shell command in the working directory. OS: {platform.system()}",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "command": {"type": "string", "description": "Command to execute"},
                            "timeout": {
                                "type": "integer",
                                "description": "Timeout in seconds",
                                "default": 30,
                            },
                        },
                        "required": ["command"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "execute_python",
                    "description": "Execute Python code and return the output",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Python code to execute"},
                            "timeout": {
                                "type": "integer",
                                "description": "Timeout in seconds",
                                "default": 30,
                            },
                        },
                        "required": ["code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "validate_python",
                    "description": "Validate Python code syntax without executing it",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Python code to validate"}
                        },
                        "required": ["code"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_system_info",
                    "description": "Get comprehensive system information (OS, Python version, hardware, etc.)",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "get_directory_structure",
                    "description": "Get overview of the current directory structure",
                    "parameters": {"type": "object", "properties": {}},
                },
            },
            # RESEARCH TOOLS
            {
                "type": "function",
                "function": {
                    "name": "wikipedia_search",
                    "description": "Search Wikipedia for articles on a topic",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Search query"},
                            "results": {
                                "type": "integer",
                                "description": "Number of results",
                                "default": 5,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "wikipedia_summary",
                    "description": "Get a short summary of a Wikipedia article",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Article title or topic"},
                            "sentences": {
                                "type": "integer",
                                "description": "Number of sentences",
                                "default": 3,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "wikipedia_full_article",
                    "description": "Get complete Wikipedia article content",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Article title or topic"}
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "web_search",
                    "description": "Search the entire web using DuckDuckGo. Supports advanced dorking: site:, filetype:, intitle:, inurl:, exact phrases, exclude terms, etc.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Search query (supports dorking syntax like site:github.com)",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 10,
                            },
                            "region": {
                                "type": "string",
                                "description": "Search region (default: wt-wt for worldwide)",
                                "default": "wt-wt",
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "news_search",
                    "description": "Search for recent news articles",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "News search query"},
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "dork_search",
                    "description": 'Advanced search with dorking techniques. Examples: site:github.com, filetype:pdf, intitle:keyword, inurl:api, "exact phrase", keyword1 -keyword2',
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "dork_query": {
                                "type": "string",
                                "description": "Query with dorking operators (e.g., site:github.com python tutorial)",
                            },
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 10,
                            },
                        },
                        "required": ["dork_query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "academic_search",
                    "description": "Search for academic/scholarly sources",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Academic search query"},
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "code_search",
                    "description": "Search for code repositories (GitHub, GitLab, StackOverflow)",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Code search query"},
                            "max_results": {
                                "type": "integer",
                                "description": "Maximum results",
                                "default": 10,
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "smart_research",
                    "description": "Auto-select best search methods. Uses multiple sources simultaneously.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Research query"},
                            "search_types": {
                                "type": "array",
                                "description": "List of types: web, wiki, news, academic, code",
                                "items": {"type": "string"},
                                "default": ["web", "wiki"],
                            },
                        },
                        "required": ["query"],
                    },
                },
            },
            {
                "type": "function",
                "function": {
                    "name": "fact_check",
                    "description": "Cross-reference multiple sources to verify information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "Statement or fact to verify",
                            }
                        },
                        "required": ["query"],
                    },
                },
            },
        ]

    def call_tool(self, tool_name: str, **kwargs) -> ToolResult:
        """Execute a tool by name with given arguments."""
        if tool_name not in self.tool_map:
            return ToolResult(
                False, error=f"Unknown tool: {tool_name}. Available: {list(self.tool_map.keys())}"
            )

        try:
            logger.info("Calling tool '%s' with args: %s", tool_name, kwargs)
            tool_func = self.tool_map[tool_name]
            result = tool_func(**kwargs)
            self.agent._log_tool_execution(tool_name, kwargs, result)
            return result
        except Exception as e:
            logger.error("Tool execution error [%s]: %s", tool_name, e)
            return ToolResult(False, error=str(e))

    def get_tool_usage_history(self) -> list[dict[str, Any]]:
        """Get history of tool executions."""
        return self.agent.history.copy()

    def format_system_prompt_addition(self) -> str:
        """Get system prompt addition describing tools and environment."""
        os_name = platform.system()
        os_version = platform.release()
        py_version = platform.python_version()

        return f"""

## AI Agent Tools Available

You have access to powerful tools to help users. OPERATE ONLY WITHIN THE LAUNCH DIRECTORY.

### Environment
- **Operating System**: {os_name} {os_version}
- **Platform**: {sys.platform}
- **Python Version**: {py_version}
- **Working Directory**: {self.agent.base_dir}

### Available Tools
- **list_directory** - Browse files and directories with tree view
- **read_file** - Read text file contents
- **write_file** - Create or overwrite files
- **edit_file** - Find and replace in files
- **create_directory** - Create directories
- **delete_path** - Delete files or directories
- **search_files** - Search files by pattern
- **run_command** - Execute shell commands
- **execute_python** - Run Python code
- **validate_python** - Validate Python syntax
- **get_system_info** - View system information
- **get_directory_structure** - See current directory structure

### Important Rules
1. ONLY work within the launch directory and subdirectories
2. NEVER attempt to access paths outside the working directory
3. Use tools proactively when users ask for file/directory operations
4. Always show results of tool operations clearly
5. For file edits, be specific about what text to replace
6. When creating files, ensure parent directories exist
7. Use run_command for OS-specific commands appropriately
"""
