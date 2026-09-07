"""
_pathfix.py

Ensures the project root (which holds config.py) is on sys.path.
Import this before `import config` in any src/ module so that:
  - `python src/foo.py` (direct run) works
  - `python main.py ...` (which already adds src/ itself) still works
  - pytest (via root conftest.py) still works

This keeps each module runnable standalone for quick manual testing,
per the file-by-file usage shown in the README.
"""

import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parent.parent
_SRC = Path(__file__).resolve().parent
for _p in (str(_ROOT), str(_SRC)):
    if _p not in sys.path:
        sys.path.insert(0, _p)
