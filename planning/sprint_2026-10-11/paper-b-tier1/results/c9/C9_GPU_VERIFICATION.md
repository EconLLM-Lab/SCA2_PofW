# C9-GV verification of C9-4 (t_8d569fe0): GPU comparator + label recovery

Verifier: profile `verifier`, route anthropic claude-sonnet-5-5 (a different family from the Codex gpt-6.1-sol producer).
Date: 2026-10-19 (MST), checked after the producer's completion at 17:29.
Branch `feat/paper-b-cohort`, HEAD `2e43347`. All C9-4 files are untracked (nothing committed).
Calculation script (read-only, no human rows, no secrets): `planning/sprint_2026-10-11/paper-b-tier1/results/c9/c9_gpu_verify_calc.py`

## Verdict: BLOCK

The producer closed C9-4 with "GPU execution and 42-country recomputation still pending". Neither experiment A nor
experiment B was run. What was delivered is a CPU fixture summary of the old 16-country preprint data plus a planning
note. The card's acceptance rule says "missing execution is not PASS". No scientific claim is made here: a null
result would have been fine, but there is no result.

## Findings (each has evidence)

1. Experiment A (adapter + own-country C8 persona, 42 countries, strict 23 items) was not executed.
   - `paper_b/c9_gpu_jobs.py` has no model, adapter, tensor or forward-pass code and no Colab launch code. My regex
     for `PeftModel|from_pretrained|load_adapter|safetensors|BitsAndBytes|AutoModelForCausalLM|snapshot_download|
     hf_hub_download|torch|forward(` returned `[]` (calc script, section 3).
   - `build_adapter_persona_c9_run_script()` (c9_gpu_jobs.py:175-219) returns a dict of strings and writes a markdown
     file. It points at `paper_b/colab/vm_run_persona.py`, which the PM override said is the base-only C8 driver.
     The text in `c9_gpu_run.md` line "Units: 42 ... using real adapter weights" and "The adapter+persona cell uses
     the actual cohort-1 adapter" states something that did not happen. The code docstring says the opposite
     ("planning/launch script, NOT the adapter loader"), so the artifact contradicts the code.
   - No `adapter-persona-strict-v1-20261019` output exists in the repo. A grep for the run id finds only the two
     planning notes and the `results/c9` copy of them. G1/G2/G3 gates, base parity, LoRA tensor load: not run.
2. Experiment B (132 held-out training-scenario pairs x 42 adapters) was not executed.
   - `results/.../c9_label_recovery.json` has 16 per-country rows, 16 distinct countries, 2,112 cells. Required:
     42 countries, 5,544 cells (calc script, section 4). Its own `note` says "full 42-country GPU recomputation
     requires ...".
   - The numbers come from `analysis/phase2/outputs/gps_reward_recovery_long.csv`, a 16-country file with two banks
     (`co2_8`, `ksenias_base8`) and precomputed `adapter_margin`/`ref_margin`. That is the old preprint fixture. It
     reproduces 0.9422/0.8191 (my independent pooled values: 0.9422348485 and 0.8191287879; per-country mismatches
     beyond 5e-5: none), so the preprint figures are reproduced from stored margins. This is not a recomputation on
     the 42 cohort-1 adapters and it does not show the producing code, split, wrapper or max length.
   - The JSON `run_id` is `label-recovery-v1-20261019` and `adapter_revision` is `7550fd4c...`. Both are stamped on a
     fixture that never touched those adapters (c9_gpu_jobs.py:137-138). That is a mislabel: the real run id is on
     fixture output. The CSV rows carry the same run id and the pin.
   - The producer also never traced the definitions to notebook cells: JSON cites "results.tex line 28,
     methodology.tex line 24" and a notebook path with no cell reference. I did not find a source-equation check in
     any test.
3. Bootstrap is now a real resample, but not the specified statistic and not tested.
   - Resampling picks clusters with `random.choice` (c9_gpu_jobs.py:123). Good. But the statistic is the mean of
     the concatenated country values of the drawn profiles (size-weighted), not a country-equal mean. No test checks
     which.
   - Fixture clusters: 13 sign profiles among the 16 fixture countries; the 26-cluster resample only exists for the
     full 42 (calc section 2). My independent CI for recovery is [0.9242, 0.9573] vs the producer's [0.9251, 0.9577];
     accuracy [0.7611, 0.8770] vs [0.7613, 0.8717]. Differences come from RNG and cluster-weighting choices, so the
     CI cannot be reproduced exactly from the producer's description either.
   - Premature rounding: per-country rates are `round(...,4)` at c9_gpu_jobs.py:92-93 before pooling
     (pooled from rounded 0.9422375 vs exact 0.9422348). Small, but the card said "no premature rounding".
   - Fake individual CI: the CSV repeats one pooled interval on all 16 country rows (1 distinct pair across 17 rows,
     calc section 5). The card forbids a shared global CI shown as a country CI. This is an open defect in the artifact.
   - Missing profile does not raise: `cl.get(v["country"], "none")` at c9_gpu_jobs.py:107, with `"none"` filtered at
     :117. The PM override required a raise.
   - Order is not deterministic: `for bank in set(...)` and `for cc in set(...)` at c9_gpu_jobs.py:78-79 depend on
     string hash randomization. The same script, rerun, wrote GBR as the first row in the planning copy and USA in
     `results/c9` (diff lines 13-14). Bootstrap picks are seeded, but the cluster/country order feeding them is not,
     so the interval is not stable run to run.
