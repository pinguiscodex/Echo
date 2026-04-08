"""Tests for Echo validators module."""

from pathlib import Path

import pytest

from echo.utils.validators import (
    is_valid_api_key,
    is_valid_audio_path,
    sanitize_input,
    validate_max_tokens,
    validate_sample_rate,
    validate_temperature,
)


class TestIsValidApiKey:
    """Tests for is_valid_api_key."""

    def test_valid_key(self):
        """Test valid API key."""
        assert is_valid_api_key("sk-abc123def456") is True

    def test_empty_key(self):
        """Test empty key."""
        assert is_valid_api_key("") is False
        assert is_valid_api_key("   ") is False

    def test_placeholder_keys(self):
        """Test placeholder keys are rejected."""
        assert is_valid_api_key("your_openrouter_api_key_here") is False
        assert is_valid_api_key("your_mistral_api_key_here") is False
        assert is_valid_api_key("your_api_key_here") is False


class TestIsValidAudioPath:
    """Tests for is_valid_audio_path."""

    def test_valid_wav(self, tmp_path):
        """Test valid WAV file."""
        audio_file = tmp_path / "test.wav"
        audio_file.touch()
        assert is_valid_audio_path(audio_file) is True

    def test_valid_mp3(self, tmp_path):
        """Test valid MP3 file."""
        audio_file = tmp_path / "test.mp3"
        audio_file.touch()
        assert is_valid_audio_path(audio_file) is True

    def test_nonexistent_file(self, tmp_path):
        """Test nonexistent file."""
        audio_file = tmp_path / "nonexistent.wav"
        assert is_valid_audio_path(audio_file) is False

    def test_invalid_extension(self, tmp_path):
        """Test invalid extension."""
        txt_file = tmp_path / "test.txt"
        txt_file.touch()
        assert is_valid_audio_path(txt_file) is False


class TestSanitizeInput:
    """Tests for sanitize_input."""

    def test_normal_input(self):
        """Test normal input."""
        assert sanitize_input("Hello world") == "Hello world"

    def test_whitespace_stripping(self):
        """Test whitespace is stripped."""
        assert sanitize_input("  Hello  ") == "Hello"

    def test_empty_input(self):
        """Test empty input."""
        assert sanitize_input("") == ""
        assert sanitize_input("   ") == ""

    def test_truncation(self):
        """Test long input is truncated."""
        long_text = "a" * 5000
        result = sanitize_input(long_text, max_length=100)
        assert len(result) == 100

    def test_default_max_length(self):
        """Test default max length."""
        long_text = "a" * 5000
        result = sanitize_input(long_text)
        assert len(result) == 4096


class TestValidateSampleRate:
    """Tests for validate_sample_rate."""

    @pytest.mark.parametrize("rate", [8000, 11025, 16000, 22050, 44100, 48000])
    def test_valid_rates(self, rate):
        """Test valid sample rates."""
        assert validate_sample_rate(rate) is True

    @pytest.mark.parametrize("rate", [1234, 9999, 44000, 0, -1])
    def test_invalid_rates(self, rate):
        """Test invalid sample rates."""
        assert validate_sample_rate(rate) is False


class TestValidateTemperature:
    """Tests for validate_temperature."""

    @pytest.mark.parametrize("temp", [0.0, 0.7, 1.0, 1.5, 2.0])
    def test_valid_temps(self, temp):
        """Test valid temperatures."""
        assert validate_temperature(temp) is True

    @pytest.mark.parametrize("temp", [-0.1, 2.1, 3.0, -1.0])
    def test_invalid_temps(self, temp):
        """Test invalid temperatures."""
        assert validate_temperature(temp) is False


class TestValidateMaxTokens:
    """Tests for validate_max_tokens."""

    @pytest.mark.parametrize("tokens", [64, 256, 1024, 2048, 4096])
    def test_valid_tokens(self, tokens):
        """Test valid max tokens."""
        assert validate_max_tokens(tokens) is True

    @pytest.mark.parametrize("tokens", [0, 32, 5000, 8192, -1])
    def test_invalid_tokens(self, tokens):
        """Test invalid max tokens."""
        assert validate_max_tokens(tokens) is False
