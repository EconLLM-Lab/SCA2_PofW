# Paper B Tier 1 implementation plan — factorial compiler design, blinded item screen, readout-robustness variants, human ceiling

> **Record, not status.** Written 2026-10-14. Lines about what is done, blocked or next describe that date, not today. Current status: [STATUS.md](../../STATUS.md). Implemented 2026-10-14 to 10-18. Moved here from the gitignored `.hermes/plans/` on 2026-10-19.

> **For Hermes:** Use the `subagent-driven-development` skill to implement this task-by-task.
> Every task below is self-contained: exact paths, complete code, exact commands, expected output.
> Do **not** edit the manuscript (`main.tex`, `planning/*.tex`) and do not rewrite the paper. This
> plan produces code, artifacts, preregistration files, and numeric result tables only.

**Goal:** Implement and scientifically verify Tier 1 of Paper B — (1) a full 2^6 factorial of sign-bit
adapters on the second scenario bank, (2) a blinded probe-selected item screen against already-fielded
WVS wave-7 items with a human criterion, (3) readout-robustness variants, (4) a human test-retest
ceiling from WVS waves 6–7 — all reusing the existing frozen scorer and analysis stack.

**Architecture:** New units are *sign profiles*, not countries: 64 code strings `P_<b1>_..._<b6>` are
trained as 42-country cohort units are today, by generalising `paper_b/config.py`'s cohort constant and
the hub adapter path helper. Exactly one new service layer is added (`paper_b/factorial*.py`), plus a
held-out item pool built from WVS-7 `.dta` metadata and questionnaire text. Everything else is a
two-line generalisation of an existing module so the frozen readout, gates, caches, and persistence
paths stay byte-identical for cohort 1 and bank 2.

**Tech stack:** Python 3.12 (project venv `env -u PYTHONPATH .venv/bin/python`), pandas, numpy,
pyreadstat, pandas-plink-free ordinary least squares (`numpy.linalg.lstsq`), pytest; Colab CLI
(T4, `env -u PYTHONPATH -u VIRTUAL_ENV colab exec ...`); HuggingFace Hub (datasets:
`Bonorinoa/SCA2-paper-b-adapters`, `Bonorinoa/SCA2-paper-b-artifacts`).

---

## 0. Current context and assumptions

Read these before touching code.

| Fact | Where it lives |
|---|---|
| Frozen training protocol (model, LoRA, DPO, split, `TRAIN_FRAC=0.80`, `SEED=42`) | `paper_b/config.py` |
| Bank-2 protocol switch, fail-closed | `paper_b/protocol_bank2.py` (`SCA2_PB_PROTOCOL=bank2`, required `SCA2_PB_DATA_ROOT`, requires `n_triplets == 658`) |
| Decide-the-run runner (prepare → train → upload, resumable, per-wave manifests) | `paper_b/run_cohort.py`, `paper_b/train_country.py` |
| Frozen readout constants (768-token prompt, completion `" "`+code, T=1, no length normalisation, `ARCHIVE_CHAT_DATE="26 Jul 2024"`) | `paper_b/eval_config.py` |
| Prompt builder, option parsing, metrics | `paper_b/eval_lib.py` |
| Scorer + `--model-only` CLI + gate marker | `paper_b/score_cohort.py` |
| Revision pin, cache fingerprints, independent loader gate, HF persistence | `paper_b/score_runtime.py` |
| Spec builder, `STRICT_ITEMS` (23 items), `spec_sha256` | `paper_b/build_scoring_spec.py` |
| Sign-profile prompts and leak scanner | `paper_b/sign_prompt.py`, `paper_b/score_sign_profiles.py` |
| Composites, recodes, Spearman + profile-block bootstrap | `paper_b/analyze_surface.py`, `paper_b/analyze_phase.py` |
| Bank gates (shared bank, labels, row order, text scan) | `paper_b/verify_gates.py` |
| Bank-2 raw pairs being generated now | `synthetic_generation/outputs/bank2_20261014/raw/checkpoint_raw_pairs.jsonl` |
| Bank-2 relabel entry point | `synthetic_generation/sca2_datagen/relabel.py` (`export_sign_relabel`) |
| New survey files | `data/WVS/timeseries/WVS_Time_Series_1981-2022_stata_v5_0.dta`, `data/WVS/wave6/WV6_Data_stata_v20201117.dta`, `data/EVS/ZA7500_v5-0-0.dta`, `data/WVS/WVS_wave7.dta` |
| Human item means (23 + Q69–71, 42 countries) | `analysis/phase2/outputs/paper_a/human_item_means_42.csv`; recomputable by `analyze_surface.reproduce_human_item_means` |
| GPS z-vectors, 77 countries | `synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json` |
| WVS-7 respondent parquets (42 countries, 44 columns) | `data/wvs_eval_full/{CC}_WVS_wave7.parquet` |

**Work on branch `feat/paper-b-cohort`** (current branch, shared working tree — run
`git ls-remote origin main` and `git status -sb` before each commit batch).

**Blinding is a hard constraint.** `Z*P_heldout_human.csv` must not be read, printed, joined, or
summarised until `paper_b/heldout/FREEZE.json` exists. Finished already-unblinded artifacts
(`human_item_means_42.csv`, the 23 strict items) may be read freely.

## 0b. Decisions the human owner must confirm before Phase C/D spend (record answers in `planning/sprint_2026-10-11/PARENT_DECISIONS.md` as a dated amendment)

- **D1 — bank-2 size rule.** Bank 1 kept all 658 pairs including 56 that its diagnostic scorer
  marked failing. Bank 2 may land on a different count. Proposed amendment: the requirement becomes
  `640 ≤ n_triplets ≤ 660`, `≥ 100` triplets per dimension, labels identical to `sign_choice`,
  shared prompts identical across units — and **no padding or trimming**. The current hard
  `REQUIRED_TRIPLETS == 658` is wrong for bank 2 and will refuse a correct bank.
- **D2 — unit change.** C3's retrain becomes 64 sign-profile units on bank 2 instead of 42 countries.
- **D3 — comment/log 403s and one slow call with one timeout (~$2).** Serving capacity, not output.
- **D4 — held-out item pool scope.** Whole questionnaire minus the 35 already-mapped items, minus
  numeric-open, minus clearly nominal items; `ordinal` flagged per item by hand at review.
- **D5 — preregistration vehicle.** Public timestamped copy (OSF or an `anonymous.4open.science`
  snapshot of a hash-only dump) plus a git tag in this repo.

---

## Phase A — bank 2 becomes a trainable bank (no GPU)

### Task A1: add `--source-run-id` to the relabel CLI

**Objective:** stop bank 2 from inheriting bank 1's `source_run_id` (a provenance lie).

**Files:**
- Modify: `synthetic_generation/sca2_datagen/relabel.py` (`export_sign_relabel`, `build_parser`)
- Test: `synthetic_generation/tests/test_relabel.py`

**Step 1 — failing test.** Append to `synthetic_generation/tests/test_relabel.py`:

```python
def test_export_sign_relabel_honours_source_run_id(tmp_path):
    import json
    from pathlib import Path
    import sca2_datagen.relabel as R

    triplet = {
        "triplet_id": "t1", "prompt": "P", "facet": "f",
        "gps_dimension": "trust", "response_a": "A", "response_b": "B",
        "source_qc_status": "pass",
    }
    ck = tmp_path / "checkpoint_raw_pairs.jsonl"
    ck.write_text(json.dumps(triplet) + "\n")
    gps = tmp_path / "gps_z_vectors.json"
    gps.write_text(json.dumps({"USA": {"trust": 1.0, "risktaking": -1.0, "patience": 1.0,
                                       "altruism": -1.0, "posrecip": 1.0, "negrecip": -1.0}}))
    manifest = R.export_sign_relabel(checkpoint_path=ck, output_dir=tmp_path / "out",
                                     gps_json=gps, source_run_id="bank2_test_run")
    assert manifest["source_run_id"] == "bank2_test_run"
    assert manifest["n_triplets"] == 1
```

**Step 2 — verify failure.** `cd synthetic_generation && env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m pytest -q tests/test_relabel.py::test_export_sign_relabel_honours_source_run_id`
Expected: `TypeError: export_sign_relabel() got an unexpected keyword argument 'source_run_id'`.

**Step 3 — implement.** In `export_sign_relabel`, add the keyword and use it:

```python
def export_sign_relabel(
    *,
    checkpoint_path: Path,
    output_dir: Path,
    gps_json: Path | None = None,
    gps_dta: Path | None = None,
    source_run_id: str | None = None,
) -> dict[str, Any]:
```

then replace the two uses of the module global:

```python
    run_id = f"gps_sign_relabel_all_{export_time.strftime('%Y%m%d_%H%M%SZ')}"
    src_run_id = source_run_id or SOURCE_RUN_ID
```

and in the manifest block `"source_run_id": src_run_id,`, and in the labeled rows pass
`source_run_id=src_run_id` (change `label_triplet_for_country` to accept
`source_run_id: str | None = None` and use `source_run_id or SOURCE_RUN_ID` for its
`"source_run_id"` field). In `build_parser()` add:

```python
    parser.add_argument("--source-run-id", default=None,
                        help="provenance: the generation run that produced the checkpoint")
```

and pass `source_run_id=args.source_run_id` in `main()`.

**Step 4 — verify pass.** Same command. Expected: `1 passed`.
Then `env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m pytest -q tests/test_relabel.py`
Expected: all pass (no regression).

**Step 5 — commit.** `git add synthetic_generation/sca2_datagen/relabel.py synthetic_generation/tests/test_relabel.py && git commit -m "feat(datagen): export_sign_relabel accepts --source-run-id"`

### Task A2: generate the bank-2 relabel export

**Objective:** a 658-ish triplet bank labeled for every profile unit, on disk, verified.

**Step 1 — run relabel for the real GPS countries (unchanged behaviour) and, separately, for the
profile units (Phase B).** First the countries:

```bash
cd /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/synthetic_generation
env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m sca2_datagen.relabel \
  --checkpoint outputs/bank2_20261014/raw/checkpoint_raw_pairs.jsonl \
  --output-dir outputs/gps_sign_relabel_bank2 \
  --source-run-id "<the run id printed in outputs/bank2_20261014/raw/generation_manifest.json>"
```
Expected: `wrote D_syn_<CC>.jsonl` for each of the 77 GPS countries and a
`manifest.json` containing `n_triplets`, `per_dimension_triplet_counts`, `source_run_id`.

**Step 2 — record the count.** `python -c "import json;m=json.load(open('outputs/gps_sign_relabel_bank2/manifest.json'));print(m['n_triplets'], m['per_dimension_triplet_counts'])"`
Expected: an integer between 640 and 660, every dimension ≥ 100. **If it is outside that band, stop
and report; do not trim or pad (D1).**

**Step 3 — gate the bank.** From the repo root:

