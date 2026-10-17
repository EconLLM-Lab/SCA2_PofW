"""Paper B, checkpoint C6 — the near-zero refit bank.

A real cohort country c in sign profile u trains (in bank 2) on the labels of u's synthetic z vector, because
the deterministic sign rule reads only signs. `country_rows` rebuilds the labels from c's REAL z and
`label_key` compares them with `factorial.label_row`; the CLI refuses to continue if any of the 42 countries
differs. The near-zero refit for c is then unit u's rows minus the rows whose `gps_dimension` d has
|z_c,d| < config.NEAR_ZERO. The train/eval split is the pipeline's own shared split of the FULL bank
(lib.make_shared_split), so dropping rows never changes which of the remaining rows are training rows.

CPU only. No model, no network, no human survey data (only the committed GPS z file). Written files carry
dimension names and counts, never z values.

    env -u PYTHONPATH .venv/bin/python paper_b/near_zero_bank.py --out-dir <dir>
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import config as C  # noqa: E402
import factorial as F  # noqa: E402
import lib  # noqa: E402

REPO = C.REPO
GPS_JSON = REPO / "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json"   # = analyze_surface.DEFAULT_GPS_JSON
BANK2_TRIPLETS = REPO / "synthetic_generation/outputs/gps_sign_relabel_bank2/triplets_bank.jsonl"
BANK2_PROFILES = REPO / "synthetic_generation/outputs/gps_sign_relabel_bank2_profiles"


def load_triplets(path: Path) -> list[dict]:
    rows = [json.loads(l) for l in Path(path).read_text().splitlines() if l.strip()]
    rows.sort(key=lambda r: r["triplet_id"])
    return rows


def load_profile_rows(profile_dir: Path, unit: str) -> list[dict]:
    rows = [json.loads(l) for l in (Path(profile_dir) / f"D_syn_{unit}.jsonl").read_text().splitlines() if l.strip()]
    rows.sort(key=lambda r: r["triplet_id"])
    return rows


def label_key(row: dict) -> tuple:
    """What a label is: which triplet, which response is chosen, which is rejected."""
    return (row["triplet_id"], row["chosen"], row["rejected"])


def country_rows(triplets: list[dict], z: dict, *, run_id: str, source_run_id: str,
                 export_timestamp: str) -> list[dict]:
    """Bank rows labeled with a country's REAL z (sign rule: chosen = A iff z >= 0).

    Deliberately does not call factorial.label_row, so comparing the two is a real test.
    """
    out = []
    for t in triplets:
        zv = float(z[t["gps_dimension"]])
        a_wins = zv >= 0
        out.append({
            "prompt": t["prompt"],
            "chosen": t["response_a"] if a_wins else t["response_b"],
            "rejected": t["response_b"] if a_wins else t["response_a"],
            "gps_dimension": t["gps_dimension"], "z_value": zv,
            "chosen_option": "A" if a_wins else "B",
            "near_zero_z": abs(zv) < C.NEAR_ZERO,
            "triplet_id": t["triplet_id"], "run_id": run_id,
            "source_run_id": source_run_id, "export_timestamp": export_timestamp,
        })
    return out


def near_zero_dims(z: dict, thr: float = C.NEAR_ZERO) -> set[str]:
    return {d for d in F.DIMS if abs(float(z[d])) < thr}


def train_prompts(rows: list[dict]) -> set[str]:
    """Normalized prompts of the pipeline's training split over the full bank."""
    prompts = {lib.normalize_prompt(r["prompt"]) for r in rows}
    train, _ = lib.make_shared_split({p for p in prompts if p is not None}, C.TRAIN_FRAC, C.SEED)
    return train


def _split_of(row: dict, train: set[str]) -> str:
    return "train" if lib.normalize_prompt(row["prompt"]) in train else "eval"


def reduced_bank(rows: list[dict], z: dict, train: set[str]) -> dict:
    """Unit rows minus the rows whose dimension is near zero for this country. Rows keep their own fields."""
    nz = near_zero_dims(z)
    kept, dropped = [], []
    for r in rows:
        tagged = {**r, "split": _split_of(r, train)}
        (dropped if r["gps_dimension"] in nz else kept).append(tagged)
    return {"kept": kept, "dropped": dropped, "near_zero_dims": sorted(nz),
            "train_kept": sum(r["split"] == "train" for r in kept),
            "train_dropped": sum(r["split"] == "train" for r in dropped)}


