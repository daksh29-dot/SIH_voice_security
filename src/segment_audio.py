"""
segment_audio.py

AASIST-L's ONNX export has a FIXED input length of 64600 samples.

Baseline windowing (matches upstream clovaai/aasist eval convention):
    audio >= 64600 samples  ->  take the FIRST 64600 samples (no random crop)
    audio <  64600 samples  ->  tile-repeat the audio to fill 64600 samples
"""

from typing import List

import numpy as np

import _pathfix  # noqa: F401
import config


# def pad_fixed(waveform: np.ndarray, window_samples: int = config.FIXED_WINDOW_SAMPLES) -> np.ndarray:
#     """Take first `window_samples` samples, or tile-repeat if audio is shorter."""
#     if waveform.ndim != 1:
#         raise ValueError(f"Expected 1D mono waveform, got shape {waveform.shape}")

#     waveform = waveform.astype(np.float32)
#     n = waveform.shape[0]

#     if n >= window_samples:
#         return waveform[:window_samples]

#     reps = window_samples // n + 1
#     return np.tile(waveform, reps)[:window_samples].astype(np.float32)
def pad_fixed(waveform, window_samples=64600):
    """
    Convert any audio shorter than the model window into exactly
    window_samples using zero-padding.

    NOTE: We deliberately use zero-padding (not tile-repeat) here.
    Tile-repeat was the original clovaai/aasist training convention but it
    creates self-similarity artifacts (beginning of voice appearing again at
    the end) that the W2V2-AASIST model flags as synthetic. Empirically,
    zero-padding gives ~85% spoof for real mic recordings vs ~97% with
    tile-repeat. Zero-padding is the lesser evil.

    Long audio is NOT truncated here — handled by segment_waveform_sliding().
    """
    if waveform.ndim != 1:
        raise ValueError("Expected mono 1D waveform")

    waveform = waveform.astype(np.float32)
    n = waveform.shape[0]

    if n >= window_samples:
        return waveform[:window_samples]

    padded = np.zeros(window_samples, dtype=np.float32)
    padded[:n] = waveform
    return padded

def segment_waveform_sliding(
    waveform: np.ndarray,
    window_samples: int = config.FIXED_WINDOW_SAMPLES,
    overlap_s: float = config.SEGMENT_OVERLAP_SECONDS,
    sample_rate: int = config.TARGET_SAMPLE_RATE,
) -> List[np.ndarray]:
    """EXPERIMENTAL (Step 5): multiple overlapping 64600-sample windows."""
    if waveform.ndim != 1:
        raise ValueError(f"Expected 1D mono waveform, got shape {waveform.shape}")

    hop = window_samples - int(overlap_s * sample_rate)
    if hop <= 0:
        raise ValueError("overlap_s must be smaller than the fixed window length")

    total = len(waveform)
    if total <= window_samples:
        return [pad_fixed(waveform, window_samples)]

    segments = []
    start = 0
    while start < total:
        end = start + window_samples
        if end <= total:
            segments.append(waveform[start:end])
        else:
            segments.append(pad_fixed(waveform[start:], window_samples))
            break
        start += hop

    return segments


def segment_waveform(waveform: np.ndarray) -> List[np.ndarray]:
    """Entry point used by inference.py."""
    if config.USE_SLIDING_WINDOWS:
        return segment_waveform_sliding(waveform)
    return [pad_fixed(waveform)]


if __name__ == "__main__":
    import sys
    from audio_preprocessing import preprocess_audio

    if len(sys.argv) != 2:
        print("Usage: python segment_audio.py <path_to_audio>")
        sys.exit(1)

    wav = preprocess_audio(sys.argv[1])
    segs = segment_waveform(wav)
    print(f"Input duration: {len(wav) / config.TARGET_SAMPLE_RATE:.2f}s ({len(wav)} samples)")
    print(f"Fixed window:   {config.FIXED_WINDOW_SAMPLES} samples")
    print(f"Sliding windows enabled: {config.USE_SLIDING_WINDOWS}")
    print(f"Produced {len(segs)} window(s) of shape {segs[0].shape if segs else 'N/A'}")