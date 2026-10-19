#!/usr/bin/env python3
"""Readout robustness (preregistration section 8): rebuild the probe selection under each readout variant.

For each variant run (reversed options, paraphrase A, paraphrase B), build the spec-checked items table from the
variant's Hub scores (`build_probe_input.py`) and run the preregistered selection on it (`probe_select.py`). The
outputs land in `planning/sprint_2026-10-11/paper-b-tier1/results/robustness/`, where
`paper_b/build_numbers_table.py` reads them and compares each with the frozen selection
(`selection_amended_20261016.csv`). The counts themselves are computed by the numbers-table builder, not here.

Model-side only: no human data is read. Each variant must carry its own pinned spec hash
(`paper_b/score_plan_pins.json`); a run whose manifests do not match is refused by `build_probe_input.py`.
An existing selection file is kept (resume); delete it to rebuild. The Hub token comes from `HF_TOKEN`.

usage: python paper_b/heldout/readout_robustness.py [--go]   (without --go it prints the plan)
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
OUT = REPO / "planning/sprint_2026-10-11/paper-b-tier1/results/robustness"
PINS = json.loads((REPO / "paper_b/score_plan_pins.json").read_text())["spec_sha256"]
VARIANTS = [("heldout_reverse", "bank2-heldout-reverse-20261016"),
            ("heldout_para_a", "bank2-heldout-para-a-20261016"),
            ("heldout_para_b", "bank2-heldout-para-b-20261016")]


def _run(*args: str) -> None:
    subprocess.run([sys.executable, *args], cwd=REPO, check=True)


def selection_for(name: str, run_id: str) -> Path:
    items, sel = OUT / f"items_{name}.csv", OUT / f"selection_{name}.csv"
    if sel.is_file():
        print(f"{name}: {sel.relative_to(REPO)} exists, kept")
        return sel
    _run("paper_b/heldout/build_probe_input.py", "--run-id", run_id, "--spec-sha", PINS[name], "--out", str(items))
    _run("paper_b/heldout/probe_select.py", "--items", str(items), "--out", str(sel))
    return sel


def main(argv: list[str] | None = None) -> int:
    go = "--go" in (sys.argv[1:] if argv is None else argv)
    for name, run_id in VARIANTS:
        print(f"{name}: run {run_id}, spec {PINS[name][:12]}")
    if not go:
        print("plan only; pass --go to build the missing selections")
        return 0
    if not os.environ.get("HF_TOKEN"):
        raise SystemExit("HF_TOKEN is not set")
    OUT.mkdir(parents=True, exist_ok=True)
    for name, run_id in VARIANTS:
        selection_for(name, run_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
