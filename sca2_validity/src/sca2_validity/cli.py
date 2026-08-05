"""Thin CLI: run a frozen profile, print JSON to stdout, humans to stderr.

Extracted contract from cvprofiles: stdout is machine-readable JSON; empty M*
is an exit-0 success path; fail loud only on schema/IO/evaluator errors.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd
import yaml

from sca2_validity.engine import Beta, Network, Restriction, Roles, SlackError, run_identify, run_theta_grid
from sca2_validity.freeze import PACKAGE_VERSION, compute_run_id, hash_payload
from sca2_validity.report import build_report_payload, write_artifacts


def _parse_lambdas(raw: str | None) -> list[float] | None:
    if raw is None:
        return None
    tokens = [t.strip() for t in raw.split(",") if t.strip()]
    if not tokens:
        raise ValueError("theta-grid must be a non-empty comma-separated list of positive numbers")
    values: list[float] = []
    for token in tokens:
        try:
            value = float(token)
        except ValueError as exc:
            raise ValueError(f"invalid lambda {token!r}") from exc
        if value <= 0.0:
            raise ValueError(f"lambda {token!r} must be > 0")
        if value in values:
            raise ValueError(f"duplicate lambda {token!r}")
        values.append(value)
    return values


def _load_roles(path: Path) -> Roles:
    data = json.loads(path.read_text())
    return Roles(
        unit_id=data.get("unit_id", "unit_id"),
        measures=tuple(data.get("measures", [])),
        aux=tuple(data.get("aux", [])),
        outcome=data.get("outcome"),
        diagnostic=tuple(data.get("diagnostic", [])),
    )


def _load_network(path: Path) -> Network:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("network YAML must be a mapping")
    restrictions = []
    for spec in data.get("restrictions", []):
        restrictions.append(
            Restriction(
                id=spec["id"],
                type=spec["type"],
                theta=float(spec["theta"]),
                params=dict(spec.get("params", {})),
            )
        )
    return Network(name=data.get("name"), delta=float(data.get("delta", 0.0)), restrictions=tuple(restrictions))


def _load_beta(path: Path | None) -> Beta | None:
    if path is None:
        return None
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise ValueError("beta YAML must be a mapping")
    return Beta(
        type=str(data.get("type", "corr_y")),
        outcome=data.get("outcome"),
        params=dict(data.get("params", {})),
    )


def _load_table(path: Path) -> pd.DataFrame:
    if path.suffix == ".csv":
        return pd.read_csv(path)
    if path.suffix in (".parquet", ".pq"):
        return pd.read_parquet(path)
    raise ValueError(f"unsupported scores format: {path.suffix} (use .csv or .parquet)")


def _add_run_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--scores", required=True, type=Path, help="unit x measure score table (.csv/.parquet)")
    parser.add_argument("--roles", required=True, type=Path, help="roles.json: unit_id/measures/aux/outcome")
    parser.add_argument("--network", required=True, type=Path, help="network.yaml: restrictions + theta + delta")
    parser.add_argument("--beta", type=Path, default=None, help="beta.yaml (optional; omit for validity-only profile)")
    parser.add_argument("--theta-grid", default=None, help="comma-separated positive threshold multipliers (diagnostic)")
    parser.add_argument("--seed", type=int, default=0, help="pinned seed (part of run id)")
    parser.add_argument("--protocol-hash", default="", help="hash of the frozen scoring protocol (from prep)")
    parser.add_argument("--out", type=Path, default=None, help="output dir (default: runs/<run_id>/)")
    parser.add_argument("--title", default="Construct-validity profile")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="sca2-validity", description="Validity profiles: M* over a menu of measures.")
    parser.add_argument("--version", action="version", version=f"sca2-validity {PACKAGE_VERSION}")
    sub = parser.add_subparsers(dest="command", required=True)
    run_parser = sub.add_parser("run", help="SCORE -> RESTRICT -> IDENTIFY -> REPORT")
    _add_run_args(run_parser)
    args = parser.parse_args(argv)

    try:
        lambdas = _parse_lambdas(args.theta_grid)
    except ValueError as exc:
        print(f"error: theta-grid: {exc}", file=sys.stderr)
        return 2

    try:
        import pandas as pd

        frame = _load_table(args.scores)
        roles = _load_roles(args.roles)
        network = _load_network(args.network)
        beta = _load_beta(args.beta)

        # fail loud on column drift between roles and the table
        table_cols = set(frame.columns)
        needed = {roles.unit_id, *roles.measures, *roles.aux, *(roles.outcome or [])}
        missing = needed - table_cols
        if missing:
            raise ValueError(f"score table missing columns: {sorted(missing)}")

        scores_hash = hash_payload(frame.sort_values(roles.unit_id).to_dict(orient="records"))
        network_hash = hash_payload(
            {"name": network.name, "delta": network.delta,
             "restrictions": [{"id": r.id, "type": r.type, "theta": r.theta, "params": r.params}
                              for r in network.restrictions]}
        )
        run_id = compute_run_id(scores_hash, network_hash, args.protocol_hash or "unpinned", args.seed)

        identify = run_identify(frame, roles, network, beta=beta)
        theta_grid = run_theta_grid(frame, roles, network, lambdas, beta=beta) if lambdas else None

        out_dir = args.out or (Path("runs") / run_id)
        payload = build_report_payload(
            title=args.title,
            run_id=run_id,
            scores_hash=scores_hash,
            network_hash=network_hash,
            protocol_hash=args.protocol_hash or "unpinned",
            seed=args.seed,
            roles=roles,
            network=network,
            beta=beta,
            identify=identify,
            theta_grid=theta_grid,
            notes="sca2_validity minimal engine; network content authored by the researcher.",
        )
        write_artifacts(payload, out_dir)

        summary = {
            "run_id": run_id,
            "out_dir": str(out_dir),
            "empty": identify.empty,
            "M_star": identify.admissible,
            "rejected": identify.rejected,
            "L": identify.range_L,
            "U": identify.range_U,
            "point_id": identify.point_id,
            "n_measures": len(identify.measures),
            "theta_grid": {"lambdas": lambdas} if lambdas else None,
            "report_html": str(out_dir / "report.html"),
            "profile_json": str(out_dir / "profile.json"),
        }
        print(json.dumps(summary, indent=2))
        if identify.empty:
            print("empty M* — clean success; see report.html for binding restrictions", file=sys.stderr)
        else:
            print(
                f"M*={identify.admissible}  [L,U]=[{identify.range_L}, {identify.range_U}]",
                file=sys.stderr,
            )
        return 0
    except (SlackError, ValueError, OSError, KeyError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
