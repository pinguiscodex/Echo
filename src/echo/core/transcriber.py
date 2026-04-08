"""Whisper speech-to-text transcription engine using faster-whisper."""

import logging
from pathlib import Path
from typing import Optional

from echo.config import get_settings

logger = logging.getLogger(__name__)


class WhisperTranscriber:
    """Speech-to-text transcription using faster-whisper (CTranslate2 backend)."""

    def __init__(self, model_name: Optional[str] = None):
        """Initialize the Whisper transcriber.

        Args:
            model_name: Whisper model size (tiny/base/small/medium/large-v3)
        """
        self.settings = get_settings()
        self.model_name = model_name or self.settings.whisper_model
        self._model = None

        logger.info("WhisperTranscriber initialized with model: %s", self.model_name)

    def _load_model(self):
        """Lazy load the faster-whisper model."""
        if self._model is None:
            try:
                from faster_whisper import WhisperModel

                logger.info("Loading faster-whisper model: %s", self.model_name)

                self._model = WhisperModel(
                    model_size_or_path=self.model_name,
                    device="cpu",
                    compute_type="int8",
                )
                logger.info("faster-whisper model loaded successfully")

            except ImportError:
                logger.error("faster-whisper not installed. Run: pip install faster-whisper")
                raise
            except Exception as e:
                logger.error("Failed to load faster-whisper model: %s", e)
                raise

        return self._model

    def transcribe(self, audio_path: Path, language: Optional[str] = None) -> str:
        """Transcribe audio file to text using faster-whisper.

        Args:
            audio_path: Path to audio file
            language: Optional language code (e.g., 'en', 'de', 'fr')

        Returns:
            Transcribed text

        Raises:
            FileNotFoundError: If audio file doesn't exist
            Exception: If transcription fails
        """
        if not audio_path.exists():
            error_msg = f"Audio file not found: {audio_path}"
            logger.error(error_msg)
            raise FileNotFoundError(error_msg)

        try:
            model = self._load_model()

            options = {
                "beam_size": 5,
                "vad_filter": True,
            }
            if language:
                options["language"] = language

            logger.info("Transcribing audio: %s", audio_path)

            segments, info = model.transcribe(str(audio_path), **options)

            logger.info(
                "Detected language: '%s' with probability %.2f",
                info.language,
                info.language_probability,
            )

            text = " ".join(segment.text for segment in segments).strip()

            logger.info("Transcription complete: %d characters", len(text))

            return text

        except Exception as e:
            logger.error("Transcription failed: %s", e, exc_info=True)
            raise

    def transcribe_async(self, audio_path: Path, language: Optional[str] = None) -> str:
        """Synchronous transcribe (alias for transcribe)."""
        return self.transcribe(audio_path, language)

    def get_segments(self, audio_path: Path, language: Optional[str] = None):
        """Get transcription with segment details."""
        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        model = self._load_model()

        options = {"beam_size": 5, "vad_filter": True}
        if language:
            options["language"] = language

        segments, info = model.transcribe(str(audio_path), **options)

        return list(segments), info

    def cleanup(self) -> None:
        """Clean up resources and unload model."""
        if self._model is not None:
            self._model = None
            logger.info("faster-whisper model unloaded")
