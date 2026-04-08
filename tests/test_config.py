"""Tests for Echo configuration."""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest


class TestConfigStore:
    """Tests for ConfigStore class."""

    def test_save_and_load_config(self, tmp_path, mock_settings):
        """Test saving and loading configuration."""
        from echo.config import ConfigStore

        config_path = tmp_path / "config.json"
        saved_path = ConfigStore.save_config(mock_settings, config_path)

        assert saved_path == config_path
        assert config_path.exists()

        loaded = ConfigStore.load_config(config_path)
        assert loaded is not None
        assert loaded["api_provider"] == "openrouter"
        assert loaded["temperature"] == 0.7

    def test_load_nonexistent_config(self):
        """Test loading config when file doesn't exist."""
        from echo.config import ConfigStore

        result = ConfigStore.load_config(Path("/nonexistent/path"))
        assert result is None

    def test_apply_config(self, mock_settings):
        """Test applying configuration to settings."""
        from echo.config import ConfigStore

        config_data = {
            "api_provider": "mistral",
            "temperature": 0.9,
            "max_tokens": 2048,
        }
        ConfigStore.apply_config(mock_settings, config_data)

        assert mock_settings.api_provider == "mistral"
        assert mock_settings.temperature == 0.9
        assert mock_settings.max_tokens == 2048

    def test_sync_to_env(self, mock_settings):
        """Test syncing settings to environment variables."""
        from echo.config import ConfigStore

        ConfigStore.sync_to_env(mock_settings)

        assert os.environ.get("API_PROVIDER") == "openrouter"
        assert os.environ.get("TEMPERATURE") == "0.7"


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self, mock_settings):
        """Test default setting values."""
        assert mock_settings.api_provider == "openrouter"
        assert mock_settings.temperature == 0.7
        assert mock_settings.max_tokens == 1024
        assert mock_settings.enable_tools is False

    def test_temperature_bounds(self):
        """Test temperature is within valid bounds."""
        from echo.config import Settings

        # This would fail validation if out of bounds
        settings = Settings()
        assert 0.0 <= settings.temperature <= 2.0
