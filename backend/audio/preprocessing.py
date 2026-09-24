"""
backend/audio/preprocessing.py

Real-time audio streaming validation and preprocessing for Project VISOR.
Ensures incoming chunks are properly converted to 16kHz mono float32 numpy arrays
and checks amplitude/energy to filter out empty or corrupt frames.
"""

from typing import Tuple, Optional, Dict, Any, Union
import numpy as np


class AudioPreprocessor:
    """
    Streaming audio preprocessor for Project VISOR audio ingest pipeline.
    Validates, standardizes (16kHz mono float32 [-1.0, 1.0]), and checks energy.
    """

    def __init__(
        self,
        target_sample_rate: int = 16000,
        min_rms_energy: float = 0.001,
        min_peak_amplitude: float = 0.002,
        max_peak_amplitude: float = 1.0,
    ):
        """
        Args:
            target_sample_rate: Required sample rate (default: 16000 Hz)
            min_rms_energy: Minimum RMS energy threshold to consider audio active (non-empty)
            min_peak_amplitude: Minimum peak value to consider audio active
            max_peak_amplitude: Maximum expected peak amplitude before clipping warning
        """
        self.target_sample_rate = target_sample_rate
        self.min_rms_energy = min_rms_energy
        self.min_peak_amplitude = min_peak_amplitude
        self.max_peak_amplitude = max_peak_amplitude

    @staticmethod
    def pcm_to_float32(
        raw_bytes: bytes,
        sample_width_bytes: int = 2,
    ) -> np.ndarray:
        """
        Convert raw PCM bytes to a normalized float32 numpy array in [-1.0, 1.0].

        Args:
            raw_bytes: Raw binary audio bytes
            sample_width_bytes: 2 for 16-bit PCM (int16), 4 for 32-bit float

        Returns:
            np.ndarray: float32 audio samples
        """
        if not raw_bytes:
            return np.empty(0, dtype=np.float32)

        if sample_width_bytes == 2:
            # 16-bit signed PCM (little endian standard for Web Audio)
            # Truncate any incomplete trailing sample byte
            num_samples = len(raw_bytes) // 2
            if num_samples == 0:
                return np.empty(0, dtype=np.float32)
            trimmed_bytes = raw_bytes[: num_samples * 2]
            int16_arr = np.frombuffer(trimmed_bytes, dtype=np.int16)
            return int16_arr.astype(np.float32) / 32768.0

        elif sample_width_bytes == 4:
            # 32-bit float PCM
            num_samples = len(raw_bytes) // 4
            if num_samples == 0:
                return np.empty(0, dtype=np.float32)
            trimmed_bytes = raw_bytes[: num_samples * 4]
            return np.frombuffer(trimmed_bytes, dtype=np.float32).copy()

        else:
            raise ValueError(f"Unsupported sample width: {sample_width_bytes} bytes")

    @staticmethod
    def to_mono(audio: np.ndarray) -> np.ndarray:
        """
        Convert multi-channel audio to mono by averaging channels.
        Accepts shape (samples,), (channels, samples), or (samples, channels).
        """
        if audio.ndim == 1:
            return audio.astype(np.float32)

        if audio.ndim == 2:
            # Determine channel dimension (smaller dimension is typically channels)
            if audio.shape[0] < audio.shape[1]:
                # Shape (channels, samples)
                return np.mean(audio, axis=0).astype(np.float32)
            else:
                # Shape (samples, channels)
                return np.mean(audio, axis=1).astype(np.float32)

        raise ValueError(f"Unexpected audio array shape: {audio.shape}")

    def resample_if_needed(
        self,
        audio: np.ndarray,
        orig_sr: int,
    ) -> np.ndarray:
        """
        Resample audio to self.target_sample_rate if orig_sr differs.
        """
        if orig_sr == self.target_sample_rate or len(audio) == 0:
            return audio

        try:
            import librosa
            return librosa.resample(
                audio,
                orig_sr=orig_sr,
                target_sr=self.target_sample_rate,
            ).astype(np.float32)
        except Exception:
            # Fallback: scipy or simple linear interpolation if librosa fails
            from scipy import signal
            num_target_samples = int(round(len(audio) * float(self.target_sample_rate) / orig_sr))
            return signal.resample(audio, num_target_samples).astype(np.float32)

    @staticmethod
    def compute_energy(audio: np.ndarray) -> Tuple[float, float]:
        """
        Compute RMS energy and peak amplitude of the audio array.

        Returns:
            Tuple[float, float]: (rms_energy, peak_amplitude)
        """
        if len(audio) == 0:
            return 0.0, 0.0

        rms = float(np.sqrt(np.mean(np.square(audio))))
        peak = float(np.max(np.abs(audio)))
        return rms, peak

    def validate_energy(self, audio: np.ndarray) -> Tuple[bool, Dict[str, Any]]:
        """
        Check amplitude and energy to determine if frame is active speech vs silence/corrupt.

        Returns:
            Tuple[bool, Dict[str, Any]]: (is_valid, metrics_dict)
        """
        if len(audio) == 0:
            return False, {
                "valid": False,
                "reason": "EMPTY_FRAME",
                "rms": 0.0,
                "peak": 0.0,
            }

        # Check for NaN or Inf (corrupted sensor/stream data)
        if not np.isfinite(audio).all():
            return False, {
                "valid": False,
                "reason": "NON_FINITE_DATA_CORRUPTION",
                "rms": 0.0,
                "peak": 0.0,
            }

        rms, peak = self.compute_energy(audio)

        # Check for silence or flatline
        if rms < self.min_rms_energy and peak < self.min_peak_amplitude:
            return False, {
                "valid": False,
                "reason": "SILENT_FRAME",
                "rms": rms,
                "peak": peak,
            }

        return True, {
            "valid": True,
            "reason": "OK",
            "rms": rms,
            "peak": peak,
        }

    def process_chunk(
        self,
        chunk: Union[bytes, np.ndarray],
        input_sr: int = 16000,
        sample_width_bytes: int = 2,
    ) -> Tuple[np.ndarray, bool, Dict[str, Any]]:
        """
        Full streaming validation pipeline:
        1. Ingests bytes or numpy array
        2. Converts to float32
        3. Collapses to mono
        4. Resamples to target_sample_rate (16000 Hz)
        5. Performs energy & corruption check

        Returns:
            Tuple[np.ndarray, bool, Dict[str, Any]]:
                - audio_16k_mono: 1D float32 numpy array
                - is_valid: True if frame passed sanity & energy checks
                - info: details regarding RMS, peak, validation status
        """
        # 1. Convert to numpy float32
        if isinstance(chunk, bytes):
            audio = self.pcm_to_float32(chunk, sample_width_bytes=sample_width_bytes)
        elif isinstance(chunk, np.ndarray):
            if chunk.dtype == np.int16:
                audio = chunk.astype(np.float32) / 32768.0
            else:
                audio = chunk.astype(np.float32)
        else:
            return np.empty(0, dtype=np.float32), False, {
                "valid": False,
                "reason": f"UNSUPPORTED_TYPE_{type(chunk).__name__}",
                "rms": 0.0,
                "peak": 0.0,
            }

        # 2. Convert to mono
        audio = self.to_mono(audio)

        # 3. Resample if needed
        if input_sr != self.target_sample_rate and len(audio) > 0:
            audio = self.resample_if_needed(audio, orig_sr=input_sr)

        # 4. Energy & corruption validation
        is_valid, info = self.validate_energy(audio)
        info["samples"] = len(audio)
        info["duration_ms"] = (len(audio) / self.target_sample_rate) * 1000.0 if len(audio) > 0 else 0.0

        return audio, is_valid, info


# ── Standalone Convenience Functions ──────────────────────────────────────────

_default_preprocessor = AudioPreprocessor()


def validate_and_convert_chunk(
    chunk: Union[bytes, np.ndarray],
    input_sr: int = 16000,
    sample_width_bytes: int = 2,
) -> Tuple[np.ndarray, bool, Dict[str, Any]]:
    """
    Convenience function to validate and convert a chunk into 16kHz mono float32.
    """
    return _default_preprocessor.process_chunk(
        chunk, input_sr=input_sr, sample_width_bytes=sample_width_bytes
    )


def check_audio_energy(
    audio: np.ndarray,
    min_rms: float = 0.001,
) -> Tuple[bool, float]:
    """
    Check if an audio array has sufficient RMS energy to be considered active.

    Returns:
        Tuple[bool, float]: (is_active, rms_energy)
    """
    if len(audio) == 0 or not np.isfinite(audio).all():
        return False, 0.0
    rms = float(np.sqrt(np.mean(np.square(audio))))
    return (rms >= min_rms), rms
