# 🤖 Echo AI Chatbot

A production-ready, voice-enabled CLI chatbot with speech-to-text and text-to-speech capabilities.

## Features

✅ **Voice Input** — Hold Caps Lock to record your voice, automatically transcribed using faster-whisper
✅ **Voice Output** — AI responses spoken aloud using edge-tts
✅ **Text Input/Output** — Traditional text chat as fallback or primary mode
✅ **Streaming Responses** — Real-time token streaming from OpenRouter API
✅ **AI Agent Tools** — File operations, code execution, and web research capabilities
✅ **Configurable Settings** — Temperature, models, voices, input/output modes
✅ **Chat History** — Persistent conversations saved to disk
✅ **Production Ready** — `src/` layout, type hints, comprehensive test suite (110+ tests)

## Quick Start

### Prerequisites

- Python 3.11+
- OpenRouter or Mistral API key
- Microphone for voice input (optional)
- Speakers/headphones for voice output (optional)

**No admin/root permissions required!** Uses only Python standard library modules for keyboard input.

### Installation

1. **Clone and navigate to the project:**
   ```bash
   cd /path/to/Echo
   ```

2. **Create and activate a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # Linux/macOS
   ```

3. **Install the package (editable mode):**
   ```bash
   pip install -e .
   ```

   Or with development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

4. **Configure environment:**
   ```bash
   cp .env.example .env
   ```

   Edit `.env` and add your API key:
   ```env
   OPENROUTER_API_KEY=your_openrouter_api_key_here
   ```

5. **Run the application:**
   ```bash
   # Using the installed command
   echo

   # Or as a module
   python -m echo
   ```

## Usage

### Voice Mode
- Hold **Caps Lock** to start recording
- Speak your message
- Release **Caps Lock** to stop recording
- Your voice is transcribed and sent to the AI
- AI response is spoken aloud (if output mode is speech/both)

### Text Mode
- Type your message and press **Enter**
- AI response appears in the terminal
- Response is also spoken aloud (if output mode is speech/both)

### Commands

| Command | Description |
|---------|-------------|
| `/quit` or `/exit` | Exit the application |
| `/clear` | Clear chat history |
| `/help` | Show available commands |
| `/save` | Save chat history to disk |
| `/load` | Load chat history from disk |
| `/tools` | Show AI agent tools status |
| `/settings` | Open interactive settings menu |

### Configuration

All settings are configurable via the `.env` file:

| Setting | Default | Options | Description |
|---------|---------|---------|-------------|
| `API_PROVIDER` | `openrouter` | `openrouter`, `mistral` | API provider to use |
| `OPENROUTER_API_KEY` | *(required)* | - | Your OpenRouter API key |
| `OPENROUTER_MODEL` | `openai/gpt-oss-120b:free` | Any OpenRouter model | AI model to use |
| `MISTRAL_API_KEY` | *(required for mistral)* | - | Your Mistral API key |
| `MISTRAL_MODEL` | `mistral-small-latest` | Any Mistral model | Mistral model to use |
| `WHISPER_MODEL` | `base` | `tiny`, `base`, `small`, `medium`, `large-v3`, etc. | Speech-to-text model |
| `TTS_VOICE` | `en-US-JennyNeural` | Any edge-tts voice | Voice for text-to-speech |
| `TEMPERATURE` | `0.7` | `0.0` - `2.0` | AI response creativity |
| `MAX_TOKENS` | `1024` | `64` - `4096` | Max response length |
| `INPUT_MODE` | `both` | `text`, `speech`, `both` | Input method |
| `OUTPUT_MODE` | `both` | `text`, `speech`, `both` | Output method |
| `SAMPLE_RATE` | `16000` | - | Audio sample rate (Hz) |
| `ENABLE_TOOLS` | `true` | `true`, `false` | Enable AI agent tools |

## Project Structure

```
Echo/
├── pyproject.toml              # PEP 621 build config, dependencies, tool configs
├── README.md                   # This file
├── CHANGELOG.md               # Semantic versioning changelog
├── .env.example               # Environment config template
├── .gitignore                 # Git ignore rules
├── .flake8                    # Flake8 linter configuration
├── .pre-commit-config.yaml    # Pre-commit hooks (black, isort, flake8, mypy, bandit)
├── .python-version            # Python version pin (3.11+)
├── Makefile                   # Common dev commands
│
├── src/
│   └── echo/
│       ├── __init__.py        # Package version and lazy exports
│       ├── __main__.py        # Entry point for `python -m echo`
│       ├── cli.py             # CLI interface and EchoConsoleApp
│       ├── config.py          # Pydantic settings, loaded from .env
│       ├── types.py           # Shared type aliases, TypedDicts
│       │
│       ├── core/
│       │   ├── chatbot.py     # OpenRouter/Mistral API integration
│       │   ├── agent.py       # Tool calling orchestration
│       │   ├── recorder.py    # Microphone recording, VAD
│       │   ├── transcriber.py # faster-whisper STT
│       │   └── tts.py         # edge-tts TTS
│       │
│       ├── tools/
│       │   ├── base.py        # ToolResult, directory confinement
│       │   ├── filesystem.py  # File operations (read, write, edit, etc.)
│       │   ├── command.py     # Shell command execution
│       │   ├── code.py        # Python code execution
│       │   ├── system.py      # System information tools
│       │   ├── research.py    # Wikipedia & DuckDuckGo search
│       │   └── _toolkit.py    # AIToolkit aggregator
│       │
│       ├── services/
│       │   └── history.py     # Chat history persistence service
│       │
│       └── utils/
│           ├── logging.py     # Centralized logging configuration
│           ├── helpers.py     # Utility functions
│           └── validators.py  # Input validation
│
├── tests/
│   ├── conftest.py            # Pytest fixtures, Faker, factory-boy
│   ├── factories.py           # Test factories (Message, Conversation, ToolCall, etc.)
│   ├── test_config.py         # Configuration tests
│   ├── test_chatbot.py        # Chatbot tests
│   ├── test_agent.py          # Agent orchestration tests
│   ├── test_tools.py          # Tool execution tests
│   ├── test_validators.py     # Validator tests
│   ├── test_utils.py          # Utility function tests
│   ├── test_services.py       # Service layer tests
│   └── integration/
│       └── test_voice_pipeline.py  # Integration tests
│
├── stubs/
│   └── edge_tts.pyi           # Type stubs for edge-tts
│
├── data/                      # Runtime data (gitignored)
│   ├── chat_history.json
│   └── config.json
│
└── logs/                      # Log files (gitignored)
    └── echo.log
