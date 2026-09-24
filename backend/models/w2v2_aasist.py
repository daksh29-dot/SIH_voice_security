"""
backend/models/w2v2_aasist.py

W2V2-AASIST ONNX inference wrapper for Project VISOR.
Executes deepfake voice detection on rolling audio windows using ONNX Runtime CPU.
"""

from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union, Tuple, Dict, Any
import time
import numpy as np
import onnxruntime as ort

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


def find_w2v2_aasist_model() -> Path:
    """Locate the w2v2-aasist ONNX model file."""
    candidates = [
        PROJECT_ROOT / "models" / "w2v2-aasist.onnx",
        PROJECT_ROOT / "models" / "w2v2_aasist.onnx",
    ]
    for path in candidates:
        if path.exists():
            return path

    # Check config.py if available
    try:
        import config
        if hasattr(config, "MODEL_PATH") and Path(config.MODEL_PATH).exists():
            return Path(config.MODEL_PATH)
    except ImportError:
        pass

    raise FileNotFoundError(
        f"W2V2-AASIST ONNX model not found. Expected at models/w2v2-aasist.onnx or models/w2v2_aasist.onnx"
    )


@dataclass
class W2V2AASISTPrediction:
    """Inference output container for W2V2-AASIST."""
    raw_logits: Tuple[float, ...]
    spoof_score: float
    inference_time_ms: float
    bona_fide_score: float

    def to_dict(self) -> Dict[str, Any]:
        return {
            "raw_logits": list(self.raw_logits),
            "spoof_score": float(self.spoof_score),
            "bona_fide_score": float(self.bona_fide_score),
            "inference_time_ms": float(self.inference_time_ms),
        }


class W2V2AASISTModel:
    """
    ONNX Runtime CPU wrapper for W2V2-AASIST deepfake voice detection model.

    Input:
        16 kHz mono audio waveform (typically 3-4s rolling buffer, 64,600 samples fixed input).
    Output:
        - raw_logits: tuple of floats (spoof_logit, bona_fide_logit)
        - spoof_score: calibrated float in [0.0, 1.0] (0.0 = Real / Bona Fide, 1.0 = Spoof / Clone)
        - inference_time_ms: execution time in milliseconds
    """

    WINDOW_SAMPLES = 64600  # Fixed model input length: 4.0375 seconds at 16kHz

    def __init__(
        self,
        model_path: Optional[Union[str, Path]] = None,
        num_threads: int = 4,
    ):
        """
        Args:
            model_path: Path to w2v2-aasist.onnx model file.
            num_threads: CPU intra-op thread count for ONNX Runtime.
        """
        if model_path is None:
            self.model_path = find_w2v2_aasist_model()
        else:
            self.model_path = Path(model_path)
            if not self.model_path.exists():
                raise FileNotFoundError(f"Model path does not exist: {self.model_path}")

        # Configure ONNX Runtime for CPU execution
        sess_options = ort.SessionOptions()
        sess_options.intra_op_num_threads = num_threads
        sess_options.inter_op_num_threads = 1
        sess_options.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL

        print(f"[*] Loading W2V2-AASIST ONNX from {self.model_path} via CPUExecutionProvider...")
        self.session = ort.InferenceSession(
            str(self.model_path),
            sess_options=sess_options,
            providers=["CPUExecutionProvider"],
        )

        self.input_name = self.session.get_inputs()[0].name
        self.output_name = self.session.get_outputs()[0].name
        print(f"[+] W2V2-AASIST ONNX loaded. Input: '{self.input_name}', Output: '{self.output_name}'")

    def predict(self, waveform: np.ndarray) -> W2V2AASISTPrediction:
        """
        Execute deepfake detection inference on a rolling audio buffer.

        Args:
            waveform: 1D numpy array of 16kHz mono audio (e.g. 48,000 to 64,600 samples)

        Returns:
            W2V2AASISTPrediction: contains raw_logits, spoof_score, and inference_time_ms
        """
        wav = np.asarray(waveform, dtype=np.float32).flatten()

        # Handle audio length: zero-pad if shorter than 64600, truncate if longer
        if len(wav) < self.WINDOW_SAMPLES:
            padded = np.zeros(self.WINDOW_SAMPLES, dtype=np.float32)
            padded[: len(wav)] = wav
            wav = padded
        elif len(wav) > self.WINDOW_SAMPLES:
            wav = wav[: self.WINDOW_SAMPLES]

        # ONNX model expects shape [batch=1, samples=64600]
        input_tensor = wav[np.newaxis, :].astype(np.float32)

        start_time = time.perf_counter()
        outputs = self.session.run(
            [self.output_name],
            {self.input_name: input_tensor},
        )
        elapsed_ms = (time.perf_counter() - start_time) * 1000.0

        logits = outputs[0]  # shape (1, 2)
        logits_flat = logits[0].astype(np.float64)

        # Numerically stable softmax:
        # Index 0 = Spoof
        # Index 1 = Bona Fide
        shifted_logits = logits_flat - np.max(logits_flat)
        exp_logits = np.exp(shifted_logits)
        probabilities = exp_logits / np.sum(exp_logits)

        spoof_prob = float(probabilities[0])
        bona_fide_prob = float(probabilities[1])
        raw_logits_tuple = tuple(float(x) for x in logits_flat)

        return W2V2AASISTPrediction(
            raw_logits=raw_logits_tuple,
            spoof_score=spoof_prob,
            bona_fide_score=bona_fide_prob,
            inference_time_ms=elapsed_ms,
        )


# Global lazy singleton for shared server instances
_global_w2v2_aasist: Optional[W2V2AASISTModel] = None


def get_w2v2_aasist_model() -> W2V2AASISTModel:
    """Retrieve or initialize the global shared W2V2-AASIST model singleton."""
    global _global_w2v2_aasist
    if _global_w2v2_aasist is None:
        _global_w2v2_aasist = W2V2AASISTModel()
    return _global_w2v2_aasist
