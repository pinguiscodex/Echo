# Echo AI Chatbot — Project Context

## Project Overview

**Echo** is a production-ready, voice-enabled CLI chatbot built in Python with a `src/` layout. It provides speech-to-text and text-to-speech capabilities alongside traditional text chat, powered by the OpenRouter or Mistral API for AI responses.

### Core Capabilities
- **Voice Input** — Press Caps Lock to toggle recording, auto-transcribed using faster-whisper (CTranslate2 backend)
- **Voice Output** — AI responses spoken aloud using edge-tts (free Microsoft Neural voices)
- **Text Input/Output** — Traditional text chat as fallback or primary mode
- **Streaming Responses** — Real-time token streaming from OpenRouter/Mistral API
- **AI Agent Tools** — File operations, code execution, shell commands, and internet research (Wikipedia, DuckDuckGo)
- **Configurable Settings** — Temperature, models, voices, input/output modes via `.env` or interactive `/settings` menu
- **Chat History** — Persistent conversations saved to `data/chat_history.json`

### Architecture Flow
```
User Speech → AudioRecorder → WhisperTranscriber (faster-whisper) → EchoChatbot (OpenRouter/Mistral)
                                                              ↓
User Audio ← TTSEngine (edge-tts) ← Response Text ← Streaming Response ←
```

## Key Technologies

| Category | Technology |
|----------|-----------|
| Language | Python 3.11+ |
| Build System | hatchling (PEP 621 via `pyproject.toml`) |
| Configuration | Pydantic + pydantic-settings + python-dotenv |
| AI API | OpenRouter or Mistral (HTTP requests, streaming) |
| Speech-to-Text | faster-whisper (CTranslate2, CPU-only, int8) |
| Text-to-Speech | edge-tts (free Microsoft Neural voices) |
| Audio I/O | sounddevice, soundfile, numpy |
| Keyboard Input | Python stdlib (termios/tty/select on Unix, msvcrt on Windows) |
| Testing | pytest + pytest-cov + factory-boy + Faker |
| Linting | flake8 + plugins (bugbear, comprehensions, docstrings, pep8-naming) |
| Formatting | black + isort |
| Type Checking | mypy (pragmatic mode) |
| Security | bandit + safety |
| Pre-commit | pre-commit framework |

## Project Structure

```
Echo/
├── pyproject.toml              # PEP 621: build, deps, tool configs
├── README.md                   # User-facing documentation
├── CHANGELOG.md               # Semantic versioning changelog
├── .env.example               # Template for environment variables
├── .gitignore                 # Git ignore rules
├── .flake8                    # Flake8 linter configuration
├── .pre-commit-config.yaml    # Pre-commit hooks
├── .python-version            # Python version pin (3.11+)
├── Makefile                   # Common dev commands
├── QWEN.md                    # This file — developer context
│
├── src/
│   └── echo/
│       ├── __init__.py        # Package version, lazy exports
│       ├── __main__.py        # Entry point for `python -m echo`
│       ├── cli.py             # CLI interface, EchoConsoleApp, main()
│       ├── config.py          # Pydantic settings, ConfigStore, loaded from .env
│       ├── types.py           # Shared TypedDicts, type aliases
│       │
│       ├── core/
│       │   ├── chatbot.py     # OpenRouter/Mistral API, streaming, conversation history
│       │   ├── agent.py       # Tool calling orchestration, result formatting
│       │   ├── recorder.py    # Microphone recording via sounddevice, VAD-based
│       │   ├── transcriber.py # faster-whisper STT, lazy model loading, VAD filtering
│       │   └── tts.py         # edge-tts TTS, async generation, sounddevice playback
│       │
│       ├── tools/
│       │   ├── base.py        # ToolResult dataclass, DirectoryConfinedTools
│       │   ├── filesystem.py  # File operations (list, read, write, edit, delete, search)
│       │   ├── command.py     # Shell command execution (subprocess)
│       │   ├── code.py        # Python code execution + validation
│       │   ├── system.py      # System info, directory structure
│       │   └── research.py    # Wikipedia, DuckDuckGo, smart research, fact-check
│       │
│       ├── services/
│       │   └── history.py     # ChatHistoryService — JSON persistence
│       │
│       └── utils/
│           ├── logging.py     # Centralized logging configuration
│           ├── helpers.py     # Pure utility functions (chat history I/O, cleanup)
│           └── validators.py  # Input validation, type guards
│
├── tests/
│   ├── conftest.py            # Pytest fixtures, mocks, Faker, factory factories
│   ├── factories.py           # factory-boy factories (Message, Conversation, ToolCall, etc.)
│   ├── test_config.py         # ConfigStore, Settings tests
│   ├── test_chatbot.py        # ChatResponse, EchoChatbot tests
│   ├── test_agent.py          # AgentOrchestrator tests
│   ├── test_tools.py          # Tool execution tests (filesystem, command, code, system, toolkit)
│   ├── test_validators.py     # Validator tests (parametrized)
│   ├── test_utils.py          # Utility function tests (logging, helpers, history)
│   ├── test_services.py       # ChatHistoryService tests
│   └── integration/
│       └── test_voice_pipeline.py  # Integration tests for voice pipeline
│
├── stubs/                     # Custom type stubs for untyped third-party libs
│   └── edge_tts.pyi
│
├── data/                      # Runtime data (gitignored)
│   ├── chat_history.json
│   └── config.json
│
└── logs/                      # Log files (gitignored)
    └── echo.log
```

