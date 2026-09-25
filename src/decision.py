from enum import Enum

class Decision(str, Enum):
    REAL = "real"
    SPOOF = "spoof"
    UNCERTAIN = "uncertain"

def decide(score, real_below, spoof_above):
    if not 0 <= real_below < spoof_above <= 1:
        raise ValueError("Expected ordered calibrated thresholds")
    if score is None:
        return Decision.UNCERTAIN
    if not 0 <= score <= 1:
        raise ValueError("Invalid score")
    if score < real_below:
        return Decision.REAL
    if score > spoof_above:
        return Decision.SPOOF
    return Decision.UNCERTAIN
