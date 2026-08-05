"""Thin REPORT: machine-readable JSON + a readable one-page HTML artifact."""
from __future__ import annotations

import html
import json
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sca2_validity.engine import IdentifyResult, ThetaGridResult
from sca2_validity.freeze import compute_run_id, hash_payload


def build_report_payload(
    *,
    title: str,
    run_id: str,
    scores_hash: str,
    network_hash: str,
    protocol_hash: str,
    seed: int,
    roles: Any,
    network: Any,
    beta: Any | None,
    identify: IdentifyResult,
    theta_grid: ThetaGridResult | None,
    notes: str = "",
) -> dict[str, Any]:
    """Assemble the full JSON audit payload (hashes + slacks + M* + range)."""
    slacks_dict: dict[str, dict[str, float]] = {}
    for m in identify.measures:
        slacks_dict[m] = {
            rid: float(identify.slacks.at[m, rid]) for rid in identify.restriction_ids
        }
    grid_payload: dict[str, Any] | None = None
    if theta_grid is not None:
        grid_payload = {
            "lambdas": theta_grid.lambdas,
            "headline_lambda": 1.0,
            "rows": [asdict(row) for row in theta_grid.rows],
            "note": "Diagnostic threshold-sensitivity surface; not part of run_id.",
        }
    return {
        "schema_version": "1",
        "title": title,
        "run_id": run_id,
        "created_at": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "package_version": __import__("sca2_validity.freeze", fromlist=["PACKAGE_VERSION"]).PACKAGE_VERSION,
        "hashes": {
            "scores": scores_hash,
            "network": network_hash,
            "protocol": protocol_hash,
            "seed": int(seed),
        },
        "roles": asdict(roles),
        "network": {
            "name": network.name,
            "delta": network.delta,
            "restrictions": [asdict(r) for r in network.restrictions],
        },
        "beta": asdict(beta) if beta is not None else None,
        "identify": {
            "empty": identify.empty,
            "point_id": identify.point_id,
            "M_star": identify.admissible,
            "rejected": identify.rejected,
            "delta": identify.delta,
            "L": identify.range_L,
            "U": identify.range_U,
            "n_menu": len(identify.measures),
            "n_admissible": len(identify.admissible),
            "beta_values": identify.beta_values,
            "slacks": slacks_dict,
        },
        "theta_grid": grid_payload,
        "notes": notes,
    }


def write_report_json(payload: dict[str, Any], out_dir: Path) -> Path:
    path = out_dir / "profile.json"
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n")
    return path


def write_report_html(payload: dict[str, Any], out_dir: Path) -> Path:
    """Minimal dependency-free HTML audit page (readable by a non-coder)."""
    ident = payload["identify"]
    esc = html.escape

    def cell_class(m: str) -> str:
        return "ok" if m in ident["M_star"] else "no"

    rows = []
    for m, slacks in ident["slacks"].items():
        cells = "".join(
            f'<td class="{cell_class(m)}">{float(slacks.get(rid, float("nan"))):.4f}</td>'
            for rid in [r["id"] for r in payload["network"]["restrictions"]]
        )
        rows.append(
            f"<tr><td>{esc(m)}</td><td>{'ADMISSIBLE' if m in ident['M_star'] else 'rejected'}</td>{cells}</tr>"
        )

    grid_section = ""
    if payload.get("theta_grid") is not None:
        grid_section = "<h2>Theta-grid (diagnostic)</h2><table><tr><th>lambda</th><th>M*</th><th>range</th></tr>"
        for row in payload["theta_grid"]["rows"]:
            rang = f"[{row['range_L']:.4f}, {row['range_U']:.4f}]" if row["range_L"] is not None else "empty M*"
            grid_section += (
                f"<tr><td>{row['lambda_value']}</td><td>{', '.join(row['admissible']) or '∅'}</td><td>{esc(rang)}</td></tr>"
            )
        grid_section += "</table>"

    headline = (
        f"<h2>Construct-identified range</h2><p><b>[L, U] = [{ident['L']:.4f}, {ident['U']:.4f}]</b> "
        f"(image of beta on survivors only)</p>"
        if ident["L"] is not None
        else "<h2>Construct-identified range</h2><p><b>Empty M* — nothing admissible under this network.</b> "
             "This is an honest result, not a failure.</p>"
    )

    page = f"""<!DOCTYPE html>
<html><head><meta charset="utf-8"><title>{esc(payload['title'])}</title>
<style>
 body {{ font-family: -apple-system, system-ui, sans-serif; margin: 2rem; color: #222; }}
 table {{ border-collapse: collapse; margin: 1rem 0; }}
 td, th {{ border: 1px solid #ccc; padding: 4px 10px; font-size: 14px; }}
 td.ok {{ background: #e8f5e9; }} td.no {{ background: #fdecea; }}
 code {{ background: #f4f4f4; padding: 1px 4px; }}
</style></head><body>
<h1>{esc(payload['title'])}</h1>
<p>run_id: <code>{esc(payload['run_id'])}</code> · package <code>{esc(payload['package_version'])}</code> ·
created {esc(payload['created_at'])}</p>
<h2>Admissible set M*</h2>
<p><b>{', '.join(esc(m) for m in ident['M_star']) or '∅ (empty)'}</b> · {ident['n_admissible']}/{ident['n_menu']} measures</p>
{headline}
<h2>Slack table (measure x restriction)</h2>
<table><tr><th>measure</th><th>status</th>{''.join(f'<th>{esc(r["id"])}</th>' for r in payload['network']['restrictions'])}</tr>
{''.join(rows)}</table>
{grid_section}
<h2>Notes</h2><pre>{esc(payload['notes'])}</pre>
</body></html>"""
    path = out_dir / "report.html"
    path.write_text(page)
    return path


def write_artifacts(payload: dict[str, Any], out_dir: Path) -> dict[str, Path]:
    out_dir.mkdir(parents=True, exist_ok=True)
    return {
        "profile.json": write_report_json(payload, out_dir),
        "report.html": write_report_html(payload, out_dir),
    }
