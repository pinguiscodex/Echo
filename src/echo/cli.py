"""
Echo AI Chatbot - CLI interface with voice support and AI agent tools.

Pure terminal chatbot with no TUI dependencies.
Tools use TEXT-BASED calling convention compatible with GPT-OSS-120B.
"""

import logging
import os
import sys
import tempfile
import threading
import time

# Suppress warnings
import warnings
from pathlib import Path

warnings.filterwarnings("ignore")

# Suppress telemetry
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"

try:
    from pythonclimenu import menu as cli_menu
    from rich.panel import Panel
    from rich.table import Table
    from rich.text import Text

    from echo.config import ConfigStore, get_settings, reload_settings, switch_model_settings
    from echo.core.agent import AgentOrchestrator
    from echo.core.chatbot import ChatResponse, EchoChatbot
    from echo.core.recorder import AudioRecorder
    from echo.core.transcriber import WhisperTranscriber
    from echo.core.tts import TTSEngine
    from echo.services.session import ChatSessionManager
    from echo.tools import AIToolkit
    from echo.utils.console import (
        console,
        print_ai_thinking,
        print_api_key_not_configured,
        print_banner,
        print_chat_cleared,
        print_error,
        print_goodbye,
        print_help,
        print_no_speech,
        print_processing_voice,
        print_recording,
        print_save_failed,
        print_session_saved,
        print_status,
        print_tool_execution_start,
        print_tool_result,
        print_tts_generating,
        print_tts_speaking,
        print_unknown_command,
        print_user_message,
    )
    from echo.utils.helpers import cleanup_temp_files, ensure_directories
    from echo.utils.logging import create_session_log, setup_logging

    def make_selection(options, label="Select"):
        """Wrapper around python-cli-menu to match make_selection API."""
        return cli_menu(title=label, options=options, cursor_color="cyan")

except ImportError as e:
    print(f"Error: {e}")
    print("Install dependencies: pip install -e .")
    sys.exit(1)