```bash
env -u PYTHONPATH .venv/bin/python - <<'PY'
import os, pathlib, sys
os.environ["SCA2_PB_PROTOCOL"] = "bank2"
os.environ["SCA2_PB_DATA_ROOT"] = "/tmp/pb_bank2_gate_root"
os.environ["SCA2_PB_BANK2_DIR"] = "synthetic_generation/outputs/gps_sign_relabel_bank2"
sys.path.insert(0, "paper_b"); import config as C, runpy
C.BANK_DIR = pathlib.Path(os.environ["SCA2_PB_BANK2_DIR"]); C.BANK_RUN_ID = "gate"
runpy.run_path("paper_b/verify_gates.py", run_name="__main__")
PY
```
(After Task B2 this uses the real manifest.) Expected: `ALL GATES PASS`, 5 gate lines, no `FAIL`.
Add `--scan-text` handling by appending it to `sys.argv` before `runpy` if you want the text scan.

**Step 4 — commit the small artifacts only.** `git add synthetic_generation/outputs/gps_sign_relabel_bank2/manifest.json` plus a short `README_BANK2.md` next to it describing counts, run ids, and the D1 band. Never commit `D_syn_*.jsonl` for bank 2 (large).

---

## Phase B — the 64-profile factorial layer (no GPU)

### Task B1: `paper_b/factorial.py` (design + bank builder)

**Objective:** one module that defines the 64 units, labels the bank for them, and writes their
`D_syn_<unit>.jsonl` files.

**Files:**
- Create: `paper_b/factorial.py`
- Test: `paper_b/test_factorial.py`

**Step 1 — failing test.** Create `paper_b/test_factorial.py`:

```python
"""CPU tests for the 2^6 sign-profile factorial design. No GPU, no network."""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "paper_b"))

import factorial as F  # noqa: E402


def test_dims_order_and_unit_count():
    assert F.DIMS == ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]
    assert len(F.all_units()) == 64
    assert len(set(F.all_units())) == 64
    assert F.all_units() == sorted(F.all_units())


def test_unit_roundtrip():
    u = "P_1_0_1_0_0_1"
    assert F.bits_of_unit(u) == (1, 0, 1, 0, 0, 1)
    assert F.unit_of_bits((1, 0, 1, 0, 0, 1)) == u
    assert F.z_vector(u) == {"trust": 1.0, "risktaking": -1.0, "patience": 1.0,
                             "altruism": -1.0, "posrecip": -1.0, "negrecip": 1.0}


def test_cohort_units_are_a_subset_of_the_factorial():
    cohort = F.cohort_units(
        ROOT / "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json")
    assert len(cohort) == 26
    assert set(cohort) <= set(F.all_units())


def test_flip_differs_in_exactly_one_bit():
    u = "P_1_1_0_0_1_0"
    v = F.flip(u, "patience")
    assert sum(a != b for a, b in zip(F.bits_of_unit(u), F.bits_of_unit(v))) == 1


def test_build_profile_bank_labels_match_sign_rule(tmp_path):
    bank = [{"triplet_id": "t1", "prompt": "P1", "facet": "f", "gps_dimension": "trust",
             "response_a": "A1", "response_b": "B1", "source_qc_status": "pass"},
            {"triplet_id": "t2", "prompt": "P2", "facet": "f", "gps_dimension": "patience",
             "response_a": "A2", "response_b": "B2", "source_qc_status": "pass"}]
    bpath = tmp_path / "triplets_bank.jsonl"
    bpath.write_text("\n".join(json.dumps(r) for r in bank) + "\n")
    out = tmp_path / "profiles"
    manifest = F.build_profile_bank(bpath, out, bank_run_id="bank2_test",
                                    source_run_id="gen_test", units=["P_1_1_1_1_1_1",
                                                                     "P_0_0_0_0_0_0"])
    assert manifest["units"] == ["P_0_0_0_0_0_0", "P_1_1_1_1_1_1"]
    for u in manifest["units"]:
        rows = [json.loads(l) for l in (out / f"D_syn_{u}.jsonl").read_text().splitlines()]
        assert len(rows) == 2
        for r in rows:
            z = r["gps_profile_vector"][r["gps_dimension"]]
            assert r["chosen_option"] == ("A" if z >= 0 else "B")
```

**Step 2 — verify failure.** `env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m pytest -q paper_b/test_factorial.py`
Expected: `ModuleNotFoundError: No module named 'factorial'`.

**Step 3 — implement `paper_b/factorial.py`:**

```python
"""Paper B — the 2^6 sign-profile factorial design.

A *unit* is one of the 64 possible sign vectors over the six GPS dimensions.
Unit codes are `P_<b_trust>_<b_risktaking>_<b_patience>_<b_altruism>_<b_posrecip>_<b_negrecip>`,
so a unit code is both a filesystem-safe token and the design cell itself. This
module only builds data; it never trains and never calls a model.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path
from typing import Iterable, Sequence

REPO = Path(__file__).resolve().parents[1]
if str(REPO / "synthetic_generation") not in sys.path:
    sys.path.insert(0, str(REPO / "synthetic_generation"))

from sca2_datagen.config import GPS_DIMENSIONS  # noqa: E402
from sca2_datagen.relabel import DIMS, label_triplet_for_country, write_jsonl  # noqa: E402

assert list(GPS_DIMENSIONS) == DIMS, "dimension order must match the generator"


def unit_of_bits(bits: Sequence[int]) -> str:
    if len(bits) != 6 or any(b not in (0, 1) for b in bits):
        raise ValueError(f"bits must be six 0/1 values, got {bits!r}")
    return "P_" + "_".join(str(int(b)) for b in bits)


def bits_of_unit(unit: str) -> tuple[int, ...]:
    parts = unit.split("_")
    if len(parts) != 7 or parts[0] != "P":
        raise ValueError(f"not a unit code: {unit!r}")
    return tuple(int(p) for p in parts[1:])


def all_units() -> list[str]:
    return [unit_of_bits(b) for b in itertools.product((0, 1), repeat=6)]


def z_vector(unit: str) -> dict[str, float]:
    return {d: (1.0 if b else -1.0) for d, b in zip(DIMS, bits_of_unit(unit))}


def flip(unit: str, dim: str) -> str:
    if dim not in DIMS:
        raise ValueError(f"unknown dimension {dim!r}")
    bits = list(bits_of_unit(unit))
    i = DIMS.index(dim)
    bits[i] = 1 - bits[i]
    return unit_of_bits(bits)


def cohort_units(gps_json: Path) -> list[str]:
    """The 64-cell subset that the 42 real cohort countries occupy (26 cells)."""
    raw = json.loads(Path(gps_json).read_text())
    units = set()
    for _, vec in raw.items():
        bits = tuple(1 if float(vec[d]) >= 0 else 0 for d in DIMS)
        units.add(unit_of_bits(bits))
    return sorted(units)


def unit_members(gps_json: Path, cohort: Sequence[str]) -> dict[str, list[str]]:
    raw = json.loads(Path(gps_json).read_text())
    out: dict[str, list[str]] = {}
    for cc in cohort:
        bits = tuple(1 if float(raw[cc][d]) >= 0 else 0 for d in DIMS)
        out.setdefault(unit_of_bits(bits), []).append(cc)
    return {u: sorted(v) for u, v in sorted(out.items())}


def build_profile_bank(triplets_bank: Path, out_dir: Path, *, bank_run_id: str,
                       source_run_id: str, units: Iterable[str] | None = None) -> dict:
    """Write D_syn_<unit>.jsonl for every unit. Chosen/rejected follow sign_choice."""
    from datetime import datetime, timezone

    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    triplets = [json.loads(l) for l in Path(triplets_bank).read_text().splitlines() if l.strip()]
    if not triplets:
        raise ValueError(f"empty triplet bank: {triplets_bank}")
    triplets.sort(key=lambda r: r["triplet_id"])
    units = sorted(units) if units else all_units()
    ts = datetime.now(timezone.utc).isoformat()
    per_unit_counts = {}
    for u in units:
        z = z_vector(u)
        rows = [label_triplet_for_country(t, u, z, run_id=bank_run_id,
                                          export_timestamp=ts) for t in triplets]
        for r in rows:
            r["source_run_id"] = source_run_id
            r["gps_profile_vector"] = {d: z[d] for d in DIMS}
        write_jsonl(rows, out_dir / f"D_syn_{u}.jsonl")
        per_unit_counts[u] = len(rows)
    dim_counts = {d: 0 for d in DIMS}
    for t in triplets:
        dim_counts[t["gps_dimension"]] += 1
    manifest = {
        "run_id": bank_run_id, "source_run_id": source_run_id,
        "source_triplets_bank": str(triplets_bank),
        "labeling_rule": "deterministic_sign",
        "n_triplets": len(triplets), "n_units": len(units), "units": units,
        "per_unit_counts": per_unit_counts, "per_dimension_triplet_counts": dim_counts,
        "notes": [
            "Unit codes are sign vectors, not countries; chosen=A iff z>=0 per dimension.",
            "Shared A/B bank is reused for every unit; only chosen/rejected are flipped.",
            "No model calls were made for this export.",
        ],
    }
    (out_dir / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest
```

**Step 4 — verify pass.** `env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m pytest -q paper_b/test_factorial.py`
Expected: `5 passed`.

**Step 5 — commit.** `git add paper_b/factorial.py paper_b/test_factorial.py && git commit -m "feat(paper_b): 2^6 sign-profile factorial design module"`

### Task B2: generalise the protocol switch for profile units

**Objective:** `SCA2_PB_UNITS=profiles` swaps `config.COHORT` for the 64 units and points the hub
prefix at `bank2/<run_id>/profiles`, failing closed on anything inconsistent.

**Files:**
- Modify: `paper_b/protocol_bank2.py`
- Modify: `paper_b/config.py` (`_maybe_apply_bank2` docstring; `N_TRAIN` helper)
- Test: `paper_b/test_bank2_ready.py` (extend)

**Step 1 — failing test.** Append to `paper_b/test_bank2_ready.py`:

