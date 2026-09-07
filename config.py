"""
Central configuration for the voice-security Phase 1 pipeline.

Keep every tunable value here so experiments (aggregation strategy,
segment length, threshold, etc.) don't require hunting through code.
"""

from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent

MODEL_PATH = PROJECT_ROOT / "models" / "aasist-l.onnx"

TEST_AUDIO_DIR = PROJECT_ROOT / "test_audio"
REAL_AUDIO_DIR = TEST_AUDIO_DIR / "real"
SPOOF_AUDIO_DIR = TEST_AUDIO_DIR / "spoof"

RESULTS_DIR = PROJECT_ROOT / "results"
PREDICTIONS_CSV = RESULTS_DIR / "predictions.csv"
METRICS_JSON = RESULTS_DIR / "metrics.json"

# ---------------------------------------------------------------------------
# Audio preprocessing
# ---------------------------------------------------------------------------
# NOTE: TARGET_SAMPLE_RATE must match whatever the ONNX model actually
# expects. Verify this with tests/test_model.py (Step 2 of Phase 1) before
# trusting this value — 16000 Hz is the common AASIST default, but confirm.
TARGET_SAMPLE_RATE = 16000
FORCE_MONO = True
# ---------------------------------------------------------------------------
# Windowing
# ---------------------------------------------------------------------------
# AASIST-L's ONNX export has a FIXED input length — confirmed via
# inspect-model: input shape is ('batch', 64600). Not a tunable value.
FIXED_WINDOW_SAMPLES = 64600

# Upstream clovaai/aasist eval convention: audio >= 64600 -> first 64600
# samples; audio < 64600 -> tile-repeat to fill. Keep False for baseline.
USE_SLIDING_WINDOWS = False
SEGMENT_OVERLAP_SECONDS = 0.0

# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
# Only relevant when USE_SLIDING_WINDOWS = True.
# One of: "mean", "median", "weighted_mean", "top_k", "majority_vote"
AGGREGATION_STRATEGY = "mean"
TOP_K = 3

# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------
# Model outputs logits[:, 1] = bona fide (higher = more real). aasist_onnx.py
# converts this to a spoof probability so "higher = more spoof-like" holds
# throughout the pipeline.
SPOOF_THRESHOLD = 0.5
UNCERTAIN_MARGIN = 0.05
# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
RANDOM_SEED = 42
