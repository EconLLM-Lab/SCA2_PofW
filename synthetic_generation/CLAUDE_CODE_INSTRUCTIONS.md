# Claude Code Task Specification: SCA 2.0 Notebook Update (v2 → v3)

## Context

You are updating a Jupyter notebook (`SCA2_SyntheticDataGeneration_v2.ipynb`) that implements a synthetic data generation pipeline for the Synthetic Cultural Agents (SCA) project. The pipeline generates culturally-conditioned preference pairs for DPO fine-tuning of language models.

The notebook has been audited. The architecture is sound, the demo run validates the data flow (120 pairs, 84.2% QC pass rate), and most components are confirmed correct. Your job is to apply targeted fixes, add one new feature, improve documentation, and generate a README for handoff.

**Reference documents in this folder:**
- `SCA2_SyntheticDataGeneration_v2.ipynb` — The notebook to edit (17 cells, ~300 lines of functional code)
- `reference/audit_condensed.md` — Audited findings with exact code changes specified
- `reference/SCA2_Project_Proposal.pdf` — Pipeline specification (§6.3), QC criteria, and hyperparameters

**Read `audit_condensed.md` thoroughly before making any edits.** It contains the exact before/after code for each change, the design decisions already made, and the list of components verified correct that must not be modified.

---

## Critical Constraints

### DO NOT MODIFY
- The `GPS_DIMENSIONS` dict (Block A) — descriptions and rubrics are verified against GPS questionnaires
- The `WVS_ITEM_MAP` dict (Block A) — all 30 codes verified against WVS Wave 7 Codebook. You may add comments/documentation around it, but do not change any codes, dimension assignments, tier assignments, or labels
- The `gps_to_profile()` function (Block B) — magnitude thresholds and profile text verified correct
- The `extract_gps_vector()` function (Block B) — verified correct
- The `extract_wvs_anchors()` function (Block B) — verified correct
- The monotonicity filter logic in `run_scoring_qc_export()` — the sign logic `(m_diff * z_sign) > 0` is verified correct. When you modify this function for 6D scoring, preserve this exact filter logic for the target dimension
- The chosen/rejected assignment in Block C results processing — `chosen = response_a` (aligned), `rejected = response_b` (opposite). Do not swap or rename
- The `generate_scenarios()` function (Block C) — do not change the prompt or call structure
- The `generate_pair()` function (Block C) — do not change the prompt, system message, or cultural conditioning
- The `CostTracker.report()` output format (beyond adding the timestamp)
- The visualization cells (cells 12, 13, 14) — leave as-is for now

### DO NOT
- Rewrite the notebook from scratch. Make surgical edits to the existing cells.
- Change any LLM prompt templates except the scoring prompt in `score_pair()` (which is being updated for 6D scoring)
- Add new pip dependencies beyond what is already installed
- Restructure the pipeline flow (Block A → B → C → D → E execution order)
- Add complexity that isn't specified in this document (no batch API, no diversity grid, no independent scorer, no native-language prompting)
- Make any live API calls. All testing must use mock data (see Phase 1C / 2B below)

### STYLE REQUIREMENTS
- Preserve the existing code style: box-drawing headers for blocks, emoji status indicators (✅, ⚠️), inline comments with `#` 
- Markdown cells should be written for an undergraduate research assistant audience. Explain *why* design choices were made, not just what they are. Avoid jargon without definition.
- Keep the notebook Colab-compatible: top-level `await` is fine, `google.colab.userdata` for secrets

---

## Execution Phases

Complete these phases in order. Do not start a later phase until the earlier phase is fully complete.

### Phase 1: Targeted Code Fixes (4 changes)

Apply the four code changes specified in `audit_condensed.md` under "Required Code Changes." Each change has exact before/after code.

#### 1A. Cost Tracker Defensive Logging (Block A)
- Add `and resp.usage` to the guard in `tracked_call()`
- Add the `else: print(...)` warning branch
- Add `self.created_at = datetime.now().isoformat()` to `CostTracker.__init__()`
- Print `self.created_at` in `CostTracker.report()` (add one line at the start of the report output, e.g., `print(f"Tracker initialized: {self.created_at}")`)

#### 1B. Score Clamping (Block D)
- Replace the `return float(...)` line in `score_pair()` with the try/except + clamping version

#### 1C. Error Handling (Block C)
- Add `return_exceptions=True` to the `atqdm.gather()` call
- Add the `isinstance(result, Exception)` check before the existing `isinstance(result, dict)` check in the results loop

#### 1D. Move Import (Block C → Block A)
- Remove `from tqdm.asyncio import tqdm as atqdm` from Block C (cell 6, first line of code)
- Add it to Block A (cell 2) near the other imports from external libraries (near `from litellm import acompletion`)

#### Phase 1 Validation: Mock Test Cell
After applying all four fixes, add a new code cell immediately after Block E (before the visualization cells) titled `# Block F — Pipeline Logic Validation (Mock Data)`. This cell should:

