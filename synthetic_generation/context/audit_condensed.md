# SCA 2.0 Pipeline Audit — Condensed for Implementation

**Source:** Full audit dated February 22, 2026, reviewed and discussed with PI on March 1, 2026.
**Scope:** This condensed version retains only the findings that require code changes or inform implementation decisions. The full audit contains detailed WVS item-by-item verification tables, theoretical discussion of proxy weaknesses, and Tier 3 extensions not in scope for this update.

---

## What Was Verified Correct (DO NOT MODIFY)

The following components were audited against authoritative sources and confirmed working:

| Component | Location | Verdict |
|-----------|----------|---------|
| WVS_ITEM_MAP (30 variable codes) | Block A | All codes verified against WVS Wave 7 Codebook V6.0 ✅ |
| Monotonicity filter sign logic | Block D, `run_scoring_qc_export()` | Correct for z > 0, z < 0, and z = 0 cases ✅ |
| Chosen/rejected DPO assignment | Block C → Block D → Export | `chosen = response_a` (aligned), `rejected = response_b` (opposite) throughout ✅ |
| GPS profile construction | Block B, `gps_to_profile()` | Magnitude thresholds and dimension descriptions verified ✅ |
| GPS dimension descriptions & rubrics | Block A, `GPS_DIMENSIONS` | Cross-referenced against GPS questionnaires ✅ |
| Concurrency safety | Block A, semaphore + async lock | Correctly scoped ✅ |
| Colab compatibility | Top-level `await`, imports, secrets | Works in Colab "Run All" flow ✅ |

---

## Score Polarization — Design Decision (NOT a code fix)

**Observation:** Scorer produces bimodal distributions (scores cluster near 0.0 and 1.0, mean |Δm| ≈ 0.68).

**Root cause:** The teacher generates maximally contrastive pairs by design ("ACTUAL disposition" vs. "OPPOSITE disposition"), so the scorer correctly detects large gaps. This is expected behavior, not a bug.

**Impact on DPO training:** None. DPO uses only ordinal preference labels (chosen > rejected), not score magnitudes. The 84.2% monotonicity pass rate confirms clean ordinal signal.

**Impact on structural estimation (Paper 2):** Continuous-valued m(x,y) scores are needed for the J-test, but these will be computed during the validation stage by scoring the *student model's* outputs on fresh prompts — not from the training data scores.

**Decision:** Keep the current scoring prompt. Document the rationale in a markdown cell. Consider two future improvements (gradient generation for Paper 3; GPS-derived calibration anchors for validation scoring). Do add a `"reasoning"` field to the scorer JSON output for diagnostic purposes.

---

## Required Code Changes

### Change 1: Cost Tracker Defensive Logging

**Location:** Block A, `tracked_call()` function
**Problem:** If `resp.usage` exists but is `None`, logging is silently skipped. Demo run showed missing Block C costs, likely from Colab cell re-execution reinitializing the tracker, but this guard prevents silent data loss regardless.

**Current code:**
```python
if resp and hasattr(resp, 'usage'):
    await cost_tracker.log(kwargs.get('model', 'unknown'), block, resp.usage)
```

**Replace with:**
```python
if resp and hasattr(resp, 'usage') and resp.usage:
    await cost_tracker.log(kwargs.get('model', 'unknown'), block, resp.usage)
else:
    print(f"  ⚠️  No usage data for {block}")
```

**Also add** a `created_at` timestamp to `CostTracker.__init__`:
```python
def __init__(self):
    self.lock = asyncio.Lock()
    self.usage = {}
    self.created_at = datetime.now().isoformat()
```
And print it in `report()` so re-initialization is immediately visible.

---

### Change 2: Score Clamping and Type Safety

**Location:** Block D, `score_pair()` return statement
**Problem:** `float(None)` raises TypeError; no clamping for out-of-range values. Either crashes the scoring run.

**Current code:**
```python
return float(parsed.get("score_a", 0.5)), float(parsed.get("score_b", 0.5))
```

**Replace with:**
```python
try:
    sa = max(0.0, min(1.0, float(parsed.get("score_a", 0.5))))
    sb = max(0.0, min(1.0, float(parsed.get("score_b", 0.5))))
    return sa, sb
except (TypeError, ValueError):
    return None, None
```

The `None, None` return is already handled downstream — the QC loop checks `if row["m_chosen"] is None` and increments `stats["score_fail"]`.

---

### Change 3: Error Handling in Pair Generation

**Location:** Block C, `run_teacher_pipeline()` — the `gather` call and results loop
**Problem:** A single API failure after 5 retries crashes the entire country's generation via exception propagation. At 10K pairs, this loses all progress.

**Part A — Modify the gather call:**

**Current:**
```python
results = await atqdm.gather(*tasks, desc=f"{country}", file=sys.stdout)
```

**Replace with:**
```python
results = await atqdm.gather(*tasks, desc=f"{country}", file=sys.stdout, return_exceptions=True)
```

**Part B — Add exception handling in the results loop:**

**Current:**
```python
for (scenario, dim_key, ctry), result in zip(task_meta, results):
    if isinstance(result, dict) and "response_a" in result:
```