```python
def test_profiles_switch_sets_cohort_and_prefix(tmp_path, monkeypatch):
    import json, importlib, os, sys
    monkeypatch.setenv("SCA2_PB_PROTOCOL", "bank2")
    monkeypatch.setenv("SCA2_PB_UNITS", "profiles")
    monkeypatch.setenv("SCA2_PB_DATA_ROOT", str(tmp_path / "root"))
    bank = tmp_path / "bank"
    bank.mkdir()
    (bank / "manifest.json").write_text(json.dumps({
        "run_id": "gps_sign_relabel_all_bank2_test", "labeling_rule": "deterministic_sign",
        "n_triplets": 655}))
    profiles = tmp_path / "profiles"
    profiles.mkdir()
    (profiles / "manifest.json").write_text(json.dumps({
        "run_id": "gps_sign_relabel_all_bank2_test", "n_triplets": 655,
        "units": [f"P_{i}" for i in range(64)]}))
    monkeypatch.setenv("SCA2_PB_BANK2_DIR", str(bank))
    monkeypatch.setenv("SCA2_PB_PROFILE_DIR", str(profiles))
    import config as C
    importlib.reload(C)
    assert C.N_ROWS == 655
    assert len(C.COHORT) == 64
    assert C.HF_ADAPTER_PREFIX == "bank2/gps_sign_relabel_all_bank2_test/profiles"
    assert C.hub_adapter_path("P_1_1_1_1_1_1") == "bank2/gps_sign_relabel_all_bank2_test/profiles/P_1_1_1_1_1_1"


def test_profiles_switch_refuses_bad_triplet_count(tmp_path, monkeypatch):
    import json, importlib
    monkeypatch.setenv("SCA2_PB_PROTOCOL", "bank2")
    monkeypatch.setenv("SCA2_PB_UNITS", "profiles")
    monkeypatch.setenv("SCA2_PB_DATA_ROOT", str(tmp_path / "root"))
    for name, n in (("bank", 600), ("profiles", 600)):
        d = tmp_path / name; d.mkdir()
        (d / "manifest.json").write_text(json.dumps({
            "run_id": "gps_sign_relabel_all_bank2_test",
            "labeling_rule": "deterministic_sign", "n_triplets": n,
            "units": ["P_0_0_0_0_0_0"]}))
    monkeypatch.setenv("SCA2_PB_BANK2_DIR", str(tmp_path / "bank"))
    monkeypatch.setenv("SCA2_PB_PROFILE_DIR", str(tmp_path / "profiles"))
    import config as C
    import pytest
    with pytest.raises(RuntimeError, match="640"):
        importlib.reload(C)
    monkeypatch.delenv("SCA2_PB_PROTOCOL")
    monkeypatch.delenv("SCA2_PB_UNITS")
    importlib.reload(C)
```

**Step 2 — verify failure.** `env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m pytest -q paper_b/test_bank2_ready.py`
Expected: the new tests fail on `N_ROWS == 655` / missing `SCA2_PB_UNITS` handling.

**Step 3 — implement.** In `paper_b/protocol_bank2.py`: replace `REQUIRED_TRIPLETS = 658` with

```python
MIN_TRIPLETS = 640
MAX_TRIPLETS = 660
MIN_PER_DIMENSION = 100
COHORT1_TRIPLETS = 658
```

and rewrite the validation body of `apply()` to:

```python
def _load_manifest(path: Path) -> dict:
    if not path.is_file():
        raise RuntimeError(f"bank manifest missing: {path}")
    manifest = json.loads(path.read_text())
    if manifest.get("labeling_rule") != "deterministic_sign":
        raise RuntimeError(f"{path}: labeling_rule is not deterministic_sign")
    n = int(manifest.get("n_triplets") or 0)
    if not (MIN_TRIPLETS <= n <= MAX_TRIPLETS):
        raise RuntimeError(
            f"{path}: {n} triplets is outside the frozen band "
            f"[{MIN_TRIPLETS}, {MAX_TRIPLETS}]; do not pad or trim")
    per_dim = manifest.get("per_dimension_triplet_counts") or {}
    thin = {d: v for d, v in per_dim.items() if int(v) < MIN_PER_DIMENSION}
    if thin:
        raise RuntimeError(f"{path}: thin dimensions {thin} (<{MIN_PER_DIMENSION})")
    run_id = str(manifest.get("run_id") or "")
    if not run_id or run_id == COHORT1_BANK_RUN_ID:
        raise RuntimeError(f"{path}: run_id missing or collides with cohort 1: {run_id!r}")
    return manifest


def apply(config_module) -> None:
    """Point the imported config module at the new bank. Fail closed."""
    if not bank2_selected():
        return
    root = os.environ.get("SCA2_PB_DATA_ROOT", "").strip()
    if not root:
        raise RuntimeError("SCA2_PB_PROTOCOL=bank2 requires SCA2_PB_DATA_ROOT")
    bank_env = os.environ.get("SCA2_PB_BANK2_DIR", "").strip()
    bank_dir = Path(bank_env) if bank_env else (
        config_module.REPO / "synthetic_generation" / "outputs" / "gps_sign_relabel_bank2")
    bank_manifest = _load_manifest(bank_dir / "manifest.json")
    data_root = Path(root)
    config_module.BANK_DIR = bank_dir
    config_module.BANK_RUN_ID = bank_manifest["run_id"]
    config_module.N_ROWS = int(bank_manifest["n_triplets"])
    config_module.DATA_ROOT = data_root
    config_module.PREPARED_DIR = data_root / "prepared"
    config_module.ADAPTER_DIR = data_root / "adapters"
    config_module.REF_CACHE_FILE = data_root / "shared_reference_logps.jsonl"
    config_module.REF_MANIFEST_FILE = data_root / "shared_reference_logps_manifest.json"
    config_module.RUN_MANIFEST_FILE = data_root / "run_manifest.json"
    config_module.LOG_DIR = data_root / "logs"

    units = os.environ.get("SCA2_PB_UNITS", "countries").strip()
    if units not in ("countries", "profiles"):
        raise RuntimeError(f"SCA2_PB_UNITS must be countries|profiles, got {units!r}")
    if units == "profiles":
        prof_env = os.environ.get("SCA2_PB_PROFILE_DIR", "").strip()
        if not prof_env:
            raise RuntimeError("SCA2_PB_UNITS=profiles requires SCA2_PB_PROFILE_DIR")
        prof_dir = Path(prof_env)
        prof_manifest = _load_manifest(prof_dir / "manifest.json")
        if prof_manifest["run_id"] != bank_manifest["run_id"]:
            raise RuntimeError("profile manifest run_id != bank manifest run_id")
        if int(prof_manifest["n_triplets"]) != int(bank_manifest["n_triplets"]):
            raise RuntimeError("profile manifest n_triplets != bank n_triplets")
        unit_list = list(prof_manifest.get("units") or [])
        if len(unit_list) != 64:
            raise RuntimeError(f"expected 64 units, got {len(unit_list)}")
        config_module.BANK_DIR = prof_dir
        config_module.COHORT = unit_list
        config_module.HF_ADAPTER_PREFIX = f"bank2/{bank_manifest['run_id']}/profiles"
    else:
        config_module.HF_ADAPTER_PREFIX = f"bank2/{bank_manifest['run_id']}/adapters"
```

Also update `hub_adapter_path_from_prefix`'s bank2 guard to accept both `bank2/.../adapters` and
`bank2/.../profiles` prefixes (the existing `path.startswith("bank2/")` check already does this; keep
the `refuses to upload onto adapters/<CC>` guard).

In `paper_b/config.py` add below `assert len(COHORT) == 42`:

```python
# Frozen split. NOTE: cohort 1 asserts 42; the bank2 profiles switch replaces COHORT.
TRAIN_ROWS = int(N_ROWS * TRAIN_FRAC)          # 526 for cohort 1
```
(and change the literal 526 in `score_runtime.validate_run_record` to `C.TRAIN_ROWS`).

**Step 4 — verify pass.** `env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m pytest -q paper_b/test_bank2_ready.py paper_b/test_score_runtime.py paper_b/test_score_hashing.py`
Expected: all pass. **If a pre-existing test asserted `658` or `526`, update the assertion to the
band rule / `C.TRAIN_ROWS` in the same commit and note it in the commit message.**

**Step 5 — commit.**

### Task B3: wave split follows the unit list

**Files:** Modify `paper_b/run_cohort.py`; Test `paper_b/test_run_unit.py`.

**Step 1 — failing test.** Add:

```python
def test_waves_cover_the_unit_list():
    import run_cohort as RC, config as C
    assert RC.WAVES[1] + RC.WAVES[2] == list(C.COHORT)
    assert len(RC.WAVES[1]) == len(RC.WAVES[2]) or abs(len(RC.WAVES[1]) - len(RC.WAVES[2])) == 1
```

**Step 2 — verify failure.** `... -m pytest -q paper_b/test_run_unit.py::test_waves_cover_the_unit_list`
Expected: FAIL (`WAVES` is built from a 42-country cohort at import time and is not list-equal for
64 units).

**Step 3 — implement.** Replace

```python
WAVES = {1: C.COHORT[:21], 2: C.COHORT[21:]}
```
with

```python
def _half(units: list[str]) -> int:
    return (len(units) + 1) // 2


WAVES = {1: list(C.COHORT[: _half(list(C.COHORT))]),
         2: list(C.COHORT[_half(list(C.COHORT)):])}
```

**Step 4 — verify pass.** `... -m pytest -q paper_b/test_run_unit.py` → all pass.

**Step 5 — commit.**

---

## Phase C — GPU run 1: train 64 profile adapters on bank 2 (≈21 T4 units)

### Task C1: hub adapter prefix is used by the scorer

**Objective:** the scorer must resolve `bank2/<run>/profiles/<unit>`, not `adapters/<unit>`.

**Files:** Modify `paper_b/score_runtime.py` (`resolve_adapter`, the default downloader) and
`paper_b/score_cohort.py` (`resolve_adapter`, `hf_adapter_names`, `_score_model_only_gpu` resolution);
Test `paper_b/test_score_runtime.py`.

**Step 1 — failing test.** Add:

```python
def test_adapter_pattern_follows_the_hub_prefix(monkeypatch, tmp_path):
    monkeypatch.setenv("SCA2_PB_PROTOCOL", "bank2")
    monkeypatch.setenv("SCA2_PB_UNITS", "profiles")
    monkeypatch.setenv("SCA2_PB_DATA_ROOT", str(tmp_path))
    monkeypatch.setenv("SCA2_PB_BANK2_DIR", str(tmp_path / "bank"))
    monkeypatch.setenv("SCA2_PB_PROFILE_DIR", str(tmp_path / "profiles"))
    import json, importlib
    for d in (tmp_path / "bank", tmp_path / "profiles"):
        d.mkdir()
        (d / "manifest.json").write_text(json.dumps({
            "run_id": "gps_sign_relabel_all_bank2_test", "labeling_rule": "deterministic_sign",
            "n_triplets": 650, "per_dimension_triplet_counts": {k: 108 for k in
             ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]},
            "units": ["P_0_0_0_0_0_0"] * 64}))
    import config as C, importlib as il
    il.reload(C)
    assert C.hub_adapter_path("P_0_0_0_0_0_0") == \
        "bank2/gps_sign_relabel_all_bank2_test/profiles/P_0_0_0_0_0_0"
    for env in ("SCA2_PB_PROTOCOL", "SCA2_PB_UNITS"):
        monkeypatch.delenv(env)
    il.reload(C)
    assert C.hub_adapter_path("CHN") == "adapters/CHN"
```

**Step 2 — verify failure.** Expect FAIL only if you have not already corrected `resolve_adapter`;
otherwise this test passes and the remaining edits are the mechanical replacements below.

**Step 3 — implement.** In `score_runtime.resolve_adapter`, replace the default downloader body:

