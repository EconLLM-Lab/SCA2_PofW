# C9-2 TVD 2×2 on 42 countries: base, adapter, persona cells (CPU; 4th cell from C9-4)

Card `t_f388a6cd`, board sca2-paper-b, assignee `engineer`, status at export: done
Created 2026-10-19 16:36 MST. Exported 2026-10-19 by the CP assembly card as a dated record, not status.

## Body

FIRST read /Users/bonorinoa/.hermes/cache/scratch/c9_explore/common.md (shared rules, paths, deadline 22:00 MST).

Context: the preprint reported a 2×2 of {adapter, no adapter} × {country-named persona prompt, none} on 16 countries: trust-GPS and mean TVD to human WVS distributions (adapter 0.74 / 0.487; persona -0.07 / 0.369; adapter+persona trust 0.67). Paper B must re-run it on the frozen stack for the 42 countries, never transcribe it (Paper B is the journal version and must not cite the preprint).

Step 1: find the preprint's exact TVD definition and code (search `misc/arxiv-submission-2026-10-05/*.tex`, `analysis/phase2/` for the producer of `analysis/phase2/outputs/2x2_tvd.csv`, and `paper_b/evaluate_local.py`). Write the definition (cells averaged over, item set, weighting, handling of skipped cells GBR/Q174, EGY/Q69-71, JOR/Q178) at the top of your output .md, quoting the source line.
Step 2: implement `paper_b/c9_tvd.py` + `paper_b/test_c9_tvd.py`. Inputs: model-only scores for base and cohort-1 adapters (`paper-b-20261011/model_probs.csv`), persona run `persona-strict-v1-20261019` (Hub `Bonorinoa/SCA2-paper-b-artifacts` runs/<run_id>, private, token), human distributions from the local-only `paper-b-20261011/local_eval/population_response_distributions.csv`. The adapter+persona cell is read from run `adapter-persona-strict-v1-20261019` IF present (produced by card C9-4); otherwise mark it pending — the same function must fill it later without code changes.
Step 3: per cell report mean TVD (country-equal), trust-GPS Spearman, per-dimension mean TVD; paired differences adapter-base and persona-base with profile-block bootstrap intervals (persona-base: country bootstrap too, persona is not profile-constant). Check that the base cell reproduces `local_eval/survey_question_metrics_all_models.csv` TVD values (test).
Outputs: `planning/sprint_2026-10-11/paper-b-tier1/results/c9/c9_tvd.{json,csv,md}` (aggregates only, no per-country human values).

## Runs

- run 52 engineer: scheduled/scheduled  
- run 68 engineer: done/completed  c9_tvd.py plus 19 tests (all pass; full paper_b suite 599 passed). Base, adapter and persona cells computed on 42 countries; the adapter+persona cell is pending because the run is not on the Hub, and the same call fills it later. Outputs are c9_tvd.{json,csv,md} under results/c9/.

## Comments

### engineer 2026-10-19 16:38

engineer note (mid-run): I called kanban_schedule by mistake while exploring tools, which parked this card as 'scheduled' and ended run 52. Work continues in the same workspace. I will try kanban_complete at the end and report if the board refuses it. PM: if it stays parked after my final report, please re-open it. Findings so far: adapter-persona-strict-v1-20261019 is NOT on the Hub (no runs/adapter-persona* prefix), so that cell will be 'pending'.

### engineer 2026-10-19 18:33

(a) Files: paper_b/c9_tvd.py, paper_b/test_c9_tvd.py (19 tests), planning/sprint_2026-10-11/paper-b-tier1/results/c9/c9_tvd.{json,csv,md}. Aggregates only; no per-country human values written. Nothing committed.
(b) Commands: `HF_TOKEN= env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest paper_b/test_c9_tvd.py -q` -> 19 passed, exit 0. Full `pytest paper_b -q` -> 599 passed, exit 0. `... .venv/bin/python paper_b/c9_tvd.py` -> exit 0 (2000 draws; profile-block seed 20261011, country seed 20260905).
(c) Numbers (all in c9_tvd.json/.md; DESCRIPTIVE / NOT PREREGISTERED), mean TVD country-equal: base 0.470, adapter 0.515, persona 0.365 (965 cells each, JOR/Q178 skipped). Trust-GPS Spearman: adapter 0.744 (profile-block [0.500, 0.865]; country [0.577, 0.847]); persona 0.028 (profile-block [-0.339, 0.381]; country [-0.273, 0.330]); base undefined (base has no country conditioning, composite is constant). Paired: adapter-base +0.045 (profile-block [0.006, 0.093]; country [0.017, 0.079]); persona-base -0.105 (profile-block [-0.122, -0.086]; country [-0.119, -0.091]). Per-dimension TVD is in the md table.
Checks: base cell and matched-adapter cell reproduce survey_question_metrics_all_models.csv tv_distance to <1e-6 (965 rows); adapter trust-GPS replays the banked C1 value exactly; persona trust-GPS 0.0278 equals persona_strict.json E1.
(d) Uncertain/failed: adapter_persona cell is PENDING. I queried the Hub (private, token): no files under runs/adapter-persona-strict-v1-20261019/synthetic/. Re-running c9_tvd.py (or placing paper_b_inputs/adapter_persona_strict.csv) fills it and adds adapter_persona_* and interaction contrasts, no code change; tested on a toy world. When it arrives, the C9-4 gates (adapter loaded, base parity) are not re-verified by this script. Definition differences from the preprint, declared in the md: preprint pooled mean over (country,item) rows, inner join on option_value with renormalisation; here country-equal headline (pooled reported beside it; they agree to 3 decimals), union of codes on option_code, no renormalisation. The preprint script applies no item filter (368 = 16x23 per the paper text). Also: this card's earlier run was parked by a mistaken kanban_schedule call (see earlier comment); the test file existed from that run and was kept.
(e) Reading: on 42 countries with the frozen stack, the country-named persona prompt sits closest to human distributions (0.365), the neutral base is in the middle (0.470) and the adapter is farthest (0.515); the adapter's extra distance over base is small but its interval excludes zero, and the persona's gain over base is clear under both resampling units. The adapter is the only cell with a clear trust rank link to the GPS anchor (0.74); the persona cell's link is indistinguishable from zero. Closeness to human answer shape and rank retention of the anchor do not favour the same cell. The fourth cell (adapter+persona) is not yet available, so the 2x2 interaction is not estimated.

