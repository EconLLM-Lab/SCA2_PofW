## Card T6 — Analyze the replicate and the 64-profile sign-prompt factorial

Starts when card T4 is done. Inputs are on `Bonorinoa/SCA2-paper-b-artifacts` under the run ids that T4
reports in its final comment (read card T4 first).

Do this:
1. Sign-prompt factorial (strict battery, 64 cells). Build one long CSV with `eval_country` = `P_` + the
   profile id. Run `paper_b/analyze_factorial.py --adapter <adapter_strict_v1.csv> --signprompt
   <that CSV> --out planning/sprint_2026-10-11/paper-b-tier1/results/factorial`. Then extend
   `paper_b/factorial_report.py` ADDITIVELY: add an option for a 64-cell sign-prompt file and add a
   `route_contrast_64_cells` block computed exactly like `route_contrast_26_cells`, but with the full
   2^6 design (`factorial_effects.fit`). Keep the 26-cell block. Re-run it and write
   `results/factorial/factorial_report.json`.
   Report for both routes: V5 (row-wise own-surface dominance), column-wise dominance, the diagonal with
   OLS t and Lenth t, the sign of every own effect, and the share of the first principal component.
2. Replicate. Write `paper_b/analyze_replicate.py` and its test. For the replicate unit against the
   original unit with the same bits: max |probability difference|, the Pearson correlation of expected
   codes over the 23 strict items and over the 223 held-out items, and the size of every strict-surface
   difference in SD units of the 64 profile composites. Call it "an unseeded retrain". Do not compute or
   cite any weight-space cosine (verifier finding F8).
3. Note: `planning/sprint_2026-10-11/paper-b-tier1/results/REPLICATE_AND_PROMPT64_20261018.md` with the
   two results and how each number was made.

Write boundary: `paper_b/analyze_replicate.py`, its test, additive changes to
`paper_b/factorial_report.py` (and its test, if one exists), files under `results/factorial/`, and the
note. Do not commit.
