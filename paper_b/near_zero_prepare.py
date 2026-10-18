#!/usr/bin/env python3
"""Paper B, C6 — prepare the DPO training files of the four near-zero units (GBR, COL, GBR_control, COL_control).

Reads each unit's reduced bank (SHA-256 checked against its manifest), re-derives from the FULL profile bank that
(a) every row's labels equal the profile file's, and (b) every row's `split` is the pipeline's shared split of
the full bank. It then takes the `split == "train"` rows, normalizes them like prepare_data.py, joins the pinned
reference log-probs by (prompt, completion), and writes `<unit>_train_with_ref.jsonl` to config.PREPARED_DIR.
It fails (writes nothing for that unit) on any mismatch, any missing reference pair, or a row count other than the
manifest's. main() also asserts the declared counts (GBR/GBR_control 164, COL/COL_control 260).

    SCA2_PB_PROTOCOL=bank2 SCA2_PB_UNITS=profiles SCA2_PB_NEARZERO=<dir> SCA2_PB_DATA_ROOT=<root> \\
        SCA2_PB_BANK2_DIR=... SCA2_PB_PROFILE_DIR=... python paper_b/near_zero_prepare.py [--countries GBR COL ...]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import lib  # noqa: E402
import near_zero_bank as NZ  # noqa: E402
import protocol_bank2 as P2  # noqa: E402

EXPECTED_TRAIN_ROWS = dict(P2.NEARZERO_EXPECTED_TRAIN)


def prepare_unit(unit: str, nz_dir, profile_dir, cache: dict, out_dir, expected: dict | None = None) -> int:
    """Write <unit>_train_with_ref.jsonl and return its row count. Raises RuntimeError and writes nothing on a failed check."""
    nz_dir, out_dir = Path(nz_dir), Path(out_dir)
    manifest = json.loads((nz_dir / unit / "manifest.json").read_text())
    bank = nz_dir / unit / manifest["file"]
    got = hashlib.sha256(bank.read_bytes()).hexdigest()
    if got != manifest["sha256"][manifest["file"]]:
        raise RuntimeError(f"{unit}: sha256 of {bank.name} differs from its manifest")
    rows = lib.load_jsonl(bank)

    profile_rows = NZ.load_profile_rows(Path(profile_dir), manifest["profile_unit"])
    by_id = {r["triplet_id"]: r for r in profile_rows}
    train = NZ.train_prompts(profile_rows)
    for r in rows:
        src = by_id.get(r["triplet_id"])
        if src is None or NZ.label_key(src) != NZ.label_key(r):
            raise RuntimeError(f"{unit}: label of triplet {r['triplet_id']} differs from the profile file")
    for r in rows:
        want = "train" if lib.normalize_prompt(r["prompt"]) in train else "eval"
        if r.get("split") != want:
            raise RuntimeError(f"{unit}: triplet {r['triplet_id']} has split {r.get('split')!r}, the full-bank split says {want!r}")

    train_rows = [r for r in rows if r["split"] == "train"]
    n = len(train_rows)
    if n != int(manifest["train_kept"]):
        raise RuntimeError(f"{unit}: {n} train rows in the file, manifest says {manifest['train_kept']}")
    if expected is not None and n != expected[unit]:
        raise RuntimeError(f"{unit}: {n} train rows, declared {expected[unit]}")

    prepared, missing = [], 0
    for r in sorted((lib.normalize_row(r) for r in train_rows), key=lambda r: r["prompt"]):
        row = dict(r)
        try:
            row["ref_chosen_logps"] = cache[(row["prompt"], row["chosen"])]
            row["ref_rejected_logps"] = cache[(row["prompt"], row["rejected"])]
        except KeyError:
            missing += 1
            continue
        row["country"] = unit
        row["item_id"] = f"{unit}_train_{len(prepared):04d}"
        prepared.append(row)
    if missing:
        raise RuntimeError(f"{unit}: {missing} training rows have a (prompt, completion) pair missing from the reference cache")
    lib.write_jsonl(prepared, out_dir / f"{unit}_train_with_ref.jsonl")
    return n


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--countries", nargs="*", default=list(P2.NEARZERO_UNITS))
    a = ap.parse_args(argv)
    import config as C
    nz = getattr(C, "NEARZERO_DIR", None)
    if nz is None:
        print("refusing: SCA2_PB_NEARZERO is not set, so config carries no near-zero units")
        return 2
    units = list(a.countries)                      # exact unit names: GBR, COL, GBR_control, COL_control
    bad = [u for u in units if u not in P2.NEARZERO_UNITS]
    if bad:
        print(f"refusing unknown units: {bad}")
        return 2
    if not C.REF_CACHE_FILE.exists():
        print(f"reference cache missing: {C.REF_CACHE_FILE}")
        return 3
    cache = lib.load_shared_cache(C.REF_CACHE_FILE)
    print(f"reference cache: {len(cache)} pairs")
    for u in units:
        n = prepare_unit(u, nz, C.BANK_DIR, cache, C.PREPARED_DIR, expected=EXPECTED_TRAIN_ROWS)
        print(f"{u}: wrote {n} training rows -> {C.PREPARED_DIR / (u + '_train_with_ref.jsonl')}")
    print(f"prepared {len(units)} near-zero units")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