```python
    if downloader is None:
        def downloader(cc, dest, r):
            from huggingface_hub import snapshot_download
            path_in_repo = C.hub_adapter_path(cc)
            snapshot_download(
                repo_id=C.HF_ADAPTER_REPO, repo_type=E.HF_ADAPTER_REPO_TYPE,
                revision=r, allow_patterns=[f"{path_in_repo}/*"],
                local_dir=str(dest))
```
and replace `local = dest_root / "adapters" / country` with

```python
    local = dest_root / C.hub_adapter_path(country)
    local.parent.mkdir(parents=True, exist_ok=True)
```

In `score_cohort`, replace the hardcoded `allow_patterns=[f"adapters/{cc}/*"]` and
`C.ADAPTER_DIR / cc` fallbacks with `[f"{C.hub_adapter_path(cc)}/*"]` and
`C.DATA_ROOT / C.hub_adapter_path(cc)`; make `hf_adapter_names()` list `f"{C.hub_adapter_path(cc)}/adapter_config.json"`.

**Step 4 — verify pass.** `... -m pytest -q paper_b/test_score_runtime.py paper_b/test_score_cli.py paper_b/test_score_model_only.py`
Expected: all pass, cohort-1 assertions unchanged.

**Step 5 — commit.**

### Task C2: first GPU hour — reference cache (T4)

**Files:** Create `paper_b/colab/vm_factorial_setup.py` (copy of `vm_setup.py` with
`BRANCH = "feat/paper-b-cohort"` and an added `pip install -q pyreadstat`), reuse
`paper_b/compute_ref_cache.py`.

**Commands (exact):**

```bash
export PATH="$HOME/.local/bin:$PATH"; unset PYTHONPATH
cd /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW
colab new -s pb-f1 --gpu T4
colab exec -s pb-f1 -f paper_b/colab/vm_factorial_setup.py --timeout 1800
```
Expected tail: `repo at: <sha>`, `torch 2.11.0+cu130 | cuda True | Tesla T4`, `transformers 4.46.3`,
`SETUP OK`.

Then ship the bank-2 profile files to the VM (they are not in git):

```bash
tar -C synthetic_generation/outputs/gps_sign_relabel_bank2 -czf /tmp/bank2_profiles.tgz .
colab upload -s pb-f1 /tmp/bank2_profiles.tgz /content/bank2_profiles.tgz
colab exec -s pb-f1 -f /Users/bonorinoa/.hermes/profiles/sca/cache/scratch/vm_bank2_unpack.py --timeout 300
```
where that probe script untars to `/content/paper_b_bank2_profiles/` and prints
`ls | wc -l` → `expected 80` (64 units + manifest + triplets + gps vectors + README).

Then, on the VM (detached, per the `colab-cli-headless-runs` skill):

```bash
colab exec -s pb-f1 -f /Users/bonorinoa/.hermes/profiles/sca/cache/scratch/pb_refcache_launch.py --timeout 5400
```
that launcher exports `SCA2_PB_PROTOCOL=bank2`, `SCA2_PB_UNITS=profiles`,
`SCA2_PB_DATA_ROOT=/content/paper_b_data_bank2`, `SCA2_PB_BANK2_DIR=/content/bank2_bank`,
`SCA2_PB_PROFILE_DIR=/content/paper_b_bank2_profiles`, then `Popen`s
`python paper_b/compute_ref_cache.py` with stdout to `/content/refcache.log`.
Expected when polled: `ref cache ready: <n> bytes`, n ≥ 900000, and the manifest records
`n_pairs == C.N_ROWS * TRAIN_FRAC` for the bank-2 row count.

### Task C3: dry-run the cohort path locally on the real prepared files (no GPU)

**Objective:** prove prepare/skip/idempotence and the run-record contract before paying for training.

**Commands:**

```bash
cd /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW
SCA2_PB_PROTOCOL=bank2 SCA2_PB_UNITS=profiles SCA2_PB_DATA_ROOT=/tmp/pb_factorial \
SCA2_PB_BANK2_DIR=synthetic_generation/outputs/gps_sign_relabel_bank2 \
SCA2_PB_PROFILE_DIR=synthetic_generation/outputs/gps_sign_relabel_bank2/profiles \
env -u PYTHONPATH .venv/bin/python paper_b/run_cohort.py --wave 1 --dry-run
```
Expected: `shared split: <n_train> train / <n_eval> eval` with `n_train + n_eval == C.N_ROWS`,
`prepared 32 units`, and on a second identical invocation `already prepared ... skip` for all 32
(idempotence). If the ref cache is missing the command must print
`ref cache missing: ...` and exit 3 — **that is the correct failure**; copy the real cache from the
VM first (`colab download -s pb-f1 /content/paper_b_data_bank2/shared_reference_logps.jsonl /tmp/`).

### Task C4: launch the two training waves

```bash
colab exec -s pb-f1 -f /Users/bonorinoa/.hermes/profiles/sca/cache/scratch/pb_factorial_wave1.py --timeout 36000 &
colab new -s pb-f2 --gpu T4 && colab exec -s pb-f2 -f paper_b/colab/vm_factorial_setup.py --timeout 1800
colab exec -s pb-f2 -f /Users/bonorinoa/.hermes/profiles/sca/cache/scratch/pb_factorial_wave2.py --timeout 36000 &
```
Each launcher runs `run_cohort.py --wave N` detached; each finished unit uploads to
`Bonorinoa/SCA2-paper-b-adapters` under `bank2/<run_id>/profiles/<unit>`.

**Verification while running:** every 20 minutes,
`colab exec -s pb-f1 -f paper_b/colab/vm_status.py` → unit name, `train_minutes`,
`bank_run_id`. Mark the milestone when 32 units carry the bank-2 `bank_run_id`.

**Acceptance:** 64/64 `run_record.json` files with `bank_run_id == bank2 run id`; hub directory
listing shows 64 `profiles/<unit>/adapter_config.json`. Record measured minutes per unit and stop
the sessions (`colab stop -s pb-f1`, `-s pb-f2`).

---

## Phase D — GPU run 2: strict-battery scoring of the 64 units, then variants

### Task D1: prompt variants in the readout (v1 default is byte-identical)

**Files:** Modify `paper_b/eval_lib.py` (`build_survey_user_prompt`), `paper_b/build_scoring_spec.py`;
Test `paper_b/test_eval_lib.py`, `paper_b/test_build_scoring_spec.py`, `paper_b/test_prompt_pin.py`.

**Step 1 — failing tests.** Append to `paper_b/test_eval_lib.py`:

```python
def test_prompt_variants_change_text_but_not_v1():
    spec = {"is_numeric_open": False, "codes": ["1", "2"], "labels": ["a", "b"],
            "question_text": "Q?"}
    v1 = L.build_survey_user_prompt(spec)
    assert L.build_survey_user_prompt(spec, variant="v1") == v1
    rev = L.build_survey_user_prompt(spec, variant="reverse_options")
    assert rev.index("2: b") < rev.index("1: a"), "option order must be reversed"
    assert "1: a" in rev and "2: b" in rev
    a, b = (L.build_survey_user_prompt(spec, variant=v) for v in ("paraphrase_a", "paraphrase_b"))
    assert v1 != a != b and v1 != b
    assert a.rstrip().endswith("Answer:") and b.rstrip().endswith("Answer:")


def test_prompt_variant_unknown_raises():
    import pytest
    with pytest.raises(ValueError, match="variant"):
        L.build_survey_user_prompt({"is_numeric_open": False, "codes": ["1"], "labels": ["a"],
                                    "question_text": "Q"}, variant="nope")


def test_variant_with_persona_country_is_refused():
    import pytest
    with pytest.raises(ValueError, match="persona"):
        L.build_survey_user_prompt({"is_numeric_open": False, "codes": ["1"], "labels": ["a"],
                                    "question_text": "Q"}, prompt_country="CHN",
                                   variant="paraphrase_a")
```

**Step 2 — verify failure.** `... -m pytest -q paper_b/test_eval_lib.py -k variant`
Expected: `TypeError: ... unexpected keyword argument 'variant'`.

**Step 3 — implement.** In `paper_b/eval_lib.py`:

```python
PROMPT_VARIANTS = ("v1", "reverse_options", "paraphrase_a", "paraphrase_b")

_PERSONA_V1 = "Answer this questionnaire as an individual person."
_INSTRUCTION_V1 = ("Select exactly one response code from the options below.\n"
                   "{options}\n\nReturn only the response code, with no words or explanation.")
_STEM_V1 = ("{persona} Respond naturally and sincerely, as someone would in real life. "
            "Do not mention being an AI or assistant.\n\nQuestion:\n{question}\n\n"
            "{instruction}\n\nAnswer:")

_VARIANTS = {
    "v1": (_PERSONA_V1, _INSTRUCTION_V1, _STEM_V1),
    "reverse_options": (_PERSONA_V1, _INSTRUCTION_V1, _STEM_V1),
    "paraphrase_a": (
        "You are one person answering a survey.",
        "Choose the single option that fits best.\n{options}\n\n"
        "Reply with the option number only. No explanation.",
        "{persona} Answer as you would in everyday life. Do not refer to being an AI or a model."
        "\n\nQuestion:\n{question}\n\n{instruction}\n\nYour answer:"),
    "paraphrase_b": (
        "Take part as an ordinary adult responding to a questionnaire.",
        "Pick one response from the list.\n{options}\n\n"
        "Write just the code of your choice, nothing else.",
        "{persona} Answer honestly, the way people normally answer surveys."
        "\n\nQuestion:\n{question}\n\n{instruction}\n\nResponse:"),
}
```

and rewrite the tail of `build_survey_user_prompt(spec, prompt_country=None, country_names=None,
variant="v1")`:

```python
    if variant not in _VARIANTS:
        raise ValueError(f"unknown prompt variant {variant!r}; use one of {PROMPT_VARIANTS}")
    if prompt_country is not None and variant != "v1":
        raise ValueError("the country-persona arm exists only for variant 'v1'")
    persona, instruction_tpl, stem_tpl = _VARIANTS[variant]
    if prompt_country is not None:
        persona = (f"Answer this questionnaire as a typical adult living in "
                   f"{country_names[prompt_country]}.")
    if spec["is_numeric_open"]:
        instruction = ("Give one whole-number response. Return only the number, with no words or "
                       "explanation.")
    else:
        pairs = list(zip(spec["codes"], spec["labels"]))
        if variant == "reverse_options":
            pairs = list(reversed(pairs))
        options = "\n".join(f"{code}: {label}" for code, label in pairs)
        instruction = instruction_tpl.format(options=options)
    return stem_tpl.format(persona=persona, question=spec["question_text"],
                           instruction=instruction)
```

**Step 4 — verify pass.** `... -m pytest -q paper_b/test_eval_lib.py paper_b/test_prompt_pin.py`
Expected: all pass, including the archived `26 Jul 2024` pin test.

**Step 5 — commit.**

### Task D2: spec builder supports variants and a held-out battery

