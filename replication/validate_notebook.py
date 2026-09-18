#!/usr/bin/env python3
import json
from pathlib import Path

nb = json.loads(Path(__file__).with_name("evaluation.ipynb").read_text())
assert nb["nbformat"] == 4
assert len(nb["cells"]) == 3
text = Path(__file__).with_name("evaluation.ipynb").read_text()
assert "/Users/" not in text
assert "Tier A" in text
print("ok", len(nb["cells"]), "cells")