## Building and Running

### Prerequisites
- Python 3.11+
- OpenRouter or Mistral API key
- Microphone (for voice input)
- Speakers/headphones (for voice output)
- Audio system dependencies:
  - Linux: `sudo apt-get install portaudio19-dev python3-dev`
  - macOS: `brew install portaudio`
  - Windows: Usually works out of the box

**No admin/root permissions required for keyboard input!** Uses only Python standard library modules.

### Setup
```bash
# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install package (editable)
pip install -e .

# Or with dev dependencies
pip install -e ".[dev]"

# Configure environment
cp .env.example .env
# Edit .env and add your OPENROUTER_API_KEY
```

### Running
```bash
# Via installed command
echo

# Via module
python -m echo
```

### Viewing Logs
```bash
tail -f logs/echo.log
```

### Available Commands (in-app)
| Command | Description |
|---------|-------------|
| `/quit` or `/exit` | Exit the application |
| `/clear` | Clear chat history |
| `/help` | Show available commands |
| `/save` | Save chat history to disk |
| `/load` | Load chat history from disk |
| `/tools` | Show AI agent tools status |
| `/settings` | Open interactive settings menu |

## Configuration (.env)

All settings are configurable via `.env`. Key settings:

| Setting | Default | Description |
|---------|---------|-------------|
| `API_PROVIDER` | `openrouter` | API provider: `openrouter` or `mistral` |
| `OPENROUTER_API_KEY` | *(required)* | Your OpenRouter API key |
| `OPENROUTER_MODEL` | `openai/gpt-oss-120b:free` | AI model to use |
| `MISTRAL_API_KEY` | *(required for mistral)* | Your Mistral API key |
| `MISTRAL_MODEL` | `mistral-small-latest` | Mistral model to use |
| `WHISPER_MODEL` | `base` | STT model size (tiny → large-v3, or distil-* variants) |
| `TTS_VOICE` | `en-US-JennyNeural` | edge-tts voice identifier |
| `TEMPERATURE` | `0.7` | AI response creativity (0.0–2.0) |
| `MAX_TOKENS` | `1024` | Max response length (64–4096) |
| `INPUT_MODE` | `both` | Input method: text, speech, or both |
| `OUTPUT_MODE` | `both` | Output method: text, speech, or both |
| `SAMPLE_RATE` | `16000` | Audio sample rate in Hz |
| `ENABLE_TOOLS` | `true` | Enable AI agent tool calling |

**Voice Recording**: Press **Caps Lock** to start recording. Press again to stop and transcribe.

## Development Conventions

### Code Style
- **Type hints** — All functions use type hints (from `typing` module)
- **Docstrings** — Google-style docstrings with Args/Returns/Raises sections
- **Logging** — Use module-level `logger = logging.getLogger(__name__)` for per-module logging
- **Error handling** — Comprehensive try/except with logging at appropriate levels
- **Path handling** — Use `pathlib.Path` instead of `os.path` strings

