VERDICT: PASS-WITH-NOTES

# Independent verification of the CP26 replication (card CP26-RV, t_6bded1bd)

Cross-family verifier (GLM-5.3 via OpenRouter, run 158). Producers of both cards: Claude Sonnet 5.5
(ASU seat). Fence: `data/` and `.replication_2026-10-25/human/` were never opened (this route is not
ASU-approved for licensed human data); human surfaces are checked by method, not by value. All probes are
in `probes_rv/` beside this file. Repo state: branch `feat/paper-b-cohort`, HEAD `354769e`
(RP2's commit), working tree clean except an unrelated untracked file from another card.
RP1 commit `5fb7252` (manifest, report, `compare_results.py`), RP2 commit `354769e`
(manifest, report, `compare_results_human.py`), both on HEAD `6e69065`.

Method per check, written as it ran (each numbered section was appended right after its check finished):

## 0 · Setup and provenance premise (recorded before the checks)

- Table: sha256 `71ee7c8c…ce186a4` (matches the lock), 562 data rows, `claim_id` unique.
- RP1/RP2 commits: `git show --stat` of `5fb7252` and `354769e` touch exactly 3 files each (their manifest,
  report, compare script) — nothing else. `.git/info/exclude` carries `.replication_2026-10-25/`.
- Code-at-recorded-commit: every `.py` under the RP1 copy tree `rtree/paper_b/` is byte-identical to
  `git show 6e69065:<path>` except `bank2_transport.py`, `w1_crosstalk.py`, `analyze_near_zero.py`, whose only
  diff is the documented `paper_b_inputs` constant pointing at `.replication_2026-10-25/model_only/inputs/`.
  `persona_strict.py` is byte-identical (it reads `BT.INPUT_DIR` from the patched `bank2_transport.py`, so the
  manifest's "four scripts" list is right in substance, imprecise on which file literally holds the constant — note N3).

## 1 · Coverage — PASS

Probe: `probes_rv/check1_coverage.py` (own classifier, stdlib only; `env -u PYTHONPATH python3 …check1_coverage.py`, exit 0).
Every one of the 562 `claim_id`s falls in exactly one card's row families (`RO_` shared by both, as both reports
say); nothing is out of scope, nothing unassigned or double-owned. Per-family counts from the table equal the
counts printed in each card's own report table: RP1 `B2_`30 `FX_`58 `FX26_`4 `RP_`17 `NZ_`32 `RO_`9 `HASH_`6
`PX_`46 `C9_W1_`66 `C9_label_recovery_`8 = 276; RP2 `SCR_`25 `PD_`27 `CMP_`10 `SP_`7 `RO_`9 `C9_a_`21 `C9_b_`14
`C9_c_`60 `C9_d_`21 `C9_e_`42 `C9_f_`9 `C9_TVD_`50 = 295; 276+295−9 = 562. Cross-check of RP2's own scope rule
(rows whose `output_file` ends with one of its 8 result files) against its prefix families: identical sets, no
stray row — so `compare_results_human.py` could not have silently skipped a table row by file-scope drift.
My first probe run flagged 8 `RO_` rows; that was my own bug (I had left the shared `RO_` family out of my RP2
prefix list and truncated the printed set at 8), reproducible in git history of the probe, not a finding on the cards.

## 2 · Model-only values, re-derived with my own code — PASS (one fp-degeneracy note)

Three families (one is `C9_W1_*`, one is `C9_label_recovery_*`, as the card requires), all from the RP1
re-run files plus the fetched Hub inputs; every probe is my own implementation, no `paper_b`/RP1 code for
the compared values. Commands and exit codes below, run as `env -u PYTHONPATH .venv/bin/python <probe>`.

- `C9_label_recovery_*` (8 rows) — `probes_rv/check2a_label_recovery.py`, exit 0, `0 mismatches`.
  Country-equal means and both bootstrap intervals re-computed from the 42 per-country rates in the re-run
  `c9_label_recovery.json`, my own percentile bootstrap mirroring the documented procedure and the recorded
  seeds (20261011 profile-block over 26 profiles, 20260905 country, 2000 draws): bit-exact on value,
  `ci_low`, `ci_high`, n=42 for all 8 rows.
- `C9_W1_*` (66 rows) — `probes_rv/check2b_w1.py`, exit 0, `0 mismatches`.
  Part A re-derives all 66 rows from `inputs/{adapter_strict_v1,cohort1_strict}.csv` + the tracked GPS z
  (my own E[recode] -> composites -> probe-design OLS -> full/own/cross decomposition -> my own Spearman /
  variance / covariance / main-effect-share / label checks): 65/66 match the tracked table within 1e-9 with
  n exact (most at <=1 ulp). The one flag, `C9_W1_altruism_spearman_cross_vs_gps` (mine 0.3013 vs tracked
  0.2845), is **not a discrepancy**: `cross` is invariant to the surface's own bit, so countries sharing a
  cross-bit pattern are exact mathematical ties that the pipeline's ~1e-16 residuals order arbitrarily
  (three altruism cross-pattern groups mix own-bit values, internal gaps 1.1e-16/5.6e-17). Part B re-ran
  the *tracked* producer chain (the unmodified rtree copy RP1 ran) on the same inputs and it reproduces the
  tracked JSON field exactly (0.28453229265088226), so the tracked value is the deterministic output of the
  tracked code — RP1's byte-identity claim holds for this family too. Note N4.
- `HASH_*` (6 rows) — `probes_rv/check2c_hash.py`, exit 0, `0 mismatches`. Working-tree sha256, git blob
  at HEAD, git blob at tag `prereg-heldout-2026-10-14` (LF and its CRLF form), `overrides.json`, frozen
  selection: all six re-hashed with my own hashlib/`git show`, byte lengths included, exact string match.

## 3 · Commands are the real ones (six manifest entries, three per card) — PASS

RP1 (`MANIFEST_model_only.md` "Commands per result file"):
- `FX_*`/`FX26_*`: manifest command `analyze_factorial.py --adapter … --signprompt … --out results/factorial`
  then `factorial_report.py --adapter … --signprompt-strict … --signprompt-strict-64 … --results results/factorial`
  = `REPLICATE_AND_PROMPT64_20261018.md` §3 "How to reproduce" lines 119-130, verbatim (same flags, same
  outputs); the note's table lines 8-9 name the same two producers.
- `RP_*`: manifest `analyze_replicate.py --replicate-strict t6/replicate_strict_v1.csv --original-strict
  adapter_strict_v1.csv --replicate-heldout … --original-heldout … --out results/replicate` = same note,
  lines 130-136, verbatim.
- `NZ_*`: manifest `analyze_near_zero.py --refit GBR/COL … --control … --manifest … --baseline
  adapter_strict_v1.csv --noise replicate_surface_diff.csv --out results/near_zero` =
  `NEAR_ZERO_20261018.md` line 124ff, verbatim (note line 4: "Every number below was produced by
  `paper_b/analyze_near_zero.py`").
- Code at the recorded commit: every `.py` under `rtree/paper_b/` is byte-identical to `git show
  6e69065:<path>` except the three scripts whose only diff is the manifest-declared `paper_b_inputs`
  constant pointing at the fetched inputs (verified in section 0; `persona_strict.py` needs no patch, note N3).

RP2 (`MANIFEST_human.md` "Result files and producing commands"):
- #1 `screen_result.json`: manifest `python paper_b/heldout/run_screen.py` — `SCREEN_RESULT_20261017.md`
  line 5 says exactly that command and output; `TIER1_ANALYSIS_20261017.md` table row "Primary screen" agrees.
- #2 ceiling: manifest says the note gives `--items` but not `--out` — `TIER1_ANALYSIS_20261017.md` line 10
  reads `ceiling.py --items ceiling_heldout/items.json` with output column `ceiling_heldout/`: the missing
  `--out` value is exactly the gap the manifest declares, no invention.
- #4 `heldout_per_dimension.json`: manifest `per_dimension.py` (defaults, seed 20261015, 2000 bootstrap,
  10000 permutation) — `HELDOUT_PER_DIMENSION_20261018.md` header names the script and the same
  seed/draws; the script's own defaults match (`grep` of `paper_b/heldout/per_dimension.py`).
  (#5b's `--arm signprompt` command is likewise the TIER1 line-11 row; arguments not recorded, declared.)
- Code at the recorded commit for RP2 is checked **by method only**: the mirror tree lives under
  `.replication_2026-10-25/human/`, which this route may not open; the manifest declares "paper_b/ is a
  copy of the tracked code (no edits)" and `compare_results_human.py:97-103` itself loads the builder from
  the tree and asserts it is the mirror tree's. Not independently byte-checked here — the fence, not a doubt.

## 4 · Compare scripts are honest — PASS

Read both (`compare_results.py`, `compare_results_human.py`, committed in the RP1/RP2 commits):
- Tolerances as briefed: exact for counts/strings and for the seeded families (`B2_`, `PX_`,
  `C9_label_recovery_` exact in RP1's `FAMILIES`; RP2 exact for `screen_result.json`,
  `heldout_analysis.json`, `heldout_per_dimension.json`, `c9_*` and exact rows except its declared
  `TOL_ROWS` = deterministic ceiling + `RO_` at 1e-9), integer-valued cells exact in both. Matches the
  replication brief (exact for seeded bootstraps/permutations, abs <= 1e-9 otherwise).
- No silent skip of a missing file: both `part1`s append `(not regenerated)` to the bad list when the
  re-run file is absent and exit 1 (`compare_results.py:135-137`, `compare_results_human.py:86-87`).
- Mismatches cannot be swallowed: `main` exits 1 iff any bad key exists (RP1 `main:212-218`, RP2
  `main:202-208`); the only declared skip is `SKIP_KEYS={"path","source"}` (`compare_results.py:73`),
  absolute paths that differ by design between copy and repo, with the sha256 beside them compared.
- Mutation test (mine, on a fresh copy of `rtree/` under the verifier scratch): one value in
  `c9/w1_why_trust.json` moved by 1e-6 → `compare_results.py --rep <copy>` exits 1 and prints exactly
  `c9/w1_why_trust.json/adapter/bank2_observed[0]/spearman_full_vs_observed |diff| 1e-06` (plus the table
  rows that read it); one file deleted from the copy → exits 1 with `(not regenerated)`. Both fail loudly.
- Baseline re-run by me: `env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python
  planning/checkpoint_2026-10-26/replication/compare_results.py --show-size` → exit 0, last line
  `0 mismatches`, per-family table identical to RP1's report (276 in scope / 286 to RP2 / 0 unassigned).
- RP2's `--self-test` (perturbed float, dropped row, changed count, exact-rule 1e-12) is in the committed
  script (`self_test`, lines 170-187) and its report quotes it; I did not execute RP2's comparator because
  it reads `.replication_2026-10-25/human/` (fence) — audited by reading, not by running.

## 5 · Nothing leaked — PASS (one pre-existing steward flag, not from the replication)

- `git show --name-only` of `5fb7252` and `354769e`: each touches exactly its three files under
  `planning/checkpoint_2026-10-26/replication/` — nothing under `data/`, nothing from
  `.replication_2026-10-25/` (which is also excluded in `.git/info/exclude`). Working tree is otherwise
  clean except an unrelated untracked file from another card.
- Content scan of every added line in both commits (my scanner): 4 pattern hits, all in
  `MANIFEST_human.md`/`REPLICATION_human.md` prose — two manifest rows naming input *paths*
  (`data/WVS/WVS_wave7.dta`, `data/GPS/…`) with no values, and two sentences of RP2's own limits /
  data-exposure paragraphs. No respondent row, no per-country human value, no model-human join.
- RP2's steward flag checked: tracked `results/heldout_items.csv` header is
  `question_id,top_dimension,sign,rho,a_i,t_top` — per-item agreement statistics, aggregate over
  countries, no country column, exactly as RP2's report describes it.
- **Pre-existing, NOT a replication finding (flag for the data steward, metadata only — this route may
  not open `data/`):** `git ls-files data/` is not empty — 54 tracked paths (public docs/manifests, and
  among them `data/validity/{gradients_wvs.csv,scores_*.csv}`, `data/merged/…`, `data/phase2/derived/rung_mix/*.jsonl`),
  all `ON-origin-main` (public remote), last touched 2026-08-04 (`2d1dc54`) and by the Paper A commit
  `5664026` (2026-09-28), i.e. long before this checkpoint. Whether any of those carries human-derived
  columns is a question for a route that may open them; the replication commits added none of them.

## 6 · Verdicts follow from the evidence — PASS

- RP1 `RESULT: REPRODUCED-WITH-NOTES` vs its own table: table says 276 rows in scope, 0 mismatches in
  every family; my coverage probe independently re-derives the same 276 (and the 286 left to RP2, 562
  total); my baseline re-run of its comparator exits 0 `0 mismatches` with the identical family table;
  my own re-derivations reproduce three of its families (label recovery bit-exact, W1 65/66 + the
  fp-degenerate 66th reproduced through the tracked chain, hashes exact). The `-WITH-NOTES` reasons
  (five families with no recorded command, scores not re-made, `bank_robustness.csv` unverified, persona
  replay partly self-referential, `SP_*` boundary) each check out against the manifest and notes.
- RP2 `RESULT: REPRODUCED-WITH-NOTES` vs its own table: table says 295 rows in scope, 0 mismatches;
  my coverage probe independently re-derives 295 from RP2's own scope rule (output_file suffixes) and
  shows it equals its prefix families with no stray row; its four documentation gaps and three limits are
  exactly what the manifest documents. I could not re-run RP2's pipeline or comparator (reads licensed
  human data through `freeze.require_freeze()` and the human replication tree — fenced for this route);
  its number-level claims rest on RP2's own run plus my method audit of the comparator, named as such.
- No verdict anywhere overclaims: neither card claims the GPU scoring was re-run; both say the scores
  were re-fetched and the tables re-derived, which is what the brief asked the replication to show.

## Notes (why PASS-WITH-NOTES)

- **N1 · Documentation gaps both cards already declare.** RP1: `B2_*`, `RO_*`, `PX_*`, `C9_W1_*`,
  `C9_label_recovery_*` have no recorded producer command (defaults/docstring used; `RO_*`'s original
  driver was a scratch script not in the repo). RP2: `ceiling_heldout` (`--out` missing),
  `heldout_analysis.json` (`--signprompt-selection` value missing), `signprompt_selection_20261017.csv`
  (arguments missing), top-level `ceiling_*` (usage line only). Both cards state these themselves; the
  matches then show the defaults give the banked numbers.
- **N2 · The human side is verified by method, not by re-run.** This route is fenced out of `data/` and
  `.replication_2026-10-25/human/`, so RP2's 295-row, 20-file byte-identity claim was checked as: scope
  re-derived from the tracked table (check 1), comparator audited line by line with its self-test read
  (check 4), commands checked against the cited notes (check 3), leak scan on the commits (check 5).
  RP2's mirror-tree "no edits" claim is manifest + comparator assertion, not my byte-check.
- **N3 · Manifest wording vs literal diffs.** RP1's manifest/report say the `paper_b_inputs` constant was
  patched "in four scripts"; only three files (`bank2_transport.py`, `w1_crosstalk.py`,
  `analyze_near_zero.py`) literally differ, because `persona_strict.py` reads `BT.INPUT_DIR` from the
  patched `bank2_transport.py`. Substance correct, count imprecise.
- **N4 · `C9_W1_altruism_spearman_cross_vs_gps` is fp-degenerate.** `cross` is invariant to the own bit,
  so countries sharing a cross-bit pattern are exact mathematical ties ordered by ~1e-16 residuals; my
  independent implementation gives 0.3013 vs the tracked 0.2845 (three pattern groups mix own-bit values,
  gaps 1.1e-16/5.6e-17). The tracked chain reproduces the tracked value exactly from the same inputs
  (verified by running it), so the row is right *as the deterministic output of the tracked code*; it is
  not stable under re-implementation at machine precision. Descriptive C9 row, no claim depends on it.
  (Found while making my probe match: my first beta path used `lstsq` where the producer uses normal
  equations, which also flipped `patience_Q50`; matching the documented solve cured all but altruism.)
- **N5 · Pre-existing tracked `data/` inventory (steward, not the replication):** 54 tracked paths under
  `data/`, on the public remote, last touched 2026-08/09 (incl. the Paper A commit `5664026`) — see
  section 5. The replication commits added nothing there.
- My own probes needed two correction rounds, both mine: the coverage script initially omitted the shared
  `RO_` family from its RP2 prefix list (and truncated the printed set), and the W1 probe's OLS path is
  described in N4. Probes as committed are the corrected versions; their exit codes are above.

## What I did not verify

- RP2's re-run outputs and byte-identity (fence: `data/`, `.replication_2026-10-25/human/`); its RESULT
  line therefore rests on RP2's own run plus my method audit, named as such.
- The GPU scoring itself (no card re-ran it; both cards say scores were re-fetched, never re-made).
- Any file under `data/` (fence) — including the column contents of the pre-existing tracked inventory
  in N5 (metadata only).
- `results/factorial/bank_robustness.csv` (tracked, regenerated by no recorded command; not read by the
  numbers table; RP1 leaves it unverified and I concur).

## Commands (exit codes captured without pipes)

- `env -u PYTHONPATH python3 planning/checkpoint_2026-10-26/replication/probes_rv/check1_coverage.py` → 0
- `env -u PYTHONPATH .venv/bin/python …/probes_rv/check2a_label_recovery.py` → 0 (`0 mismatches`)
- `env -u PYTHONPATH .venv/bin/python …/probes_rv/check2b_w1.py` → 0 (65/66 at 1e-9 + N4 resolved)
- `env -u PYTHONPATH .venv/bin/python …/probes_rv/check2c_hash.py` → 0 (`0 mismatches`)
- `env -u PYTHONPATH .venv/bin/python planning/checkpoint_2026-10-26/replication/compare_results.py
  --show-size` → 0 (`0 mismatches`; mutation variants → exit 1 with exact keys)
- Route: GLM-5.3 via OpenRouter (verifier profile, run 158), a different family from the producing cards
  (Claude Sonnet 5.5, ASU seat). No `data/` or `.replication_2026-10-25/human/` path was opened by any
  probe above; `HF_TOKEN` was never read or printed.
