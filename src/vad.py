"""Silero v5/v6 ONNX streaming adapter; VAD is NOT a real/fake detector.
Reference: https://github.com/snakers4/silero-vad/blob/master/src/silero_vad/utils_vad.py
The main inference pipeline uses SpeechGate (WebRTC); this is the legacy path.
"""
import numpy as np
import config
from audio_preprocessing import validate_waveform


class SileroVAD:
    def __init__(self, model_path=None):
        import onnxruntime as ort
        if model_path is None:
            model_path = str(config.PROJECT_ROOT / "models" / "silero_vad.onnx")
        self.session = ort.InferenceSession(str(model_path), providers=["CPUExecutionProvider"])
        if {m.name for m in self.session.get_inputs()} != {"input", "state", "sr"}:
            raise ValueError("Expected Silero v5/v6 input/state/sr ONNX export")
        self.reset_states()

    def reset_states(self):
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = None
        self._last_sr = None

    def process_chunk(self, chunk, sr=16000):
        if sr not in (8000, 16000):
            raise ValueError("Silero supports 8000 or 16000 Hz")
        x = np.asarray(chunk)
        if x.ndim == 2 and x.shape[0] == 1:
            x = x[0]
        x = validate_waveform(x)
        n, context_n = (512, 64) if sr == 16000 else (256, 32)
        if x.size != n:
            raise ValueError(f"Supply exactly {n} samples at {sr} Hz")
        if self._last_sr != sr:
            self.reset_states()
            self._context = np.zeros((1, context_n), dtype=np.float32)
        framed = np.concatenate((self._context, x[None]), axis=1)
        out, state = self.session.run(None, {
            "input": framed, "state": self._state, "sr": np.array(sr, dtype=np.int64)})
        probability = float(np.asarray(out).reshape(-1)[0])
        if not np.isfinite(probability) or not 0 <= probability <= 1:
            raise ValueError("Invalid Silero speech probability")
        self._state = state
        self._context = framed[:, -context_n:].copy()
        self._last_sr = sr
        return probability


def trim_silence(waveform, sr=16000, threshold=0.3, window_size=512):
    """Trim only outer silence with a 200 ms margin; retain all internal pauses.

    Kept for compatibility. Main detector intentionally does not trim or splice.
    No detected speech returns the original for downstream quality rejection.
    """
    x = validate_waveform(waveform)
    if sr not in (8000, 16000) or not 0 <= threshold <= 1:
        raise ValueError("Invalid sample rate or threshold")
    n = 512 if sr == 16000 else 256
    if window_size != n:
        raise ValueError(f"window_size must be {n} at {sr} Hz")
    vad = SileroVAD()
    active = []
    for start in range(0, len(x), n):
        chunk = x[start:start+n]
        padded = np.pad(chunk, (0, n-len(chunk)))
        if vad.process_chunk(padded, sr) > threshold:
            active.append((start, start+len(chunk)))
    if not active:
        return x
    margin = int(0.2 * sr)
    return x[max(0, active[0][0]-margin):min(len(x), active[-1][1]+margin)].copy()