```

## Architecture

```
User Speech → AudioRecorder → WhisperTranscriber → EchoChatbot (OpenRouter/Mistral)
                                                              ↓
User Audio ← TTSEngine ← Response Text ← Streaming Response ←
```

### Component Overview

| Module | Description |
|--------|-------------|
| `echo.config` | Pydantic settings loaded from `.env` with validation |
| `echo.core.chatbot` | OpenRouter/Mistral API integration with streaming |
| `echo.core.agent` | Tool calling orchestration and result formatting |
| `echo.core.recorder` | Microphone recording with VAD-based speech detection |
| `echo.core.transcriber` | faster-whisper STT with CTranslate2 backend |
| `echo.core.tts` | edge-tts integration for high-quality TTS |
| `echo.tools.*` | AI agent tools: file ops, code exec, web research |
| `echo.services.history` | Chat history persistence (JSON) |
| `echo.utils.logging` | Centralized logging configuration |
| `echo.cli` | CLI entry point and main application loop |

## Development

### Development Toolchain

| Tool | Purpose | Status |
|------|---------|--------|
| **pytest** | Test framework (110+ tests) | ✅ 60% coverage |
| **pytest-cov** | Coverage reporting | ✅ |
| **factory-boy** | Test fixture generation | ✅ 7 factories |
| **Faker** | Fake data generation | ✅ |
| **flake8 + plugins** | Linting (bugbear, comprehensions, docstrings, naming) | ✅ 0 violations |
| **black** | Code formatting | ✅ |
| **isort** | Import sorting | ✅ |
| **mypy** | Type checking | ✅ Pragmatic mode |
| **bandit** | Security linting | ✅ |
| **safety** | Dependency vulnerability scanning | ✅ |
| **pre-commit** | Pre-commit hook framework | ✅ Installed |
| **httpx** | HTTP client (testing) | ✅ |
| **watchdog** | File watcher for auto-testing | ✅ |

### Common Tasks

```bash
# Install development dependencies
make dev

