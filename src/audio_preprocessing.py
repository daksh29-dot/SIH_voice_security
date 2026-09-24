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

from vad import trim_silence
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

    # Try librosa first for ALL formats (librosa uses ffmpeg under the hood and
    # handles WebM/Opus, OGG, WAV, MP3, FLAC, etc.). This is the preferred path
    # because it preserves the native sample rate correctly.
    try:
        waveform, sample_rate = librosa.load(str(path), sr=None, mono=False)
        if waveform is not None and len(waveform.flat) > 0:
            return waveform.astype(np.float32), sample_rate
    except Exception as librosa_err:
        print(f"[!] librosa.load failed for {path.name}: {librosa_err}. Trying PyAV fallback...")

    # PyAV fallback: handles WebM/Opus, OGG, and all media streams that librosa misses
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
        print(f"[+] PyAV decoded {path.name}: {len(waveform)} samples at {target_sr}Hz")
        return waveform, target_sr
    except ImportError:
        raise AudioLoadError(
            f"Cannot decode {path.name}: librosa failed and PyAV is not installed. "
            f"Run: pip install av"
        )
    except Exception as av_err:
        raise AudioLoadError(f"Failed to decode audio file {path}: {av_err}") from av_err



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
    
    # Trim Silence / Noise using Silero VAD
    # This prevents the W2V2-AASIST model from evaluating background noise
    # as synthetic generative artifacts.
    waveform = trim_silence(waveform, sr=config.TARGET_SAMPLE_RATE)
    
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