**Files:** Modify `paper_b/build_scoring_spec.py`; Test `paper_b/test_build_scoring_spec.py`.

**Step 1 — failing test.** Add:

```python
def test_spec_records_variant_and_changes_sha():
    import pandas as pd
    from build_scoring_spec import build_scoring_spec, spec_sha256
    import eval_lib as L
    qmap = pd.DataFrame([{
        "Question": "Q57", "ResponseType": "single_choice_2",
        "ResponseCodes": "1; 2", "ResponseLabels": "Most people can be trusted; Need to be careful",
        "StandaloneQuestion": "Generally speaking, would you say that most people can be trusted?",
        "gps_dimension": "trust"}])
    v1 = build_scoring_spec(qmap, numeric_support={}, battery="strict")
    rev = build_scoring_spec(qmap, numeric_support={}, battery="strict", prompt_variant="reverse_options")
    assert v1["prompt_variant"] == "v1" and rev["prompt_variant"] == "reverse_options"
    assert spec_sha256(v1) != spec_sha256(rev)


def test_heldout_battery_accepts_an_explicit_item_list():
    import pandas as pd
    from build_scoring_spec import build_scoring_spec
    qmap = pd.DataFrame([
        {"Question": q, "ResponseType": "scale_1_10", "ResponseCodes": "; ".join(map(str, range(1, 11))),
         "ResponseLabels": "", "StandaloneQuestion": f"item {q}", "gps_dimension": ""}
        for q in ("Q150", "Q151")])
    spec = build_scoring_spec(qmap, numeric_support={}, battery="heldout",
                              heldout_items=["Q150", "Q151"])
    assert spec["n_questions"] == 2 and spec["battery"] == "heldout"
    assert [q["question_id"] for q in spec["questions"]] == ["Q150", "Q151"]
```

**Step 2 — verify failure.** `... -m pytest -q paper_b/test_build_scoring_spec.py -k "variant or heldout"`
Expected: `TypeError: ... unexpected keyword argument 'prompt_variant'`.

**Step 3 — implement.** Change the signature to

```python
def build_scoring_spec(question_map, numeric_support: dict[str, list[str]],
                       battery: str = "strict", sanitized: bool = False,
                       expect_missing: bool = True, prompt_variant: str = "v1",
                       heldout_items: list[str] | None = None) -> dict:
```

Change the `question_map.iterrows()` loop's `if qid not in keep: continue` to include the new branch
by adding, immediately after the `keep` selection block:

```python
    if battery == "heldout":
        if not heldout_items:
            raise ValueError("battery='heldout' requires heldout_items")
        keep = set(heldout_items)
        if keep & strict_item_ids():
            raise ValueError("held-out battery may not overlap the 23 strict items")
```
and use `elif battery == "strict":` / `elif battery == "archive":` above (the `else` becomes
`elif battery == "heldout"` with the block above; keep the existing `raise ValueError` for unknown
batteries). Return the variant: add `"prompt_variant": prompt_variant,` to the returned dict, and add
the CLI flag `--prompt-variant choices=["v1","reverse_options","paraphrase_a","paraphrase_b"]`
plus `--heldout-items-file` (JSON list) passed through.