# Run tests
make test

# Run tests with coverage report
make test-cov

# Generate HTML coverage report
make test-html

# Run linters
make lint

# Format code
make format

# Check formatting (CI-safe)
make check

# Run type checker
make type-check

# Run security scanner
make security

# Check dependencies for vulnerabilities
make deps-check

# Run full CI pipeline
make ci

# Install pre-commit hooks
make pre-commit

# Watch for file changes and auto-test
make watch

# Clean build artifacts
make clean
```

### Viewing Logs

```bash
tail -f logs/echo.log
```

### Adding Features

The modular architecture makes it easy to extend:

1. **New Core Module:** Add to `src/echo/core/`
2. **New Tool:** Add to `src/echo/tools/` and register in `_toolkit.py`
3. **New Service:** Add to `src/echo/services/`
4. **New Settings:** Add to `src/echo/config.py`
5. **New Commands:** Add to `EchoConsoleApp._handle_command()` in `cli.py`
6. **New Tests:** Add to `tests/` with factory-boy fixtures

## Dependencies

### Production

| Category | Package | Purpose |
|----------|---------|---------|
| Configuration | `pydantic>=2.5`, `pydantic-settings>=2.0`, `python-dotenv>=1.0` | Settings management |
| HTTP | `requests>=2.31` | API communication |
| Speech-to-Text | `faster-whisper>=1.0`, `ctranslate2>=4.0`, `onnxruntime>=1.14` | Voice transcription |
| Audio I/O | `sounddevice>=0.4.6`, `soundfile>=0.12.1`, `numpy>=1.24` | Recording and playback |
| Text-to-Speech | `edge-tts>=7.2.0` | Voice synthesis |
| Research | `wikipedia-api>=0.6.0`, `ddgs>=9.0.0`, `beautifulsoup4>=4.12` | Web search tools |
| CLI | `python-cli-menu>=1.5.0` | Interactive menus |

### Development

| Tool | Package |
|------|---------|
| Testing | `pytest`, `pytest-cov`, `pytest-asyncio`, `factory-boy`, `Faker` |
| Linting | `flake8`, `flake8-bugbear`, `flake8-comprehensions`, `flake8-docstrings`, `pep8-naming` |
| Formatting | `black`, `isort` |
| Type Checking | `mypy`, `types-requests`, `types-beautifulsoup4` |
| Security | `bandit`, `safety` |
| Hooks | `pre-commit` |
| HTTP Testing | `httpx` |
| File Watching | `watchdog` |

## Troubleshooting

### Audio Recording Issues

**No audio input detected:**
- Ensure microphone is connected and not muted
- Check audio input device permissions
- Install system dependencies:
  ```bash
  # Ubuntu/Debian
  sudo apt-get install portaudio19-dev python3-dev

  # macOS
  brew install portaudio
  ```

### API Issues

**"API_KEY not configured":**
- Ensure `.env` file exists with valid API key
- Key must not be the placeholder text

**Request timeout:**
- Check internet connection
- Verify API key is valid
- Try a different model

### Whisper Model Loading

**Model download takes too long:**
- Models are downloaded on first use and cached
- Use `base` or `small` for faster startup
- Larger models (`large-v3`) take longer to download

## License

MIT License

## Contributing

Contributions are welcome! Please:

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run `make ci` to ensure all checks pass
5. Submit a pull request

---

**Built with ❤️ using Python, faster-whisper, and edge-tts**
