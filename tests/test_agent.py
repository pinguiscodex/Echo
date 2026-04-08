"""Tests for Echo agent orchestration."""

from unittest.mock import MagicMock, patch

import pytest


class TestAgentOrchestrator:
    """Tests for AgentOrchestrator class."""

    def test_initialization(self):
        """Test agent orchestrator initialization."""
        from echo.core.agent import AgentOrchestrator

        with patch("echo.core.agent.AIToolkit") as mock_toolkit:
            orchestrator = AgentOrchestrator()
            assert orchestrator.tool_calls_history == []

    def test_process_tool_calls_empty(self):
        """Test processing empty tool calls."""
        from echo.core.agent import AgentOrchestrator

        with patch("echo.core.agent.AIToolkit") as mock_toolkit:
            orchestrator = AgentOrchestrator()
            results = orchestrator.process_tool_calls([])
            assert results == []

    def test_should_use_tools_heuristic(self):
        """Test tool usage heuristic."""
        from echo.core.agent import AgentOrchestrator

        with patch("echo.core.agent.AIToolkit") as mock_toolkit:
            orchestrator = AgentOrchestrator()

            assert orchestrator.should_use_tools("list files in directory") is True
            assert orchestrator.should_use_tools("read the main.py file") is True
            assert orchestrator.should_use_tools("hello how are you") is False

    def test_get_tool_usage_summary_empty(self):
        """Test tool usage summary when empty."""
        from echo.core.agent import AgentOrchestrator

        with patch("echo.core.agent.AIToolkit") as mock_toolkit:
            orchestrator = AgentOrchestrator()
            summary = orchestrator.get_tool_usage_summary()
            assert summary == "No tools used in this session"
