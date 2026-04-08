"""OpenRouter and Mistral AI chatbot integration with streaming support."""

import json
import logging
from collections.abc import Generator
from pathlib import Path
from typing import Any

import requests

from echo.config import get_settings

logger = logging.getLogger(__name__)


class ChatResponse:
    """Container for chat response with optional tool calls."""

    def __init__(self, content: str = "", tool_calls: list[dict[str, Any]] | None = None):
        self.content = content
        self.tool_calls = tool_calls or []

    def has_tool_calls(self) -> bool:
        return len(self.tool_calls) > 0

    def __bool__(self):
        return bool(self.content) or self.has_tool_calls()


class EchoChatbot:
    """AI chatbot integration using OpenRouter or Mistral API with streaming responses."""

    def __init__(self, system_prompt: str | None = None, toolkit: Any | None = None):
        """Initialize the chatbot with settings and conversation history.

        Args:
            system_prompt: Custom system prompt (uses settings default if None)
            toolkit: AIToolkit instance for text-based tool calling (optional)
        """
        self.settings = get_settings()
        self.messages: list[dict] = []
        self.toolkit = toolkit

        # Determine API provider
        self.api_provider = self.settings.api_provider
        if self.api_provider == "openrouter":
            self.api_url = "https://openrouter.ai/api/v1/chat/completions"
            self.api_model = self.settings.openrouter_model
        elif self.api_provider == "mistral":
            self.api_url = "https://api.mistral.ai/v1/chat/completions"
            self.api_model = self.settings.mistral_model
        else:
            raise ValueError(f"Unknown API provider: {self.api_provider}")

        # Set system prompt
        prompt = system_prompt or self.settings.system_prompt
        self.messages.append({"role": "system", "content": prompt})

        logger.info(
            "EchoChatbot initialized with provider: %s, model: %s",
            self.api_provider,
            self.api_model,
        )
        if self.toolkit:
            logger.info("Text-based AI Toolkit enabled with %d tools", len(self.toolkit.tool_map))

    def _get_api_key(self) -> str | None:
        """Get the API key for the selected provider."""
        if self.api_provider == "openrouter":
            return self.settings.openrouter_api_key
        if self.api_provider == "mistral":
            return self.settings.mistral_api_key
        return None

    def _get_headers(self) -> dict[str, str]:
        """Get request headers for the selected provider."""
        api_key = self._get_api_key()
        if self.api_provider == "openrouter":
            return {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": "https://github.com/echo-chatbot",
                "X-Title": "Echo AI Chatbot",
            }
        if self.api_provider == "mistral":
            return {
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            }
        return {}

    def _build_request_data(self) -> dict[str, Any]:
        """Build request payload for the selected provider."""
        request_data = {
            "model": self.api_model,
            "messages": self.messages,
            "temperature": self.settings.temperature,
            "max_tokens": self.settings.max_tokens,
            "stream": True,
        }

        # Add tools if toolkit is available
        if self.toolkit:
            if self.api_provider == "openrouter" or self.api_provider == "mistral":
                request_data["tools"] = self.toolkit.tool_definitions
                request_data["tool_choice"] = "auto"

        return request_data

    def add_message(self, role: str, content: str, reasoning_details: str | None = None) -> None:
        """Add a message to the conversation history.

        Args:
            role: Message role ('user', 'assistant', 'system', or 'tool')
            content: Message content
            reasoning_details: Optional reasoning details for assistant messages
        """
        message = {"role": role, "content": content}
        if reasoning_details and role == "assistant":
            message["reasoning_details"] = reasoning_details
        self.messages.append(message)

    def chat(self, user_input: str) -> Generator[str, None, ChatResponse]:
        """Send a message to the API and stream the response.

        Args:
            user_input: User's input message

        Yields:
            Response tokens as they arrive

        Returns:
            ChatResponse object with content and any tool_calls
        """
        api_key = self._get_api_key()
        if (
            not api_key
            or api_key == "your_openrouter_api_key_here"
            or api_key == "your_mistral_api_key_here"
        ):
            error_msg = f"Error: {self.api_provider.upper()}_API_KEY not configured. Please set it in .env file."
            logger.error(error_msg)
            yield error_msg
            return ChatResponse(content=error_msg)

        # Add user message
        self.add_message("user", user_input)

        full_response = ""
        reasoning_details = None
        tool_calls = []

        try:
            # Build request payload using helper
            request_data = self._build_request_data()

            response = requests.post(
                self.api_url,
                headers=self._get_headers(),
                json=request_data,
                timeout=60,
                stream=True,
            )

            response.raise_for_status()

            # Process streaming response
            for line in response.iter_lines():
                if line:
                    line = line.decode("utf-8")
                    if line.startswith("data: "):
                        data = line[6:]
                        if data == "[DONE]":
                            break
                        try:
                            chunk = json.loads(data)
                            if "choices" in chunk and len(chunk["choices"]) > 0:
                                delta = chunk["choices"][0].get("delta", {})

                                # Handle text content
                                content = delta.get("content", "")
                                if content:
                                    full_response += content
                                    yield content

                                # Handle tool calls
                                if "tool_calls" in delta:
                                    for tc in delta["tool_calls"]:
                                        # Find or create tool call entry
                                        index = tc.get("index", 0)
                                        while len(tool_calls) <= index:
                                            tool_calls.append(
                                                {
                                                    "id": "",
                                                    "function": {"name": "", "arguments": ""},
                                                }
                                            )

                                        if "id" in tc and tc["id"]:
                                            tool_calls[index]["id"] = tc["id"]
                                        if "function" in tc:
                                            if "name" in tc["function"] and tc["function"]["name"]:
                                                tool_calls[index]["function"]["name"] = tc[
                                                    "function"
                                                ]["name"]
                                            if (
                                                "arguments" in tc["function"]
                                                and tc["function"]["arguments"]
                                            ):
                                                tool_calls[index]["function"]["arguments"] += tc[
                                                    "function"
                                                ]["arguments"]

                        except json.JSONDecodeError as e:
                            logger.debug("JSON decode error: %s", e)
                            continue

            # Add assistant response to history
            self.add_message("assistant", full_response, reasoning_details)

            # If there are tool_calls, add them to the message history as well
            if tool_calls:
                self.messages.append(
                    {"role": "assistant", "content": None, "tool_calls": tool_calls}
                )

            logger.info(
                "Response received: %d characters, %d tool_calls",
                len(full_response),
                len(tool_calls),
            )

            return ChatResponse(content=full_response, tool_calls=tool_calls)

        except requests.exceptions.Timeout:
            error_msg = "Error: Request timed out. Please try again."
            logger.error("Request timeout: %s", error_msg)
            yield error_msg
            return ChatResponse(content=error_msg)

        except requests.exceptions.RequestException as e:
            error_msg = f"Error: API request failed - {str(e)}"
            logger.error("Request error: %s", e)
            yield error_msg
            return ChatResponse(content=error_msg)

        except Exception as e:
            error_msg = f"Error: Unexpected error - {str(e)}"
            logger.error("Unexpected error: %s", e, exc_info=True)
            yield error_msg
            return ChatResponse(content=error_msg)

    def chat_sync(self, user_input: str) -> ChatResponse:
        """Synchronous chat method that returns complete response.

        Args:
            user_input: User's input message

        Returns:
            ChatResponse object with content and any tool_calls
        """
        full_response = ""
        generator = self.chat(user_input)

        # Consume the generator
        for chunk in generator:
            full_response = chunk

        # The generator's return value has the ChatResponse, but we can't access it
        # So we need to track tool_calls separately. For now, rebuild from messages.
        chat_response = ChatResponse(content=full_response)

        # Extract tool_calls from the last assistant message if present
        if self.messages and self.messages[-1].get("role") == "assistant":
            if "tool_calls" in self.messages[-1]:
                chat_response.tool_calls = self.messages[-1]["tool_calls"]

        return chat_response

    def clear_history(self) -> None:
        """Clear conversation history, keeping only system prompt."""
        self.messages = [self.messages[0]]  # Keep system prompt
        logger.info("Conversation history cleared")

    def get_history(self) -> list[dict]:
        """Get conversation history.

        Returns:
            List of message dictionaries
        """
        return self.messages.copy()

    def save_history(self, filepath: Path | None = None) -> Path:
        """Save conversation history to file.

        Args:
            filepath: Custom filepath (uses default if None)

        Returns:
            Path to saved file
        """
        if filepath is None:
            filepath = Path("data/chat_history.json")

        filepath.parent.mkdir(parents=True, exist_ok=True)

        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(self.messages, f, indent=2, ensure_ascii=False)

        logger.info("Chat history saved to: %s", filepath)
        return filepath

    def load_history(self, filepath: Path | None = None) -> None:
        """Load conversation history from file.

        Args:
            filepath: Custom filepath (uses default if None)
        """
        if filepath is None:
            filepath = Path("data/chat_history.json")

        if not filepath.exists():
            logger.info("No chat history found at: %s", filepath)
            return

        try:
            with open(filepath, encoding="utf-8") as f:
                self.messages = json.load(f)
            logger.info("Chat history loaded from: %s", filepath)
        except Exception as e:
            logger.error("Failed to load chat history: %s", e)