1. **NOT make any API calls.** It tests the pipeline logic on synthetic/mock data only.

2. Create a mock `df_raw` DataFrame with ~8 rows covering:
   - 2 countries (e.g., "TEST_POS" with z_values all positive, "TEST_NEG" with z_values all negative)
   - At least 2 GPS dimensions
   - Known chosen/rejected text values (can be placeholder strings)

3. Create a mock `cultural_profiles` dict with known z_c values for the test countries.

4. Mock the scoring step by directly assigning known `m_chosen` and `m_rejected` values to test:
   - A pair that should PASS monotonicity (positive z, m_chosen > m_rejected)
   - A pair that should PASS monotonicity (negative z, m_chosen < m_rejected)  
   - A pair that should FAIL monotonicity (positive z, m_chosen < m_rejected)
   - A pair that should FAIL distance threshold (|m_diff| < 0.20)
   - A pair where m_chosen is None (should increment score_fail)

5. Run the QC filter logic (extract it into a testable function or replicate the filter loop) on this mock data.

6. Assert expected outcomes:
   - Exactly 2 pairs pass (the two correct monotonicity cases)
   - 1 monotonicity failure
   - 1 distance failure  
   - 1 scoring failure
   - Print "✅ All mock QC tests passed." on success

7. Also test the score clamping: verify that `max(0.0, min(1.0, 1.5))` returns 1.0 and `max(0.0, min(1.0, -0.3))` returns 0.0.

8. Also test the error handling: create a mock results list containing one Exception object, verify the processing loop skips it and continues.

