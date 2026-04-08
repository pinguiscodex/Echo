# Echo AI Chatbot

> Voice-enabled CLI chatbot with AI agent tools, powered by OpenRouter or Mistral.

[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)
[![Tests: 110+](https://img.shields.io/badge/tests-110+-brightgreen.svg)](https://github.com/pinguiscodex/Echo)
[![Coverage: 60%](https://img.shields.io/badge/coverage-60%25-orange.svg)](https://github.com/pinguiscodex/Echo)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## Features

| Capability | Details |
|------------|---------|
| **Voice Input** | Press Caps Lock to toggle recording, transcribed via faster-whisper |
| **Voice Output** | AI responses spoken aloud via edge-tts |
| **Text Chat** | Traditional input/output as fallback |
| **Streaming** | Real-time token streaming from AI |
| **Agent Tools** | File ops, code execution, web research (Wikipedia, DuckDuckGo) |
| **Configurable** | Models, voices, temperature, input/output modes |
| **Persistent** | Chat history auto-saved to disk |

## Quick Start

```bash
# 1. Clone & enter
git clone https://github.com/pinguiscodex/Echo.git && cd Echo

# 2. Create venv & install
python -m venv venv && source venv/bin/activate
pip install -e .

# 3. Configure
cp .env.example .env
# Edit .env -> add your OPENROUTER_API_KEY

# 4. Run
echo
```

> No admin permissions required. Keyboard input uses Python stdlib only.

## How It Works

```
You speak -> Caps Lock toggles recording -> Whisper transcribes -> AI thinks -> TTS responds
```

| Layer | Technology |
|-------|-----------|
| AI Backend | OpenRouter or Mistral API (streaming) |
| Speech-to-Text | faster-whisper (CTranslate2, CPU int8) |
| Text-to-Speech | edge-tts (Microsoft Neural voices) |
| Audio I/O | sounddevice + soundfile |

## Commands

| Command | Action |
|---------|--------|
| `/quit` | Exit |
| `/clear` | Clear history |
| `/save` / `/load` | Save/load chat history |
| `/tools` | List AI agent tools |
| `/settings` | Interactive settings menu |
| `/help` | Show all commands |

**Voice:** Press **Caps Lock** once to start recording, press again to stop and transcribe.

## Configuration

Edit `.env` to customize:

```env
API_PROVIDER=openrouter           # openrouter | mistral
OPENROUTER_API_KEY=sk-...         # your API key
OPENROUTER_MODEL=openai/gpt-oss-120b:free
WHISPER_MODEL=base                # tiny | base | small | medium | large-v3
TTS_VOICE=en-US-JennyNeural       # any edge-tts voice
TEMPERATURE=0.7                   # 0.0 - 2.0
ENABLE_TOOLS=true                 # enable AI agent tools
INPUT_MODE=both                   # text | speech | both
OUTPUT_MODE=both                  # text | speech | both
```

See [.env.example](.env.example) for all options.

## Development

### Setup

```bash
pip install -e ".[dev]"      # install dev dependencies
make pre-commit              # install git hooks
```

### Commands

```bash
make dev          # install all dev dependencies
make test         # run 110+ tests
make test-cov     # run tests with coverage
make lint         # flake8 + plugins
make format       # black + isort
make type-check   # mypy
make security     # bandit
make deps-check   # safety (vulnerability scan)
make ci           # full pipeline: format -> lint -> type-check -> test -> security
make watch        # auto-test on file changes
make clean        # remove build artifacts
```

### Toolchain

| Category | Tools |
|----------|-------|
| **Testing** | pytest, pytest-cov, factory-boy, Faker |
| **Linting** | flake8 + bugbear + comprehensions + docstrings + pep8-naming |
| **Formatting** | black, isort |
| **Types** | mypy (pragmatic mode) |
| **Security** | bandit, safety |
| **Hooks** | pre-commit (5 hooks) |

## Project Structure

```
src/echo/
├── cli.py              # Entry point, EchoConsoleApp
├── config.py           # Pydantic settings, ConfigStore
├── types.py            # Shared TypedDicts
├── core/
│   ├── chatbot.py      # OpenRouter/Mistral streaming API
│   ├── agent.py        # Tool orchestration
│   ├── recorder.py     # VAD-based microphone recording
│   ├── transcriber.py  # faster-whisper STT
│   └── tts.py          # edge-tts synthesis
├── tools/
│   ├── base.py         # ToolResult, directory confinement
│   ├── filesystem.py   # File CRUD operations
│   ├── command.py      # Shell command execution
│   ├── code.py         # Python execution + validation
│   ├── system.py       # System info tools
│   └── research.py     # Wikipedia, DuckDuckGo, fact-check
├── services/
│   └── history.py      # Chat history persistence
└── utils/
    ├── logging.py      # Centralized logging config
    ├── helpers.py      # Pure utility functions
    └── validators.py   # Input validation

tests/                  # 110+ tests, 60% coverage
├── factories.py        # factory-boy test factories
├── conftest.py         # Pytest fixtures
└── integration/        # End-to-end tests
```

## AI Agent Tools

Echo includes 23 built-in tools for the AI to use:

| Category | Tools |
|----------|-------|
| **Files** | `list_directory`, `read_file`, `write_file`, `edit_file`, `create_directory`, `delete_path`, `search_files` |
| **System** | `run_command`, `execute_python`, `validate_python`, `get_system_info`, `get_directory_structure` |
| **Research** | `web_search`, `news_search`, `wikipedia_search`, `wikipedia_summary`, `academic_search`, `code_search`, `smart_research`, `fact_check`, `dork_search`, `wikipedia_random`, `wikipedia_full_article` |

> All file operations are **confined to the launch directory**. Research tools have **no restrictions**.

## Troubleshooting

| Problem | Fix |
|---------|-----|
| No audio input | Install `portaudio19-dev` (Linux) or `brew install portaudio` (macOS) |
| API_KEY not configured | Add your key to `.env` |
| Request timeout | Check internet, verify API key, try a different model |
| Whisper slow to load | Use `base` or `small` -- models are cached after first download |

## License

MIT -- see [LICENSE](LICENSE).

## Contributing

1. Fork the repo
2. Create a feature branch
3. Make your changes
4. Run `make ci` to verify
5. Submit a pull request

---

Built with Python, [faster-whisper](https://github.com/SYSTRAN/faster-whisper), and [edge-tts](https://github.com/rany2/edge-tts)
