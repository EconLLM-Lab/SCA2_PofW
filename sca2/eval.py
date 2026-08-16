"""sca2 eval — freeze a WVS transport plan. Does not score a model."""

from __future__ import annotations

import csv
import json
from collections import Counter
from pathlib import Path
from typing import Any

from .protocol import load_protocol, repo_root, resolve_repo_path
from .runs import format_receipt, new_run_id, prepare_run_dir, write_receipt


def inspect_item_map(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(f"eval item map not found: {path}")
    with path.open(encoding="utf-8", newline="") as handle:
        rows = list(csv.DictReader(handle))
    dims: Counter[str] = Counter()
    mapped = 0
    demographic = 0
    questions: list[str] = []
    for row in rows:
        q = (row.get("Question") or "").strip()
        if not q:
            continue
        questions.append(q)
        dim = (row.get("gps_dimension") or "").strip()
        if dim:
            mapped += 1
            dims[dim] += 1
        else:
            demographic += 1
    return {
        "path": str(path),
        "n_rows": len(questions),
        "n_mapped": mapped,
        "n_demographic": demographic,
        "per_dimension": dict(dims),
        "questions": questions,
    }


def build_eval_plan(protocol: dict[str, Any], item_report: dict[str, Any]) -> dict[str, Any]:
    ev = protocol["eval"]
    return {
        "surface": ev.get("surface"),
        "item_map": item_report["path"],
        "n_items": item_report["n_rows"],
        "n_mapped": item_report["n_mapped"],
        "n_demographic": item_report["n_demographic"],
        "per_dimension": item_report["per_dimension"],
        "country_conditioning": ev.get("country_conditioning"),
        "primary_metric": ev.get("primary_metric"),
        "matched_vs_cross_means": ev.get("matched_vs_cross_means"),
        "notebook_score": ev.get("notebook_score"),
        "notebook_analyze": ev.get("notebook_analyze"),
        "execute": False,
        "claim_boundary": (
            "Option-likelihood TVD is predictive-criterion evidence for the protocol. "
            "It is not recovery of P_human. With country_conditioning=false, "
            "matched-vs-cross is proximity of one fixed model distribution to two "
            "population distributions, not country-conditioned inference."
        ),
    }


def run_eval(
    protocol_path: str | Path,
    *,
    execute: bool = False,
    runs_root: Path | None = None,
) -> dict[str, Any]:
    protocol = load_protocol(protocol_path)
    if execute:
        raise RuntimeError(
            "Refusing to execute evaluation. GPU option-likelihood scoring still lives in "
            f"{protocol['eval'].get('notebook_score')}. sca2 eval writes a plan first."
        )

    item_path = resolve_repo_path(protocol["eval"]["item_map"], repo_root())
    item_report = inspect_item_map(item_path)
    plan = build_eval_plan(protocol, item_report)

    run_id = new_run_id(str(protocol["name"]))
    run_dir = prepare_run_dir(
        Path(runs_root) if runs_root else repo_root() / "runs",
        run_id,
        protocol,
    )
    (run_dir / "eval_plan.json").write_text(json.dumps(plan, indent=2) + "\n", encoding="utf-8")
    receipt = {
        "run_id": run_id,
        "stage": "eval",
        "status": "planned",
        "protocol_name": protocol["name"],
        "protocol_hash": protocol["_hash"],
        "protocol_path": protocol["_path"],
        "rows": item_report["n_mapped"],
        "rule": protocol["eval"].get("primary_metric"),
        "out": str(run_dir / "eval_plan.json"),
        "surface": protocol["eval"].get("surface"),
        "country_conditioning": protocol["eval"].get("country_conditioning"),
        "matched_vs_cross_means": protocol["eval"].get("matched_vs_cross_means"),
    }
    write_receipt(run_dir, receipt)
    print(format_receipt(receipt))
    print(
        f"items     {item_report['n_rows']}  "
        f"mapped={item_report['n_mapped']}  "
        f"demographic={item_report['n_demographic']}"
    )
    print(f"claim     {plan['matched_vs_cross_means']}")
    return receipt
