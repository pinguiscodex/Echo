"""Echo AI Chatbot - Voice-enabled CLI chatbot with OpenRouter integration."""

__version__ = "1.0.0"
__author__ = "Christoph"
__all__ = ["EchoConsoleApp", "EchoChatbot", "AgentOrchestrator", "AIToolkit"]


def __getattr__(name):
    """Lazy imports to avoid circular dependencies."""
    if name == "EchoChatbot":
        from echo.core.chatbot import EchoChatbot

        return EchoChatbot
    elif name == "ChatResponse":
        from echo.core.chatbot import ChatResponse

        return ChatResponse
    elif name == "AgentOrchestrator":
        from echo.core.agent import AgentOrchestrator

        return AgentOrchestrator
    elif name == "AIToolkit":
        from echo.tools import AIToolkit

        return AIToolkit
    elif name == "EchoConsoleApp":
        from echo.cli import EchoConsoleApp

        return EchoConsoleApp
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
