"""Paper B — pure scoring logic (no torch).

Mirrors `DPO_eval_WVS/DPO_survey_distribution_evaluation.ipynb` cells 5-8 and
13 exactly: option-code parsing, the survey user prompt, population
distributions, and the per-question metrics. Everything here is deterministic
and testable on CPU; the model forward pass lives in `score_cohort.py`.

Fidelity rules (do not "improve" these):
  * option codes come from `question_map_wvs_edited.csv` (`ResponseCodes`),
    not from `survey_spec.json`;
  * numeric-open grids are the *observed* support inside the scored countries —
    this is country-set dependent, so the archived grids are pinned by the gate;
  * a completion is the leading space plus the code, summed without length
    normalization, then softmaxed over the supplied codes at temperature 1.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

import eval_config as E


# ---------------------------------------------------------------- option parsing
def canonical_code(value) -> str:
    """Stable string form for a numeric response code (3.0 -> '3')."""
    number = float(value)
    if not np.isfinite(number):
        raise ValueError(f"Non-finite response code: {value}")
    if number.is_integer():
        return str(int(number))
    return format(number, "g")


def parse_semicolon_field(value) -> list[str]:
    if value is None or (isinstance(value, float) and np.isnan(value)) or pd.isna(value):
        return []
    return [part.strip() for part in str(value).split(";") if part.strip()]


def parse_fixed_options(row) -> tuple[list[str], list[str]]:
    codes = [canonical_code(c) for c in parse_semicolon_field(row["ResponseCodes"])]
    labels = parse_semicolon_field(row["ResponseLabels"])
    labels = labels[: len(codes)]
    labels += codes[len(labels):]
    labels = [code if str(label).lower() == "nan" else label
              for code, label in zip(codes, labels)]
    return codes, labels


# ---------------------------------------------------------------- inputs
def load_question_map(path=None) -> pd.DataFrame:
    path = path or E.QUESTION_MAP_FILE
    qmap = pd.read_csv(path).drop(columns=["Unnamed: 0"], errors="ignore").copy()
    qmap["Question"] = qmap["Question"].astype(str).str.strip()
    qmap["StandaloneQuestion"] = qmap["StandaloneQuestion"].astype(str).str.strip()
    dupes = qmap.loc[qmap["Question"].duplicated(), "Question"].tolist()
    if dupes:
        raise ValueError(f"Duplicate question IDs in map: {dupes}")
    return qmap


def load_survey_frames(countries, wvs_dir=None) -> dict[str, pd.DataFrame]:
    wvs_dir = wvs_dir or E.WVS_DIR
    frames = {}
    for cc in countries:
        path = wvs_dir / f"{cc}_WVS_wave7.parquet"
        if not path.exists():
            raise FileNotFoundError(f"missing population file: {path}")
        frame = pd.read_parquet(path)
        frame.columns = [str(c).strip() for c in frame.columns]
        if E.USE_SURVEY_WEIGHTS and E.WEIGHT_COLUMN not in frame.columns:
            raise ValueError(f"{cc}: weight column {E.WEIGHT_COLUMN!r} not found")
        frames[cc] = frame
    return frames


def observed_numeric_support(question_id, survey_frames) -> list[str]:
    lower, upper = E.NUMERIC_VALID_RANGES.get(question_id, (-np.inf, np.inf))
    values: list[float] = []
    for frame in survey_frames.values():
        series = pd.to_numeric(frame[question_id], errors="coerce")
        series = series[np.isfinite(series)]
        series = series[(series >= lower) & (series <= upper)]
        values.extend(series.tolist())
    if not values:
        raise ValueError(f"No valid numeric responses for {question_id}")
    support = sorted({int(round(v)) for v in values})
    if len(support) > E.MAX_NUMERIC_SUPPORT:
        raise ValueError(
            f"{question_id} has {len(support)} observed values, above "
            f"MAX_NUMERIC_SUPPORT={E.MAX_NUMERIC_SUPPORT}")
    return [str(v) for v in support]


def build_question_specs(question_map, survey_frames,
                         numeric_support: dict[str, list[str]] | None = None) -> list[dict]:
    """One spec per mapped question.

    `numeric_support` optionally pins the numeric-open grids (used by the gate
    to reproduce the archived country set); otherwise the grid is observed
    inside `survey_frames`.
    """
    specs = []
    for _, row in question_map.iterrows():
        qid = row["Question"]
        response_type = str(row["ResponseType"])
        is_numeric_open = response_type == "numeric_open"

        if is_numeric_open:
            if not E.INCLUDE_NUMERIC_OPEN:
                continue
            if numeric_support and qid in numeric_support:
                codes = list(numeric_support[qid])
            else:
                codes = observed_numeric_support(qid, survey_frames)
            labels = codes.copy()
        else:
            codes, labels = parse_fixed_options(row)

        if len(codes) < 2:
            raise ValueError(f"Question {qid} has fewer than two response codes")

        specs.append({
            "question_id": qid,
            "question_text": row["StandaloneQuestion"],
            "response_type": response_type,
            "codes": codes,
            "labels": labels,
            "is_numeric_open": is_numeric_open,
            "is_ordered": qid not in E.NOMINAL_QUESTION_IDS,
            "gps_dimension": row.get("gps_dimension"),
        })
    return specs


# ---------------------------------------------------------------- prompt
def build_survey_user_prompt(spec, prompt_country=None,
                             country_names: dict | None = None) -> str:
    country_names = country_names or E.COUNTRY_NAMES
    if prompt_country is None:
        persona = "Answer this questionnaire as an individual person."
    else:
        persona = (f"Answer this questionnaire as a typical adult living in "
                   f"{country_names[prompt_country]}.")

    if spec["is_numeric_open"]:
        response_instruction = (
            "Give one whole-number response. Return only the number, with no "
            "words or explanation."
        )
    else:
        option_lines = "\n".join(f"{code}: {label}"
                                 for code, label in zip(spec["codes"], spec["labels"]))
        response_instruction = (
            "Select exactly one response code from the options below.\n"
            f"{option_lines}\n\n"
            "Return only the response code, with no words or explanation."
        )

    return (
        f"{persona} Respond naturally and sincerely, as someone would in real life. "
        "Do not mention being an AI or assistant.\n\n"
        f"Question:\n{spec['question_text']}\n\n"
        f"{response_instruction}\n\n"
        "Answer:"
    )


# ---------------------------------------------------------------- population
def get_country_weights(frame) -> tuple[pd.Series, str | None]:
    if not E.USE_SURVEY_WEIGHTS:
        return pd.Series(np.ones(len(frame), dtype=float), index=frame.index), None
    weights = pd.to_numeric(frame[E.WEIGHT_COLUMN], errors="coerce")
    weights = weights.where(np.isfinite(weights) & (weights > 0))
    return weights, E.WEIGHT_COLUMN


def build_population_distributions(question_specs, survey_frames,
                                   skipped: list | None = None) -> pd.DataFrame:
    """Weighted population option distributions.

    A (country, question) cell with no valid response is SKIPPED, not an error:
    Great Britain was not asked Q174 and Jordan's Q178 is coded -4 (not asked)
    for all respondents, so the cell is genuinely empty. Skips are permitted
    ONLY through the `skipped` ledger — each entry carries
    {eval_country, question_id, reason, n_valid, total_weight}. With
    `skipped=None` (the default, used by the reproduction gate) an empty cell
    raises instead of silently dropping.
    """
    rows = []
    for country, frame in survey_frames.items():
        weights, weight_column = get_country_weights(frame)
        for spec in question_specs:
            qid = spec["question_id"]
            answers = pd.to_numeric(frame[qid], errors="coerce")
            code_values = np.array([float(c) for c in spec["codes"]], dtype=float)

            valid = answers.isin(code_values) & weights.notna()
            n_valid = int(valid.sum())
            total_weight = float(weights.loc[valid].sum())
            if n_valid == 0 or total_weight <= 0:
                if skipped is None:
                    raise ValueError(
                        f"{country}/{qid}: no valid responses "
                        f"(n_valid={n_valid}, total_weight={total_weight}). Record "
                        "this cell explicitly via the skipped ledger to drop it.")
                skipped.append({"eval_country": country, "question_id": qid,
                                "reason": "no_valid_responses",
                                "n_valid": n_valid, "total_weight": total_weight})
                continue

            for option_index, (code, label) in enumerate(zip(spec["codes"], spec["labels"])):
                selected = valid & answers.eq(float(code))
                rows.append({
                    "eval_country": country,
                    "question_id": qid,
                    "question_text": spec["question_text"],
                    "response_type": spec["response_type"],
                    "gps_dimension": spec["gps_dimension"],
                    "is_ordered": spec["is_ordered"],
                    "is_numeric_open": spec["is_numeric_open"],
                    "option_index": option_index,
                    "option_code": code,
                    "option_value": float(code),
                    "option_label": label,
                    "unweighted_count": int(selected.sum()),
                    "weighted_count": float(weights.loc[selected].sum()),
                    "population_prob": float(weights.loc[selected].sum()) / total_weight,
                    "n_valid": n_valid,
                    "total_weight": total_weight,
                    "weight_column": weight_column,
                })

    population = pd.DataFrame(rows)
    checks = (population.groupby(["eval_country", "question_id"])["population_prob"]
              .sum().sub(1.0).abs())
    if checks.max() > 1e-8:
        raise AssertionError("Population probabilities do not sum to one")
    population.attrs["skipped_cells"] = sorted(
        {(str(s["eval_country"]), str(s["question_id"])) for s in (skipped or ())})
    population.attrs["n_skipped_cells"] = len(skipped or ())
    return population


# ---------------------------------------------------------------- metrics
def relationship_label(model_name: str, eval_country: str) -> str:
    if model_name == "base":
        return "base"
    if model_name.startswith("persona_"):
        cc = model_name[len("persona_"):]
        return "persona_matched" if cc == eval_country else "persona_cross"
    adapter_country = model_name.replace("_adapter", "")
    return "matched" if adapter_country == eval_country else "cross"


def safe_entropy(probabilities) -> float:
    p = np.asarray(probabilities, dtype=float)
    positive = p > 0
    return float(-np.sum(p[positive] * np.log(p[positive])))


def jensen_shannon_divergence(population_prob, model_prob) -> float:
    p = np.asarray(population_prob, dtype=float)
    q = np.asarray(model_prob, dtype=float)
    m = 0.5 * (p + q)

    def kl(a, b):
        positive = a > 0
        return np.sum(a[positive] * np.log(a[positive] / b[positive]))

    return float(0.5 * kl(p, m) + 0.5 * kl(q, m))


def discrete_wasserstein(values, population_prob, model_prob) -> float:
    order = np.argsort(values)
    x = np.asarray(values, dtype=float)[order]
    p = np.asarray(population_prob, dtype=float)[order]
    q = np.asarray(model_prob, dtype=float)[order]
    if len(x) < 2:
        return 0.0
    cdf_difference = np.abs(np.cumsum(p)[:-1] - np.cumsum(q)[:-1])
    return float(np.sum(cdf_difference * np.diff(x)))


def calculate_question_metrics(option_evaluation: pd.DataFrame) -> pd.DataFrame:
    rows = []
    group_columns = ["model", "eval_country", "question_id"]
    for (model_name, eval_country, qid), group in option_evaluation.groupby(
            group_columns, sort=False):
        group = group.sort_values("option_index")
        p = group["population_prob"].to_numpy(dtype=float)
        q = group["model_prob"].to_numpy(dtype=float)
        values = group["option_value"].to_numpy(dtype=float)
        is_ordered = bool(group["is_ordered"].iloc[0])

        population_mean = float(np.dot(p, values)) if is_ordered else np.nan
        model_mean = float(np.dot(q, values)) if is_ordered else np.nan
        population_std = (float(np.sqrt(np.dot(p, (values - population_mean) ** 2)))
                          if is_ordered else np.nan)
        model_std = (float(np.sqrt(np.dot(q, (values - model_mean) ** 2)))
                     if is_ordered else np.nan)
        top_population_code = group.iloc[int(np.argmax(p))]["option_code"]
        top_model_code = group.iloc[int(np.argmax(q))]["option_code"]

        rows.append({
            "model": model_name,
            "eval_country": eval_country,
            "relationship": relationship_label(model_name, eval_country),
            "question_id": qid,
            "question_text": group["question_text"].iloc[0],
            "response_type": group["response_type"].iloc[0],
            "gps_dimension": group["gps_dimension"].iloc[0],
            "is_ordered": is_ordered,
            "is_numeric_open": bool(group["is_numeric_open"].iloc[0]),
            "n_options": len(group),
            "n_valid": int(group["n_valid"].iloc[0]),
            "total_weight": float(group["total_weight"].iloc[0]),
            "tv_distance": float(0.5 * np.abs(p - q).sum()),
            "js_divergence": jensen_shannon_divergence(p, q),
            "brier_score": float(np.square(p - q).sum()),
            "cross_entropy": float(-np.sum(p * np.log(np.clip(q, E.EPS, 1.0)))),
            "population_entropy": safe_entropy(p),
            "model_entropy": safe_entropy(q),
            "entropy_error": float(safe_entropy(q) - safe_entropy(p)),
            "top_option_match": bool(top_population_code == top_model_code),
            "population_top_code": top_population_code,
            "model_top_code": top_model_code,
            "population_mean": population_mean,
            "model_mean": model_mean,
            "mean_error": model_mean - population_mean if is_ordered else np.nan,
            "abs_mean_error": abs(model_mean - population_mean) if is_ordered else np.nan,
            "population_std": population_std,
            "model_std": model_std,
            "std_error": model_std - population_std if is_ordered else np.nan,
            "abs_std_error": abs(model_std - population_std) if is_ordered else np.nan,
            "wasserstein_distance": (discrete_wasserstein(values, p, q)
                                     if is_ordered else np.nan),
        })
    return pd.DataFrame(rows)


JOIN_COLUMNS = ["eval_country", "question_id", "option_code", "option_value",
                "option_index", "population_prob", "weighted_count",
                "unweighted_count", "n_valid", "total_weight",
                "question_text", "response_type", "gps_dimension",
                "is_ordered", "is_numeric_open"]


def _cc_q(value) -> tuple[str, str]:
    """Canonical (eval_country, question_id) pair for a skip-ledger key."""
    country, qid = value
    return str(country).strip(), str(qid).strip()


def join_option_evaluation(model_scores: pd.DataFrame,
                           population_long: pd.DataFrame,
                           skipped_cells=None,
                           dropped: list[dict] | None = None) -> pd.DataFrame:
    """Join broadcast model scores to population distributions, loudly.

    A model row may be dropped ONLY when its (eval_country, question_id) cell
    is listed in `skipped_cells` AND that cell is genuinely ABSENT from the
    population (a whole empty cell — never a partial option-support mismatch).
    Everything else fails: unexpected missing cells, bogus skips that actually
    have population rows, non-unique population keys, non-canonical codes.

    Reporting (also on the result's `.attrs`):
      * `dropped` list gets one record per dropped cell
        {eval_country, question_id, reason, dropped_rows} when provided;
      * attrs `dropped_rows`, `dropped_cells`, `skipped_cells_used`.

    A cell genuinely absent from the survey (GBR/Q174, JOR/Q178) must be
    explicitly recorded by the caller — an empty `skipped_cells` (the default)
    means NO row may be dropped.
    """
    skipped = {_cc_q(cell) for cell in (skipped_cells or ())}

    model = model_scores.copy()
    population = population_long.copy()
    # canonical string keys: a CSV round-trip coerces option_code '1' -> int64
    for frame in (model, population):
        frame["option_code"] = frame["option_code"].map(canonical_code)
        frame["eval_country"] = frame["eval_country"].astype(str).str.strip()
        frame["question_id"] = frame["question_id"].astype(str).str.strip()

    dup = population.duplicated(subset=["eval_country", "question_id", "option_code"])
    if dup.any():
        raise AssertionError(
            "Population join keys are not unique: "
            + str(population.loc[dup, ["eval_country", "question_id", "option_code"]]
                  .to_dict("records")))

    pop_cells = set(zip(population["eval_country"], population["question_id"]))
    bogus = sorted(f"{c}/{q}" for c, q in skipped if (c, q) in pop_cells)
    if bogus:
        raise ValueError(f"Bogus skipped_cells — these cells HAVE population rows: {bogus}")

    key = ["eval_country", "question_id", "option_code", "option_value", "option_index"]
    merged = model.merge(population[JOIN_COLUMNS], on=key, how="left",
                         validate="many_to_one", indicator=True)
    missing = merged["_merge"].eq("left_only")
    dropped_cells: dict[str, int] = {}
    if missing.any():
        missing_pairs = (merged.loc[missing, ["eval_country", "question_id"]]
                         .drop_duplicates().itertuples(index=False))
        unexpected = sorted(f"{c}/{q}" for c, q in missing_pairs
                            if (c, q) not in skipped)
        if unexpected:
            raise AssertionError(
                f"Join lost rows for cells not recorded as population skips: {unexpected}. "
                "Do not silently bless absent populations: add a cell to skipped_cells "
                "only if the whole cell is genuinely empty in the survey data.")
        counts = (merged.loc[missing].groupby(["eval_country", "question_id"]).size()
                  .sort_index())
        dropped_cells = {f"{c}/{q}": int(n) for (c, q), n in counts.items()}
        if dropped is not None:
            for (c, q), n in counts.items():
                dropped.append({"eval_country": c, "question_id": q,
                                "reason": "explicitly_recorded_empty_population_cell",
                                "dropped_rows": int(n)})
        merged = merged.loc[~missing]
    merged = merged.drop(columns="_merge")

    merged.attrs["dropped_rows"] = int(sum(dropped_cells.values()))
    merged.attrs["dropped_cells"] = dropped_cells
    merged.attrs["skipped_cells_used"] = sorted(dropped_cells)
    merged["relationship"] = [relationship_label(m, c)
                              for m, c in zip(merged["model"], merged["eval_country"])]
    return merged


def stable_softmax(values, temperature: float = 1.0) -> np.ndarray:
    v = np.asarray(values, dtype=float) / float(temperature)
    v = v - np.max(v)
    exp_v = np.exp(v)
    return exp_v / exp_v.sum()
