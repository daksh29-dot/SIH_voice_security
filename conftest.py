"""
Root conftest.py — ensures both the project root (for config.py) and
src/ (for the pipeline modules) are importable from tests without
needing an installed package.
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
SRC = ROOT / "src"

for p in (str(ROOT), str(SRC)):
    if p not in sys.path:
        sys.path.insert(0, p)
