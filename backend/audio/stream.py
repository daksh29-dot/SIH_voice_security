"""
backend/audio/stream.py

Thread-safe circular/rolling FIFO buffer for Project VISOR.
Accumulates valid speech frames into a rolling window (e.g., 3-second window
updating every 500ms) for streaming deepfake model inference.
"""

import threading
from typing import Optional, Dict, Any
import numpy as np


class RollingAudioBuffer:
    """
    Thread-safe circular FIFO audio buffer for streaming inference.

    Accumulates 16kHz mono float32 audio chunks. Once the buffer fills to the
    target window size (e.g. 3.0s = 48,000 samples), it signals that a window
    is ready every `step_duration_sec` (e.g. 500ms = 8,000 samples).
    """

    def __init__(
        self,
        sample_rate: int = 16000,
        window_duration_sec: float = 4.0375,
        step_duration_sec: float = 0.5,
    ):
        """
        Args:
            sample_rate: Audio sampling frequency in Hz (default: 16000)
            window_duration_sec: Length of analysis window in seconds (default: 3.0)
            step_duration_sec: Hop size / cadence between inference runs in seconds (default: 0.5)
        """
        self.sample_rate = sample_rate
        self.window_duration_sec = window_duration_sec
        self.step_duration_sec = step_duration_sec

        self.window_samples = int(round(window_duration_sec * sample_rate))
        self.step_samples = int(round(step_duration_sec * sample_rate))

        if self.window_samples <= 0 or not 0 < self.step_samples <= self.window_samples:
            raise ValueError("Invalid buffer window/hop")
        self._lock = threading.RLock()
        self._buffer = np.empty(0, dtype=np.float32)
        self._accumulated_since_step = 0
        self._total_samples_ingested = 0

    def push(self, chunk: np.ndarray) -> bool:
        """
        Thread-safely append an audio chunk to the rolling FIFO buffer.

        Args:
            chunk: 1D float32 numpy array of speech samples

        Returns:
            bool: True if a new inference window is ready (buffer full and hop size satisfied)
        """
        if chunk is None or len(chunk) == 0:
            return False

        chunk_1d = np.asarray(chunk, dtype=np.float32)
        if chunk_1d.ndim != 1 or not np.isfinite(chunk_1d).all():
            raise ValueError("Buffer requires finite mono PCM")
        num_new_samples = len(chunk_1d)

        with self._lock:
            self._total_samples_ingested += num_new_samples
            self._accumulated_since_step += num_new_samples

            if len(self._buffer) == 0:
                self._buffer = chunk_1d.copy()
            else:
                self._buffer = np.concatenate([self._buffer, chunk_1d])

            # Circular FIFO retention: truncate oldest samples past window_samples
            if len(self._buffer) > self.window_samples:
                overflow = len(self._buffer) - self.window_samples
                self._buffer = self._buffer[overflow:]

            # Ready when we have accumulated a full window AND enough new data for a step
            is_ready = (
                len(self._buffer) >= self.window_samples
                and self._accumulated_since_step >= self.step_samples
            )
            return is_ready

    def is_ready(self) -> bool:
        """Check if buffer is full and sufficient new data has arrived since last get_window()."""
        with self._lock:
            return (
                len(self._buffer) >= self.window_samples
                and self._accumulated_since_step >= self.step_samples
            )

    def get_window(self) -> np.ndarray:
        """
        Retrieve a copy of the latest rolling window and reset the hop-size accumulator.

        If the buffer is not full, raises instead of manufacturing silence.

        Returns:
            np.ndarray: 1D float32 array of shape (window_samples,)
        """
        with self._lock:
            self._accumulated_since_step = 0

            if len(self._buffer) < self.window_samples:
                raise ValueError("Wait for a full contiguous model window")
            return self._buffer[-self.window_samples:].copy()

    def peek_window(self) -> np.ndarray:
        """Actual buffered samples, without padding or hop reset (enrollment)."""
        with self._lock:
            return self._buffer.copy()

    def clear(self) -> None:
        """Flush buffer and reset state for a new stream."""
        with self._lock:
            self._buffer = np.empty(0, dtype=np.float32)
            self._accumulated_since_step = 0
            self._total_samples_ingested = 0

    @property
    def current_samples(self) -> int:
        """Number of samples currently held in the rolling buffer."""
        with self._lock:
            return len(self._buffer)

    @property
    def current_duration_sec(self) -> float:
        """Duration of audio currently held in the rolling buffer (seconds)."""
        with self._lock:
            return len(self._buffer) / self.sample_rate

    @property
    def is_full(self) -> bool:
        """True if buffer has reached capacity (window_samples)."""
        with self._lock:
            return len(self._buffer) >= self.window_samples

    def stats(self) -> Dict[str, Any]:
        """Diagnostic metadata for logging and debugging."""
        with self._lock:
            return {
                "current_samples": len(self._buffer),
                "window_samples": self.window_samples,
                "step_samples": self.step_samples,
                "current_duration_sec": round(len(self._buffer) / self.sample_rate, 3),
                "window_duration_sec": self.window_duration_sec,
                "step_duration_sec": self.step_duration_sec,
                "accumulated_since_step": self._accumulated_since_step,
                "is_full": len(self._buffer) >= self.window_samples,
                "is_ready": self.is_ready(),
                "total_samples_ingested": self._total_samples_ingested,
            }
