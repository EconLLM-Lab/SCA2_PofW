"""Scoring plan for the 64 bank-2 adapters: what is scored, under which run id, and what is left.

Everything that decides the scoring run lives here and in score_plan_pins.json (spec hashes), so
the VM and the laptop cannot drift apart. Resume reads the Hub listing, never the local disk.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path

import factorial as F

HERE = Path(__file__).resolve().parent
POOL = HERE / "heldout" / "pool_skeleton.csv"
PINS = HERE / "score_plan_pins.json"
ARTIFACTS_REPO = "Bonorinoa/SCA2-paper-b-artifacts"
# Adapter-repo commit that holds all 64 profile adapters and the r1 replicate (2026-10-16).
ADAPTER_REVISION = "902f262e92bea5450f69335aa3977f28319ff3a1"
STAMP = "20261016"

# kind "adapter": base + 64 adapters through score_cohort --model-only.
# kind "signprompt": base model with the sign prompt for each of the 64 cells (no adapter).
CONDITIONS = {
    "strict_v1": {"run_id": f"bank2-strict-v1-{STAMP}", "battery": "strict", "variant": "v1", "kind": "adapter"},
    "heldout_v1": {"run_id": f"bank2-heldout-v1-{STAMP}", "battery": "heldout", "variant": "v1", "kind": "adapter"},
    "heldout_reverse": {"run_id": f"bank2-heldout-reverse-{STAMP}", "battery": "heldout",
                        "variant": "reverse_options", "kind": "adapter"},
    "heldout_para_a": {"run_id": f"bank2-heldout-para-a-{STAMP}", "battery": "heldout",
                       "variant": "paraphrase_a", "kind": "adapter"},
    "heldout_para_b": {"run_id": f"bank2-heldout-para-b-{STAMP}", "battery": "heldout",
                       "variant": "paraphrase_b", "kind": "adapter"},
    "signprompt_heldout_v1": {"run_id": f"bank2-signprompt-heldout-v1-{STAMP}", "battery": "heldout",
                              "variant": "v1", "kind": "signprompt"},
}
# Priority order of a launch: the preregistered primary first, sensitivity arms after it.
ORDER = ["strict_v1", "heldout_v1", "signprompt_heldout_v1", "heldout_reverse", "heldout_para_a", "heldout_para_b"]


def units_for_half(half: str) -> list[str]:
    units = F.all_units()
    if half not in ("A", "B"):
        raise ValueError(f"half must be A or B, got {half!r}")
    return units[:32] if half == "A" else units[32:]


def scores_base(half: str) -> bool:
    return half == "A"


def _present(run_id: str, files, model: str) -> bool:
    fs = set(files)
    return (f"runs/{run_id}/synthetic/{model}_option_probabilities.csv" in fs
            and f"runs/{run_id}/manifests/{model}_manifest.json" in fs)


def todo_units(run_id: str, half: str, hub_files) -> dict:
    """Units of this half still missing a verified CSV + manifest on the Hub."""
    todo = [u for u in units_for_half(half) if not _present(run_id, hub_files, f"{u}_adapter")]
    return {"units": todo, "base": bool(scores_base(half) and not _present(run_id, hub_files, "base"))}


def score_cohort_args(run_id: str, spec_path: str, marker: str, todo: dict) -> list[str]:
    """Arguments for score_cohort --model-only, or [] when nothing is left to score."""
    arms = (["base"] if todo["base"] else []) + (["adapter"] if todo["units"] else [])
    if not arms:
        return []
    args = ["--model-only", "--spec-file", str(spec_path), "--run-id", run_id, "--gate-marker", marker,
            "--adapter-revision", ADAPTER_REVISION, "--artifact-repo", ARTIFACTS_REPO, "--arms", ",".join(arms)]
    if todo["units"]:
        args += ["--countries", *todo["units"]]
    return args


def heldout_items() -> list[str]:
    with POOL.open(newline="") as fh:
        return [r["Question"] for r in csv.DictReader(fh)]


def build_spec(name: str) -> dict:
    import eval_lib as L
    from build_scoring_spec import build_scoring_spec
    c = CONDITIONS[name]
    if c["battery"] == "heldout":
        qmap = L.load_question_map(str(POOL))
        return build_scoring_spec(qmap, numeric_support={}, battery="heldout", prompt_variant=c["variant"],
                                  heldout_items=heldout_items())
    return build_scoring_spec(L.load_question_map(), numeric_support={}, battery="strict",
                              prompt_variant=c["variant"])


def spec_hash(spec: dict) -> str:
    from build_scoring_spec import spec_sha256
    return spec_sha256(spec)


def write_pins() -> dict:
    pins = {"adapter_revision": ADAPTER_REVISION,
            "spec_sha256": {n: spec_hash(build_spec(n)) for n in CONDITIONS}}
    PINS.write_text(json.dumps(pins, indent=2) + "\n")
    return pins


if __name__ == "__main__":
    print(json.dumps(write_pins(), indent=2))