The cell should be self-contained (no imports beyond what's in Block A) and run without any external data files or API keys.

---

### Phase 2: 6-Dimensional Scoring Feature

#### 2A. Modify `score_pair()` (Block D)
Replace the scoring prompt and return logic as specified in `audit_condensed.md` under "New Feature: 6-Dimensional Scoring." Key changes:
- Prompt now includes all 6 rubrics and requests `scores_a` / `scores_b` dicts
- Add `"reasoning"` field to requested JSON output
- Return two dicts instead of two floats, with per-key clamping
- Preserve the try/except → `return None, None` fallback from Change 2

#### 2B. Modify `run_scoring_qc_export()` (Block D)
Update the function to handle dict scores:

- After scoring, extract target dimension scores for QC filtering:
  ```python
  m_chosen_target = scores_a[dim] if scores_a else None
  m_rejected_target = scores_b[dim] if scores_b else None
  ```
- The monotonicity filter and distance filter continue to use only the target dimension. **Do not change the filter logic itself.**
- When building `qc_rows`, flatten the score dicts into per-dimension columns:
  ```
  m_chosen_trust, m_chosen_risktaking, ..., m_rejected_trust, ...
  ```
  Plus retain `m_chosen` and `m_rejected` as aliases for the target dimension scores (for backward compatibility with the visualization cells).
- Add a `reasoning` field to `qc_rows` capturing the scorer's justification.
- Compute and store the contamination ratio per pair:
  ```python
  # C_k = sum of non-target |Δm_j| / |Δm_target|
  cross_diffs = sum(abs(scores_a.get(j, 0.5) - scores_b.get(j, 0.5)) 
                     for j in GPS_DIMENSIONS if j != dim)
  target_diff = abs(m_chosen_target - m_rejected_target)
  contamination = round(cross_diffs / target_diff, 4) if target_diff > 0 else None
  ```

#### 2C. Update Block E (QC Report, Export, Cost Summary)
- Per-dimension breakdown: for each GPS dimension, report both the target-dimension mean |Δm| (as currently) AND the mean contamination ratio.
- Export: the JSONL and HuggingFace exports should include all 12 score columns, the contamination ratio, and the reasoning field.
- Manifest: add `mean_contamination_ratio` and per-dimension contamination summaries.

#### Phase 2 Validation: Extend Mock Test Cell
Add tests to the Block F mock test cell for 6D scoring:

1. Create mock `scores_a` and `scores_b` dicts with known values for all 6 dimensions.
2. Verify that the QC filter still uses only the target dimension for monotonicity and distance checks.
3. Verify that the contamination ratio computes correctly for a known case (provide expected value).
4. Verify that all 12 score columns appear in the output DataFrame.
5. Verify that a malformed scores dict (e.g., missing a key, or a non-numeric value) is handled gracefully (returns None, None).

---

### Phase 3: Documentation and Markdown Polish

#### 3A. Cell 0 (Title/Header Markdown)
Update to reflect v3 status. Add a brief note that this version includes 6D scoring and improved error handling. Keep it concise — 4-6 lines maximum.

#### 3B. Add Documentation Cell: WVS Proxy Coverage (new cell, insert before Block A's WVS_ITEM_MAP)
Actually, since WVS_ITEM_MAP is inside the Block A code cell, add a markdown cell between Cell 1 (pip install) and Cell 2 (Block A code) OR add it as the existing Block B markdown cell (Cell 3) expanded. The better option: add a new markdown cell immediately before Cell 2 that documents the configuration decisions. Content:

- Brief explanation of the three-tier WVS moment structure: Tier 2 = overidentifying moments for J-test, Tier 3 = held-out validation
- Note that trust (12 items) and negative reciprocity (4 items) have the strongest WVS proxy coverage
- Note that patience and positive reciprocity have weak proxies — cite that the best WVS proxy for GPS patience (Q13 "thrift") has a non-significant correlation (ρ = 0.09, p = .52 per Falk et al. 2018 Table II)
- Note that Q152 (Schwartz "adventure and risks") was investigated as a risk-taking proxy but is not available in WVS Wave 7 (Q152 is the postmaterialist index in this wave)
- Note the `inv` convention: items marked "inv" have raw WVS scales where higher values = less of the trait. Currently computed as raw means (fine for contextual anchors), but must be inverted for J-test moment computation
- Flag this as a pre-registration decision per the existing inline warning

#### 3C. Block C Markdown (Cell 5)
Expand the existing markdown to better explain:
- The two-stage architecture (scenarios are country-independent → saves tokens; paired generation is country-specific)
- The DPO convention: chosen = culturally aligned = what the student should prefer
- Why scenarios are generated at temperature 0.9 (diversity) but pairs at temperature 0.8 (quality)

#### 3D. Add Markdown Cell: Score Polarization Rationale (insert before Block D)
Explain that training-data scores are bimodal by design because the teacher generates maximally contrastive pairs. This does not affect DPO training (ordinal labels only). Continuous scores for structural estimation will be computed at validation time on student model outputs. Reference two future improvements: gradient generation (Paper 3) and GPS-derived calibration anchors.

#### 3E. Rewrite Cell 15 ("Expert Opinion" → "Design Notes")
Replace the current content with a concise "Design Notes" section. Requirements:
- Write in first-person plural ("We chose...", "The pipeline uses...") — this is a lab notebook, not an AI assessment
- Organize around design decisions and their justifications, not a generic strengths/weaknesses list
- Cover: (1) why GPS conditioning rather than vague persona prompting, (2) why contrastive pair generation rather than single-response + reward model, (3) why same-model scoring (pragmatic choice, acknowledge self-preference risk), (4) why single-dimension filtering with 6D scoring (monotonicity on target, contamination as diagnostic), (5) known proxy weakness on patience and positive reciprocity
- Keep it under 300 words. An undergrad should finish reading it in 2 minutes.

#### 3F. Update Cell 16 (Next Steps)
Update to reflect v3 changes (6D scoring now implemented, error handling added). Remaining next steps for the production run: scale `scenarios_per_dim`, add trigram deduplication, run pre-training bias tests. Keep the DPO handoff loading instructions.

---

### Phase 4: README Generation

Create a `README.md` file (separate from the notebook) for the handoff package. Structure:

```
# SCA 2.0 — Synthetic Data Generation Pipeline

## Overview
[1 paragraph: what this pipeline does, its role in the SCA 2.0 project]

## Quick Start
[How to run in Colab: upload datasets, set API key, Runtime → Run All]

## Pipeline Architecture
[Brief description of Blocks A-E, what each does, data flow between them]

## Output Format
[Description of the JSONL and HuggingFace dataset schema, including all columns]
[Description of manifest.json contents]

## For the DPO Fine-Tuning Step
[Loading instructions for TRL DPOTrainer]
[Key fields: prompt, chosen, rejected]
[Reference to manifest.json for hyperparameter suggestions]

## Configuration
[How to change target countries, scenarios_per_dim, model, etc.]
[Cost estimates at different scales]

## Quality Control
[What the QC filters check and what pass/fail means]
[How to interpret the contamination ratio]

## Known Limitations
[Proxy weakness on patience/posrecip, single-model scoring, no human validation yet]

## File Manifest
[List of all files in the handoff package and what each contains]
```

Keep the README under 400 lines. Write for a colleague who knows DPO and HuggingFace TRL but hasn't seen this specific pipeline before.

---

## Final Checklist

Before declaring the task complete, verify:

- [ ] All 4 code fixes applied (Changes 1-4 from audit)
- [ ] 6D scoring implemented in `score_pair()`, `run_scoring_qc_export()`, and Block E
- [ ] Mock test cell (Block F) passes all assertions for both Phase 1 and Phase 2
- [ ] No new pip dependencies added
- [ ] `atqdm` import is in Block A, not Block C
- [ ] All markdown cells updated per Phase 3 specs
- [ ] Cell 15 rewritten as "Design Notes" (not "Expert Opinion")
- [ ] README.md created
- [ ] The notebook is valid JSON (parseable as a .ipynb file)
- [ ] The visualization cells (12, 13, 14) still reference valid column names (note: `m_chosen` and `m_rejected` must still exist as target-dimension aliases)
- [ ] No API calls are made anywhere in the mock test cell
