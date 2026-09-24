import numpy as np
import onnxruntime as ort
from pathlib import Path
import config

class SileroVAD:
    def __init__(self, model_path: str = None):
        if model_path is None:
            model_path = str(config.PROJECT_ROOT / "models" / "silero_vad.onnx")
        self.session = ort.InferenceSession(model_path, providers=["CPUExecutionProvider"])
        self.reset_states()

    def reset_states(self):
        self._state = np.zeros((2, 1, 128), dtype=np.float32)

    def process_chunk(self, chunk: np.ndarray, sr: int = 16000) -> float:
        """
        Process a chunk of audio (e.g. 512 samples for 16kHz).
        Returns probability of speech.
        """
        if chunk.ndim == 1:
            chunk = chunk[np.newaxis, :]
            
        inputs = {
            "input": chunk.astype(np.float32),
            "state": self._state,
            "sr": np.array([sr], dtype=np.int64)
        }
        
        out, state = self.session.run(None, inputs)
        self._state = state
        return float(out[0, 0])

def trim_silence(waveform: np.ndarray, sr: int = 16000, threshold: float = 0.3, window_size: int = 512) -> np.ndarray:
    """
    Uses Silero VAD to extract only the active speech segments from a waveform.
    Returns the concatenated active speech waveform.
    """
    vad = SileroVAD()
    active_chunks = []
    
    num_chunks = len(waveform) // window_size
    for i in range(num_chunks):
        chunk = waveform[i * window_size : (i + 1) * window_size]
        prob = vad.process_chunk(chunk, sr)
        if prob > threshold:
            active_chunks.append(chunk)
            
    if not active_chunks:
        return waveform # Fallback to original if no speech detected
        
    return np.concatenate(active_chunks)
