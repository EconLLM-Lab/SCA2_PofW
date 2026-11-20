#!/usr/bin/env python3
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
CELLS = ROOT / "_cells"
OUT = ROOT / "evaluation.ipynb"

nb = {
    "nbformat": 4,
    "nbformat_minor": 5,
    "metadata": {
        "kernelspec": {"display_name": "Python 3", "language": "python", "name": "python3"},
        "language_info": {"name": "python", "pygments_lexer": "ipython3"},
    },
    "cells": [],
}
for path in sorted(CELLS.iterdir()):
    if path.name.startswith("."):
        continue
    if path.suffix == ".md":
        nb["cells"].append({"cell_type": "markdown", "metadata": {}, "source": path.read_text().splitlines(True)})
    elif path.suffix == ".py":
        nb["cells"].append({"cell_type": "code", "metadata": {}, "execution_count": None, "outputs": [], "source": path.read_text().splitlines(True)})
    else:
        raise SystemExit(f"unexpected cell file {path}")

OUT.write_text(json.dumps(nb, indent=1) + "\n")
print(f"wrote {OUT} cells={len(nb['cells'])}")
