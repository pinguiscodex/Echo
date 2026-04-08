# Changelog

All notable changes to Echo AI Chatbot will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Production-ready `src/` layout for proper package structure
- `pyproject.toml` as single source of truth (PEP 621 compliant)
- Dedicated `tests/` directory with pytest fixtures and initial test suite
- Custom type stubs for `edge-tts` in `stubs/` directory
- `Makefile` for common development tasks
- `.python-version` for pyenv/uv compatibility
- Dedicated `tools/` package split from monolithic `tools.py`
- `services/` layer for chat history persistence
- `types.py` for shared type aliases and TypedDicts
- Centralized logging configuration in `utils/logging.py`
- Input validation utilities in `utils/validators.py`

### Changed
- Migrated from flat layout to `src/echo/` package structure
- Renamed `core/audio_recorder.py` → `core/recorder.py`
- Renamed `core/tts_engine.py` → `core/tts.py`
- Split `core/tools.py` into modular `tools/` package:
  - `tools/base.py` - Core types and directory confinement
  - `tools/filesystem.py` - File operations
  - `tools/command.py` - Shell command execution
  - `tools/code.py` - Python code execution
  - `tools/system.py` - System information
  - `tools/research.py` - Wikipedia & DuckDuckGo search
  - `tools/_toolkit.py` - Main AIToolkit aggregator
- Updated all imports from `from core import ...` to `from echo.core import ...`
- Entry point now supports `python -m echo` via `__main__.py`
- CLI interface separated into `cli.py` for testability

### Removed
- `requirements.txt` (dependencies moved to `pyproject.toml`)
- Flat directory structure (`config/`, `core/`, `utils/` at root)

## [1.0.0] - 2026-04-08

### Initial Release
- Voice-enabled CLI chatbot with OpenRouter/Mistral API integration
- Speech-to-text via faster-whisper
- Text-to-speech via edge-tts
- AI agent tools for file operations, code execution, and web research
- Caps Lock voice recording with VAD
- Streaming AI responses
- Chat history persistence
- Interactive settings menu
