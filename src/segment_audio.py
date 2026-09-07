"""
segment_audio.py

Splits a preprocessed waveform into fixed-length windows for inference.

    10-second recording
    ├── Segment 1
    ├── Segment 2
    ├── Segment 3
    └── Segment 4

Window size and overlap are controlled from config.py so they're easy to
sweep during Step 5 (single window vs multiple windows vs sliding windows).
"""

from typing import List

import numpy as np

import _pathfix  # noqa: F401
import config


def segment_waveform(
    waveform: np.ndarray,
    sample_rate: int = config.TARGET_SAMPLE_RATE,
    segment_length_s: float = config.SEGMENT_LENGTH_SECONDS,
    overlap_s: float = config.SEGMENT_OVERLAP_SECONDS,
    pad_short: bool = config.PAD_SHORT_AUDIO,
) -> List[np.ndarray]:
    """
    Split a 1D waveform into fixed-length segments.

    Args:
        waveform: 1D float32 array (mono, already resampled/normalized).
        sample_rate: sample rate of `waveform`.
        segment_length_s: length of each segment in seconds.
        overlap_s: overlap between consecutive segments in seconds.
        pad_short: if True, zero-pad audio shorter than one segment instead
            of returning an empty list.

    Returns:
        List of 1D float32 arrays, each of length `segment_length_s * sample_rate`
        (except possibly the last one, unless it was padded).
    """
    if waveform.ndim != 1:
        raise ValueError(f"Expected 1D mono waveform, got shape {waveform.shape}")

    segment_len = int(segment_length_s * sample_rate)
    hop_len = segment_len - int(overlap_s * sample_rate)
    if hop_len <= 0:
        raise ValueError("overlap_s must be smaller than segment_length_s")

    total_samples = len(waveform)

    # Audio shorter than one full segment.
    if total_samples < segment_len:
        if pad_short:
            padded = np.zeros(segment_len, dtype=np.float32)
            padded[:total_samples] = waveform
            return [padded]
        return []

    segments = []
    start = 0
    while start + segment_len <= total_samples:
        segments.append(waveform[start:start + segment_len])
        start += hop_len

    # Capture any leftover tail as a final (padded) segment so we don't
    # silently discard the end of the recording.
    remainder_start = start
    if remainder_start < total_samples:
        tail = waveform[remainder_start:]
        if pad_short:
            padded = np.zeros(segment_len, dtype=np.float32)
            padded[:len(tail)] = tail
            segments.append(padded)

    return segments


if __name__ == "__main__":
    import sys
    from audio_preprocessing import preprocess_audio

    if len(sys.argv) != 2:
        print("Usage: python segment_audio.py <path_to_audio>")
        sys.exit(1)

    wav = preprocess_audio(sys.argv[1])
    segs = segment_waveform(wav)
    print(f"Total duration: {len(wav) / config.TARGET_SAMPLE_RATE:.2f}s")
    print(f"Produced {len(segs)} segment(s) of shape {segs[0].shape if segs else 'N/A'}")
