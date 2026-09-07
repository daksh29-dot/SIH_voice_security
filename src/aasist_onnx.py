"""
aasist_onnx.py

Thin wrapper around the pretrained AASIST-L ONNX model.

    waveform -> ONNX Runtime -> AASIST-L -> prediction/score

The model itself is never modified here. This module's job is only to:
  1. Load the .onnx file once.
  2. Expose its true input/output names & shapes (Step 2 of Phase 1 —
     never guess this, always inspect it).
  3. Run inference on a single segment and return a spoof-probability score.
"""

from pathlib import Path
from typing import Any, Dict

import numpy as np
import onnxruntime as ort

import _pathfix  # noqa: F401
import config


class AasistOnnxModel:
    def __init__(self, model_path: str | Path = config.MODEL_PATH):
        model_path = Path(model_path)
        if not model_path.exists():
            raise FileNotFoundError(
                f"AASIST-L ONNX model not found at {model_path}. "
                f"Place the pretrained model at models/aasist-l.onnx."
            )

        # CPU by default for reproducibility. Swap providers list if a GPU
        # is available and you want to speed up batch evaluation.
        self.session = ort.InferenceSession(
            str(model_path), providers=["CPUExecutionProvider"]
        )

        self._input_meta = self.session.get_inputs()[0]
        self._output_meta = self.session.get_outputs()[0]

    def input_info(self) -> Dict[str, Any]:
        """Return the model's true input name/shape/dtype — inspect before trusting config.py."""
        return {
            "name": self._input_meta.name,
            "shape": self._input_meta.shape,
            "type": self._input_meta.type,
        }

    def output_info(self) -> Dict[str, Any]:
        """Return the model's true output name/shape/dtype."""
        return {
            "name": self._output_meta.name,
            "shape": self._output_meta.shape,
            "type": self._output_meta.type,
        }

    def predict_segment(self, segment: np.ndarray) -> float:
        """
        Run inference on a single audio segment.

        Args:
            segment: 1D float32 waveform of the expected input length.

        Returns:
            A single float score. Convention used here: higher score =
            more likely SPOOF. Confirm this convention against the actual
            model outputs/labels during Step 2 — some AASIST checkpoints
            output [bonafide_logit, spoof_logit] and need a softmax + index
            pick rather than a raw single score. Adjust this method once
            verified.
        """
        # Most ONNX AASIST exports expect shape (batch, samples).
        input_array = segment.astype(np.float32)[np.newaxis, :]

        input_name = self._input_meta.name
        output_name = self._output_meta.name

        result = self.session.run([output_name], {input_name: input_array})[0]
        raw = np.asarray(result).squeeze()

        if raw.ndim == 0:
            # Single scalar output.
            score = float(raw)
        elif raw.ndim == 1 and raw.shape[0] == 2:
            # [bonafide_logit, spoof_logit] style output -> softmax -> spoof prob.
            exp = np.exp(raw - np.max(raw))
            probs = exp / exp.sum()
            score = float(probs[1])
        else:
            # Fallback: take the max value. Flag for manual review.
            score = float(np.max(raw))

        return score


if __name__ == "__main__":
    model = AasistOnnxModel()
    print("Input info: ", model.input_info())
    print("Output info:", model.output_info())