class EchoConsoleApp:
    """Main Echo application - pure terminal I/O."""

    def __init__(self):
        self.settings = get_settings()
        self.running = False
        self.recording = False
        self.speaking = False
        self._recording_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._audio_path: Path | None = None
        self._voice_processing = False  # Blocks prompt while transcribing/AI responds

        self.chatbot: EchoChatbot | None = None
        self.recorder: AudioRecorder | None = None
        self.transcriber: WhisperTranscriber | None = None
        self.tts: TTSEngine | None = None
        self.toolkit: AIToolkit | None = None
        self.agent_orchestrator: AgentOrchestrator | None = None
        self.session_manager: ChatSessionManager | None = None
        self.session_id: str | None = None

    def _log(self, message: str):
        """Log message to console."""
        console.print()
        console.print(message)

    def _log_override(self, message: str):
        """Log message, clearing the current input line first.

        Used when recording starts/stops while user is at the prompt.
        """
        # Clear current line and move cursor to beginning
        console.print("\r\033[K", end="")
        console.print(f"[{message}]")

    def _reprompt(self):
        """Re-show the input prompt after recording finishes."""
        console.print(Text("You: ", style="bold green"), end="")

    def _init_components(self):
        """Initialize all core components."""
        # Apply config.json if it exists (overrides .env defaults)
        config_data = ConfigStore.load_config()
        if config_data:
            ConfigStore.apply_config(self.settings, config_data)
            ConfigStore.sync_to_env(self.settings)
            logging.getLogger(__name__).info("Config loaded from data/config.json")

        # Initialize toolkit if enabled
        toolkit = None
        if self.settings.enable_tools:
            toolkit = AIToolkit()
            self.toolkit = toolkit
            self.agent_orchestrator = AgentOrchestrator(toolkit=toolkit)
            logging.getLogger(__name__).info(
                "AI Toolkit enabled with %d tools", len(toolkit.tool_map)
            )

        # Build enhanced system prompt with tool instructions
        import platform
        import sys as sys_mod

        base_prompt = self.settings.system_prompt
        system_prompt = f"""{base_prompt}

CORE PRINCIPLES

1. Clarity First
   - Speak in plain, natural language that sounds great when read aloud.
   - Use short to medium sentences. Vary sentence structure for engagement.
   - Explain complex ideas simply, but never talk down to the user.
   - If something is uncertain, say so clearly and suggest next steps.

2. Voice-Optimized Output (CRITICAL)
   - NEVER use any formatting characters that would sound awkward when spoken:
     - No asterisks: * or **
     - No underscores: _
     - No backticks: `
     - No quotation marks for emphasis: " or '
     - No markdown headers: # or ##
     - No bullet symbols: - or * at line start
     - No emojis of any kind
     - No special symbols like arrows, dots, dashes used for decoration
   - Write as if you are speaking naturally to someone.
   - Use numbers naturally: "three options" not "3 options" unless it is a specific value.
   - Spell out abbreviations on first use if they might be unclear when spoken.

3. Adapt to Context
   - Match the user tone: casual for chat, professional for work tasks, technical for code.
   - Scale detail to the query: brief answers for simple questions, thorough explanations for complex ones.
   - Anticipate follow-up needs and offer relevant next steps without being pushy.

4. Accuracy and Honesty
   - Base answers on facts. If using tools, synthesize results clearly.
   - If you do not know something, say so directly and offer to find out or suggest alternatives.
   - Never hallucinate citations, code, or facts.
   - Distinguish clearly between facts, opinions, and speculation.

5. Proactive Helpfulness
   - Break complex tasks into clear, logical steps.
   - Offer concise summaries before diving into details.
   - When multiple options exist, present them with clear trade-offs.
   - Suggest relevant tools or actions when they could help.

ENVIRONMENT

  Operating System: {platform.system()} {platform.release()}
  Platform: {sys_mod.platform}
  Python Version: {platform.python_version()}
  Working Directory: {Path.cwd()}

DIRECTORY CONFINEMENT

You are STRICTLY CONFINED to the working directory: {Path.cwd()}

CRITICAL RULES:
1. You can ONLY access files and directories WITHIN {Path.cwd()} and its subdirectories.
2. If a user asks about a path OUTSIDE this directory, you MUST inform them that you can only access files within the working directory.
3. NEVER attempt to use tools with paths outside the working directory.
4. ALWAYS use relative paths from the working directory, for example: "file.txt" not "/home/user/file.txt".

YOUR TOOLS

You have access to powerful tools for file operations, code execution, shell commands, AND INTERNET RESEARCH.
File operations are STRICTLY CONFINED to the working directory and subdirectories.
Research tools (Wikipedia, DuckDuckGo) have NO directory restrictions -- you can search the entire internet.

When you need to use tools, respond with EXACTLY this format (one tool per line):

[TOOL:tool_name]
[param1: value1]
[param2: value2]
[END_TOOL]

File and System Tools (CONFINED to working directory):
  list_directory [path: "."] -- List files in directory with tree view
  read_file [path: "filename"] -- Read text file contents
  write_file [path: "filename"] [content: "file content here"] -- Create or overwrite files
  edit_file [path: "filename"] [old_text: "text to find"] [new_text: "replacement"] -- Edit files
  create_directory [path: "dirname"] -- Create directories
  delete_path [path: "filename"] [recursive: false] -- Delete files or directories
  search_files [pattern: "*.py"] [path: "."] -- Search files by pattern
  run_command [command: "ls -la"] [timeout: 30] -- Execute shell commands
  execute_python [code: "print('hello')"] [timeout: 30] -- Run Python code
  validate_python [code: "x = 1"] -- Validate Python syntax
  get_system_info -- Get system information
  get_directory_structure -- Get current directory structure

Research Tools (UNRESTRICTED -- can search entire internet):
  wikipedia_search [query: "Quantum Computing"] [results: 5] -- Search Wikipedia articles
  wikipedia_summary [query: "Artificial Intelligence"] [sentences: 3] -- Get article summary
  wikipedia_full_article [query: "Machine Learning"] -- Get complete article content
  wikipedia_random -- Get random Wikipedia articles
  web_search [query: "latest AI developments 2024"] [max_results: 10] -- Search entire web
  news_search [query: "technology"] [max_results: 10] -- Search recent news
  dork_search [dork_query: "site:github.com python tutorial"] [max_results: 10] -- Advanced dorking
  academic_search [query: "machine learning"] [max_results: 10] -- Academic and scholarly sources
  code_search [query: "python web framework"] [max_results: 10] -- Code repositories
  smart_research [query: "climate change"] [search_types: ["web", "wiki", "news"]] -- Multi-source research
  fact_check [query: "statement to verify"] -- Cross-reference multiple sources

Advanced Web Dorking Techniques:
  Use these in web_search, dork_search, or any web search query.
  Site-specific: site:github.com python tutorial
  File type: filetype:pdf machine learning tutorial
  Title search: intitle:security vulnerabilities
  URL search: inurl:api documentation
  Exact phrase: "artificial intelligence ethics"
  Exclude terms: python programming -snake
  OR logic: machine learning OR deep learning
  Wildcard: best * for programming
  Number range: python tutorial 2020..2024
  Combined: site:medium.com intitle:python filetype:pdf

When to Use Research Tools:
  User asks about current events: use web_search or news_search
  User wants to learn about a topic: use wikipedia_summary or wikipedia_full_article
  User asks for comparisons: use smart_research with multiple sources
  User wants specific file types: use web_search with filetype dorking
  User needs academic sources: use academic_search
  User wants code examples: use code_search
  User asks to verify information: use fact_check
  PROACTIVELY offer to research when users ask questions that need factual answers.

IMPORTANT:
  If a tool fails, always explain what happened to the user.
  NEVER return an empty response -- always say something.
  For directory confinement errors, EXPLAIN the restriction to the user.
  After tool execution, you will receive the result. Continue responding normally.
  For regular responses, do NOT use the tool format -- just respond naturally.

CONVERSATION FLOW

  Start with a direct answer to the core question.
  Expand with context, details, or options as needed.
  End with a natural invitation for follow-up.
  Remember conversation context and refer back naturally when relevant.

WHAT TO AVOID

  No formatting characters of any kind: no asterisks, backticks, markdown, emojis, special symbols.
  No robotic phrases like "As an AI language model" or "I hope this helps."
  No unnecessary apologies.
  No walls of text -- break long answers into natural paragraphs.

Remember: Your voice is your interface. Every word you write will be spoken aloud. Make it sound natural, clear, and helpful.
"""

        self.chatbot = EchoChatbot(system_prompt=system_prompt, toolkit=toolkit)
        self.recorder = AudioRecorder()
        self.transcriber = WhisperTranscriber()
        self.tts = TTSEngine()

        # Initialize session manager and create/load current session
        self.session_manager = ChatSessionManager()
        self.session_id = self.session_manager.create_session(
            system_prompt=system_prompt
        ).session_id
        logging.getLogger(__name__).info("New session started: %s", self.session_id)

    def _start_caps_lock_monitor(self):
        """Start monitoring Caps Lock as a TOGGLE for voice recording.

        Toggle behavior:
          - Press Caps Lock once  → start recording (LED turns ON)
          - Press Caps Lock again → stop recording & transcribe (LED turns OFF)
        """
        if self.settings.input_mode not in ("speech", "both"):
            return

        # ── Try pynput first (works on Linux X11 without root) ──────────
        try:
            from pynput import keyboard as pynput_kb

            def on_caps_release(key, _listener):
                """Toggle recording on each Caps Lock release."""
                if key != pynput_kb.Key.caps_lock:
                    return
                if self.speaking:
                    return  # Don't toggle during speech playback
                if not self.running:
                    return

                if not self.recording:
                    # Toggle ON → start recording
                    self._start_recording()
                else:
                    # Toggle OFF → stop & transcribe
                    self._stop_recording()

            listener = pynput_kb.Listener(on_release=lambda key: on_caps_release(key, listener))
            listener.daemon = True
            listener.start()
            return
        except Exception as e:
            self._log(f"[pynput failed: {e}]")

        # ── Fallback: keyboard library ──────────────────────────────────
        try:
            import keyboard

            def on_event(event):
                if event.name != "caps lock":
                    return
                if event.event_type != "down":
                    return  # Only toggle on key-down to avoid double-fire
                if self.speaking or not self.running:
                    return

                if not self.recording:
                    self._start_recording()
                else:
                    self._stop_recording()

            keyboard.hook(on_event)
            return
        except (PermissionError, OSError) as e:
            self._log(f"[keyboard failed: {e}]")
        except ImportError:
            pass

        # ── All backends failed ─────────────────────────────────────────
        self._log("[Voice input disabled — no keyboard backend available]")
        if sys.platform.startswith("linux"):
            self._log("[Install pynput: pip install pynput]")

    def _start_recording(self):
        """Start recording — triggered by Caps Lock toggle ON."""
        if self.recording or not self.recorder:
            return
        self.recording = True
        self._stop_event.clear()
        self._audio_path = Path(tempfile.mktemp(suffix=".wav"))
        print_recording()

        import numpy as np
        import sounddevice as sd
        import soundfile as sf

        def record():
            chunks = []
            sr = self.settings.sample_rate
            block = int(sr * 0.05)
            try:
                stream = sd.InputStream(
                    samplerate=sr, channels=1, dtype=np.float32, blocksize=block
                )
                stream.start()
                while not self._stop_event.is_set():
                    data, _ = stream.read(block)
                    chunks.append(data.copy())
                    time.sleep(0.05)
                stream.stop()
                stream.close()
                if chunks:
                    audio = np.concatenate(chunks, axis=0)
                    sf.write(str(self._audio_path), audio, sr)
            except Exception as e:
                self._log(f"[Recording error: {e}]")
                self._audio_path = None

        self._recording_thread = threading.Thread(target=record, daemon=True)
        self._recording_thread.start()

    def _stop_recording(self):
        """Stop recording — triggered by Caps Lock toggle OFF."""
        logger = logging.getLogger(__name__)
        if not self.recording:
            logger.debug("_stop_recording called but not recording")
            return
        logger.info("Stopping recording...")
        print_processing_voice()
        self._stop_event.set()
        if self._recording_thread and self._recording_thread.is_alive():
            self._recording_thread.join(timeout=5.0)
            logger.debug("Recording thread joined")

        audio_path = self._audio_path
        self._audio_path = None
        self._recording_thread = None

        # Clear recording state
        self.recording = False
        logger.info("Recording stopped, audio path: %s", audio_path)

        if audio_path and audio_path.exists():
            # Transcribe first, then block prompt only if there's speech
            try:
                logger.info("Transcribing audio: %s", audio_path)
                text = self.transcriber.transcribe(audio_path) if self.transcriber else ""
                logger.info("Transcription result: %s", repr(text))
            except Exception as e:
                logger.error("Transcription failed: %s", e, exc_info=True)
                self._log_override(f"Transcription failed: {e}")
                self._reprompt()
                if audio_path.exists():
                    audio_path.unlink(missing_ok=True)
                return

            if audio_path.exists():
                audio_path.unlink(missing_ok=True)
                logger.debug("Temporary audio file deleted")

            if not text or not text.strip():
                logger.info("No speech detected in audio")
                print_no_speech()
                self._reprompt()
                return

            # We have speech — block prompt until AI responds
            logger.info("Processing voice input: %s", text[:100])
            self._voice_processing = True
            print_user_message(text)
            self._handle_chat(text)
            self._voice_processing = False
            logger.info("Voice processing complete")
            self._reprompt()
        else:
            logger.warning("No audio recorded or file does not exist")
            self._log_override("No audio recorded")
            self._reprompt()

    def _process_text_input(self, text: str):
        """Process text input."""
        logger = logging.getLogger(__name__)
        logger.info("Processing text input: %s", text[:100])
        if not all([self.chatbot, self.tts]):
            logger.error("Chatbot or TTS not initialized")
            return
        self._handle_chat(text)

    def _handle_chat(self, user_text: str, max_retries: int = 2):
        """Handle chat request with streaming and multi-step tool execution."""
        logger = logging.getLogger(__name__)
        logger.info("_handle_chat called with: %s", user_text[:100])

        # Track user message in session
        if self.session_manager:
            self.session_manager.add_message("user", user_text)

        max_tool_iterations = 10  # Prevent infinite loops
        tool_iteration = 0
        full_response = ""

        try:
            # First call: send user message
            console.print()
            console.print(Text("AI thinking...", style="dim yellow"))
            logger.info("Sending request to AI...")
            for chunk in self.chatbot.chat(user_text):
                full_response += chunk
                console.print(chunk, end="")
            console.print()  # Newline after response
            logger.info("AI response received: %d chars", len(full_response))

            # Multi-step tool execution loop
            while tool_iteration < max_tool_iterations:
                # Extract tool_calls from the LAST assistant message (the most recent one).
                # When Mistral returns tool_calls with no text content, the message has
                # content: None but full_response is "". We must check the last message only.
                tool_calls = []
                if self.chatbot.messages and self.chatbot.messages[-1].get("role") == "assistant":
                    last_msg = self.chatbot.messages[-1]
                    tool_calls = last_msg.get("tool_calls", [])

                chat_response = ChatResponse(content=full_response, tool_calls=tool_calls)

                # Handle empty responses with retry (but NOT if there are tool_calls)
                if not full_response.strip():
                    if chat_response.has_tool_calls():
                        # Has tool calls but no text - proceed with tool execution
                        pass
                    elif max_retries > 0:
                        console.print()
                        console.print(
                            Text("[AI returned empty response, retrying...]", style="dim yellow")
                        )
                        self.chatbot.messages.pop()  # Remove empty assistant message
                        self._handle_chat(
                            "(Please respond to my previous message. You returned an empty response.)",
                            max_retries - 1,
                        )
                        return
                    else:
                        console.print()
                        console.print(
                            Text("[AI returned empty response after retries]", style="dim yellow")
                        )
                        return

                # Check for native tool_calls
                if (
                    self.agent_orchestrator
                    and self.settings.enable_tools
                    and chat_response.has_tool_calls()
                ):
                    tool_iteration += 1
                    print_tool_execution_start(tool_iteration)
                    tool_results = self.agent_orchestrator.process_tool_calls(
                        chat_response.tool_calls
                    )

                    # Display tool results
                    for result in tool_results:
                        content = result.get("content", "")
                        success = not content.startswith("Error:")
                        tool_name = ""
                        for tc in chat_response.tool_calls:
                            fn = tc.get("function", {})
                            if fn.get("name"):
                                tool_name = fn["name"]
                                break
                        print_tool_result(tool_name or "unknown", success, content)

                    # Add tool results as proper tool-role messages
                    for tool_result in tool_results:
                        self.chatbot.messages.append(tool_result)

                    # Get AI follow-up using chat_continue() (no user message added)
                    print_ai_thinking()
                    full_response = ""
                    for chunk in self.chatbot.chat_continue():
                        full_response += chunk
                        console.print(chunk, end="")
                    console.print()
                    continue  # Loop back to check for more tool_calls

                # Check for text-based tool calls (fallback)
                if self.toolkit and self.settings.enable_tools and "[TOOL:" in full_response:
                    tool_iteration += 1
                    tool_output = self._execute_text_tools(full_response)
                    if tool_output:
                        console.print()
                        console.print(
                            Panel(
                                tool_output[:500],
                                border_style="blue",
                                title="Tool Output",
                                padding=(1, 2),
                            )
                        )
                        # Send tool result back to AI for follow-up
                        print_ai_thinking()
                        full_response = ""
                        for chunk in self.chatbot.chat(
                            f"Tool execution result:\n{tool_output}\n\nPlease summarize what was done and continue helping."
                        ):
                            full_response += chunk
                            console.print(chunk, end="")
                        console.print()
                        continue  # Loop back to check for more tool_calls

                # No more tool calls - exit loop
                break

            if tool_iteration >= max_tool_iterations:
                console.print()
                console.print(Text("[Warning: Maximum tool iterations reached]", style="yellow"))

            # Track assistant response in session
            if self.session_manager and full_response.strip():
                self.session_manager.add_message("assistant", full_response)

            # TTS if enabled
            if self.settings.output_mode in ("speech", "both") and full_response.strip():
                # Skip TTS for error messages
                is_error = full_response.strip().startswith(("Error:", "API request failed"))
                if is_error:
                    logger.info("TTS skipped (error response): %s", full_response[:100])
                else:
                    self.speaking = True
                    logger.info("Starting TTS for response: %d chars", len(full_response))
                    tts_thread = threading.Thread(
                        target=self._run_tts, args=(full_response,), daemon=True
                    )
                    tts_thread.start()
                    tts_thread.join()
                    logger.info("TTS thread joined")
            else:
                logger.info(
                    "TTS skipped: output_mode=%s, response_empty=%s",
                    self.settings.output_mode,
                    not full_response.strip(),
                )
        except Exception as e:
            logger.error("_handle_chat failed: %s", e, exc_info=True)
            console.print()
            console.print(
                Panel(f"Chat failed: {e}", style="red", border_style="red", title="Error")
            )

    def _execute_text_tools(self, response: str) -> str:
        """Parse and execute text-based tool calls from AI response.

        Format: [TOOL:tool_name]\n[param: value]\n[END_TOOL]
        """
        import re

        tool_pattern = r"\[TOOL:(\w+)\](.*?)\[END_TOOL\]"
        param_pattern = r"\[(\w+):\s*(.*?)\]"

        results = []
        for match in re.finditer(tool_pattern, response, re.DOTALL):
            tool_name = match.group(1).strip()
            params_str = match.group(2).strip()

            # Parse parameters
            params = {}
            for param_match in re.finditer(param_pattern, params_str):
                param_name = param_match.group(1).strip()
                param_value = param_match.group(2).strip()
                # Strip quotes
                param_value = param_value.strip("\"'")

                # Auto-convert numeric strings to proper types
                if param_value.isdigit():
                    param_value = int(param_value)
                else:
                    try:
                        # Try float conversion
                        if "." in param_value:
                            param_value = float(param_value)
                    except (ValueError, TypeError):
                        pass  # Keep as string

                params[param_name] = param_value

            # Execute tool
            if tool_name in self.toolkit.tool_map:
                try:
                    result = self.toolkit.call_tool(tool_name, **params)
                    if result.success:
                        content = result.content[:500] if result.content else "Success"
                        if len(result.content) > 500:
                            content += "... (truncated)"
                        results.append(f"[OK] {tool_name}: {content}")
                    else:
                        results.append(f"[FAIL] {tool_name}: {result.error}")
                except Exception as e:
                    results.append(f"[FAIL] {tool_name}: Execution error - {e}")
            else:
                results.append(f"[FAIL] {tool_name}: Unknown tool")

        return "\n".join(results) if results else ""

    def _run_tts(self, text: str):
        """Run TTS playback with Rich status messages."""
        import sys

        last_status = [None]

        def show_status(msg):
            """Show status message, clearing previous one."""
            if last_status[0]:
                # Move cursor up one line and clear it using raw stdout
                sys.stdout.write("\033[1A\r\033[K")
                sys.stdout.flush()
            if "Generating" in msg:
                console.print(Text("Generating audio...", style="dim magenta"))
            elif "Speaking" in msg:
                console.print(Text("Speaking...", style="bold magenta"))
            else:
                console.print(Text(msg, style="dim magenta"))
            last_status[0] = msg

        logger = logging.getLogger(__name__)
        logger.info("TTS playback started for text: %s", text[:100])
        try:
            self.tts.speak(text, status_callback=show_status)
            logger.info("TTS playback completed successfully")
        except Exception as e:
            logger.error("TTS playback error: %s", e, exc_info=True)
            console.print()
            console.print(
                Panel(f"TTS playback error: {e}", style="red", border_style="red", title="Error")
            )
        finally:
            # Clear the final status line
            if last_status[0]:
                sys.stdout.write("\033[1A\r\033[K")
                sys.stdout.flush()
            # Always reset speaking state when TTS completes
            self.speaking = False
            logger.info("TTS speaking flag reset")

    def _handle_command(self, cmd: str) -> bool:
        """Handle slash commands. Returns True to exit."""
        cmd = cmd.strip().lower()
        if cmd in ("/quit", "/exit"):
            console.print()
            console.print(Text("Exiting Echo...", style="bold cyan"))
            return True
        if cmd == "/clear":
            if self.chatbot:
                self.chatbot.clear_history()
            if self.session_manager:
                system_msg = [
                    m for m in self.session_manager.get_messages() if m.get("role") == "system"
                ]
                self.session_manager.set_messages(system_msg)
            print_chat_cleared()
        elif cmd == "/help":
            print_help()
        elif cmd == "/save":
            if self.session_manager:
                try:
                    self.session_manager.save_current_session()
                    print_session_saved(self.session_id)
                except Exception as e:
                    print_save_failed(str(e))
        elif cmd == "/sessions":
            self._show_sessions()
        elif cmd == "/resume":
            self._resume_session()
        elif cmd == "/tools":
            self._show_tools_status()
        elif cmd == "/settings":
            self._show_settings()
        else:
            print_unknown_command(cmd)
        return False

    def _show_help(self):
        """Show help information."""
        help_text = """
=== Echo AI Chatbot - Commands ===

Commands:
  /quit, /exit  - Exit the application
  /clear        - Clear current session chat
  /help         - Show this help
  /save         - Save current session to disk
  /sessions     - List all past chat sessions
  /resume       - Resume a past chat session (opens menu)
  /tools        - Show AI agent tools status
  /settings     - Open interactive settings menu

Voice Controls:
  Press CAPS LOCK to record, press again to stop and transcribe

AI Agent Tools:
  The AI can perform file operations, run code, and execute commands.
  All operations are confined to the launch directory.
  Examples: "list files", "read main.py", "create hello.txt with content 'Hello'"

Configuration:
  Use /settings for an interactive menu, or edit .env file directly.
  Edit .env to change model, voice, temperature, tools, etc.
"""
        print(help_text)

    def _show_sessions(self):
        """List all saved chat sessions."""
        if not self.session_manager:
            console.print(Text("[No session manager available]", style="dim"))
            return

        sessions = self.session_manager.list_sessions()
        if not sessions:
            console.print(Text("[No saved sessions found]", style="dim"))
            return

        console.print()
        table = Table(title="Saved Sessions", border_style="blue", header_style="bold cyan")
        table.add_column("#", style="dim", width=4)
        table.add_column("Timestamp", style="cyan")
        table.add_column("Messages", style="dim", width=10)
        table.add_column("Status", style="green")

        for i, session in enumerate(sessions, 1):
            marker = "[green]← Current[/]" if session.session_id == self.session_id else ""
            table.add_row(str(i), session.timestamp, str(session.message_count), marker)

        console.print(table)
        console.print(Text("Use /resume to load a past session", style="dim"))
        console.print()

    def _resume_session(self):
        """Resume a past chat session via menu."""
        if not self.session_manager:
            console.print(Text("[No session manager available]", style="dim"))
            return

        sessions = self.session_manager.list_sessions()
        # Filter out current session
        available = [s for s in sessions if s.session_id != self.session_id]
        if not available:
            console.print(Text("[No other sessions to resume]", style="dim"))
            return

        options = []
        for session in available:
            label = f"{session.timestamp} ({session.message_count} messages)"
            options.append(label)
        options.append("Cancel")

        try:
            selected = make_selection(options, "Select session to resume")
        except (KeyboardInterrupt, EOFError):
            return

        if selected == "Cancel":
            return

        # Find the matching session
        idx = options.index(selected)
        target_session = available[idx]

        # Load the session into both session_manager and chatbot
        loaded = self.session_manager.load_session(target_session.session_id)
        if loaded is None:
            console.print(Panel("Failed to load session", style="red", border_style="red"))
            return

        if self.chatbot:
            self.chatbot.messages = loaded.messages.copy()
        self.session_id = loaded.session_id
        console.print()
        console.print(Text(f"Resumed session: {self.session_id}", style="bold green"))
        console.print(Text(f"{loaded.message_count} previous messages loaded", style="dim green"))

    def _show_tools_status(self):
        """Show AI agent tools status."""
        if not self.toolkit or not self.settings.enable_tools:
            console.print()
            console.print(
                Panel(
                    "AI Tools: DISABLED\nSet ENABLE_TOOLS=true in .env to enable",
                    style="yellow",
                    border_style="yellow",
                    title="Tools",
                )
            )
            return

        tools_list = list(self.toolkit.tool_map.keys())
        console.print()
        table = Table(
            title=f"AI Tools ({len(tools_list)} available)",
            border_style="cyan",
            header_style="bold",
        )
        table.add_column("#", style="dim", width=4)
        table.add_column("Tool Name", style="cyan")
        table.add_column("Status", style="green", width=10)

        for i, tool in enumerate(tools_list, 1):
            table.add_row(str(i), tool, "[green]✓[/]")

        console.print(table)

        history = self.toolkit.get_tool_usage_history()
        if history:
            console.print()
            console.print(Text(f"Tool calls this session: {len(history)}", style="dim"))

    def _save_config(self):
        """Save current settings to data/config.json."""
        path = ConfigStore.save_config(self.settings)
        console.print(Text(f"Config saved to {path}", style="dim green"))

    def _apply_settings(self, load_model_settings: bool = False):
        """Save config.json, reload settings, and update the chatbot reference.

        Args:
            load_model_settings: If True, load model-specific settings (temperature,
                max_tokens, enable_tools) for the current model.
        """
        self._save_config()
        # Reload from config.json + .env
        self.settings = reload_settings()
        # Load model-specific settings if requested
        if load_model_settings:
            applied = switch_model_settings(self.settings)
            if applied:
                model_key = (
                    self.settings.openrouter_model
                    if self.settings.api_provider == "openrouter"
                    else self.settings.mistral_model
                )
                console.print()
                console.print(
                    Text(f"Loaded model-specific settings for: {model_key}", style="dim cyan")
                )
        # Update chatbot's settings reference if chatbot exists
        if self.chatbot:
            self.chatbot.settings = self.settings
            # Re-init API URL and model for the new provider
            if self.settings.api_provider == "openrouter":
                self.chatbot.api_url = "https://openrouter.ai/api/v1/chat/completions"
                self.chatbot.api_model = self.settings.openrouter_model
            elif self.settings.api_provider == "mistral":
                self.chatbot.api_url = "https://api.mistral.ai/v1/chat/completions"
                self.chatbot.api_model = self.settings.mistral_model
            self.chatbot.api_provider = self.settings.api_provider

    def _show_settings(self):
        """Interactive settings menu using make_selection. Auto-saves every change."""
        while True:
            model_key = (
                self.settings.openrouter_model
                if self.settings.api_provider == "openrouter"
                else self.settings.mistral_model
            )
            model = (
                self.settings.openrouter_model
                if self.settings.api_provider == "openrouter"
                else self.settings.mistral_model
            )

            console.print()
            console.print(
                Panel(
                    f"Provider: [{'bold blue' if self.settings.api_provider == 'openrouter' else 'bold magenta'}]{self.settings.api_provider.title()}[/]\n"
                    f"Model: [bold]{model}[/]\n"
                    f"Temperature: [yellow]{self.settings.temperature}[/] (for: [dim]{model_key}[/])\n"
                    f"Max Tokens: [yellow]{self.settings.max_tokens}[/] (for: [dim]{model_key}[/])\n"
                    f"Input Mode: [cyan]{self.settings.input_mode}[/]  |  Output: [cyan]{self.settings.output_mode}[/]\n"
                    f"TTS Voice: [dim]{self.settings.tts_voice}[/]\n"
                    f"Whisper Model: [dim]{self.settings.whisper_model}[/]\n"
                    f"AI Tools: [{'green' if self.settings.enable_tools else 'red'}]{'Enabled' if self.settings.enable_tools else 'Disabled'}[/] (for: [dim]{model_key}[/])"
                    + (
                        f"\nSystem Prompt: [dim]{self.settings.system_prompt[:60]}...[/]"
                        if self.settings.system_prompt
                        else ""
                    ),
                    title="[bold]Echo Settings[/]",
                    border_style="blue",
                    padding=(1, 2),
                )
            )

            options = [
                "API Provider",
                "Model",
                "Temperature",
                "Max Tokens",
                "Input Mode",
                "Output Mode",
                "TTS Voice",
                "Whisper Model",
                "AI Tools (Enable/Disable)",
                "System Prompt",
                "Back",
            ]

            try:
                selected = make_selection(options, "Select setting to change")
            except (KeyboardInterrupt, EOFError):
                return

            if selected == "Back":
                return
            if selected == "API Provider":
                all_options = ["openrouter", "mistral"]
                current = self.settings.api_provider
                choice_options = [current] + [o for o in all_options if o != current]
                try:
                    choice = make_selection(choice_options, "Select API provider")
                except (KeyboardInterrupt, EOFError):
                    continue
                object.__setattr__(self.settings, "api_provider", choice)
                self._apply_settings(load_model_settings=True)
                console.print(Text(f"✓ API provider saved: {choice}", style="dim green"))
            elif selected == "Model":
                if self.settings.api_provider == "openrouter":
                    all_models = [
                        "openai/gpt-oss-120b:free",
                        "google/gemma-3-27b-it:free",
                        "meta-llama/llama-3.3-70b-instruct:free",
                        "qwen/qwen3-coder:free",
                        "mistralai/mistral-small-3.1-24b-instruct:free",
                    ]
                    key = "openrouter_model"
                    current = self.settings.openrouter_model
                else:
                    all_models = [
                        "mistral-small-latest",
                        "mistral-medium-latest",
                        "mistral-large-latest",
                        "open-mistral-nemo",
                        "codestral-latest",
                    ]
                    key = "mistral_model"
                    current = self.settings.mistral_model
                choice_options = [current] + [m for m in all_models if m != current] + ["Custom..."]
                try:
                    choice = make_selection(choice_options, "Select model")
                except (KeyboardInterrupt, EOFError):
                    continue
                if choice == "Custom...":
                    print("Enter model name: ", end="", flush=True)
                    try:
                        choice = input().strip()
                    except (EOFError, KeyboardInterrupt):
                        continue
                    if not choice:
                        continue
                object.__setattr__(self.settings, key, choice)
                self._apply_settings(load_model_settings=True)
                console.print(Text(f"✓ Model saved: {choice}", style="dim green"))
            elif selected == "Temperature":
                all_temps = ["0.1", "0.3", "0.5", "0.7", "1.0", "1.5", "2.0"]
                current = str(self.settings.temperature)
                choice_options = [current] + [t for t in all_temps if t != current]
                try:
                    choice = make_selection(choice_options, "Select temperature")
                except (KeyboardInterrupt, EOFError):
                    continue
                object.__setattr__(self.settings, "temperature", float(choice))
                self._apply_settings()
                console.print(Text(f"✓ Temperature saved: {choice}", style="dim green"))
            elif selected == "Max Tokens":
                all_tokens = ["256", "512", "1024", "2048", "4096"]
                current = str(self.settings.max_tokens)
                choice_options = [current] + [t for t in all_tokens if t != current]
                try:
                    choice = make_selection(choice_options, "Select max tokens")
                except (KeyboardInterrupt, EOFError):
                    continue
                object.__setattr__(self.settings, "max_tokens", int(choice))
                self._apply_settings()
                console.print(Text(f"✓ Max tokens saved: {choice}", style="dim green"))
            elif selected == "Input Mode":
                all_modes = ["text", "speech", "both"]
                current = self.settings.input_mode
                choice_options = [current] + [m for m in all_modes if m != current]
                try:
                    choice = make_selection(choice_options, "Select input mode")
                except (KeyboardInterrupt, EOFError):
                    continue
                object.__setattr__(self.settings, "input_mode", choice)
                self._apply_settings()
                console.print(Text(f"✓ Input mode saved: {choice}", style="dim green"))
            elif selected == "Output Mode":
                all_modes = ["text", "speech", "both"]
                current = self.settings.output_mode
                choice_options = [current] + [m for m in all_modes if m != current]
                try:
                    choice = make_selection(choice_options, "Select output mode")
                except (KeyboardInterrupt, EOFError):
                    continue
                object.__setattr__(self.settings, "output_mode", choice)
                self._apply_settings()
                console.print(Text(f"✓ Output mode saved: {choice}", style="dim green"))
            elif selected == "TTS Voice":
                all_voices = [
                    "en-US-JennyNeural",
                    "en-US-GuyNeural",
                    "en-US-AriaNeural",
                    "en-GB-SoniaNeural",
                    "en-GB-RyanNeural",
                    "de-DE-KatjaNeural",
                    "fr-FR-DeniseNeural",
                    "es-ES-ElviraNeural",
                ]
                current = self.settings.tts_voice
                choice_options = [current] + [v for v in all_voices if v != current] + ["Custom..."]
                try:
                    choice = make_selection(choice_options, "Select TTS voice")
                except (KeyboardInterrupt, EOFError):
                    continue
                if choice == "Custom...":
                    print("Enter voice name: ", end="", flush=True)
                    try:
                        choice = input().strip()
                    except (EOFError, KeyboardInterrupt):
                        continue
                    if not choice:
                        continue
                object.__setattr__(self.settings, "tts_voice", choice)
                self._apply_settings()
                console.print(Text(f"✓ TTS voice saved: {choice}", style="dim green"))
            elif selected == "Whisper Model":
                all_whisper = [
                    "tiny",
                    "base",
                    "small",
                    "medium",
                    "large-v3",
                    "distil-small.en",
                    "distil-medium.en",
                    "distil-large-v3",
                ]
                current = self.settings.whisper_model
                choice_options = [current] + [w for w in all_whisper if w != current]
                try:
                    choice = make_selection(choice_options, "Select Whisper model")
                except (KeyboardInterrupt, EOFError):
                    continue
                object.__setattr__(self.settings, "whisper_model", choice)
                self._apply_settings()
                console.print(Text(f"✓ Whisper model saved: {choice}", style="dim green"))
            elif selected == "AI Tools (Enable/Disable)":
                current = "Enabled" if self.settings.enable_tools else "Disabled"
                choice_options = [current, "Disabled" if current == "Enabled" else "Enabled"]
                try:
                    choice = make_selection(choice_options, f"AI Tools (currently: {current})")
                except (KeyboardInterrupt, EOFError):
                    continue
                val = choice == "Enabled"
                object.__setattr__(self.settings, "enable_tools", val)
                self._apply_settings()
                console.print(
                    Text(f"✓ AI Tools: {'Enabled' if val else 'Disabled'}", style="dim green")
                )
            elif selected == "System Prompt":
                self._log(f"Current: {self.settings.system_prompt}")
                print(
                    "Enter new system prompt (or press Enter to keep current): ", end="", flush=True
                )
                try:
                    prompt = input().strip()
                except (EOFError, KeyboardInterrupt):
                    continue
                if prompt:
                    object.__setattr__(self.settings, "system_prompt", prompt)
                    self._apply_settings()
                    console.print(Text("✓ System prompt saved", style="dim green"))

    def _cleanup(self):
        """Clean up resources."""
        self.running = False
        if self.recording:
            self._stop_event.set()

        # Auto-save session and settings on exit
        if self.session_manager:
            try:
                self.session_manager.save_current_session()
            except Exception as e:
                logging.getLogger(__name__).error("Failed to save session: %s", e)
        ConfigStore.save_config(self.settings)

        for comp in [self.recorder, self.transcriber, self.tts]:
            if comp:
                comp.cleanup()
        cleanup_temp_files()
        print_goodbye()

    def run(self):
        """Main application loop - pure terminal I/O."""
        # Create per-session log file
        session_log = create_session_log()
        setup_logging(log_level="DEBUG", log_file=session_log, console_output=False)
        ensure_directories()
        cleanup_temp_files()

        # Validate API key based on selected provider
        if self.settings.api_provider == "openrouter":
            if (
                not self.settings.openrouter_api_key
                or self.settings.openrouter_api_key == "your_openrouter_api_key_here"
            ):
                print_api_key_not_configured("openrouter", "https://openrouter.ai/")
                sys.exit(1)
        elif self.settings.api_provider == "mistral":
            if (
                not self.settings.mistral_api_key
                or self.settings.mistral_api_key == "your_mistral_api_key_here"
            ):
                print_api_key_not_configured("mistral", "https://console.mistral.ai/")
                sys.exit(1)

        # Initialize components
        self._init_components()
        self.running = True

        # Print welcome banner with Rich
        print_banner(self.session_id, self.settings)

        # Start Caps Lock monitor if speech input enabled
        if self.settings.input_mode in ("speech", "both"):
            self._start_caps_lock_monitor()

        try:
            logger = logging.getLogger(__name__)
            logger.info("Entering main chat loop")
            while self.running:
                # Don't prompt if currently speaking, recording, or processing voice
                if self.speaking:
                    time.sleep(0.1)
                    continue

                if self.recording:
                    time.sleep(0.1)
                    continue

                if self._voice_processing:
                    time.sleep(0.1)
                    continue

                # Get user input - show "You: " BEFORE typing using readline
                try:
                    user_input = self._get_input_with_prompt().strip()
                    logger.debug("User input received: %s", repr(user_input[:100]))
                except EOFError:
                    logger.info("EOF received, exiting")
                    user_input = "/quit"
                except KeyboardInterrupt:
                    logger.info("Keyboard interrupt received")
                    console.print()
                    console.print(Text("[Interrupted]", style="dim yellow"))
                    break

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    logger.info("Command received: %s", user_input)
                    print_user_message(user_input)
                    if self._handle_command(user_input):
                        break
                else:
                    # Display user input AFTER submission
                    logger.info("Chat message received: %s", user_input[:100])
                    print_user_message(user_input)
                    # Process as chat input
                    self._process_text_input(user_input)

        except Exception as e:
            logger.error("Fatal error in main loop: %s", e, exc_info=True)
            console.print()
            console.print(
                Panel(f"Error: {e}", style="red", border_style="red", title="Fatal Error")
            )
        finally:
            self._cleanup()

    def _get_input_with_prompt(self) -> str:
        """Get user input with styled 'You: ' prefix that stays on the line."""
        try:
            __import__("readline")
            return console.input(Text("You: ", style="bold green"))
        except ImportError:
            # Fallback for systems without readline
            return input()


def main() -> None:
    """Run the Echo AI Chatbot application."""
    try:
        app = EchoConsoleApp()
        app.run()
    except KeyboardInterrupt:
        console.print()
        console.print(Text("Exiting...", style="dim cyan"))
    except Exception as e:
        console.print()
        console.print(Panel(f"Error: {e}", style="red", border_style="red", title="Fatal Error"))
        sys.exit(1)


if __name__ == "__main__":
    main()
