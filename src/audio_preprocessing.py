"""
audio_preprocessing.py

Loads arbitrary audio (wav/mp3/flac/etc.) and converts it into the exact
waveform format AASIST-L expects:

    Input audio -> mono -> target sample rate -> normalized waveform

Uses soundfile + librosa for broad format support and resampling.
"""

from pathlib import Path
from typing import Tuple

import numpy as np
import librosa

import _pathfix  # noqa: F401
import config


class AudioLoadError(Exception):
    """Raised when an audio file can't be loaded or decoded."""


def load_audio(path: str | Path) -> Tuple[np.ndarray, int]:
    """
    Load an audio file from disk. Supports WAV, FLAC, MP3, OGG, WebM/Opus, etc.

    Returns:
        waveform: 1D or 2D float32 numpy array, shape (samples,) or (channels, samples)
        sample_rate: native sample rate of the file (before resampling)
    """
    path = Path(path)
    if not path.exists():
        raise AudioLoadError(f"Audio file not found: {path}")

    # Try librosa first for standard formats
    if path.suffix.lower() not in ('.webm', '.ogg'):
        try:
            waveform, sample_rate = librosa.load(str(path), sr=None, mono=False)
            return waveform.astype(np.float32), sample_rate
        except Exception:
            pass

    # PyAV fallback: handles WebM/Opus, OGG, and all media streams
    try:
        import av
        container = av.open(str(path))
        audio_stream = next((s for s in container.streams if s.type == 'audio'), None)
        if not audio_stream:
            raise AudioLoadError(f"No audio stream found in {path}")

        target_sr = getattr(config, 'TARGET_SAMPLE_RATE', 16000)
        resampler = av.AudioResampler(format='fltp', layout='mono', rate=target_sr)
        frames = []
        for frame in container.decode(audio_stream):
            for resampled in resampler.resample(frame):
                frames.append(resampled.to_ndarray())
        container.close()

        if not frames:
            raise AudioLoadError(f"Empty audio decoded from {path}")

        waveform = np.concatenate(frames, axis=1).squeeze(0).astype(np.float32)
        return waveform, target_sr
    except Exception as e:
        # Final attempt: try librosa.load as last resort
        try:
            waveform, sample_rate = librosa.load(str(path), sr=None, mono=False)
            return waveform.astype(np.float32), sample_rate
        except Exception:
            raise AudioLoadError(f"Failed to decode audio file {path}: {e}") from e



def to_mono(waveform: np.ndarray) -> np.ndarray:
    """Collapse multi-channel audio to mono by averaging channels."""
    if waveform.ndim == 1:
        return waveform
    return np.mean(waveform, axis=0).astype(np.float32)


def resample(waveform: np.ndarray, orig_sr: int, target_sr: int) -> np.ndarray:
    """Resample a mono waveform to the target sample rate."""
    if orig_sr == target_sr:
        return waveform
    return librosa.resample(waveform, orig_sr=orig_sr, target_sr=target_sr).astype(np.float32)


def normalize(waveform: np.ndarray, eps: float = 1e-9) -> np.ndarray:
    """
    Peak-normalize a waveform to [-1, 1].

    Peak normalization is used rather than z-score normalization because
    AASIST-style models are typically trained on raw waveforms scaled to
    this range. Revisit this if Step 2 (model inspection) shows otherwise.
    """
    peak = np.max(np.abs(waveform))
    if peak < eps:
        # Silent or near-silent audio — avoid divide-by-zero, return as-is.
        return waveform
    return (waveform / peak).astype(np.float32)


def preprocess_audio(path: str | Path) -> np.ndarray:
    """
    Full preprocessing pipeline: load -> mono -> resample -> normalize.

    NOTE: Do NOT add trim/filter steps. AASIST-L is extremely sensitive to
    waveform modifications — even a Butterworth high-pass filter causes
    real-speech files to be misclassified as spoof. The model was trained
    on raw normalized waveforms and must receive them unmodified.

    This is the single entry point the rest of the pipeline should call.
    """
    waveform, sr = load_audio(path)

    if config.FORCE_MONO:
        waveform = to_mono(waveform)
    elif waveform.ndim > 1:
        # If mono isn't forced but we got multi-channel audio, still collapse
        # it, since AASIST-L expects a single channel.
        waveform = to_mono(waveform)

    waveform = resample(waveform, sr, config.TARGET_SAMPLE_RATE)
    waveform = normalize(waveform)

    return waveform


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python audio_preprocessing.py <path_to_audio>")
        sys.exit(1)

    wav = preprocess_audio(sys.argv[1])
    print(f"Loaded waveform: shape={wav.shape}, dtype={wav.dtype}, "
          f"min={wav.min():.4f}, max={wav.max():.4f}, "
          f"duration={len(wav) / config.TARGET_SAMPLE_RATE:.2f}s")
