"""
inference.py

Runs the full single-file pipeline:

    Audio -> Preprocessing -> Segmentation -> AASIST-L -> Scores

This module produces per-segment scores plus an aggregated final score and
decision. It's the piece both main.py (single file, CLI/demo use) and the
batch evaluation script build on top of.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

import _pathfix  # noqa: F401
import config
from audio_preprocessing import preprocess_audio
from segment_audio import segment_waveform
from model import Wav2Vec2SpoofDetector
from aggregation import aggregate
from decision import decide, Decision


@dataclass
class InferenceResult:
    file_path: str
    segment_scores: List[float] = field(default_factory=list)
    aggregated_score: float = 0.0
    decision: Decision = Decision.UNCERTAIN


class VoiceSpoofDetector:
    """
    High-level pipeline object. Loads the model once, then can process
    any number of audio files via `analyze()`.
    """

    def __init__(self, model_name: str = config.MODEL_NAME):
        self.model = Wav2Vec2SpoofDetector(model_name)

    def analyze(self, audio_path: str | Path) -> InferenceResult:
        audio_path = str(audio_path)

        waveform = preprocess_audio(audio_path)
        segments = segment_waveform(waveform)

        if not segments:
            raise ValueError(
                f"No segments produced for {audio_path} — audio may be empty "
                f"or shorter than expected even after padding."
            )

        scores = [self.model.predict_segment(seg) for seg in segments]
        agg_score = aggregate(scores)
        label = decide(agg_score)

        return InferenceResult(
            file_path=audio_path,
            segment_scores=scores,
            aggregated_score=agg_score,
            decision=label,
        )


if __name__ == "__main__":
    import sys

    if len(sys.argv) != 2:
        print("Usage: python inference.py <path_to_audio>")
        sys.exit(1)

    detector = VoiceSpoofDetector()
    result = detector.analyze(sys.argv[1])

    print(f"File:            {result.file_path}")
    print(f"Segment scores:  {[f'{s:.4f}' for s in result.segment_scores]}")
    print(f"Aggregated score:{result.aggregated_score:.4f}")
    print(f"Decision:        {result.decision.value}")