**Replace with:**
```python
for (scenario, dim_key, ctry), result in zip(task_meta, results):
    if isinstance(result, Exception):
        print(f"  ⚠️  Skipped failed pair: {type(result).__name__}: {result}")
        continue
    if isinstance(result, dict) and "response_a" in result:
```

---

### Change 4: Move `atqdm` Import

**Current location:** Block C (first line of code cell)
```python
from tqdm.asyncio import tqdm as atqdm
```

**Move to:** Block A, with the other imports (near `from litellm import acompletion`).

**Reason:** `atqdm` is used in both Block C and Block D. If Block D is run without Block C (common during development), it raises `NameError`.

---

## New Feature: 6-Dimensional Scoring

### Motivation

Currently each pair is scored only on the target GPS dimension. The structural estimation in Paper 2 requires the full feature vector m(x,y) ∈ R^6 per response, and cross-dimension contamination analysis is impossible without all six scores.

### Specification

**Modified `score_pair()` prompt:**

```python
rubric_block = "\n".join([
    f"- {GPS_DIMENSIONS[k]['symbol']} ({k}): {GPS_DIMENSIONS[k]['rubric']}"
    for k in GPS_DIMENSIONS
])

prompt = f"""You are a cultural behavioral scientist scoring responses on six dimensions.

DIMENSIONS AND RUBRICS:
{rubric_block}

SCENARIO: {scenario}

RESPONSE A: {chosen_text}

RESPONSE B: {rejected_text}

Score each response on ALL 6 dimensions (0.0 to 1.0 each).
Return ONLY JSON:
{{"scores_a": {{"trust": <float>, "risktaking": <float>, "patience": <float>, "altruism": <float>, "posrecip": <float>, "negrecip": <float>}},
 "scores_b": {{"trust": <float>, "risktaking": <float>, "patience": <float>, "altruism": <float>, "posrecip": <float>, "negrecip": <float>}},
 "reasoning": "<1-sentence justification for the target dimension scores>"}}"""
```

**Modified return value:**

```python
# score_pair() now returns two dicts instead of two floats
try:
    scores_a = {k: max(0.0, min(1.0, float(v))) for k, v in parsed["scores_a"].items()}
    scores_b = {k: max(0.0, min(1.0, float(v))) for k, v in parsed["scores_b"].items()}
    return scores_a, scores_b
except (TypeError, ValueError, KeyError):
    return None, None
```

**Modified data schema in `run_scoring_qc_export()`:**

Replace scalar `m_chosen` / `m_rejected` columns with per-dimension columns:
```
m_chosen_trust, m_chosen_risktaking, m_chosen_patience, m_chosen_altruism, m_chosen_posrecip, m_chosen_negrecip
m_rejected_trust, m_rejected_risktaking, ...
```

The monotonicity filter continues to use only the **target dimension** scores:
```python
m_chosen_target = scores_a[dim]    # where dim = row["gps_dimension"]
m_rejected_target = scores_b[dim]
m_diff = m_chosen_target - m_rejected_target
```

The distance filter also uses only the target dimension's absolute difference.

**QC report and export updates (Block E):**

- Per-dimension breakdown should report mean |Δm| for both the target dimension and cross-dimension means.
- Add a contamination ratio diagnostic: `C_k = Σ_{j≠k} |m_j(chosen) - m_j(rejected)| / |m_k(chosen) - m_k(rejected)|`
- Export all 12 score columns (6 chosen + 6 rejected) in both JSONL and HuggingFace formats.
- Update manifest.json to include per-dimension mean scores and the contamination ratio summary.

**Cost estimate:** Adds ~$10 per 10K-pair run (~300 extra input tokens + ~100 extra output tokens per call).

---

## Documentation Notes (from PI review)

These are content decisions made during the audit review. The coding agent should implement them in markdown cells:

1. **WVS proxy weakness acknowledgment:** Add a documentation cell before or within `WVS_ITEM_MAP` explaining that patience and positive reciprocity have weak proxies (cite Falk et al. Table II correlations). Note that Q152 (Schwartz "adventure and risks" value item) was investigated as a risk-taking proxy but is not available in WVS Wave 7 (Q152 is the postmaterialist index in Wave 7).

2. **Score polarization rationale:** Add a markdown cell in/before Block D explaining the bimodal score distribution as a design feature (see "Score Polarization — Design Decision" section above).

3. **Monotonicity filter explanation:** Add inline comments explaining the sign logic: `(m_diff × sign(z)) > 0` ensures aligned responses score in the direction consistent with the culture's GPS value.

4. **DPO convention note:** Add a comment in Block C near the chosen/rejected assignment: "DPO convention: chosen = what the student should prefer = culturally aligned response."

5. **Scale inversion warning:** Add a comment in `WVS_ITEM_MAP` noting that items marked "inv" have raw WVS scales where higher values = less of the trait. The current pipeline computes raw means without inverting, which is fine for contextual anchors but must be handled when computing J-test moments.

6. **Rewrite Cell 15** ("Expert Opinion"): Replace with a concise "Design Notes" section written in the PI's voice for a Level I lab member audience. Focus on *why* each design choice was made, not just what the strengths/limitations are.
