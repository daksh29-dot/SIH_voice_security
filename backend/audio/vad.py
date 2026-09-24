"""
backend/audio/vad.py

Silero Voice Activity Detection (VAD) via ONNX Runtime for Project VISOR.
Classifies streaming audio frames into speech vs. non-speech with sub-millisecond
latency on CPU, preventing non-speech frames from triggering expensive downstream inference.
"""

from pathlib import Path
from typing import Tuple, Optional, Union
import urllib.request
import numpy as np
import onnxruntime as ort


SILERO_MODEL_URL = "https://raw.githubusercontent.com/snakers4/silero-vad/master/src/silero_vad/data/silero_vad.onnx"
DEFAULT_MODEL_PATH = Path(__file__).resolve().parent.parent.parent / "models" / "silero_vad.onnx"


class SileroVAD:
    """
    Ultra-fast ONNX Runtime wrapper for Silero VAD (v5).
    Operates on 16kHz mono audio frames in increments of 512 samples (32ms)
    with a 64-sample preceding context window.
    Maintains recurrent hidden states and context across streaming chunks.
    """

    SAMPLE_RATE = 16000
    WINDOW_SIZE_SAMPLES = 512  # 32ms window at 16kHz
    CONTEXT_SIZE_SAMPLES = 64  # Context size for Silero VAD v5 at 16kHz

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        threshold: float = 0.5,
    ):
        """
        Args:
            model_path: Path to silero_vad.onnx file. If None or non-existent, attempts to locate or download it.
            threshold: Speech probability threshold (default: 0.5). Probabilities >= threshold are considered speech.
        """
        self.threshold = threshold
        self.model_path = Path(model_path) if model_path else DEFAULT_MODEL_PATH

        if not self.model_path.exists():
            self._download_model()

        # Optimize ONNX Runtime session for low-latency CPU streaming
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = 1
        sess_options.inter_op_num_threads = 1
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )

        self._sr_tensor = np.array(self.SAMPLE_RATE, dtype=np.int64)
        self.reset_states()

    def _download_model(self) -> None:
        """Download silero_vad.onnx if not present locally."""
        self.model_path.parent.mkdir(parents=True, exist_ok=True)
        print(f"[*] Downloading Silero VAD ONNX model to {self.model_path}...")
        try:
            urllib.request.urlretrieve(SILERO_MODEL_URL, str(self.model_path))
            print(f"[+] Silero VAD ONNX downloaded successfully ({self.model_path.stat().st_size} bytes).")
        except Exception as e:
            raise RuntimeError(
                f"Failed to download Silero VAD model from {SILERO_MODEL_URL}: {e}. "
                f"Please manually place silero_vad.onnx in {self.model_path.parent}"
            )

    def reset_states(self) -> None:
        """Reset recurrent hidden state, context, and leftover sample buffer."""
        self._state = np.zeros((2, 1, 128), dtype=np.float32)
        self._context = np.zeros((1, self.CONTEXT_SIZE_SAMPLES), dtype=np.float32)
        self._leftover_samples = np.empty(0, dtype=np.float32)

    def _infer_frame(self, frame_512: np.ndarray) -> float:
        """
        Run inference on exactly 512 samples with prepended 64-sample context.
        Updates internal recurrent state `self._state` and `self._context`.
        Returns speech probability [0.0, 1.0].
        """
        frame_2d = frame_512.reshape(1, self.WINDOW_SIZE_SAMPLES).astype(np.float32)
        # Input to Silero VAD v5 is [context (64), frame (512)] -> total 576 samples
        model_input = np.concatenate([self._context, frame_2d], axis=1)

        out, new_state = self.session.run(
            None,
            {
                "input": model_input,
                "state": self._state,
                "sr": self._sr_tensor,
            },
        )
        self._state = new_state
        self._context = model_input[:, -self.CONTEXT_SIZE_SAMPLES :].copy()
        return float(out[0][0])

    def is_speech(
        self,
        chunk: np.ndarray,
        threshold: Optional[float] = None,
    ) -> Tuple[bool, float]:
        """
        Evaluate if an arbitrary-length 16kHz mono audio chunk contains active speech.

        Accumulates leftover samples across streaming calls so partial frames are not discarded.
        Slices chunk into 512-sample windows and executes ONNX forward passes.

        Args:
            chunk: 1D float32 numpy array at 16kHz
            threshold: Custom threshold for this call (defaults to self.threshold)

        Returns:
            Tuple[bool, float]:
                - is_speech: True if speech detected (prob >= threshold)
                - max_speech_prob: Peak speech probability detected in this chunk
        """
        active_thresh = self.threshold if threshold is None else threshold

        if chunk is None or len(chunk) == 0:
            return False, 0.0

        chunk_1d = np.asarray(chunk, dtype=np.float32).flatten()

        # Combine with leftover samples from previous call
        if len(self._leftover_samples) > 0:
            full_audio = np.concatenate([self._leftover_samples, chunk_1d])
        else:
            full_audio = chunk_1d

        num_full_windows = len(full_audio) // self.WINDOW_SIZE_SAMPLES
        if num_full_windows == 0:
            # Buffer remainder and return False
            self._leftover_samples = full_audio
            return False, 0.0

        probs = []
        for i in range(num_full_windows):
            start_idx = i * self.WINDOW_SIZE_SAMPLES
            end_idx = start_idx + self.WINDOW_SIZE_SAMPLES
            frame = full_audio[start_idx:end_idx]
            prob = self._infer_frame(frame)
            probs.append(prob)

        # Retain unconsumed remainder for the next chunk
        remainder_idx = num_full_windows * self.WINDOW_SIZE_SAMPLES
        self._leftover_samples = full_audio[remainder_idx:]

        # Maximum confidence across the frames in this chunk
        max_prob = max(probs) if probs else 0.0
        return (max_prob >= active_thresh), max_prob


def create_vad_detector(threshold: float = 0.5) -> SileroVAD:
    """Factory helper to instantiate a configured SileroVAD instance."""
    return SileroVAD(threshold=threshold)
