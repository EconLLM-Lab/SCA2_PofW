"""Import setup shared by the relocated Paper B tests."""

from __future__ import annotations

import sys
from pathlib import Path


PAPER_B_DIR = Path(__file__).resolve().parents[1]
HELDOUT_DIR = PAPER_B_DIR / "heldout"

for path in (PAPER_B_DIR, HELDOUT_DIR):
    if str(path) not in sys.path:
        sys.path.insert(0, str(path))
