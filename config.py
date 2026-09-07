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
# Segmentation
# ---------------------------------------------------------------------------
# Window length in seconds for each segment fed to the model.
SEGMENT_LENGTH_SECONDS = 4.0
# Overlap between consecutive windows, in seconds (0.0 = no overlap).
SEGMENT_OVERLAP_SECONDS = 0.0
# If the total audio is shorter than one segment, pad instead of dropping it.
PAD_SHORT_AUDIO = True

# ---------------------------------------------------------------------------
# Aggregation
# ---------------------------------------------------------------------------
# One of: "mean", "median", "weighted_mean", "top_k", "majority_vote"
AGGREGATION_STRATEGY = "mean"
TOP_K = 3  # used only when AGGREGATION_STRATEGY == "top_k"

# ---------------------------------------------------------------------------
# Decision
# ---------------------------------------------------------------------------
# Placeholder threshold — Step 5/6 of Phase 1 replaces this with a value
# derived from the validation set (e.g. via EER or precision/recall tradeoff).
SPOOF_THRESHOLD = 0.5
# Scores within this band of the threshold are reported as UNCERTAIN rather
# than forced into REAL/SPOOF. Set to 0.0 to disable the uncertain band.
UNCERTAIN_MARGIN = 0.05

# ---------------------------------------------------------------------------
# Misc
# ---------------------------------------------------------------------------
RANDOM_SEED = 42
