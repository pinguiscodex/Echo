"""
Echo AI Chatbot - CLI interface with voice support and AI agent tools.

Pure terminal chatbot with no TUI dependencies.
Tools use TEXT-BASED calling convention compatible with GPT-OSS-120B.
"""

import os
import sys
import tempfile
import threading
import time

# Suppress warnings
import warnings
from pathlib import Path
from typing import Optional

warnings.filterwarnings("ignore")

# Suppress telemetry
os.environ["HF_HUB_DISABLE_TELEMETRY"] = "1"
os.environ["HF_HUB_DISABLE_PROGRESS_BARS"] = "0"

try:
    from pythonclimenu import menu as cli_menu

    from echo.config import ConfigStore, get_settings, reload_settings
    from echo.core.agent import AgentOrchestrator
    from echo.core.chatbot import ChatResponse, EchoChatbot
    from echo.core.recorder import AudioRecorder
    from echo.core.transcriber import WhisperTranscriber
    from echo.core.tts import TTSEngine
    from echo.tools import AIToolkit
    from echo.utils.helpers import cleanup_temp_files, ensure_directories
    from echo.utils.logging import setup_logging

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
        self._recording_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._audio_path: Optional[Path] = None
        self._voice_processing = False  # Blocks prompt while transcribing/AI responds

        self.chatbot: Optional[EchoChatbot] = None
        self.recorder: Optional[AudioRecorder] = None
        self.transcriber: Optional[WhisperTranscriber] = None
        self.tts: Optional[TTSEngine] = None
        self.toolkit: Optional[AIToolkit] = None
        self.agent_orchestrator: Optional[AgentOrchestrator] = None

    def _log(self, message: str):
        """Log message to console."""
        print(f"\n{message}", flush=True)

    def _log_override(self, message: str):
        """Log message, clearing the current input line first.

        Used when recording starts/stops while user is at the prompt.
        """
        # Clear current line and move cursor to beginning
        print("\r\033[K", end="", flush=True)
        print(f"[{message}]", flush=True)

    def _reprompt(self):
        """Re-show the input prompt after recording finishes."""
        print("You: ", end="", flush=True)

    def _init_components(self):
        """Initialize all core components."""
        # Apply config.json if it exists (overrides .env defaults)
        config_data = ConfigStore.load_config()
        if config_data:
            ConfigStore.apply_config(self.settings, config_data)
            ConfigStore.sync_to_env(self.settings)
            self._log("[Loaded config from data/config.json]")

        # Initialize toolkit if enabled
        toolkit = None
        if self.settings.enable_tools:
            toolkit = AIToolkit()
            self.toolkit = toolkit
            self.agent_orchestrator = AgentOrchestrator(toolkit=toolkit)
            self._log(f"[AI Toolkit enabled with {len(toolkit.tool_map)} tools]")

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

        # Load chat history if exists
        history_path = Path("data/chat_history.json")
        if history_path.exists() and self.chatbot:
            try:
                self.chatbot.load_history(history_path)
                history = self.chatbot.get_history()
                msg_count = len([m for m in history if m["role"] in ("user", "assistant")])
                if msg_count > 0:
                    self._log(f"[Loaded {msg_count} previous messages]")
            except Exception:
                pass

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
        self._log_override("Recording... press CAPS LOCK again to stop")

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
        if not self.recording:
            return
        self._log_override("Processing voice input...")
        self._stop_event.set()
        if self._recording_thread and self._recording_thread.is_alive():
            self._recording_thread.join(timeout=5.0)

        audio_path = self._audio_path
        self._audio_path = None
        self._recording_thread = None

        # Clear recording state
        self.recording = False

        if audio_path and audio_path.exists():
            # Transcribe first, then block prompt only if there's speech
            try:
                text = self.transcriber.transcribe(audio_path) if self.transcriber else ""
            except Exception as e:
                self._log_override(f"Transcription failed: {e}")
                self._reprompt()
                if audio_path.exists():
                    audio_path.unlink(missing_ok=True)
                return

            if audio_path.exists():
                audio_path.unlink(missing_ok=True)

            if not text or not text.strip():
                self._log_override("No speech detected")
                self._reprompt()
                return

            # We have speech — block prompt until AI responds
            self._voice_processing = True
            self._log(f"You: {text}")
            self._handle_chat(text)
            self._voice_processing = False
            self._reprompt()
        else:
            self._log_override("No audio recorded")
            self._reprompt()

    def _process_text_input(self, text: str):
        """Process text input."""
        if not all([self.chatbot, self.tts]):
            return
        self._handle_chat(text)

    def _handle_chat(self, user_text: str, max_retries: int = 2):
        """Handle chat request with streaming and tool execution."""
        self._log("[AI thinking...]")

        try:
            full_response = ""
            chat_response = None

            # Stream the response
            for chunk in self.chatbot.chat(user_text):
                full_response += chunk
                # Print streaming output
                print(chunk, end="", flush=True)

            print()  # Newline after response

            # Extract ChatResponse from the last assistant message
            if self.chatbot.messages and self.chatbot.messages[-1].get("role") == "assistant":
                last_msg = self.chatbot.messages[-1]
                if "tool_calls" in last_msg:
                    chat_response = ChatResponse(
                        content=full_response, tool_calls=last_msg["tool_calls"]
                    )
                else:
                    chat_response = ChatResponse(content=full_response)
            else:
                chat_response = ChatResponse(content=full_response)

            # Handle empty responses with retry
            if not full_response.strip():
                if max_retries > 0:
                    self._log("[AI returned empty response, retrying...]")
                    self.chatbot.messages.pop()  # Remove empty assistant message
                    self._handle_chat(
                        f"(Please respond to my previous message. You returned an empty response.)",
                        max_retries - 1,
                    )
                    return
                else:
                    self._log("[AI returned empty response after retries]")
                    return

            # Handle native OpenRouter tool_calls
            if (
                self.agent_orchestrator
                and self.settings.enable_tools
                and chat_response.has_tool_calls()
            ):
                self._log("\n[Executing tools...]")
                tool_results = self.agent_orchestrator.process_tool_calls(chat_response.tool_calls)

                # Display tool results
                for result in tool_results:
                    content = result.get("content", "")
                    if len(content) > 300:
                        content = content[:300] + "..."
                    status = "[OK]" if not content.startswith("Error:") else "[FAIL]"
                    self._log(f"{status} Tool result: {content}")

                # Send tool results back to AI for follow-up
                self._log("[AI processing tool result...]")
                follow_up = ""
                tool_result_text = "\n".join([r.get("content", "") for r in tool_results])
                for chunk in self.chatbot.chat(
                    f"Tool execution result:\n{tool_result_text}\n\nPlease summarize what was done and continue helping."
                ):
                    follow_up += chunk
                    print(chunk, end="", flush=True)
                print()  # Newline
                full_response = follow_up

            # Also check for text-based tool calls (fallback)
            elif self.toolkit and self.settings.enable_tools and "[TOOL:" in full_response:
                tool_output = self._execute_text_tools(full_response)
                if tool_output:
                    self._log(f"\n{tool_output}")
                    # Send tool result back to AI for follow-up
                    self._log("[AI processing tool result...]")
                    follow_up = ""
                    for chunk in self.chatbot.chat(
                        f"Tool execution result:\n{tool_output}\n\nPlease summarize what was done and continue helping."
                    ):
                        follow_up += chunk
                        print(chunk, end="", flush=True)
                    print()  # Newline
                    full_response = follow_up

            # TTS if enabled
            if self.settings.output_mode in ("speech", "both") and full_response.strip():
                self.speaking = True
                self._log("[Speaking...]")
                tts_thread = threading.Thread(
                    target=self._run_tts, args=(full_response,), daemon=True
                )
                tts_thread.start()
                tts_thread.join()
        except Exception as e:
            self._log(f"[Chat failed: {e}]")

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
                            content += f"... (truncated)"
                        results.append(f"[OK] {tool_name}: {content}")
                    else:
                        results.append(f"[FAIL] {tool_name}: {result.error}")
                except Exception as e:
                    results.append(f"[FAIL] {tool_name}: Execution error - {e}")
            else:
                results.append(f"[FAIL] {tool_name}: Unknown tool")

        return "\n".join(results) if results else ""

    def _run_tts(self, text: str):
        """Run TTS playback."""
        try:
            self.tts.speak(text)
        except Exception as e:
            self._log(f"[TTS playback error: {e}]")
        finally:
            # Always reset speaking state when TTS completes
            self.speaking = False

    def _handle_command(self, cmd: str) -> bool:
        """Handle slash commands. Returns True to exit."""
        cmd = cmd.strip().lower()
        if cmd in ("/quit", "/exit"):
            self._log("Exiting Echo...")
            return True
        elif cmd == "/clear":
            if self.chatbot:
                self.chatbot.clear_history()
                self._log("[Chat cleared]")
        elif cmd == "/help":
            self._show_help()
        elif cmd == "/save":
            if self.chatbot:
                try:
                    self.chatbot.save_history()
                    self._log("[Chat saved]")
                except Exception as e:
                    self._log(f"[Save failed: {e}]")
        elif cmd == "/load":
            if self.chatbot:
                try:
                    self.chatbot.load_history()
                    self._log("[Chat loaded]")
                except Exception as e:
                    self._log(f"[Load failed: {e}]")
        elif cmd == "/tools":
            self._show_tools_status()
        elif cmd == "/settings":
            self._show_settings()
        else:
            self._log(f"[Unknown command: {cmd}]")
        return False

    def _show_help(self):
        """Show help information."""
        help_text = """
=== Echo AI Chatbot - Commands ===

Commands:
  /quit, /exit  - Exit the application
  /clear        - Clear chat history
  /help         - Show this help
  /save         - Save chat history to disk
  /load         - Load chat history from disk
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

    def _show_tools_status(self):
        """Show AI agent tools status."""
        if not self.toolkit or not self.settings.enable_tools:
            self._log("[AI Tools: DISABLED - Set ENABLE_TOOLS=true in .env to enable]")
            return

        tools_list = list(self.toolkit.tool_map.keys())
        self._log(f"AI Tools: ENABLED ({len(tools_list)} tools available)")
        self._log(f"Base directory: {self.toolkit.agent.base_dir}")
        self._log("Available tools:")
        for tool in tools_list:
            self._log(f"  - {tool}")

        history = self.toolkit.get_tool_usage_history()
        if history:
            self._log(f"Tool calls this session: {len(history)}")

    def _save_config(self):
        """Save current settings to data/config.json."""
        path = ConfigStore.save_config(self.settings)
        self._log(f"[Config saved to {path}]")

    def _apply_settings(self):
        """Save config.json, reload settings, and update the chatbot reference."""
        self._save_config()
        # Reload from config.json + .env
        self.settings = reload_settings()
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
            print("\n" + "=" * 50)
            print("  Echo Settings")
            print("=" * 50)
            print(f"  API Provider : {self.settings.api_provider}")
            if self.settings.api_provider == "openrouter":
                print(f"  Model        : {self.settings.openrouter_model}")
            else:
                print(f"  Model        : {self.settings.mistral_model}")
            print(f"  Temperature  : {self.settings.temperature}")
            print(f"  Max Tokens   : {self.settings.max_tokens}")
            print(f"  Input Mode   : {self.settings.input_mode}")
            print(f"  Output Mode  : {self.settings.output_mode}")
            print(f"  TTS Voice    : {self.settings.tts_voice}")
            print(f"  Whisper Model: {self.settings.whisper_model}")
            print(f"  AI Tools     : {'Enabled' if self.settings.enable_tools else 'Disabled'}")
            if self.settings.system_prompt:
                prompt_preview = (
                    self.settings.system_prompt[:60] + "..."
                    if len(self.settings.system_prompt) > 60
                    else self.settings.system_prompt
                )
                print(f"  System Prompt: {prompt_preview}")
            print("=" * 50)

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
            elif selected == "API Provider":
                all_options = ["openrouter", "mistral"]
                current = self.settings.api_provider
                choice_options = [current] + [o for o in all_options if o != current]
                try:
                    choice = make_selection(choice_options, "Select API provider")
                except (KeyboardInterrupt, EOFError):
                    continue
                object.__setattr__(self.settings, "api_provider", choice)
                self._apply_settings()
                self._log(f"[API provider saved: {choice}]")
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
                self._apply_settings()
                self._log(f"[Model saved: {choice}]")
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
                self._log(f"[Temperature saved: {choice}]")
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
                self._log(f"[Max tokens saved: {choice}]")
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
                self._log(f"[Input mode saved: {choice}]")
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
                self._log(f"[Output mode saved: {choice}]")
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
                self._log(f"[TTS voice saved: {choice}]")
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
                self._log(f"[Whisper model saved: {choice}]")
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
                self._log(f"[AI Tools: {'Enabled' if val else 'Disabled'}]")
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
                    self._log("[System prompt saved]")

    def _cleanup(self):
        """Clean up resources."""
        self.running = False
        if self.recording:
            self._stop_event.set()
        if self.chatbot:
            try:
                self.chatbot.save_history()
            except Exception:
                pass
        for comp in [self.recorder, self.transcriber, self.tts]:
            if comp:
                comp.cleanup()
        cleanup_temp_files()
        self._log("Goodbye!")

    def run(self):
        """Main application loop - pure terminal I/O."""
        setup_logging(log_level="INFO", console_output=False)
        ensure_directories()
        cleanup_temp_files()

        # Validate API key based on selected provider
        if self.settings.api_provider == "openrouter":
            if (
                not self.settings.openrouter_api_key
                or self.settings.openrouter_api_key == "your_openrouter_api_key_here"
            ):
                print("ERROR: OPENROUTER_API_KEY not configured!")
                print("Add your API key to the .env file")
                print("Get your key from: https://openrouter.ai/")
                sys.exit(1)
        elif self.settings.api_provider == "mistral":
            if (
                not self.settings.mistral_api_key
                or self.settings.mistral_api_key == "your_mistral_api_key_here"
            ):
                print("ERROR: MISTRAL_API_KEY not configured!")
                print("Add your API key to the .env file")
                print("Get your key from: https://console.mistral.ai/")
                sys.exit(1)

        # Initialize components
        self._init_components()
        self.running = True

        # Print welcome message
        print("\n" + "=" * 60)
        print("  Echo AI Chatbot - Pure Terminal Mode")
        print("=" * 60)
        if self.settings.api_provider == "openrouter":
            print(f"  Provider: OpenRouter")
            print(f"  Model: {self.settings.openrouter_model}")
        elif self.settings.api_provider == "mistral":
            print(f"  Provider: Mistral")
            print(f"  Model: {self.settings.mistral_model}")
        print(f"  Input: {self.settings.input_mode} | Output: {self.settings.output_mode}")
        print(f"  Temperature: {self.settings.temperature}")
        if self.settings.enable_tools:
            print(
                f"  AI Tools: Enabled ({len(self.toolkit.tool_map) if self.toolkit else 0} tools)"
            )
        print("=" * 60)

        if self.settings.input_mode in ("speech", "both"):
            print("\nVoice: Press CAPS LOCK to record, press again to stop")
            print("Text:  Type your message and press ENTER")
        else:
            print("\nType your message and press ENTER")

        print("Type /help for commands, /quit to exit")
        print("-" * 60)

        # Start Caps Lock monitor if speech input enabled
        if self.settings.input_mode in ("speech", "both"):
            self._start_caps_lock_monitor()

        try:
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
                except EOFError:
                    user_input = "/quit"
                except KeyboardInterrupt:
                    self._log("\n[Interrupted]")
                    break

                if not user_input:
                    continue

                # Handle commands
                if user_input.startswith("/"):
                    self._log(f"You: {user_input}")
                    if self._handle_command(user_input):
                        break
                else:
                    # Display user input AFTER submission
                    self._log(f"You: {user_input}")
                    # Process as chat input
                    self._process_text_input(user_input)

        except Exception as e:
            self._log(f"\n[Error: {e}]")
        finally:
            self._cleanup()

    def _get_input_with_prompt(self) -> str:
        """Get user input with 'You: ' prefix that stays on the line."""
        try:
            __import__("readline")
            return input("You: ")
        except ImportError:
            # Fallback for systems without readline
            return input()


def main() -> None:
    """Run the Echo AI Chatbot application."""
    try:
        app = EchoConsoleApp()
        app.run()
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"\nError: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
