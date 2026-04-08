"""Audio recording with VAD (Voice Activity Detection) for automatic start/stop."""

import logging
import threading
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import sounddevice as sd
import soundfile as sf

from echo.config import get_settings

logger = logging.getLogger(__name__)


class AudioRecorder:
    """Audio recorder with VAD-based automatic speech detection."""

    def __init__(self):
        """Initialize the audio recorder with settings."""
        self.settings = get_settings()
        self.is_recording = False
        self.is_listening = True
        self.audio_chunks = []
        self._recording_thread: threading.Thread | None = None
        self._stop_event = threading.Event()
        self._callback: Callable | None = None
        self._stream = None

        # VAD parameters
        self._silence_threshold = 0.01
        self._silence_duration = 1.5
        self._speech_duration = 0.3
        self._current_silence_time = 0.0
        self._current_speech_time = 0.0
        self._chunk_duration = 0.05

        # Audio buffer for pre-speech capture
        self._pre_speech_buffer = []
        self._pre_speech_max = 20

        logger.info(
            "AudioRecorder initialized with VAD (sample rate: %d)", self.settings.sample_rate
        )

    def _calculate_rms(self, audio_data: np.ndarray) -> float:
        """Calculate RMS amplitude of audio data."""
        if len(audio_data) == 0:
            return 0.0
        return np.sqrt(np.mean(audio_data**2))

    def _is_speech(self, audio_data: np.ndarray) -> bool:
        """Detect if audio chunk contains speech based on amplitude."""
        rms = self._calculate_rms(audio_data)
        return rms > self._silence_threshold

    def _audio_callback(self, indata, frames, time_info, status):
        """Callback for sounddevice input stream with VAD processing."""
        if status:
            logger.debug("Audio status: %s", status)

        if not self.is_listening:
            return

        self._pre_speech_buffer.append(indata.copy())
        if len(self._pre_speech_buffer) > self._pre_speech_max:
            self._pre_speech_buffer.pop(0)

        if self.is_recording:
            if self._is_speech(indata):
                self._current_silence_time = 0.0
                self.audio_chunks.append(indata.copy())
            else:
                self._current_silence_time += self._chunk_duration
                self.audio_chunks.append(indata.copy())

                if self._current_silence_time >= self._silence_duration:
                    logger.info("VAD: Silence detected, stopping recording")
                    self.is_recording = False
                    self._stop_event.set()
        else:
            if self._is_speech(indata):
                self._current_speech_time += self._chunk_duration
                if self._current_speech_time >= self._speech_duration:
                    logger.info("VAD: Speech detected, starting recording")
                    self.is_recording = True
                    self._current_silence_time = 0.0
                    self.audio_chunks = self._pre_speech_buffer.copy()
            else:
                self._current_speech_time = 0.0

    def start_listening(self) -> None:
        """Start continuous audio listening with VAD."""
        if self._stream is not None:
            logger.warning("Already listening")
            return

        self.is_listening = True
        self.is_recording = False
        self.audio_chunks = []
        self._pre_speech_buffer = []
        self._stop_event.clear()
        self._current_silence_time = 0.0
        self._current_speech_time = 0.0

        try:
            self._stream = sd.InputStream(
                samplerate=self.settings.sample_rate,
                channels=1,
                callback=self._audio_callback,
                dtype=np.float32,
                blocksize=int(self.settings.sample_rate * self._chunk_duration),
            )
            self._stream.start()
            logger.info("VAD listening started")
        except Exception as e:
            logger.error("Failed to start VAD listening: %s", e)
            self.is_listening = False
            raise

    def stop_listening(self) -> None:
        """Stop all audio listening and recording."""
        self.is_listening = False
        self.is_recording = False
        self._stop_event.set()

        if self._stream is not None:
            try:
                self._stream.stop()
                self._stream.close()
                self._stream = None
            except Exception as e:
                logger.error("Error closing stream: %s", e)

        logger.info("VAD listening stopped")

    def wait_for_recording_done(self, timeout: float = 10.0) -> bool:
        """Wait for current recording to finish."""
        if not self.is_recording:
            return True

        result = self._stop_event.wait(timeout=timeout)
        if result:
            self._stop_event.clear()
        return result

    def save_recording(self, filepath: Path | None = None) -> Path | None:
        """Save recorded audio to file."""
        if not self.audio_chunks:
            logger.warning("No audio chunks to save")
            return None

        if filepath is None:
            filepath = Path(f"data/rec_{int(time.time())}.wav")

        filepath.parent.mkdir(parents=True, exist_ok=True)

        try:
            audio_data = np.concatenate(self.audio_chunks, axis=0)
            audio_data = self._trim_silence(audio_data)

            if len(audio_data) < self.settings.sample_rate * 0.3:
                logger.warning("Recording too short, likely noise")
                return None

            sf.write(str(filepath), audio_data, self.settings.sample_rate)
            logger.info(
                "Audio saved to: %s (%.2f seconds)",
                filepath,
                len(audio_data) / self.settings.sample_rate,
            )
            return filepath
        except Exception as e:
            logger.error("Failed to save audio: %s", e)
            return None

    def _trim_silence(self, audio_data: np.ndarray, threshold: float = 0.005) -> np.ndarray:
        """Trim silence from start and end of audio."""
        start = 0
        for i in range(len(audio_data)):
            if abs(audio_data[i]) > threshold:
                start = max(0, i - int(self.settings.sample_rate * 0.05))
                break

        end = len(audio_data)
        for i in range(len(audio_data) - 1, -1, -1):
            if abs(audio_data[i]) > threshold:
                end = min(len(audio_data), i + int(self.settings.sample_rate * 0.05))
                break

        return audio_data[start:end]

    def cleanup(self) -> None:
        """Clean up resources."""
        self.stop_listening()
        self._stop_event.set()
        self.audio_chunks.clear()
        self._pre_speech_buffer.clear()
        logger.info("AudioRecorder cleaned up")