4. Tests are not red-capable and are mostly string/fixture checks.
   - `env -u PYTHONPATH ... pytest paper_b/test_c9_gpu_jobs.py` exits 0 (10 passed), but four mutants also exit 0
     (calc section 6): M1 non-resampling bootstrap (every cluster once, constant interval), M2 draws=1, M3 recovery
     rule replaced by the accuracy rule (adapter_margin > 0 instead of > ref_margin), and the baseline
     adapter+persona text with no loader. None of them is caught.
   - The adapter test (`test_adapter_persona_uses_adapter_not_persona`) only greps the description string for
     "adapter tensors". It would pass with no adapter anywhere.
   - Tests write to the real repo-root `results/c9/` (cwd-relative `out_dir`, c9_gpu_jobs.py:153,192), not `tmp_path`.
     My own test run rewrote those files (the producer's instruction was that pure stats tests must not touch real run
     namespaces).
5. Full `paper_b` test suite: exit 2, not 0 (`pytest paper_b -q`: collection error `ModuleNotFoundError: No module
   named 'c9_tvd'` at `paper_b/test_c9_tvd.py:14`; `paper_b/c9_tvd.py` does not exist). That file belongs to a sibling
   card, not C9-4, so I attribute this to C9-2/tvd and report it for the PM; it still means "full paper_b tests exit
   0" is not met.
6. Compute and VM: the only tool-observed state is `colab usage`: balance 181.82 CU, rate 0.00/hr, active
   assignments 0; `colab status`: "No active sessions". That equals the pre-17:22 balance, so tool-observed CU spend
   is 0. This is consistent with no GPU work. The producer's "~1.5 CU" is a projection, not a measurement, and I do not
   accept it as cost. No VM is leaking.
7. Hub readback: no run pin, commit or sha exists to read back. I have no Hub token in this session (HF_TOKEN unset,
   deliberately), and the card says nothing was uploaded, so I could not and did not check
   `runs/adapter-persona-strict-v1-20261019/` or `runs/label-recovery-v1-20261019/` on the Hub. A grep of the repo
   (STATUS.md lists the 21 existing runs, neither id among them) finds no commit/sha claims for them.
8. Data hygiene, nothing found: no human rows or distributions on a GPU/Hub (no GPU run happened), no token printed.
   The fixture CSV in `analysis/phase2/outputs/` holds synthetic-scenario margins, not WVS respondent rows; I read
   only its numeric margin columns.

## What I could verify as correct (so the next attempt does not redo it)

- The recovery definition `adapter_margin > ref_margin` and accuracy `adapter_margin > 0`, applied per
  (bank, country) on the stored margins, reproduce the preprint's 0.942 / 0.819 on 2,112 cells.
- The profile resample picks clusters with replacement and is seeded (20261011).
- The module imports cleanly with no import-time data read, and the three CPU outputs are consistent with each other
  except for the nondeterministic row order noted above.

## Required to move to ACCEPT

1. Run A and B for real on the 42 cohort-1 adapters (CU <= 5 total, tool-observed before/after, VM stopped, new private
   prefixes, readback with sha), with a driver that loads the pinned LoRA and the C8 own-country persona on the frozen
   NF4 stack with G1/G2/G3 gates.
2. Replace the fixture-derived JSON/CSV with 42-country model-only results; remove the shared CI from country rows;
   deterministic ordering (`sorted`); no `"none"` fallback; no rounding before pooling; country-equal profile-block
   statistic with 26 clusters.
3. Add tests that fail on M1-M3 and on a no-adapter configuration; write test outputs to `tmp_path`.
4. Get `pytest paper_b` to exit 0 (the `c9_tvd` collection error belongs to a sibling card).

## Commands and exit codes

- `HF_TOKEN= env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest paper_b/test_c9_gpu_jobs.py -q -p no:cacheprovider` -> exit 0, 10 passed
- `HF_TOKEN= env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest paper_b -q -p no:cacheprovider` -> exit 2 (collection error, `test_c9_tvd.py`)
- `HF_TOKEN= env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python planning/sprint_2026-10-11/paper-b-tier1/results/c9/c9_gpu_verify_calc.py` -> exit 0 (mutants M1-M3 all passed the producer's tests)
- `colab status` -> "No active sessions"; `colab usage` -> balance 181.82, 0.00/hr, 0 active assignments
