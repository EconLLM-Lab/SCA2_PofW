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
CONDITIONS: dict[str, dict] = {
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

# Card T4 (2026-10-18). The replicate is the unseeded retrain of one profile unit; it is banked at
# bank2/<bank run>/replicates/r1/profiles/<unit> in the adapter repo (found by listing that prefix, 2026-10-17).
REPLICATE_TAG = "r1"
REPLICATE_UNIT = "P_1_0_1_1_0_1"
GATE_RUN_ID_T4 = "gate-bank2-replicate-r1-20261018"
# "units" names the cells a condition scores on its own: all 64, or exactly these.
CONDITIONS.update({
    "signprompt_strict_v1": {"run_id": "bank2-signprompt-strict-v1-20261018", "battery": "strict",
                             "variant": "v1", "kind": "signprompt", "units": "all64"},
    "replicate_strict_v1": {"run_id": "bank2-replicate-r1-strict-v1-20261018", "battery": "strict",
                            "variant": "v1", "kind": "adapter", "units": [REPLICATE_UNIT],
                            "replicate": REPLICATE_TAG},
    "replicate_heldout_v1": {"run_id": "bank2-replicate-r1-heldout-v1-20261018", "battery": "heldout",
                             "variant": "v1", "kind": "adapter", "units": [REPLICATE_UNIT],
                             "replicate": REPLICATE_TAG},
})
# Launch order of the T4 session: the cheap single-unit replicate scores first, then the 64-cell sign-prompt cell.
T4_ORDER = ["replicate_strict_v1", "replicate_heldout_v1", "signprompt_strict_v1"]
# Priority order of a launch: the preregistered primary first, sensitivity arms after it.
ORDER = ["strict_v1", "heldout_v1", "signprompt_heldout_v1", "heldout_reverse", "heldout_para_a", "heldout_para_b"]


def units_for_half(half: str) -> list[str]:
    units = F.all_units()
    if half not in ("A", "B"):
        raise ValueError(f"half must be A or B, got {half!r}")
    return units[:32] if half == "A" else units[32:]


def gate_unit(half: str) -> str:
    """The unit this half's VM gates: always one the half itself will score."""
    return units_for_half(half)[-1]


def check_marker(marker: dict, half: str) -> None:
    """Refuse a gate marker that does not cover this half or this adapter revision."""
    if not marker.get("gate_pass"):
        raise RuntimeError("gate marker says gate_pass=false")
    if marker.get("unit") not in units_for_half(half):
        raise RuntimeError(f"gate marker unit {marker.get('unit')!r} is not in half {half}")
    if marker.get("adapter_revision") != ADAPTER_REVISION:
        raise RuntimeError(f"gate marker adapter revision {marker.get('adapter_revision')!r} is not the pinned {ADAPTER_REVISION}")


def scores_base(half: str) -> bool:
    return half == "A"


def _present(run_id: str, files, model: str, spec_sha: str | None = None, read_manifest=None) -> bool:
    """A scored model counts as done only with its CSV and its manifest, and — when a spec hash is given —
    only if the manifest records that same spec.

    The spec check is not decoration: `heldout_v1` and the other pool conditions keep their run id across an
    amendment, so a name-only resume would silently keep scores produced from the superseded item wording.
    """
    fs = set(files)
    csv_name = f"runs/{run_id}/synthetic/{model}_option_probabilities.csv"
    man_name = f"runs/{run_id}/manifests/{model}_manifest.json"
    if csv_name not in fs or man_name not in fs:
        return False
    if spec_sha is None:
        return True
    if read_manifest is None:
        raise ValueError("spec_sha was given, so a manifest reader is required")
    recorded = (read_manifest(run_id, model) or {}).get("spec_sha256")
    return bool(recorded) and recorded == spec_sha


def todo_units(run_id: str, half: str, hub_files, spec_sha: str | None = None,
               read_manifest=None) -> dict:
    """Units of this half still missing a verified CSV + manifest for THIS spec."""
    if spec_sha is not None and read_manifest is None:      # fail fast: a missing reader is a programming error
        raise ValueError("spec_sha was given, so a manifest reader is required")
    todo = [u for u in units_for_half(half)
            if not _present(run_id, hub_files, f"{u}_adapter", spec_sha, read_manifest)]
    return {"units": todo,
            "base": bool(scores_base(half) and not _present(run_id, hub_files, "base", spec_sha, read_manifest))}


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


def condition_units(name: str) -> list[str]:
    """Cells a T4 condition scores by itself. Half-split conditions have no list and raise."""
    units = CONDITIONS[name].get("units")
    if units is None:
        raise ValueError(f"{name} is scored per half (units_for_half), it has no unit list of its own")
    return F.all_units() if units == "all64" else list(units)


def condition_env(name: str) -> dict:
    """Extra environment for a condition's driver. The replicate switch is the only one: it moves the Hub
    prefix and the local adapter directory to replicates/<tag>, so the original adapters are never read."""
    rep = CONDITIONS[name].get("replicate")
    return {"SCA2_PB_REPLICATE": rep} if rep else {}


def todo_condition(name: str, hub_files, spec_sha: str, read_manifest) -> list[str]:
    """Units of a T4 condition still missing a CSV + manifest recorded under THIS spec (the Hub is the store)."""
    if read_manifest is None:
        raise ValueError("a manifest reader is required: a name-only resume would keep superseded scores")
    c = CONDITIONS[name]
    suffix = "_adapter" if c["kind"] == "adapter" else ""
    return [u for u in condition_units(name)
            if not _present(c["run_id"], hub_files, f"{u}{suffix}", spec_sha, read_manifest)]


def check_marker_for(name: str, marker: dict, replicate_adapter_sha: str | None = None) -> None:
    """Refuse a gate marker that does not authorise this T4 condition.

    A replicate condition scores weights the original run never saw, so the marker must carry the SHA-256 of
    those exact weights; a marker produced for the original unit has the same unit name and would pass any
    check that looked at the name alone. The sign-prompt cell loads no adapter: it needs a passed gate on
    this stack, at the pinned revision, for a real unit.
    """
    c = CONDITIONS[name]
    if not marker.get("gate_pass"):
        raise RuntimeError("gate marker says gate_pass=false")
    if marker.get("adapter_revision") != ADAPTER_REVISION:
        raise RuntimeError(f"gate marker adapter revision {marker.get('adapter_revision')!r} is not the pinned {ADAPTER_REVISION}")
    if marker.get("unit") not in condition_units(name) and not (
            c["kind"] == "signprompt" and marker.get("unit") in F.all_units()):
        raise RuntimeError(f"gate marker unit {marker.get('unit')!r} is outside {name}")
    if c.get("replicate"):
        if not replicate_adapter_sha:
            raise RuntimeError(f"{name}: no replicate adapter SHA-256 to compare the marker against")
        if marker.get("adapter_sha256") != replicate_adapter_sha:
            raise RuntimeError(f"{name}: gate marker was made on different weights than the replicate adapter")


def t4_steps() -> list[tuple[str, list[str], dict]]:
    """The detached chain for the T4 session: gate the replicate adapter, then score each condition."""
    gate_env = {"GATE_UNIT": REPLICATE_UNIT, "SCA2_PB_ADAPTER_REVISION": ADAPTER_REVISION,
                "SCORE_RUN_ID": GATE_RUN_ID_T4, "SCA2_PB_REPLICATE": REPLICATE_TAG}
    steps = [("t4_gate", ["paper_b/colab/vm_gate_factorial.py"], gate_env)]
    for name in T4_ORDER:
        steps.append((f"t4_{name}", ["paper_b/colab/vm_score_t4.py", name], condition_env(name)))
    return steps


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
