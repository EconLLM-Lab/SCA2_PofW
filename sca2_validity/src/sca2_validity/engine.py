"""Minimal validity-profile engine: SCORE -> RESTRICT -> IDENTIFY.

A self-contained, dependency-light re-implementation of the *ideas* of the
cvprofiles methods package (menu of measurement functions, slack convention,
admissible set M*, image of a target functional on survivors, theta-grid as an
additive diagnostic). It does NOT import cvprofiles.

Key semantic choices (deliberate, documented):
  - ``corr_min``  : signed correlation floor  (corr(m, v) - theta >= 0)
  - ``corr_abs_min``: |corr(m, v)| - theta >= 0  (agnostic to direction)
  - ``corr_sign`` : sign * corr(m, v) - theta >= 0
  - ``mean_order``: direction * (mean(m | g==1) - mean(m | g==0)) - theta >= 0
  - beta is OPTIONAL: a pure measurement-recovery profile reports M* and
    slacks without inventing an outcome (unlike a full cvprofiles run).
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Literal

import numpy as np
import pandas as pd

RestrictionType = Literal["corr_min", "corr_abs_min", "corr_sign", "mean_order"]
_KNOWN_TYPES: frozenset[str] = frozenset(RestrictionType.__args__)  # type: ignore[attr-defined]


class SlackError(ValueError):
    """Loud slack-evaluation failure (bad schema reference, too few units)."""


@dataclass(frozen=True)
class Restriction:
    """One restriction r in R with threshold theta.

    params by type:
      corr_min / corr_abs_min : {"variable": <aux column>}
      corr_sign               : {"variable": <aux column>, "sign": +1 | -1}
      mean_order              : {"group": <binary group column>, "direction": +1 | -1,
                                 "min_count": int (default 1)}
    """

    id: str
    type: str
    theta: float
    params: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class Network:
    """Researcher-authored nomological network R with slack tolerance delta."""

    name: str | None = None
    delta: float = 0.0
    restrictions: tuple[Restriction, ...] = ()


@dataclass(frozen=True)
class Roles:
    """Column roles for the unit x measure score table."""

    unit_id: str = "unit_id"
    measures: tuple[str, ...] = ()
    aux: tuple[str, ...] = ()
    outcome: str | None = None
    diagnostic: tuple[str, ...] = ()


@dataclass(frozen=True)
class Beta:
    """Target functional. ``type="none"`` (or beta=None) -> validity-only profile."""

    type: str = "corr_y"
    outcome: str | None = None
    params: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Validation (fail loud on schema errors; never silently coerce)
# ---------------------------------------------------------------------------

def _require(predicate: bool, message: str) -> None:
    if not predicate:
        raise SlackError(message)


def validate_restriction(r: Restriction) -> None:
    _require(r.id.strip() != "", f"restriction id must be non-empty: {r.id!r}")
    _require(r.type in _KNOWN_TYPES, f"restriction type {r.type!r} has no evaluator (known: {sorted(_KNOWN_TYPES)})")
    _require(math.isfinite(float(r.theta)), f"restriction {r.id}: theta must be finite")
    p = r.params
    if r.type in ("corr_min", "corr_abs_min", "corr_sign"):
        _require(isinstance(p.get("variable"), str) and p["variable"].strip(), f"{r.id}: corr* requires params.variable")
        if r.type == "corr_sign":
            _require(p.get("sign") in (1, -1, 1.0, -1.0), f"{r.id}: corr_sign requires params.sign in {+1,-1}")
    elif r.type == "mean_order":
        _require(isinstance(p.get("group"), str) and p["group"].strip(), f"{r.id}: mean_order requires params.group")
        _require(p.get("direction") in (1, -1, 1.0, -1.0), f"{r.id}: mean_order requires params.direction in {+1,-1}")


def validate_network(network: Network) -> None:
    _require(network.delta >= 0.0, f"network {network.name}: delta must be >= 0")
    ids = [r.id for r in network.restrictions]
    _require(len(ids) == len(set(ids)), f"network {network.name}: restriction ids must be unique")
    for r in network.restrictions:
        validate_restriction(r)


# ---------------------------------------------------------------------------
# Slacks
# ---------------------------------------------------------------------------

def pearson_corr(x: np.ndarray, y: np.ndarray, min_n: int = 10) -> float:
    """Pairwise-complete Pearson correlation with a minimum-n guard."""
    _require(len(x) == len(y), "corr length mismatch")
    mask = np.isfinite(x) & np.isfinite(y)
    xc, yc = x[mask], y[mask]
    _require(len(xc) >= max(2, min_n), f"corr needs >= {min_n} complete units (have {len(xc)})")
    c = float(np.corrcoef(xc, yc)[0, 1])
    _require(math.isfinite(c), "corr produced non-finite result (zero variance?)")
    return c


def _group_means(measure: np.ndarray, group: np.ndarray, direction: float, min_count: int) -> float:
    mask = np.isfinite(measure) & np.isfinite(group)
    m, g = measure[mask], group[mask]
    _require(set(np.unique(g)).issubset({0.0, 1.0}), "mean_order group column must be binary (0/1)")
    g1, g0 = m[g == 1.0], m[g == 0.0]
    _require(len(g1) >= min_count and len(g0) >= min_count,
             f"mean_order needs >= {min_count} units per group (g1={len(g1)}, g0={len(g0)})")
    return direction * (float(np.mean(g1)) - float(np.mean(g0)))


def evaluate_slack(measure: np.ndarray, frame: pd.DataFrame, restriction: Restriction) -> float:
    """Sample slack s_r(m); satisfied when s_r >= -delta (delta applied by caller)."""
    validate_restriction(restriction)
    t = restriction.type
    theta = float(restriction.theta)
    p = restriction.params

    if t in ("corr_min", "corr_abs_min", "corr_sign"):
        var = str(p["variable"])
        _require(var in frame.columns, f"{restriction.id}: variable {var!r} not in score columns")
        c = pearson_corr(measure, frame[var].to_numpy(dtype=float))
        if t == "corr_abs_min":
            return abs(c) - theta
        sign = float(p.get("sign", 1.0)) if t == "corr_sign" else 1.0
        return sign * c - theta

    if t == "mean_order":
        group = str(p["group"])
        _require(group in frame.columns, f"{restriction.id}: group {group!r} not in score columns")
        direction = float(p.get("direction", 1.0))
        min_count = int(p.get("min_count", 1))
        return _group_means(measure, frame[group].to_numpy(dtype=float), direction, min_count) - theta

    raise SlackError(f"restriction type {t!r} has no evaluator")


def slack_matrix(frame: pd.DataFrame, measures: list[str], restrictions: list[Restriction]) -> pd.DataFrame:
    """Return DataFrame index=measures, columns=restriction ids, values=slacks."""
    data: dict[str, list[float]] = {r.id: [] for r in restrictions}
    for m in measures:
        _require(m in frame.columns, f"missing measure column {m!r}")
        mvec = frame[m].to_numpy(dtype=float)
        for r in restrictions:
            data[r.id].append(evaluate_slack(mvec, frame, r))
    return pd.DataFrame(data, index=list(measures))


# ---------------------------------------------------------------------------
# IDENTIFY
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class IdentifyResult:
    slacks: pd.DataFrame
    admissible: list[str]
    rejected: dict[str, list[str]]
    beta_values: dict[str, float] | None
    range_L: float | None
    range_U: float | None
    empty: bool
    point_id: bool
    delta: float
    measures: list[str]
    restriction_ids: list[str]


def run_identify(
    frame: pd.DataFrame,
    roles: Roles,
    network: Network,
    beta: Beta | None = None,
) -> IdentifyResult:
    """Slacks -> M* -> beta image -> [L,U]=min/max on survivors.

    Empty M* is a clean result, not an error. beta=None -> validity-only
    profile (no invented outcome, no range).
    """
    validate_network(network)
    measures = list(roles.measures)
    _require(len(measures) > 0, "roles.measures must be non-empty")

    try:
        slacks = slack_matrix(frame, measures, list(network.restrictions))
    except SlackError as exc:
        raise SlackError(f"IDENTIFY failed: {exc}") from exc

    delta = float(network.delta)
    admissible: list[str] = []
    rejected: dict[str, list[str]] = {}
    for m in measures:
        failing = [str(rid) for rid in slacks.columns if float(slacks.at[m, rid]) < -delta]
        if failing:
            rejected[m] = failing
        else:
            admissible.append(m)

    beta_values: dict[str, float] | None = None
    L: float | None = None
    U: float | None = None
    if beta is not None and beta.type != "none":
        _require(beta.outcome is not None and beta.outcome in frame.columns,
                 "beta.outcome must name a column in the score table")
        _require(beta.type == "corr_y", f"beta type {beta.type!r} not implemented (corr_y only)")
        beta_values = {m: pearson_corr(frame[m].to_numpy(dtype=float), frame[beta.outcome].to_numpy(dtype=float))
                       for m in measures}
        if admissible:
            b_star = [beta_values[m] for m in admissible]
            L, U = float(min(b_star)), float(max(b_star))

    return IdentifyResult(
        slacks=slacks,
        admissible=admissible,
        rejected=rejected,
        beta_values=beta_values,
        range_L=L,
        range_U=U,
        empty=len(admissible) == 0,
        point_id=len(admissible) == 1,
        delta=delta,
        measures=measures,
        restriction_ids=[r.id for r in network.restrictions],
    )


# ---------------------------------------------------------------------------
# Theta-grid (additive diagnostic; lambda=1.0 is the headline)
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ThetaGridRow:
    lambda_value: float
    admissible: list[str]
    rejected: dict[str, list[str]]
    empty: bool
    range_L: float | None
    range_U: float | None


@dataclass(frozen=True)
class ThetaGridResult:
    lambdas: list[float]
    rows: list[ThetaGridRow]


def _scaled_network(network: Network, lam: float) -> Network:
    return Network(
        name=network.name,
        delta=network.delta,
        restrictions=tuple(
            Restriction(id=r.id, type=r.type, theta=float(r.theta) * lam, params=dict(r.params))
            for r in network.restrictions
        ),
    )


def run_theta_grid(
    frame: pd.DataFrame,
    roles: Roles,
    network: Network,
    lambdas: list[float],
    beta: Beta | None = None,
) -> ThetaGridResult:
    """Recompute M* on a declared grid of threshold multipliers. Diagnostic only."""
    rows: list[ThetaGridRow] = []
    for lam in lambdas:
        _require(math.isfinite(float(lam)) and float(lam) > 0.0, "theta-grid lambdas must be finite and > 0")
        res = run_identify(frame, roles, _scaled_network(network, lam), beta=beta)
        rows.append(
            ThetaGridRow(
                lambda_value=float(lam),
                admissible=res.admissible,
                rejected=res.rejected,
                empty=res.empty,
                range_L=res.range_L,
                range_U=res.range_U,
            )
        )
    return ThetaGridResult(lambdas=[float(x) for x in lambdas], rows=rows)