def declare_subset(candidates: list[dict]) -> dict:
    """The preregistered rule: most near-zero TRAINING rows; one singleton-profile country, one multi-member.

    Uses exposure only. Ties go to the alphabetically first ISO3 code. Countries without a near-zero
    training row are not candidates.
    """
    live = [c for c in candidates if c["exposure"] > 0]

    def best(pool: list[dict]) -> str:
        if not pool:
            raise ValueError("no candidate in this class")
        return sorted(pool, key=lambda c: (-c["exposure"], c["cc"]))[0]["cc"]

    return {"singleton": best([c for c in live if c["members"] == 1]),
            "multi": best([c for c in live if c["members"] > 1])}


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def write_bank(out_dir: Path, cc: str, unit: str, z: dict, red: dict, *, bank_run_id: str,
               source_rows: int, source_sha256: str | None = None) -> dict:
    d = Path(out_dir) / cc
    d.mkdir(parents=True, exist_ok=True)
    name = f"D_syn_{cc}_nearzero.jsonl"
    rows = sorted(red["kept"], key=lambda r: r["triplet_id"])
    with (d / name).open("w", encoding="utf-8") as fh:
        for r in rows:
            fh.write(json.dumps(r, ensure_ascii=False) + "\n")
    per_dim = {dim: sum(1 for r in red["dropped"] if r["gps_dimension"] == dim) for dim in red["near_zero_dims"]}
    manifest = {
        "country": cc, "profile_unit": unit, "bank_run_id": bank_run_id,
        "rule": f"drop rows whose gps_dimension has |z| < {C.NEAR_ZERO}; split = lib.make_shared_split of the full bank",
        "threshold": C.NEAR_ZERO, "near_zero_dimensions": red["near_zero_dims"],
        "train_frac": C.TRAIN_FRAC, "seed": C.SEED,
        "n_source": source_rows, "n_kept": len(red["kept"]), "n_dropped": len(red["dropped"]),
        "train_kept": red["train_kept"], "train_dropped": red["train_dropped"],
        "eval_kept": sum(r["split"] == "eval" for r in red["kept"]),
        "dropped_by_dimension": per_dim,
        "dropped_triplet_ids": sorted(r["triplet_id"] for r in red["dropped"]),
        "file": name, "sha256": {name: _sha(d / name)},
        "source_profile_file_sha256": source_sha256,
        "notes": ["rows are the unit's bank-2 rows with an added `split` field (train|eval)",
                  "no model call, no upload; ref log-probs join on the VM by (prompt, completion)"],
    }
    (d / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    return manifest


def verify_all_labels(triplets: list[dict], gps: dict) -> dict:
    """Prove, for every cohort country, that real-z labels == profile-unit labels. Raises on any mismatch."""
    bad = []
    for cc in C.COHORT:
        unit = F.unit_of_z(gps[cc])
        mine = country_rows(triplets, gps[cc], run_id="x", source_run_id="x", export_timestamp="x")
        ref = [F.label_row(t, unit, run_id="x", source_run_id="x", export_timestamp="x") for t in triplets]
        if [label_key(r) for r in mine] != [label_key(r) for r in ref]:
            bad.append(cc)
    if bad:
        raise SystemExit(f"label equality FAILED for {bad}; the near-zero definition does not hold")
    return {"countries_checked": len(C.COHORT), "triplets": len(triplets), "mismatches": 0}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--out-dir", required=True)
    ap.add_argument("--triplets", default=str(BANK2_TRIPLETS))
    ap.add_argument("--profiles", default=str(BANK2_PROFILES))
    ap.add_argument("--gps", default=str(GPS_JSON))
    a = ap.parse_args()

    gps = json.loads(Path(a.gps).read_text())
    triplets = load_triplets(Path(a.triplets))
    proof = verify_all_labels(triplets, gps)
    print(f"label equality: {proof['countries_checked']} countries x {proof['triplets']} triplets, "
          f"{proof['mismatches']} mismatches")

    bank_run_id = json.loads((Path(a.profiles) / "manifest.json").read_text())["run_id"]
    members = F.unit_members(Path(a.gps), C.COHORT)
    cands = []
    cache: dict[str, tuple[list[dict], set[str]]] = {}
    for cc in C.COHORT:
        unit = F.unit_of_z(gps[cc])
        if unit not in cache:
            rows = load_profile_rows(Path(a.profiles), unit)
            cache[unit] = (rows, train_prompts(rows))
        rows, train = cache[unit]
        red = reduced_bank(rows, gps[cc], train)
        cands.append({"cc": cc, "profile": unit, "members": len(members[unit]),
                      "near_zero_dimensions": red["near_zero_dims"],
                      "exposure": red["train_dropped"], "train_kept": red["train_kept"]})
    subset = declare_subset(cands)
    print("candidates (near-zero training rows):")
    for c in sorted(cands, key=lambda c: (-c["exposure"], c["cc"])):
        if c["exposure"]:
            print(f"  {c['cc']} {c['profile']} members={c['members']} dims={','.join(c['near_zero_dimensions'])} "
                  f"train_rows_dropped={c['exposure']}")
    print(f"declared subset: singleton={subset['singleton']} multi={subset['multi']}")

    out = Path(a.out_dir)
    manifests = {}
    for role in ("singleton", "multi"):
        cc = subset[role]
        unit = F.unit_of_z(gps[cc])
        rows, train = cache[unit]
        red = reduced_bank(rows, gps[cc], train)
        m = write_bank(out, cc, unit, gps[cc], red, bank_run_id=bank_run_id, source_rows=len(rows),
                       source_sha256=_sha(Path(a.profiles) / f"D_syn_{unit}.jsonl"))
        manifests[cc] = m
        print(f"{role} {cc} {unit}: train {m['train_kept'] + m['train_dropped']} -> kept {m['train_kept']} "
              f"dropped {m['train_dropped']}; all rows kept {m['n_kept']} dropped {m['n_dropped']}")
    declaration = {"rule": "among cohort countries with >=1 dimension |z| < 0.10, the singleton-profile country and the "
                           "multi-member-profile country with the most near-zero TRAINING rows; ties -> first ISO3",
                   "uses_scores": False, "bank_run_id": bank_run_id, "label_equality": proof,
                   "subset": subset,
                   "candidates": sorted(cands, key=lambda c: (-c["exposure"], c["cc"])),
                   "manifests": {cc: str(out / cc / "manifest.json") for cc in manifests}}
    (out / "subset_declaration.json").write_text(json.dumps(declaration, indent=2) + "\n")
    print(f"wrote {out / 'subset_declaration.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
