"""
model.py

Wav2Vec2-based deepfake voice detector using a HuggingFace pretrained model.

    waveform -> Wav2Vec2 Feature Extractor -> Wav2Vec2ForSequenceClassification -> score

This replaces the AASIST-L ONNX wrapper. The Wav2Vec2 model was trained on
diverse real-world data (human recordings + AI-generated audio from ElevenLabs,
Amazon Polly, Google TTS, etc.) and generalizes well to browser microphone input,
unlike AASIST-L which only worked on ASVspoof2019-style recordings.

Model: garystafford/wav2vec2-deepfake-voice-detector
"""

from pathlib import Path
from typing import Any, Dict

import numpy as np
import torch
from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

import _pathfix  # noqa: F401
import config


class Wav2Vec2SpoofDetector:
    """
    Wraps the HuggingFace Wav2Vec2 deepfake voice detector.

    Exposes the same `predict_segment(segment)` interface as the old
    AasistOnnxModel so nothing else in the pipeline needs to change.
    """

    def __init__(self, model_name: str = config.MODEL_NAME):
        self.device = "cuda" if torch.cuda.is_available() else "cpu"

        print(f"[*] Loading model from HuggingFace: {model_name}")
        print(f"[*] Using device: {self.device}")

        # Set optimal CPU threads for lightning-fast inference
        if self.device == "cpu":
            import os
            num_threads = min(8, max(2, os.cpu_count() or 4))
            torch.set_num_threads(num_threads)

        self.feature_extractor = AutoFeatureExtractor.from_pretrained(model_name)
        self.model = AutoModelForAudioClassification.from_pretrained(model_name)
        self.model.eval().to(self.device)

        # Get label mapping from model config
        self._id2label = self.model.config.id2label
        print(f"[*] Labels: {self._id2label}")

        # Pre-warmup model on dummy input for instant first-time response
        try:
            dummy = np.zeros(config.TARGET_SAMPLE_RATE * 2, dtype=np.float32)
            self.predict_segment(dummy)
            print("[*] Model warmed up and ready for lightning-fast inference.")
        except Exception:
            pass

    def input_info(self) -> Dict[str, Any]:
        """Return model input information for compatibility."""
        return {
            "name": "wav2vec2",
            "shape": ["batch", "variable_length"],
            "type": "float32",
            "sample_rate": self.feature_extractor.sampling_rate,
        }

    def output_info(self) -> Dict[str, Any]:
        """Return model output information for compatibility."""
        return {
            "name": "logits",
            "shape": ["batch", len(self._id2label)],
            "type": "float32",
            "labels": self._id2label,
        }

    @torch.inference_mode()
    def predict_segment(self, segment: np.ndarray) -> float:
        """
        Run lightning-fast inference on a single audio segment.
        """
        # Optimize length for real-time responsiveness (cap at 3.5s max per segment)
        max_samples = int(config.TARGET_SAMPLE_RATE * 3.5)
        if len(segment) > max_samples:
            waveform = segment[:max_samples].astype(np.float32)
        else:
            waveform = segment.astype(np.float32)

        # Extract features
        inputs = self.feature_extractor(
            waveform,
            sampling_rate=config.TARGET_SAMPLE_RATE,
            return_tensors="pt",
            padding=False,
        )
        input_values = inputs.input_values.to(self.device)

        # Run inference
        logits = self.model(input_values).logits
        probs = torch.nn.functional.softmax(logits, dim=-1)
        probs = probs.squeeze().cpu().numpy()

        # Find the spoof/fake label index
        spoof_idx = None
        for idx, label in self._id2label.items():
            label_lower = str(label).lower()
            if label_lower in ("spoof", "fake", "deepfake", "synthetic", "ai"):
                spoof_idx = int(idx)
                break

        if spoof_idx is not None:
            return float(probs[spoof_idx])

        if len(probs) == 2:
            return float(probs[1])

        raise ValueError(
            f"Cannot determine spoof class from model labels: {self._id2label}"
        )


if __name__ == "__main__":
    model = Wav2Vec2SpoofDetector()
    print("Input info: ", model.input_info())
    print("Output info:", model.output_info())