### Formatting & Linting
- **Black** — Code formatter (100 char line length)
- **isort** — Import sorter (black profile)
- **flake8** — Linter with plugins (bugbear, comprehensions, docstrings, pep8-naming)
- **mypy** — Type checker (pragmatic mode — not strict)

### Testing
- **pytest** — Test framework with `-v --tb=short` defaults
- **pytest-cov** — Coverage reporting (50% minimum threshold, excluding audio/network modules)
- **factory-boy** — Test fixture generation
- **Faker** — Fake data generation
- **Fixtures** — Defined in `tests/conftest.py`
- **Factories** — Defined in `tests/factories.py`

### Settings Pattern
- Settings are defined as Pydantic `BaseSettings` with `Field()` validators
- Singleton via `@lru_cache()` on `get_settings()`
- `ConfigStore` class saves/loads user preferences to `data/config.json`
- Reload via `reload_settings()` which clears the cache

### Async/Await
- Main entry point uses `EchoConsoleApp.run()` (synchronous with background threads)
- TTS uses async edge-tts but bridges with `asyncio.run()` for sync contexts
- Main loop is synchronous (`app.run()`) with background threads for recording/TTS

### Console Output
- Simple `print()` statements with clear formatting
- State indicators via text (`[Recording...]`, `[AI thinking...]`, `[Speaking...]`)
- No TUI framework — works in any terminal

### Component Design
- Each core module is a self-contained class (e.g., `AudioRecorder`, `WhisperTranscriber`)
- Lazy loading where applicable (e.g., Whisper model loaded on first transcription)
- `cleanup()` method on each component for resource management
- Components instantiated in `EchoConsoleApp._init_components()`
- Tools split into dedicated modules (`tools/filesystem.py`, `tools/command.py`, etc.)

### TTS Speaking State
- TTS runs in a dedicated background thread
- `self.speaking` flag tracks playback state
- Main loop blocks during speech to prevent overlapping input
- Speaking flag is always reset in `finally` block, even on errors

### Logging
- Log file: `logs/echo.log`
- Noisy third-party loggers suppressed (`requests`, `urllib3`, `httpx`)
- Log levels: DEBUG for detailed operations, INFO for normal flow, ERROR for failures
- Console output disabled during initialization (`console_output=False`)

## Development Workflow

```bash
# Install dev dependencies
make dev

# Run tests
make test

# Run tests with coverage
make test-cov

# Run linters
make lint

# Format code
make format

# Run type checker
make type-check

# Run security scan
make security

# Run full CI pipeline
make ci

# Install pre-commit hooks
make pre-commit

# Watch for file changes and auto-test
make watch
```

## Pre-commit Hooks

The following hooks run automatically on each commit:
1. **pre-commit-hooks** -- Trailing whitespace, EOF fixer, YAML/TOML/JSON validation, large files, merge conflicts, debug statements, private keys
2. **bandit** -- Security linting
3. **black** -- Code formatting
4. **isort** -- Import sorting
5. **flake8** -- Linting with plugins

Note: mypy and safety are available via make type-check and make deps-check but excluded from pre-commit due to missing type stubs and build tool incompatibilities.

## Important Notes

- **Cross-platform keyboard input** — Uses Python stdlib only (termios/tty/select on Unix, msvcrt on Windows). No admin/root permissions required.
- **No GPU/CUDA dependencies** — faster-whisper runs on CPU with int8 quantization by default.
- **edge-tts is async-only** — The TTS wrapper uses `asyncio.run()` to bridge sync/async contexts.
- **Chat history** — Saved as JSON to `data/chat_history.json`, auto-loaded on startup.
- **Temp file cleanup** — Recording temp files (`rec_*.wav`) are cleaned up on startup and shutdown.
- **No TUI framework** — Simple terminal output, works everywhere.
- **src/ layout** — Package is importable as `echo` after `pip install -e .`
- **Lazy `__init__.py`** — Uses `__getattr__` to avoid circular imports