**Step 4 — verify pass.** `... -m pytest -q paper_b/test_build_scoring_spec.py paper_b/test_score_cli.py`
Expected: all pass (the strict spec's `n_questions == 23` assertion still holds).

**Step 5 — commit.**

### Task D3: GPU run 2 — strict scoring of 64 units and the gates

**Commands (exact):**

```bash
cd /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW
# 1. build the strict spec locally (v1)
env -u PYTHONPATH .venv/bin/python paper_b/build_scoring_spec.py --battery strict \
  --out /tmp/pb_specs/strict_v1.json
# 2. adapter-path gate marker for one bank-2 profile (repeat the vm_gate pattern with GATE_UNIT)
colab new -s pb-g2 --gpu T4 && colab exec -s pb-g2 -f paper_b/colab/vm_factorial_setup.py --timeout 1800
GATE_UNIT=P_1_1_1_1_1_1 colab exec -s pb-g2 -f paper_b/colab/vm_gate_factorial.py --timeout 7200
colab download -s pb-g2 /content/paper_b_data_bank2/adapter_gate.json /tmp/pb_bank2_adapter_gate.json
```
Expected marker JSON: `{"gate_pass": true, "unit": "P_1_1_1_1_1_1", "adapter_revision": "<40-hex>"}`
and `"switchback_ok": true`. `vm_gate_factorial.py` is `vm_gate.py` with `GATE_UNIT =
os.environ.get("GATE_UNIT", "CHN")` replacing the literal `CHN` (three occurrences) and the marker
key renamed from `country` to `unit`.

```bash
# 3. score strict v1 for base + 64 adapters (two sessions, split the unit list in half)
colab exec -s pb-f1 -f /Users/bonorinoa/.hermes/profiles/sca/cache/scratch/pb_score_units.py --timeout 10800
```
`pb_score_units.py` exports `SCORE_SPEC=/content/paper_b_data/strict_v1.json`,
`SCORE_RUN_ID=bank2-strict-v1-20261015`, `SCORE_GATE_MARKER`, `SCORE_ADAPTER_REVISION`,
`SCORE_COUNTRIES="<half the units>"` and runs `paper_b/colab/vm_score.py` detached.
Expected: for each unit, `gate_pass` true, `wrote <unit>_adapter_option_probabilities.csv`, then
`model-only scoring complete`. Hub check afterwards:

```bash
env -u PYTHONPATH .venv/bin/python - <<'PY'
import os, sys, pathlib
os.environ["HF_TOKEN"] = next(l.split("=",1)[1].strip() for l in
    pathlib.Path("/Users/bonorinoa/.hermes/profiles/sca/.env").read_text().splitlines()
    if l.startswith("HF_TOKEN="))
from huggingface_hub import HfApi
files = HfApi().list_repo_files("Bonorinoa/SCA2-paper-b-artifacts", repo_type="dataset",
                               revision="main")
print(len([f for f in files if "bank2-strict-v1-20261015" in f and f.endswith(".csv")]))
PY
```
Expected: `65` (base + 64 units).

**Acceptance:** 65 score files; each unit's strict composites reproduce the adapter's own scores
across two independent SCORE_RUN_IDs run on different sessions (re-run 4 units in session 2 and diff:
`max|ΔE[recode]| == 0` exactly, because the readout is deterministic given identical weights).

### Task D4: GPU run 3 — variant specs and the 64-profile sign-prompt cell

```bash
for v in reverse_options paraphrase_a paraphrase_b; do
  env -u PYTHONPATH .venv/bin/python paper_b/build_scoring_spec.py --battery strict \
    --prompt-variant $v --out /tmp/pb_specs/strict_$v.json
done
```
Then score `base` + all 64 units for each variant with
`SCORE_RUN_ID=bank2-strict-<variant>-20261015` (same launcher, ~1.5 h per variant). Then the
sign-prompt cell on all 64 profiles:

```bash
colab exec -s pb-s3 -f /Users/bonorinoa/.hermes/profiles/sca/cache/scratch/pb_sign64.py --timeout 9000
```
Expected (per profile line): `[k/64] <unit> members=...`, then
`wrote <unit>_option_probabilities.csv rows=<n>` where n = 23 items × Σ option counts
(the strict v1 cell produced 140 rows for 23 items; expect the same 140 for every profile because the
option grids are shared), and probability sums within `1e-4` of 1 on every question.

Add `--units all64 --gps <gps_z_vectors.json>` to `paper_b/score_sign_profiles.py`:

```python
def all_profile_rows() -> list[dict]:
    import factorial as F
    rows = []
    for u in F.all_units():
        signs = {d: ("positive" if b else "negative")
                 for d, b in zip(F.DIMS, F.bits_of_unit(u))}
        prompt = SP.sign_prompt(signs)
        hits = SP.leak_hits(prompt)
        if hits:
            raise SystemExit(f"sign prompt leaked {hits}")
        rows.append({"profile_id": u, "signs": signs, "prompt": prompt, "members": []})
    return rows
```
and in `prepare()` choose `all_profile_rows()` when `--units all64`, asserting `len(rows) == 64`
instead of 26. Upload the CSVs to
`Bonorinoa/SCA2-paper-b-artifacts` under `runs/sign-prompt-bank2-all64-20261015/`.

**Acceptance:** 64 files × 3 variants present on the hub; leak scan clean on all 64 prompts.

---

## Phase E — the held-out item pool and the preregistration (no GPU)

### Task E1: pool builder from WVS-7 metadata

**Files:**
- Create: `paper_b/heldout/build_pool.py`
- Create: `paper_b/heldout/questionnaire_text.py`
- Create: `paper_b/heldout/overrides.json` (manual per-item text fixes; starts `{}`)
- Test: `paper_b/heldout/test_build_pool.py`

**Install the one new dependency:**

```bash
cd /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW
env -u PYTHONPATH -- .venv/bin/python -m pip install -q pyreadstat
env -u PYTHONPATH .venv/bin/python -c "import pyreadstat; print('pyreadstat', pyreadstat.__version__)"
```
Expected: `pyreadstat 1.2.x` (if `pip` is missing from the uv venv, run
`uv pip install --python .venv/bin/python pyreadstat`).

**Step 1 — failing test.** Create `paper_b/heldout/test_build_pool.py`:

```python
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import build_pool as B  # noqa: E402


def test_pool_excludes_mapped_and_numeric_open(tmp_path):
    items = {
        "Q57": {"valid": ["1", "2"], "type": "single_choice_2", "nominal": False},
        "Q150": {"valid": [str(i) for i in range(1, 11)], "type": "scale_1_10", "nominal": False},
        "Q261": {"valid": [], "type": "numeric_open", "nominal": False},
        "Q12": {"valid": [], "type": "multi_mention", "nominal": True},
    }
    keep = B.select_pool(items, already_mapped={"Q57"})
    assert keep == ["Q150"]


def test_standalone_question_prefers_questionnaire_text():
    text = "Q150. Most people consider both freedom and security to be important, but if you had " \
           "to choose between them, which would you say is more important?\n     1 Freedom"
    assert B.standalone("Q150", text, "Q150 - Some variable label") == \
        "Most people consider both freedom and security to be important, but if you had to choose " \
        "between them, which would you say is more important?"


def test_standalone_falls_back_to_label_then_raises():
    assert B.standalone("Q150", "", "Trust: people of another nationality?") == \
        "Trust: people of another nationality?"
    import pytest
    with pytest.raises(ValueError, match="no text"):
        B.standalone("Q999", "", "")
```

**Step 2 — verify failure.** `env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m pytest -q paper_b/heldout/test_build_pool.py`
Expected: `ModuleNotFoundError: No module named 'build_pool'`.

**Step 3 — implement `paper_b/heldout/questionnaire_text.py`:**

```python
"""Questionnaire text extraction for the held-out pool.

The official WVS-7 MasterQuestionnaire PDF (data/WVS/MasterQuestionnaire.pdf) is the
authoritative source of item wording; planning/pre_arxiv_checks/item_table/
MasterQuestionnaire.txt is its text layer. Pool items are read as text only.
"""
from __future__ import annotations

import re
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
DEFAULT_TEXT = REPO / "planning" / "pre_arxiv_checks" / "item_table" / "MasterQuestionnaire.txt"

# "Q150. Most people consider both freedom ... ?"  -> body on the same or next lines
_STANDALONE = re.compile(r"^\s*(Q\d{1,3})\.\s+(.*)$")
# " Q58        Your family          1    2    3    4"
_GRID_ROW = re.compile(r"^\s*(Q\d{1,3})\s{2,}([A-Za-z'].*?)\s{2,}\d")
_NOISE = re.compile(r"\(Code.*?\)|\(Read out.*?\)|Interviewer:.*|SHOW CARD.*", re.IGNORECASE)


def clean(text: str) -> str:
    text = _NOISE.sub("", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text.rstrip(":").strip()


def extract(path: Path | None = None) -> dict[str, str]:
    """Map every Q-id in the questionnaire text to its wording."""
    path = Path(path or DEFAULT_TEXT)
    if not path.is_file():
        raise FileNotFoundError(f"questionnaire text not found: {path}")
    lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
    out: dict[str, str] = {}
    pending: tuple[str, list[str]] | None = None
    for line in lines:
        m = _STANDALONE.match(line)
        if m:
            if pending and pending[1]:
                out.setdefault(pending[0], clean(" ".join(pending[1])))
            pending = (m.group(1), [m.group(2)])
            continue
        g = _GRID_ROW.match(line)
        if g:
            qid, stem = g.group(1), clean(g.group(2))
            if qid not in out and stem:
                out[qid] = stem
            continue
        if pending is not None:
            stripped = line.strip()
            if stripped and not stripped.startswith("Q"):
                pending[1].append(stripped)
            elif stripped.startswith("Q"):
                if pending[1]:
                    out.setdefault(pending[0], clean(" ".join(pending[1])))
                pending = None
    if pending and pending[1]:
        out.setdefault(pending[0], clean(" ".join(pending[1])))
    return {k: v for k, v in out.items() if v}
```

**Step 4 — implement `paper_b/heldout/build_pool.py`:**

```python
#!/usr/bin/env python3
"""Build the held-out WVS-7 item pool (metadata + questionnaire text only).

Reads NO responses. Writes:
  paper_b/heldout/pool_skeleton.csv   Question,VariableLabel,ResponseCodes,ResponseLabels,
                                      ResponseType,ordinal,StandaloneQuestion,text_source
Usage:
  python paper_b/heldout/build_pool.py --out paper_b/heldout/pool_skeleton.csv
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import sys
from pathlib import Path

import pyreadstat

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "paper_b"))
sys.path.insert(0, str(Path(__file__).resolve().parent))
import questionnaire_text as QT  # noqa: E402

WVS7 = REPO / "data" / "WVS" / "WVS_wave7.dta"
OVERRIDES = Path(__file__).resolve().parent / "overrides.json"
Q_RE = re.compile(r"^Q(\d{1,3})$")
COHORT31 = {  # already mapped (23 strict + Q69-71 + demographics); never in the pool
    "Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73", "Q43", "Q50",
    "Q106", "Q107", "Q109", "Q178", "Q81", "Q176", "Q177", "Q179", "Q195",
    "Q99", "Q101", "Q103", "Q69", "Q70", "Q71", "Q12", "Q13", "Q14", "Q174",
    "Q260", "Q261", "Q262", "Q275", "Q288",
}


def _codes(values: list[str]) -> list[str]:
    out = []
    for v in values:
        try:
            f = float(v)
        except ValueError:
            continue
        if f >= 1 and f.is_integer():
            out.append(str(int(f)))
    return sorted(out, key=int)


def select_pool(items: dict[str, dict], already_mapped: set[str]) -> list[str]:
    keep = []
    for qid in sorted(items, key=lambda q: int(q[1:])):
        meta = items[qid]
        if qid in already_mapped or meta["nominal"] or not meta["valid"]:
            continue
        codes = meta["valid"]
        if not (2 <= len(codes) <= 11):
            continue
        if codes != [str(i) for i in range(int(codes[0]), int(codes[-1]) + 1)]:
            continue
        keep.append(qid)
    return keep


def standalone(qid: str, questionnaire: str, label: str) -> str:
    text = questionnaire.strip() or label.strip()
    if len(text) < 20:
        raise ValueError(f"{qid}: no text (questionnaire and label both empty)")
    return text


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(Path(__file__).resolve().parent / "pool_skeleton.csv"))
    ap.add_argument("--wvs", default=str(WVS7))
    a = ap.parse_args()

    _, meta = pyreadstat.read_dta(a.wvs, metadataonly=True)
    items = {}
    for name, label in zip(meta.column_names, meta.column_labels):
        m = Q_RE.match(name)
        if not m:
            continue
        codes = _codes(list((meta.variable_value_labels.get(name) or {}).keys()))
        items[name] = {"label": (label or "").strip(), "valid": codes,
                       "nominal": (meta.variable_measure or {}).get(name, "") == "nominal"
                       or len(codes) > 11}
    questionnaire = QT.extract()
    overrides = json.loads(OVERRIDES.read_text()) if OVERRIDES.is_file() else {}
    keep = select_pool(items, COHORT31)

    rows = []
    missing_text = []
    for qid in keep:
        text = overrides.get(qid, {}).get("StandaloneQuestion", "")
        source = "override" if text else ""
        if not text:
            text = questionnaire.get(qid, "")
            source = "questionnaire"
        if not text:
            text = items[qid]["label"]
            source = "varlabel"
        try:
            text = standalone(qid, text, items[qid]["label"])
        except ValueError:
            missing_text.append(qid)
            continue
        rows.append({"Question": qid, "VariableLabel": items[qid]["label"],
                     "ResponseCodes": "; ".join(items[qid]["valid"]),
                     "ResponseLabels": "", "ResponseType": f"scale_1_{len(items[qid]['valid'])}",
                     "ordinal": "REVIEW", "StandaloneQuestion": text, "text_source": source})
    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)
    print(f"pool items: {len(rows)} -> {out}")
    print(f"text from questionnaire: {sum(1 for r in rows if r['text_source'] == 'questionnaire')}"
          f" | from varlabel: {sum(1 for r in rows if r['text_source'] == 'varlabel')}"
          f" | from overrides: {sum(1 for r in rows if r['text_source'] == 'override')}")
    print(f"items with no text at all (dropped, listed for review): {missing_text}")
    print(f"overlap with the mapped 35: {sorted(set(keep) & COHORT31)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 5 — verify pass.** `env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m pytest -q paper_b/heldout/test_build_pool.py`
Expected: `3 passed`.

**Step 6 — run it and review.** `env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python paper_b/heldout/build_pool.py`
Expected: `overlap with the mapped 35: []`, pool size printed (target 120–220).

**Step 7 — manual review gate (human, ~20 minutes).** Open `pool_skeleton.csv`; for every row set
`ordinal` to `TRUE` or `FALSE` and fix `StandaloneQuestion` where the text is a fragment (record the
fix in `overrides.json` as `{"<Qid>": {"StandaloneQuestion": "..."}}`). Then re-run step 6.
Acceptance: no `REVIEW` left, no item text shorter than 20 characters, and a spot check of 15 rows
against `data/WVS/MasterQuestionnaire.pdf` reads clean. Commit `pool_skeleton.csv` and
`overrides.json` only (no respondent data).

### Task E2: the probe-selection rule and the freeze

**Files:** Create `paper_b/heldout/probe_select.py`; Test `paper_b/heldout/test_probe_select.py`;
Create `paper_b/heldout/FREEZE.json` (only after E3).

**Step 1 — failing test.**

```python
from __future__ import annotations
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import numpy as np
import pandas as pd
import probe_select as P  # noqa: E402


def _frame(signal: float) -> pd.DataFrame:
    import factorial as F
    rows = []
    for u in F.all_units():
        bits = np.array(F.bits_of_unit(u), dtype=float)
        y = signal * bits[0] + 0.05 * np.arange(len(bits)) @ bits  # trust bit dominates
        rows.append({"unit": u, "item": "Q150", "value": float(y)})
    return pd.DataFrame(rows)


def test_probe_recovers_the_planted_dimension():
    out = P.effects(_frame(1.0))
    row = out.iloc[0]
    assert row["question_id"] == "Q150"
    assert row["top_dimension"] == "trust"
    assert row["t_top"] > 3
    assert row["error_df"] == 42           # 64 units - 1 - 6 - 15 parameters


def test_probe_flags_a_null_item_as_none():
    import numpy as np
    import pandas as pd
    import factorial as F
    rng = np.random.default_rng(0)
    rows = [{"unit": u, "item": "Q999", "value": float(rng.normal())} for u in F.all_units()]
    out = P.effects(pd.DataFrame(rows))
    assert out.iloc[0]["top_dimension"] == "none"


def test_selection_requires_imprint_and_threshold():
    df = pd.DataFrame([
        {"question_id": "Q1", "top_dimension": "trust", "t_top": 5.0},
        {"question_id": "Q2", "top_dimension": "patience", "t_top": 9.0},
        {"question_id": "Q3", "top_dimension": "altruism", "t_top": 1.0},
    ])
    sel = P.select(df, imprint={"trust", "risktaking", "posrecip", "altruism"}, t_crit=3.0)
    assert sel == ["Q1"]
```

**Step 2 — verify failure.** Expect `ModuleNotFoundError: No module named 'probe_select'`.

**Step 3 — implement `paper_b/heldout/probe_select.py`:**

```python
#!/usr/bin/env python3
"""The preregistered probe: item -> dimension, from the 2^6 factorial.

Model: y_item(unit) = b0 + sum_d b_d * x_d + sum_{d<e} b_de * x_d*x_e + e, with x_d = +/-0.5
(so b_d is the effect of flipping bit d). Estimated by ordinary least squares on all 64 units.
Everything is computed BEFORE any human held-out value is read.
"""
from __future__ import annotations

import itertools
import json
import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "paper_b"))
import factorial as F  # noqa: E402

IMPRINT = ("trust", "risktaking", "posrecip", "altruism")
SURFACES = ("trust", "risktaking", "patience", "altruism", "posrecip", "negrecip")


def design() -> tuple[np.ndarray, list[str]]:
    units = F.all_units()
    x = np.array([[0.5 if b else -0.5 for b in F.bits_of_unit(u)] for u in units], float)
    names = list(F.DIMS)
    cols = [np.ones(len(units))]
    cols += [x[:, i] for i in range(6)]
    for i, j in itertools.combinations(range(6), 2):
        cols.append(x[:, i] * x[:, j])
        names.append(f"{F.DIMS[i]}:{F.DIMS[j]}")
    return np.column_stack(cols), names


