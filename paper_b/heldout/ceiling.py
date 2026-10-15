#!/usr/bin/env python3
"""Human test-retest ceiling: WVS wave 6 vs wave 7 country means, via the Time Series.

Crosswalk (WVS-7 item -> Time-Series variable), blind-safe by construction:
  1. shortlist the k Time-Series variables whose labels best match the WVS-7 variable
     label (token Jaccard), so only those columns are ever read;
  2. read wave-7 rows of the shortlisted columns and accept the candidate whose
     unweighted country means correlate with the WVS-7 item's at r >= 0.999 over
     >= 30 countries (the same respondents appear in both files, so a true match is
     near-identical); otherwise the item is left unmatched and reported.
Ceiling per matched item: Spearman of weighted country means, wave 6 vs wave 7, over
the cohort countries present in both waves.

Items outside the 23 already-analysed battery items are held-out and pass
`freeze.require_freeze` first.

Usage:
  python paper_b/heldout/ceiling.py --items strict --out <dir>
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd

HERE = Path(__file__).resolve().parent
REPO = HERE.parents[1]
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(REPO / "paper_b"))
import freeze as FR  # noqa: E402

TS = REPO / "data/WVS/timeseries/WVS_Time_Series_1981-2022_stata_v5_0.dta"
WVS7 = REPO / "data/WVS/WVS_wave7.dta"
FREEZE = HERE / "FREEZE.json"
_TOK = re.compile(r"[a-z]+")
_STOP = {"the", "of", "a", "to", "in", "and", "your", "you", "for", "how", "much", "is", "be"}


def _stem(t: str) -> str:
    return t[:-1] if len(t) > 3 and t.endswith("s") and not t.endswith("ss") else t


def _tokens(s: str) -> set[str]:
    return {_stem(t) for t in _TOK.findall(str(s).lower()) if t not in _STOP}


def shortlist(label: str, ts_labels: dict[str, str], k: int = 6) -> list[str]:
    q = _tokens(label)
    scored = []
    for name, lab in ts_labels.items():
        t = _tokens(lab)
        j = len(q & t) / len(q | t) if q and t else 0.0
        scored.append((-j, name))
    return [n for s, n in sorted(scored)[:k] if s < 0]


def candidates(label: str, ts_labels: dict[str, str], *, k: int,
               hint: list[str] | None = None) -> list[str]:
    """Label shortlist plus explicit hints; every candidate still faces accept()."""
    out = shortlist(label, ts_labels, k=k)
    for h in hint or []:
        if h in ts_labels and h not in out:
            out.append(h)
    return out


# Auditable crosswalk hints, for items whose labels share no stem with the TS label.
HINTS = {"Q106": ["E035"]}


def wave_means(df: pd.DataFrame, var: str, *, wave: int, weight: str | None = None,
               country: str = "country", wave_col: str = "wave") -> pd.Series:
    d = df[(df[wave_col] == wave) & (df[var] >= 0)]
    if weight:
        w = d[weight].astype(float)
        return (d[var] * w).groupby(d[country]).sum() / w.groupby(d[country]).sum()
    return d.groupby(country)[var].mean()


def accept(item: pd.Series, candidates: dict[str, pd.Series], *, min_r: float = 0.999,
           min_countries: int = 30) -> tuple[str | None, dict[str, float]]:
    table = {}
    for name, s in candidates.items():
        d = pd.concat([item.rename("i"), s.rename("c")], axis=1).dropna()
        table[name] = float(d.i.corr(d.c)) if len(d) >= min_countries else float("nan")
    ok = {n: r for n, r in table.items() if not np.isnan(r) and r >= min_r}
    return (max(ok, key=ok.get) if ok else None), table


def guard_items(items: list[str], *, strict_ids: set[str], freeze_path: Path = FREEZE) -> list[str]:
    if any(q not in strict_ids for q in items):
        FR.require_freeze(freeze_path)
    return list(items)


def run(items: list[str], cohort: list[str], out_dir: Path, k: int = 10) -> dict:
    import pyreadstat
    _, m7 = pyreadstat.read_dta(str(WVS7), metadataonly=True, encoding="latin1")
    lab7 = dict(zip(m7.column_names, m7.column_labels))
    _, mts = pyreadstat.read_dta(str(TS), metadataonly=True, encoding="latin1")
    labts = {n: l or "" for n, l in zip(mts.column_names, mts.column_labels)
             if re.match(r"^[A-Z]\d{3}", n)}
    short = {q: candidates(lab7[q], labts, k=k, hint=HINTS.get(q)) for q in items}
    cols = sorted({c for v in short.values() for c in v})
    ts, _ = pyreadstat.read_dta(str(TS), usecols=["S002VS", "COUNTRY_ALPHA", "S017"] + cols,
                                encoding="latin1")
    ts = ts.rename(columns={"S002VS": "wave", "COUNTRY_ALPHA": "country"})
    w7, _ = pyreadstat.read_dta(str(WVS7), usecols=["B_COUNTRY_ALPHA"] + items, encoding="latin1")
    w7 = w7.rename(columns={"B_COUNTRY_ALPHA": "country"}).assign(wave=7)

    crosswalk, ceiling_rows = {}, []
    for q in items:
        item_means = wave_means(w7, q, wave=7)
        cands = {c: wave_means(ts, c, wave=7) for c in short[q]}
        best, table = accept(item_means, cands)
        crosswalk[q] = {"wvs7_label": lab7[q], "accepted": best,
                        "accepted_label": labts.get(best) if best else None,
                        "candidates": {c: {"label": labts[c], "r": table[c]} for c in short[q]}}
        if not best:
            continue
        m6 = wave_means(ts, best, wave=6, weight="S017").reindex(cohort)
        m7 = wave_means(ts, best, wave=7, weight="S017").reindex(cohort)
        both = pd.concat([m6.rename("w6"), m7.rename("w7")], axis=1).dropna()
        ceiling_rows.append({
            "question_id": q, "ts_variable": best, "n_countries": int(len(both)),
            "spearman_w6_w7": float(both.w6.corr(both.w7, method="spearman"))
            if len(both) > 3 else float("nan"),
            "pearson_w6_w7": float(both.w6.corr(both.w7)) if len(both) > 3 else float("nan"),
        })
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "ts_crosswalk.json").write_text(json.dumps(crosswalk, indent=1) + "\n")
    cdf = pd.DataFrame(ceiling_rows)
    cdf.to_csv(out_dir / "ceiling_items.csv", index=False)
    return {"items": len(items), "matched": int(sum(v["accepted"] is not None for v in crosswalk.values())),
            "median_spearman": float(cdf.spearman_w6_w7.median()) if len(cdf) else float("nan")}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--items", default="strict", help="'strict' or a JSON list file of item ids")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    import build_scoring_spec as B
    import config as C
    strict = B.strict_item_ids()
    items = sorted(strict, key=lambda s: int(s[1:])) if a.items == "strict" \
        else json.loads(Path(a.items).read_text())
    items = guard_items(items, strict_ids=set(strict))
    print(json.dumps(run(items, list(C.COHORT), Path(a.out)), indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
