"""Import setup shared by the relocated held-out tests."""

from __future__ import annotations

import sys
from pathlib import Path


HELDOUT_DIR = Path(__file__).resolve().parents[1]
PAPER_B_DIR = HELDOUT_DIR.parent

for path in (PAPER_B_DIR, HELDOUT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