def effects(values: pd.DataFrame) -> pd.DataFrame:
    """values: columns unit, item, value (one row per unit x item)."""
    X, names = design()
    units = F.all_units()
    order = {u: i for i, u in enumerate(units)}
    rows = []
    for item, g in values.groupby("item", sort=True):
        y = np.full(len(units), np.nan)
        for _, r in g.iterrows():
            y[order[r["unit"]]] = float(r["value"])
        if np.isnan(y).any():
            raise ValueError(f"{item}: missing units {[units[i] for i in np.where(np.isnan(y))[0]]}")
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        resid = y - X @ beta
        df = len(units) - X.shape[1]
        s2 = float(resid @ resid) / df
        xtx_inv = np.linalg.inv(X.T @ X)
        se = np.sqrt(s2 * np.diag(xtx_inv))
        t_main = {F.DIMS[i]: float(beta[1 + i] / se[1 + i]) for i in range(6)}
        top = max(t_main, key=lambda d: abs(t_main[d]))
        rows.append({
            "question_id": item, "error_df": df, "sigma": float(np.sqrt(s2)),
            **{f"t_{d}": t_main[d] for d in F.DIMS},
            "top_dimension": top if abs(t_main[top]) > 0 else "none",
            "t_top": t_main[top],
        })
    return pd.DataFrame(rows).sort_values("question_id").reset_index(drop=True)


def dichotomize(df: pd.DataFrame, *, top_share: float = 0.25,
                min_abs_t: float = 2.0) -> pd.Series:
    """PRIMARY selection rule: the top `top_share` of items by |t_top|, restricted to
    items whose top dimension is an imprint dimension and |t_top| >= min_abs_t."""
    ranked = df.copy()
    ranked["rank"] = ranked["t_top"].abs().rank(ascending=False, method="first")
    cut = max(1, int(np.ceil(top_share * len(ranked))))
    return ranked["rank"] <= cut


def select(df: pd.DataFrame, imprint=IMPRINT, t_crit: float = 2.0) -> list[str]:
    """SECONDARY rule used for the reliability check: fixed |t| threshold."""
    keep = df[(df.top_dimension.isin(imprint)) & (df.t_top >= t_crit)]
    return sorted(keep.question_id.astype(str).tolist())


def main() -> int:
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--items", required=True, help="CSV: unit,item,value (model composites)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--t-crit", type=float, default=2.0)
    a = ap.parse_args()
    df = effects(pd.read_csv(a.items))
    df["primary_selected"] = dichotomize(df)
    df["secondary_selected"] = df.question_id.astype(str).isin(select(df, t_crit=a.t_crit))
    Path(a.out).write_text(df.to_csv(index=False))
    print(f"items {len(df)} | primary selected {int(df.primary_selected.sum())} "
          f"| secondary selected {int(df.secondary_selected.sum())}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
```

**Step 4 — verify pass.** `... -m pytest -q paper_b/heldout/test_probe_select.py` → `3 passed`.

**Step 5 — commit.**

### Task E3: the freeze guard

**Files:** Create `paper_b/heldout/freeze.py`; Test `paper_b/heldout/test_freeze.py`.

**Step 1 — failing test.**

```python
from __future__ import annotations
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pytest
import freeze as FR  # noqa: E402


def test_freezing_records_hashes(tmp_path):
    sel = tmp_path / "selection.csv"
    sel.write_text("question_id,primary_selected\nQ150,True\n")
    pool = tmp_path / "pool_skeleton.csv"
    pool.write_text("Question\nQ150\n")
    fr = FR.freeze(selection_path=sel, pool_path=pool, freeze_path=tmp_path / "FREEZE.json",
                   code_revision="deadbeef", run_ids={"strict_v1": "bank2-strict-v1-20261015"})
    assert fr["selection_sha256"] and fr["pool_sha256"]
    assert fr["selected_items"] == 1


def test_human_read_refused_before_freeze(tmp_path):
    with pytest.raises(RuntimeError, match="FREEZE"):
        FR.require_freeze(tmp_path / "FREEZE.json")


def test_human_read_allowed_after_freeze(tmp_path):
    f = tmp_path / "FREEZE.json"
    f.write_text(json.dumps({"selection_sha256": "x", "frozen_at": "2026-10-15T00:00:00Z"}))
    assert FR.require_freeze(f)["selection_sha256"] == "x"
```

**Step 2 — verify failure.** `... -m pytest -q paper_b/heldout/test_freeze.py` → collection error.

**Step 3 — implement `paper_b/heldout/freeze.py`:**

```python
"""The blinding gate: no held-out human value is read before FREEZE.json exists."""
from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def freeze(*, selection_path: Path, pool_path: Path, freeze_path: Path,
           code_revision: str, run_ids: dict[str, str], rubric: dict | None = None) -> dict:
    import pandas as pd
    sel = pd.read_csv(selection_path)
    payload = {
        "frozen_at": datetime.now(timezone.utc).isoformat(),
        "selection_path": str(selection_path), "selection_sha256": _sha(selection_path),
        "pool_path": str(pool_path), "pool_sha256": _sha(pool_path),
        "code_revision": code_revision, "run_ids": run_ids,
        "selected_items": int(sel["primary_selected"].sum()) if "primary_selected" in sel else None,
        "n_items": int(len(sel)),
        "rubric": rubric or {},
    }
    Path(freeze_path).write_text(json.dumps(payload, indent=2) + "\n")
    return payload


def require_freeze(freeze_path: Path) -> dict:
    fp = Path(freeze_path)
    if not fp.is_file():
        raise RuntimeError(
            f"BLOCKED: {fp} does not exist. The held-out human criterion may not be read "
            "before the item selection is frozen (preregistration section 5).")
    return json.loads(fp.read_text())
```

**Step 4 — verify pass.** `... -m pytest -q paper_b/heldout/test_freeze.py` → `3 passed`.

**Step 5 — write the preregistration.** Create `paper_b/heldout/PREREGISTRATION.md` with these
sections filled with the real numbers (item counts, spec shas, run ids, revision):
1. Question and estimator; 2. Pool construction rule and exclusions; 3. The probe (design matrix,
LS, `top_share=0.25`, `t_crit=2.0`, imprint set); 4. Human criterion (weighted country means,
Spearman vs GPS z, sign agreement, permutation null over items, country bootstrap); 5. Blinding
statement (the FREEZE guard); 6. Comparators (face-valid "section rule" declared now, plus a random
allocation null); 7. Ceiling construction; 8. Planned sensitivity (secondary threshold rule,
item-level dropping of items with |ρ| < 0.15, country leave-one-out); 9. What would falsify each
claim; 10. Version and hashes.

**Step 6 — publish the timestamp.** `git add paper_b/heldout/PREREGISTRATION.md paper_b/heldout/pool_skeleton.csv paper_b/heldout/pool_skeleton.selection_rule.json` and
`git commit -m "docs(paper-b): held-out screen preregistration (pre-selection)"`, then
`git tag prereg-heldout-2026-10-15 && git push origin prereg-heldout-2026-10-15` (ask the user to
push if the org push 403s). Upload the same two files to an OSF/Anonymous-GitHub copy per D5.

### Task E4: GPU run 4 — score the held-out battery, freeze, then join humans

**Commands:**

```bash
env -u PYTHONPATH .venv/bin/python paper_b/build_scoring_spec.py --battery heldout \
  --heldout-items-file /tmp/pb_heldout_items.json --out /tmp/pb_specs/heldout_v1.json
env -u PYTHONPATH .venv/bin/python -c "
import json; s=json.load(open('/tmp/pb_specs/heldout_v1.json')); print(s['n_questions'], s['spec_sha256'][:16])"
```
Expected: the pool size and a 16-hex prefix — record both in the preregistration addendum.

Score base + 64 adapters (**model-only**, `adapter` arm; no gating needed because these are the same
weights already gated — set `SCORE_GATE_MARKER` to the bank-2 marker):
`SCORE_RUN_ID=bank2-heldout-v1-20261015`. Also score the 64 sign profiles on the same held-out
items: `python paper_b/score_sign_profiles.py --units all64 --spec /content/paper_b_data/heldout_v1.json --out-dir ...`.

Then, **on this machine, in this order**:

```bash
# 1. model composites for held-out items (no humans involved)
env -u PYTHONPATH .venv/bin/python paper_b/heldout/build_probe_items.py \
  --scores /tmp/pb_local_scores/heldout_v1 --items-file /tmp/pb_heldout_items.json \
  --out /tmp/pb_heldout_items.csv
# 2. probe selection (still no humans)
env -u PYTHONPATH .venv/bin/python paper_b/heldout/probe_select.py \
  --items /tmp/pb_heldout_items.csv --out paper_b/heldout/selection.csv
# 3. FREEZE
env -u PYTHONPATH .venv/bin/python -m paper_b.heldout.freeze_cli --selection paper_b/heldout/selection.csv \
  --pool paper_b/heldout/pool_skeleton.csv --freeze paper_b/heldout/FREEZE.json \
  --code-revision "$(git rev-parse --short HEAD)"
cat paper_b/heldout/FREEZE.json
```
`build_probe_items.py` computes, for each unit and item, `E[raw_code]` (no recode; see
`analyze_surface.expected_recode` for the shape, minus the recode step) and writes
`unit,item,value`. Only after step 3 does anything read `Z*P_heldout_human.csv`.

**Acceptance:** `selection.csv` exists with `primary_selected`; `FREEZE.json` lists
`selected_items` and hashes; no human file was opened before it.

---

## Phase F — analyses and verification (CPU, no GPU)

### Task F1: `paper_b/factorial_effects.py` (MTMM and bank robustness)

**Files:** Create `paper_b/factorial_effects.py`; Test `paper_b/test_factorial_effects.py`.

**Step 1 — failing test.**

```python
from __future__ import annotations
import sys
from pathlib import Path
import numpy as np
import pandas as pd
sys.path.insert(0, str(Path(__file__).resolve().parent))
import factorial_effects as FE  # noqa: E402


def test_matrix_is_6_by_7_and_diagonal_dominates_when_planted():
    import factorial as F
    rows = []
    for u in F.all_units():
        bits = {d: b for d, b in zip(F.DIMS, F.bits_of_unit(u))}
        for surface, dim in (("trust", "trust"), ("risktaking", "risktaking"),
                             ("posrecip", "posrecip"), ("altruism", "altruism"),
                             ("patience:Q43", "patience"), ("patience:Q50", "patience"),
                             ("negrecip", "negrecip")):
            rows.append({"unit": u, "surface": surface,
                         "composite": 10.0 + 3.0 * (1 if bits[dim] else 0)})
    comp = pd.DataFrame(rows)
    m = FE.effect_matrix(comp)
    assert m.shape == (6, 7)
    for dim in F.DIMS:
        col = {"patience": "patience:Q43"}.get(dim, dim)
        assert abs(m.loc[dim, col]) == m.loc[dim].abs().max()
    assert FE.diagonal_dominance(m) == 1.0


def test_contract_with_cohort1_returns_the_26_shared_units():
    import pandas as pd
    a = pd.Series({f"P_{i}": 1.0 for i in range(64)})
    b = pd.Series({f"P_{i}": 1.0 + i / 100 for i in range(64)})
    out = FE.bank_contract(a, b)
    assert out["n_units"] == 64 and out["pearson"] > 0.99
```

**Step 2 — verify failure.** Expect import error.

**Step 3 — implement `paper_b/factorial_effects.py`:**

```python
#!/usr/bin/env python3
"""Factorial effect matrix (bit -> surface), diagonal dominance, bank robustness.

`unit` is a 64-cell design point. Coefficients are OLS main effects of flipping one sign bit,
computed with the same design matrix as the probe (`probe_select.design`).
"""
from __future__ import annotations

import sys
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO / "paper_b"))
import factorial as F  # noqa: E402
from heldout.probe_select import design  # noqa: E402

