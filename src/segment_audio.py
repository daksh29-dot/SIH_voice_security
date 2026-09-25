"""Full, contiguous windows. A final end-aligned window replaces padded tails."""
from dataclasses import dataclass
import numpy as np
from config import DEFAULTS

@dataclass
class Window:
    start: int
    waveform: np.ndarray
    valid_samples: int

def windows(x, settings=DEFAULTS):
    x = np.asarray(x, dtype=np.float32)
    if x.ndim != 1 or not np.isfinite(x).all():
        raise ValueError("Expected finite mono waveform")
    n, w, h = len(x), settings.window_samples, settings.hop_samples
    if n == 0:
        return []
    if n < w:
        if settings.short_audio == "abstain":
            return []
        # Match reference padding; never count repeated samples as extra speech.
        repeated = np.tile(x, (w + n - 1) // n)[:w]
        return [Window(0, repeated, n)]
    starts = list(range(0, n - w + 1, h))
    if starts[-1] != n - w:
        starts.append(n - w)
    return [Window(s, x[s:s+w], w) for s in starts]

def segment_waveform(x, settings=DEFAULTS):
    return [w.waveform for w in windows(x, settings)]
