"""Agent orchestration for Echo AI Chatbot - manages tool calling workflow."""

import json
import logging
from typing import Any, Dict, List, Optional

from echo.tools import AIToolkit

logger = logging.getLogger(__name__)


class AgentOrchestrator:
    """Manages AI agent tool calling workflow."""

    def __init__(self, toolkit: Optional[AIToolkit] = None):
        """Initialize agent orchestrator.

        Args:
            toolkit: AI Toolkit instance (creates new one if None)
        """
        self.toolkit = toolkit or AIToolkit()
        self.tool_calls_history: List[Dict[str, Any]] = []
        logger.info("Agent Orchestrator initialized")

    def process_tool_calls(self, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Execute tool calls and format results for AI."""
        results = []

        for tool_call in tool_calls:
            try:
                tool_id = tool_call.get("id", "")
                function_info = tool_call.get("function", {})
                tool_name = function_info.get("name", "")
                arguments_str = function_info.get("arguments", "{}")

                if not tool_name:
                    logger.error("Tool call missing tool name")
                    results.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": "Error: Tool call missing tool name",
                        }
                    )
                    continue

                try:
                    arguments = json.loads(arguments_str) if arguments_str else {}
                    logger.debug("Parsed arguments for %s: %s", tool_name, arguments)
                except json.JSONDecodeError as e:
                    logger.error("Failed to parse tool arguments for %s: %s", tool_name, e)
                    results.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": f"Error: Invalid JSON arguments - {e}",
                        }
                    )
                    continue

                if not arguments:
                    logger.warning("Tool %s called with no arguments", tool_name)
                    results.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": f"Error: Tool '{tool_name}' requires arguments but none were provided",
                        }
                    )
                    continue

                missing_required = []
                for key, value in arguments.items():
                    if value is None or (isinstance(value, str) and not value.strip()):
                        missing_required.append(key)

                if missing_required:
                    logger.warning(
                        "Tool %s has empty required arguments: %s", tool_name, missing_required
                    )
                    results.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": f"Error: Tool '{tool_name}' has empty values for: {', '.join(missing_required)}",
                        }
                    )
                    continue

                logger.debug("Tool %s arguments validated successfully: %s", tool_name, arguments)
                logger.info("Executing tool: %s with args: %s", tool_name, arguments)

                result = self.toolkit.call_tool(tool_name, **arguments)

                self.tool_calls_history.append(
                    {
                        "tool": tool_name,
                        "args": arguments,
                        "success": result.success,
                        "content_preview": result.content[:200] if result.content else "",
                    }
                )

                if result.success:
                    content = result.content
                    if len(content) > 4000:
                        content = (
                            content[:4000]
                            + f"\n... (truncated, total length: {len(result.content)} chars)"
                        )

                    results.append({"role": "tool", "tool_call_id": tool_id, "content": content})
                else:
                    results.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_id,
                            "content": f"Error: {result.error}",
                        }
                    )

            except Exception as e:
                logger.error("Tool execution failed: %s", e, exc_info=True)
                results.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", "unknown"),
                        "content": f"Execution error: {str(e)}",
                    }
                )

        logger.info("Executed %d tool calls", len(results))
        return results

    def format_tool_results_for_display(self, results: List[Dict[str, Any]]) -> str:
        """Format tool results for display to user."""
        if not results:
            return ""

        lines = []
        for result in results:
            content = result.get("content", "")
            if len(content) > 200:
                content = content[:200] + "..."
            lines.append(f"[Tool: {content}]")

        return "\n".join(lines)

    def should_use_tools(self, user_message: str) -> bool:
        """Determine if a message might benefit from tool use."""
        tool_indicators = [
            "file",
            "directory",
            "folder",
            "create",
            "read",
            "write",
            "list",
            "show",
            "run",
            "execute",
            "system",
            "info",
            "search",
            "find",
            "delete",
            "remove",
            "edit",
            "replace",
        ]

        message_lower = user_message.lower()
        return any(indicator in message_lower for indicator in tool_indicators)

    def get_tool_usage_summary(self) -> str:
        """Get summary of recent tool usage."""
        if not self.tool_calls_history:
            return "No tools used in this session"

        summary_lines = ["Recent tool usage:"]
        for call in self.tool_calls_history[-5:]:
            status = "[OK]" if call["success"] else "[FAIL]"
            summary_lines.append(
                f"  {status} {call['tool']}: {call.get('content_preview', '')[:100]}"
            )

        return "\n".join(summary_lines)