PATIENCE_SURFACES = ("patience:Q43", "patience:Q50")


def effect_matrix(composites: pd.DataFrame) -> pd.DataFrame:
    """composites: unit, surface, composite -> rows=dimension, cols=surface."""
    X, _ = design()
    units = F.all_units()
    order = {u: i for i, u in enumerate(units)}
    out = {}
    for surface, g in composites.groupby("surface", sort=True):
        y = np.full(len(units), np.nan)
        for _, r in g.iterrows():
            y[order[r["unit"]]] = float(r["composite"])
        if np.isnan(y).any():
            raise ValueError(f"{surface}: missing units")
        beta, *_ = np.linalg.lstsq(X, y, rcond=None)
        out[surface] = {d: float(beta[1 + i]) for i, d in enumerate(F.DIMS)}
    return pd.DataFrame(out).T.rename_axis("surface").T.rename_axis("dimension")


def diagonal_dominance(matrix: pd.DataFrame) -> float:
    """Share of dimensions whose own surface carries the largest |effect|."""
    hits = 0
    for dim in F.DIMS:
        col = "patience:Q43" if dim == "patience" else dim
        if col not in matrix.columns:
            raise ValueError(f"surface column {col!r} missing")
        if abs(matrix.loc[dim, col]) == matrix.loc[dim].abs().max():
            hits += 1
    return hits / len(F.DIMS)


def param_noise(matrix: pd.DataFrame, rcond: float | None = None) -> float:
    """Lenth-style pseudo standard error of the 15 two-way interaction coefficients.

    Requires a third axis: call with the interaction frame columns removed. Kept simple and
    explicit: the caller passes a frame of interaction terms only.
    """
    vals = np.abs(matrix.to_numpy(float).ravel())
    s = 1.5 * float(np.median(vals))
    return float(s)


def bank_contract(cohort1: pd.Series, bank2: pd.Series) -> dict:
    """Agreement of a surface composite between the two banks, over shared units."""
    d = pd.concat([cohort1.rename("bank1"), bank2.rename("bank2")], axis=1).dropna()
    return {"n_units": int(len(d)),
            "pearson": float(np.corrcoef(d.bank1, d.bank2)[0, 1]) if len(d) > 2 else float("nan"),
            "max_abs_diff": float((d.bank1 - d.bank2).abs().max())}
```

**Step 4 — verify pass.** `... -m pytest -q paper_b/test_factorial_effects.py` → `2 passed`.

**Step 5 — commit.**

### Task F2: `paper_b/analyze_factorial.py` (the report drives everything)

**Files:** Create `paper_b/analyze_factorial.py`; Create `paper_b/heldout/human_means.py`;
Create `paper_b/heldout/ceiling.py`; Tests `paper_b/test_analyze_factorial.py` (at minimum the
`freeze` guard, the sign-agreement statistic, and the comparator construction).

**Required outputs (all written to `planning/sprint_2026-10-11/paper-b-tier1/results/`):**

| File | Content |
|---|---|
| `mtmm_adapter.csv`, `mtmm_signprompt.csv` | 6×7 effect matrices |
| `mtmm_summary.json` | diagonal dominance per route, Lenth PSE, |t| per cell |
| `bank_robustness.csv` | per surface: bank-2 profile composites vs cohort-1 (26 shared cells), with 2000-draw profile bootstrap CIs (`analyze_surface.bootstrap_spearman`, `clusters=` the cell id) |
| `readout_variants.csv` | per surface: composite by variant, max abs deviation from v1, diagonal dominance per variant |
| `heldout_selection.csv` | the frozen selection with `t_top` per item |
| `heldout_human.csv` | per selected item: `rho_human`, predicted sign, agreement, `rho_human` for non-selected items |
| `screen_test.json` | sign-agreement rate, binomial p, permutation p (10 000 item permutations, seed 20261015), comparator rates (section rule, random), ceiling-adjusted agreement |
| `ceiling.csv` | per surface and per selected item: wave6 vs wave7 country-mean Spearman (28 countries), and adapter–human beside it |

Rules that must be enforced in code, with tests:
- **Refuse to read any human held-out file unless `FREEZE.json` validates** (`freeze.require_freeze`).
- **Never recode held-out items**; use raw codes on both sides (`E[raw_code]` vs weighted human
  mean of the raw code). Reversed-scale battery items keep the frozen `INVERT_*` recodes via
  `analyze_surface.recode_value`.
- **Every number carries its surface label** and the run id it came from.

**Ceiling crosswalk (`ceiling.py`):** map each item to a Time-Series variable by exact
country-mean equality over 32 wave-7 countries: load only wave-7 rows from
`data/WVS/timeseries/...dta` (filter on `S002VS == 7`), compute unweighted country means per
candidate variable, and accept the TS variable with the highest Pearson r against the item's WVS-7
mean vector **only if r ≥ 0.999**. For the 23 battery items (already unblinded) this check runs
now; for held-out items it runs after the freeze. Write the accepted map to
`planning/sprint_2026-10-11/paper-b-tier1/results/ts_crosswalk.json` with the r for every pair,
and the rejected candidates listed with their r.

**Step 4 — verify.** `env -u PYTHONPATH .venv/bin/python paper_b/analyze_factorial.py --help` prints
the CLI; a full local run on the downloaded scores must complete without reading a human file when
`FREEZE.json` is absent (prove it: run with the human file moved aside and expect the guarded
analysis to exit with the `BLOCKED:` message).

### Task F3: verification report

**File:** Create `planning/sprint_2026-10-11/paper-b-tier1/VERIFICATION.md` containing:
1. what each artifact is and which run id produced it;
2. hashes (spec sha, adapter revision, selection sha, freeze sha);
3. the five Tier-1 acceptance checks and their measured values:

| # | Check | Pass criterion |
|---|---|---|
| V1 | Bank 2 gates | `ALL GATES PASS`, 640–660 triplets, zero label mismatches, `source_run_id` = bank-2 generation run |
| V2 | 64/64 adapters | every `run_record.json` carries the bank-2 `bank_run_id`; hub listing shows 64 |
| V3 | Readout determinism | re-scoring 4 units on a second session reproduces `E[recode]` exactly (`max abs diff == 0`) |
| V4 | Blinding | `FREEZE.json` mtime precedes every read of `Z*P_heldout_human.csv`; guard test passes |
| V5 | Factorial is informative | diagonal dominance > chance (≥ 4 of 6 dimensions) on the adapter route, with Lenth PSE and per-cell t reported |

4. everything that FAILED or is unresolved, in plain language.

---

## Phase G — tests, lint, and coverage of the frozen paths

- Run the whole suite after every phase:
  `env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m pytest -q paper_b/ synthetic_generation/tests/`
  Expected baseline before this work: 3 failures in
  `synthetic_generation/tests/test_run_scoring_optional.py` (an unbuilt `--diagnostic-scorer` spec).
  Do not fix or delete those as part of this plan; report them as pre-existing.
- `env -u PYTHONPATH -u VIRTUAL_ENV .venv/bin/python -m pytest -q paper_b/test_bank2_ready.py paper_b/test_score_runtime.py paper_b/test_score_hashing.py paper_b/test_persist_unit.py paper_b/test_analyze_surface.py`
  must stay green: these encode the frozen cohort-1 contract.
- No `sed -i` edits to frozen constants. Every constant change is a dated note in
  `planning/sprint_2026-10-11/PARENT_DECISIONS.md`.

## Phase H — compute ledger

Append every GPU session to `paper_b/compute/publication_estimate.json` and
`paper_b/compute/ledger.jsonl` via `paper_b/compute_ledger.py`:
`env -u PYTHONPATH .venv/bin/python -c "import sys; sys.path.insert(0,'paper_b'); import compute_ledger as L; L.try_record(L.make_event(stage='train', unit='factorial64', wall_minutes=<measured>, scope='wave1+wave2', source='run_cohort.py', role='live', hardware=L.hardware_snapshot()))"`.
Record endpoint dollars from `synthetic_generation/outputs/bank2_20261014/raw/generation_manifest.json`
(`cost_summary.endpoint_runtime_cost`). Budget band: ≤ 55 Colab units, ≤ $40 endpoints.

---

## Risks, tradeoffs, and open questions

1. **Bank-2 triplet count (D1).** If generation lands at 660, the current `658`-only guard refuses a
   correct bank; if it lands at 655 the frozen 526/132 split changes by one row. Relaxing to a band
   is a protocol change; keeping 658 means trimming, which is forbidden. **Blocks Phase B2 onward.**
2. **Sign-prompt strength (the scientific risk).** The prompt route already matches the adapter on
   four surfaces. The factorial may show the adapters are a redundant encoding. The plan reports
   that outcome rather than dodging it; the MTMM contrast (route × diagonal dominance) is the
   strongest available rescue, and it is measurable.
3. **Per-dimension prompts.** `STRICT_ITEMS["posrecip"] = ["Q81"]` is one item, so its composite is a
   single item; and `patience` stays two surfaces. Diagonal dominance uses `patience:Q43`.
4. **Held-out pool dependence on generated text.** If the questionnaire text layer yields < 120
   usable items, the pool shrinks and the primary selection becomes coarse (`top_share=0.25` of
   ~60 items = 15). Record the count in the preregistration before selection.
5. **Time cost of the manual review (E1 step 7).** ~20 minutes of human attention on ~150 rows, and
   it must happen before the freeze. It cannot be delegated.
6. **Regression risk in the shared scorer.** Three files (`score_runtime.py`, `score_cohort.py`,
   `protocol_bank2.py`) are edited; each edit is covered by a test that also asserts cohort-1
   behaviour is unchanged. If any cohort-1 test cannot be kept green, stop and report.
7. **Open:** whether the secondary fixed-threshold rule (`t_crit=2.0`) is the reliability check or a
   co-primary; the plan treats it as secondary and reports both. Someone must decide before the
   preregistration is timestamped.
8. **Open:** EVS is out of scope here (8 of 42 countries). The 8-country EVS/WVS comparison remains a
   named future appendix, not part of Tier 1.
