"""Rich console utilities for Echo AI Chatbot."""

from rich.console import Console
from rich.panel import Panel
from rich.rule import Rule
from rich.table import Table
from rich.text import Text

# Global console instance (thread-safe)
console = Console()
chatbot_console = console  # Alias for backward compatibility


def print_banner(session_id: str, settings) -> None:
    """Print the Echo welcome banner with session info."""

    provider = settings.api_provider
    if provider == "openrouter":
        model = settings.openrouter_model
        provider_style = "bold blue"
    else:
        model = settings.mistral_model
        provider_style = "bold magenta"

    tools_count = 0
    if settings.enable_tools:
        try:
            from echo.tools import AIToolkit

            tools_count = len(AIToolkit().tool_map)
        except Exception:
            pass

    # Build info lines
    info_lines = [
        f"Session: [bold]{session_id}[/]",
        f"Provider: [{provider_style}]{provider.title()}[/]",
        f"Model: [bold]{model}[/]",
        f"Input: [cyan]{settings.input_mode}[/]  |  Output: [cyan]{settings.output_mode}[/]",
        f"Temperature: [yellow]{settings.temperature}[/]",
        f"AI Tools: [{'green' if settings.enable_tools else 'red'}]{'Enabled' if settings.enable_tools else 'Disabled'} ({tools_count} tools)[/]",
    ]

    info_text = "\n".join(info_lines)

    voice_hint = ""
    if settings.input_mode in ("speech", "both"):
        voice_hint = "\n[dim]Voice: Press [bold red]CAPS LOCK[/] to record, press again to stop[/]\n[dim]Text:  Type your message and press [bold]ENTER[/][/] "

    banner = Panel(
        info_text + voice_hint,
        title="[bold white on blue] Echo AI Chatbot [/]",
        border_style="blue",
        padding=(1, 2),
    )

    console.print()
    console.print(banner)
    console.print(Rule(style="dim"))
    console.print()


def print_user_message(text: str) -> None:
    """Print a user message with styling."""
    console.print()
    console.print(Text("You: ", style="bold green") + Text(text, style="green"))


def print_ai_thinking() -> None:
    """Print AI thinking indicator."""
    console.print()
    console.print(Text("AI thinking...", style="dim yellow"))


def print_ai_response(text: str) -> None:
    """Print a complete AI response wrapped in a panel."""
    if not text.strip():
        return
    console.print()
    console.print(
        Panel(text.strip(), border_style="cyan", title="[bold cyan]Echo[/]", padding=(1, 2))
    )


def print_status(message: str, style: str = "dim") -> None:
    """Print a status message. Clears previous line if called consecutively."""
    console.print(f"[{style}]{message}[/]")


def print_error(message: str) -> None:
    """Print an error message."""
    console.print()
    console.print(Panel(message, style="red", border_style="red", title="[bold red]Error[/]"))


def print_tool_execution_start(step: int) -> None:
    """Print tool execution start message."""
    console.print()
    console.print(Text(f"Executing tools (step {step})...", style="bold blue"))


def print_tool_result(tool_name: str, success: bool, content: str) -> None:
    """Print a tool execution result."""
    status_icon = "[green]✓[/]" if success else "[red]✗[/]"
    status_style = "green" if success else "red"
    preview = content[:200] + "..." if len(content) > 200 else content

    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Status", style=status_style, width=2)
    table.add_column("Tool", style="bold blue", width=20)
    table.add_column("Result", style="dim")
    table.add_row(status_icon, tool_name, preview)

    console.print()
    console.print(table)


def print_tts_generating() -> None:
    """Print TTS audio generation status."""
    console.print(Text("Generating audio...", style="dim magenta"))


def print_tts_speaking() -> None:
    """Print TTS playback status."""
    console.print(Text("Speaking...", style="bold magenta"))


def print_recording() -> None:
    """Print recording started status."""
    console.print()
    console.print(
        Text("Recording... ", style="bold red") + Text("(press Caps Lock to stop)", style="dim red")
    )


def print_no_speech() -> None:
    """Print no speech detected message."""
    console.print(Text("No speech detected", style="dim"))


def print_processing_voice() -> None:
    """Print processing voice input status."""
    console.print()
    console.print(Text("Processing voice input...", style="yellow"))


def print_config_loaded() -> None:
    """Print config loaded message."""
    console.print(Text("Config loaded from data/config.json", style="dim"))


def print_toolkit_enabled(count: int) -> None:
    """Print toolkit enabled message."""
    console.print(Text(f"AI Toolkit enabled with {count} tools", style="dim cyan"))


def print_session_started(session_id: str) -> None:
    """Print new session message."""
    console.print(Text(f"New session: {session_id}", style="dim"))


def print_chat_cleared() -> None:
    """Print chat cleared message."""
    console.print(Text("Chat cleared", style="dim green"))


def print_session_saved(session_id: str) -> None:
    """Print session saved message."""
    console.print(Text(f"Session saved: {session_id}", style="dim green"))


def print_save_failed(error: str) -> None:
    """Print save failure message."""
    console.print(Text(f"Save failed: {error}", style="red"))


def print_goodbye() -> None:
    """Print goodbye message."""
    console.print()
    console.print(Rule(style="dim"))
    console.print(Text("Goodbye!", style="bold cyan"))
    console.print()


def print_help() -> None:
    """Print help information with Rich formatting."""
    console.print()
    console.print(
        Panel(
            """[bold cyan]Commands[/]
  [bold]/quit[/] or [bold]/exit[/]     Exit the application
  [bold]/clear[/]                      Clear chat history
  [bold]/help[/]                       Show this help message
  [bold]/save[/]                       Save chat history to disk
  [bold]/load[/]                       Load chat history from disk
  [bold]/tools[/]                      Show AI agent tools status
  [bold]/settings[/]                   Open interactive settings menu

[dim]Voice Controls[/]
  [bold red]CAPS LOCK[/] (press once)    Start recording
  [bold red]CAPS LOCK[/] (press again)   Stop recording and transcribe

[dim]AI Agent Tools[/]
  File operations, code execution, shell commands, and internet research.
  Tools are automatically confined to the working directory.

[dim]Configuration[/]
  Temperature, models, voices, input/output modes configurable via /settings.
  Or edit the .env file directly.[/]""",
            title="[bold]Echo Help[/]",
            border_style="blue",
            padding=(1, 2),
        )
    )
    console.print()


def print_unknown_command(cmd: str) -> None:
    """Print unknown command message."""
    console.print(Text(f"Unknown command: {cmd}", style="yellow"))


def print_api_key_not_configured(provider: str, url: str) -> None:
    """Print API key not configured error."""
    console.print()
    console.print(
        Panel(
            f"[bold]{provider.upper()}_API_KEY[/] not configured!\n\n"
            f"Add your API key to the .env file\n"
            f"Get your key from: [link={url}]{url}[/]",
            style="red",
            border_style="red",
            title="[bold red]Configuration Error[/]",
        )
    )
