#!/usr/bin/env python3
"""Replace USA/MEX adapter rows in the paper score file with the first-wave scores."""
from __future__ import annotations

import hashlib
import shutil
from pathlib import Path

import numpy as np
import pandas as pd

REPO = Path("/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW")
PAPER = REPO / "analysis/phase2/outputs/paper_a"
FROZEN = PAPER / "country_item_scores.csv"
STAMP = PAPER / "country_item_scores_SUPERSEDED_stitched_20260925.csv"
KSENIA = REPO / "data/phase2/raw/wvs/ksenias_base8"
INVERT_1_4 = {
    "Q59", "Q61", "Q62", "Q63", "Q64", "Q69", "Q70", "Q71",
    "Q58", "Q60", "Q73", "Q81",
}
INVERT_10 = {"Q177", "Q179"}
BINARY = {"Q57"}


def recode(v, item):
    s = float(v)
    if item in INVERT_1_4:
        return 5.0 - s
    if item in INVERT_10:
        return 11.0 - s
    if item in BINARY:
        return 1.0 if s == 1.0 else 0.0
    return s


def wave_rows(cc: str) -> pd.DataFrame:
    opt = pd.read_csv(
        KSENIA / f"model_option_probabilities_{cc}_adapter_on_{cc}.csv",
        usecols=["question_id", "option_value", "model_prob"],
    )
    met = pd.read_csv(
        KSENIA / f"survey_question_metrics_{cc}_adapter_on_{cc}.csv",
        usecols=["question_id", "tv_distance"],
    )
    rows = []
    for q, g in opt.groupby("question_id"):
        pm = g.model_prob.to_numpy(float)
        if pm.sum() <= 0:
            continue
        pm = pm / pm.sum()
        rec = np.array([recode(v, q) for v in g.option_value.to_numpy(float)])
        rows.append({"country": cc, "item": q, "raw": float((rec * pm).sum())})
    out = pd.DataFrame(rows)
    out = out.merge(met, left_on="item", right_on="question_id", how="left")
    return out


def sha(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def main() -> None:
    if not STAMP.exists():
        shutil.copy2(FROZEN, STAMP)
    old = sha(STAMP)
    df = pd.read_csv(STAMP)
    for cc in ("USA", "MEX"):
        wave = wave_rows(cc)
        for row in wave.itertuples(index=False):
            mask = (df.arm == "adapter") & (df.country == cc) & (df.item == row.item)
            if mask.sum() != 1:
                continue
            df.loc[mask, "raw"] = row.raw
            if np.isfinite(row.tv_distance):
                df.loc[mask, "tvd"] = row.tv_distance
    df.to_csv(FROZEN, index=False)
    print("old_sha", old)
    print("new_sha", sha(FROZEN))
    print("stamped", STAMP)


if __name__ == "__main__":
    main()
