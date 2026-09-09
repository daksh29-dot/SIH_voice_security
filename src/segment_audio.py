"""
segment_audio.py

AASIST-L's ONNX export has a FIXED input length of 64600 samples.

Windowing:
    audio >= 64600 samples  ->  take the FIRST 64600 samples
    audio <  64600 samples  ->  tile-repeat the audio to fill 64600 samples

This allows audio samples of ANY duration to be processed.
"""

from typing import List

import numpy as np

import _pathfix  # noqa: F401
import config


def pad_fixed(
    waveform: np.ndarray,
    window_samples: int = config.FIXED_WINDOW_SAMPLES
) -> np.ndarray:
    """
    Convert audio to the fixed input size required by AASIST-L.

    - If audio is longer than or equal to the fixed window:
        Take the first `window_samples` samples.

    - If audio is shorter than the fixed window:
        Tile-repeat the audio until the fixed window is filled.

    This means there is NO minimum audio-duration restriction.
    """

    if waveform.ndim != 1:
        raise ValueError(
            f"Expected 1D mono waveform, got shape {waveform.shape}"
        )

    waveform = waveform.astype(np.float32)
    n = waveform.shape[0]

    if n == 0:
        raise ValueError("Audio waveform is empty.")

    if n < window_samples:
        reps = window_samples // n + 1
        return np.tile(waveform, reps)[:window_samples].astype(np.float32)

    return waveform[:window_samples]


def segment_waveform_sliding(
    waveform: np.ndarray,
    window_samples: int = config.FIXED_WINDOW_SAMPLES,
    overlap_s: float = config.SEGMENT_OVERLAP_SECONDS,
    sample_rate: int = config.TARGET_SAMPLE_RATE,
) -> List[np.ndarray]:
    """
    Create fixed-size overlapping windows.

    Audio shorter than one window is passed through pad_fixed(),
    which tile-repeats it instead of rejecting it.
    """

    if waveform.ndim != 1:
        raise ValueError(
            f"Expected 1D mono waveform, got shape {waveform.shape}"
        )

    hop = window_samples - int(overlap_s * sample_rate)

    if hop <= 0:
        raise ValueError(
            "overlap_s must be smaller than the fixed window length"
        )

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
            segments.append(
                pad_fixed(waveform[start:], window_samples)
            )
            break

        start += hop

    return segments


def segment_waveform(waveform: np.ndarray) -> List[np.ndarray]:
    """
    Entry point used by inference.py.
    """

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

    print(
        f"Input duration: "
        f"{len(wav) / config.TARGET_SAMPLE_RATE:.2f}s "
        f"({len(wav)} samples)"
    )

    print(
        f"Fixed window:   "
        f"{config.FIXED_WINDOW_SAMPLES} samples"
    )

    print(
        f"Sliding windows enabled: "
        f"{config.USE_SLIDING_WINDOWS}"
    )

    print(
        f"Produced {len(segs)} window(s) "
        f"of shape {segs[0].shape if segs else 'N/A'}"
    )