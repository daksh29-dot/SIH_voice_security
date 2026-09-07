"""
decision.py

Converts a final aggregated score into a REAL / SPOOF / UNCERTAIN label.

Uses a configurable threshold (config.SPOOF_THRESHOLD) plus an optional
uncertainty margin around it, rather than blindly assuming 0.5 = fake.
The actual threshold should be derived from validation data (Step 5/6).
"""

from enum import Enum

import _pathfix  # noqa: F401
import config


class Decision(str, Enum):
    REAL = "REAL"
    SPOOF = "SPOOF"
    UNCERTAIN = "UNCERTAIN"


def decide(
    score: float,
    threshold: float = config.SPOOF_THRESHOLD,
    uncertain_margin: float = config.UNCERTAIN_MARGIN,
) -> Decision:
    """
    Args:
        score: aggregated spoof-probability score in [0, 1] (higher = more spoof-like).
        threshold: decision boundary between REAL and SPOOF.
        uncertain_margin: half-width of the band around `threshold` that is
            reported as UNCERTAIN instead of forced to REAL/SPOOF. Set to 0
            to disable and always return a hard REAL/SPOOF label.

    Returns:
        Decision.REAL, Decision.SPOOF, or Decision.UNCERTAIN
    """
    lower = threshold - uncertain_margin
    upper = threshold + uncertain_margin

    if uncertain_margin > 0 and lower <= score <= upper:
        return Decision.UNCERTAIN
    return Decision.SPOOF if score >= threshold else Decision.REAL


if __name__ == "__main__":
    for s in [0.1, 0.48, 0.5, 0.52, 0.9]:
        print(f"score={s:.2f} -> {decide(s).value}")
