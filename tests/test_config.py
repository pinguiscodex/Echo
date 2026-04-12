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
        # Model-specific settings are now stored under model_settings
        assert "model_settings" in loaded
        assert loaded["model_settings"]["test-model"]["temperature"] == 0.7
        assert loaded["model_settings"]["test-model"]["max_tokens"] == 1024
        assert loaded["model_settings"]["test-model"]["enable_tools"] is False

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
            "mistral_model": "mistral-small-latest",
            "model_settings": {
                "mistral-small-latest": {
                    "temperature": 0.9,
                    "max_tokens": 2048,
                    "enable_tools": True,
                }
            },
        }
        ConfigStore.apply_config(mock_settings, config_data)

        assert mock_settings.api_provider == "mistral"
        assert mock_settings.temperature == 0.9
        assert mock_settings.max_tokens == 2048
        assert mock_settings.enable_tools is True

    def test_sync_to_env(self, mock_settings):
        """Test syncing settings to environment variables."""
        from echo.config import ConfigStore

        ConfigStore.sync_to_env(mock_settings)

        assert os.environ.get("API_PROVIDER") == "openrouter"
        assert os.environ.get("TEMPERATURE") == "0.7"

    def test_model_specific_settings_save_and_load(self, tmp_path, mock_settings):
        """Test saving and loading model-specific settings."""
        from echo.config import ConfigStore

        config_path = tmp_path / "config.json"

        # Save with first model
        mock_settings.openrouter_model = "model-1"
        mock_settings.temperature = 0.5
        mock_settings.max_tokens = 512
        mock_settings.enable_tools = True
        ConfigStore.save_config(mock_settings, config_path)

        # Change to second model and save
        mock_settings.openrouter_model = "model-2"
        mock_settings.temperature = 1.0
        mock_settings.max_tokens = 2048
        mock_settings.enable_tools = False
        ConfigStore.save_config(mock_settings, config_path)

        # Load and verify both models exist
        loaded = ConfigStore.load_config(config_path)
        assert "model_settings" in loaded
        assert "model-1" in loaded["model_settings"]
        assert "model-2" in loaded["model_settings"]
        assert loaded["model_settings"]["model-1"]["temperature"] == 0.5
        assert loaded["model_settings"]["model-2"]["temperature"] == 1.0

    def test_apply_model_settings(self, mock_settings):
        """Test applying model-specific settings."""
        from echo.config import ConfigStore

        # Set the model that matches config_data
        mock_settings.api_provider = "openrouter"
        mock_settings.openrouter_model = "target-model"

        config_data = {
            "api_provider": "openrouter",
            "openrouter_model": "target-model",
            "model_settings": {
                "target-model": {
                    "temperature": 1.5,
                    "max_tokens": 4096,
                    "enable_tools": True,
                }
            },
        }

        result = ConfigStore.apply_model_settings(mock_settings, config_data)
        assert result is True
        assert mock_settings.temperature == 1.5
        assert mock_settings.max_tokens == 4096
        assert mock_settings.enable_tools is True

    def test_apply_model_settings_no_data(self, mock_settings):
        """Test apply_model_settings with no model data."""
        from echo.config import ConfigStore

        config_data = {"api_provider": "openrouter"}
        result = ConfigStore.apply_model_settings(mock_settings, config_data)
        assert result is False

    def test_model_switching(self, tmp_path, mock_settings):
        """Test switching between models loads correct settings."""
        from echo.config import ConfigStore

        config_path = tmp_path / "config.json"

        # Setup model 1
        mock_settings.api_provider = "openrouter"
        mock_settings.openrouter_model = "model-1"
        mock_settings.temperature = 0.3
        mock_settings.max_tokens = 256
        mock_settings.enable_tools = False
        ConfigStore.save_config(mock_settings, config_path)

        # Setup model 2
        mock_settings.openrouter_model = "model-2"
        mock_settings.temperature = 1.2
        mock_settings.max_tokens = 2048
        mock_settings.enable_tools = True
        ConfigStore.save_config(mock_settings, config_path)

        # Switch to model 1: first update the model on mock, then apply config
        mock_settings.openrouter_model = "model-1"
        loaded = ConfigStore.load_config(config_path)
        ConfigStore.apply_config(mock_settings, loaded)

        assert mock_settings.temperature == 0.3
        assert mock_settings.max_tokens == 256
        assert mock_settings.enable_tools is False

        # Switch to model 2
        mock_settings.openrouter_model = "model-2"
        loaded = ConfigStore.load_config(config_path)
        ConfigStore.apply_config(mock_settings, loaded)

        assert mock_settings.temperature == 1.2
        assert mock_settings.max_tokens == 2048
        assert mock_settings.enable_tools is True


class TestSettings:
    """Tests for Settings class."""

    def test_default_values(self, mock_settings):
        """Test default setting values."""
        assert mock_settings.api_provider == "openrouter"
        assert mock_settings.temperature == 0.7
        assert mock_settings.max_tokens == 1024
        # Note: mock_settings enables tools by default in conftest
        assert mock_settings.enable_tools is False

    def test_temperature_bounds(self):
        """Test temperature is within valid bounds."""
        from echo.config import Settings

        # This would fail validation if out of bounds
        settings = Settings()
        assert 0.0 <= settings.temperature <= 2.0
