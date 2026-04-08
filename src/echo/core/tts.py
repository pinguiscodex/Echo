"""Text-to-speech engine using edge-tts directly."""

import asyncio
import logging
import tempfile
from pathlib import Path
from typing import Generator, Optional

import sounddevice as sd
import soundfile as sf

from echo.config import get_settings

logger = logging.getLogger(__name__)


class TTSEngine:
    """Text-to-speech engine using edge-tts for high-quality, free voices."""

    def __init__(self, voice: Optional[str] = None):
        """Initialize the TTS engine.

        Args:
            voice: Voice identifier (uses settings default if None)
        """
        self.settings = get_settings()
        self.voice = voice or self.settings.tts_voice
        self._initialized = False

        logger.info("TTSEngine initialized with voice: %s", self.voice)

    async def _generate_speech(self, text: str, output_file: Path) -> None:
        """Generate speech audio file from text using edge-tts."""
        import edge_tts

        communicate = edge_tts.Communicate(text, self.voice)
        await communicate.save(str(output_file))
        logger.debug("Speech generated: %s", output_file)

    def speak(self, text: str, block: bool = True) -> None:
        """Speak text aloud using edge-tts."""
        if not text or not text.strip():
            logger.debug("Empty text provided, skipping TTS")
            return

        stripped = text.strip()
        if len(stripped) < 3:
            logger.debug("Response too short for TTS (%d chars): %s", len(stripped), stripped)
            return

        import string

        if all(c in string.punctuation for c in stripped):
            logger.debug("Response is punctuation-only, skipping TTS: %s", stripped)
            return

        try:
            temp_file = Path(tempfile.mktemp(suffix=".mp3"))
            asyncio.run(self._generate_speech(text, temp_file))

            if temp_file.exists():
                audio_data, sample_rate = sf.read(str(temp_file))
                sd.play(audio_data, sample_rate)

                if block:
                    sd.wait()
                    logger.info("Speech playback complete")

                temp_file.unlink(missing_ok=True)
            else:
                logger.warning("Audio file not generated")

        except Exception as e:
            logger.error("TTS failed: %s", e, exc_info=True)

    def speak_stream(self, text_generator: Generator[str, None, None]) -> str:
        """Speak text as it streams in. Note: collects full text first."""
        full_text = ""
        for chunk in text_generator:
            full_text += chunk

        self.speak(full_text)
        return full_text

    def stop(self) -> None:
        """Stop current speech playback."""
        try:
            sd.stop()
            logger.info("Speech stopped")
        except Exception as e:
            logger.error("Error stopping speech: %s", e)

    def set_voice(self, voice: str) -> None:
        """Change the voice used for TTS."""
        self.voice = voice
        logger.info("Voice changed to: %s", voice)

    async def get_available_voices(self) -> list:
        """Get list of available edge-tts voices."""
        try:
            import edge_tts

            voices = await edge_tts.list_voices()
            logger.info("Retrieved %d available voices", len(voices))
            return voices
        except Exception as e:
            logger.error("Failed to get available voices: %s", e)
            return []

    def cleanup(self) -> None:
        """Clean up TTS resources."""
        self.stop()
        logger.info("TTS engine cleaned up")
