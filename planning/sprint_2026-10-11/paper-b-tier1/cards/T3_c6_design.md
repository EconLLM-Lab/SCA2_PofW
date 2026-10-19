## Card T3 — Near-zero margin (checkpoint C6): design note only, no GPU

Why: journey checkpoint C6 asks for a refit of a predeclared subset with the near-zero pairs removed
(|z| < 0.10). Two facts make the original wording unusable:
- No subset was ever declared (`planning/sprint_2026-10-11/PARENT_DECISIONS.md` has none).
- Bank-2 adapters are 64 sign-profile units. Their labels come from synthetic z vectors
  (`paper_b/factorial.py`, `z_vector(unit)`), so the `near_zero_z` flag is always false for them.

A real cohort country's bank-2 labels equal the labels of its sign-profile unit, because the
deterministic sign rule reads only the signs. So the near-zero refit for a country c in profile u is:
unit u's bank-2 training rows minus the rows whose `gps_dimension` d has |z_c,d| < 0.10 (z from the GPS
z-vector file, `paper_b/analyze_surface.DEFAULT_GPS_JSON`). The baseline is the existing adapter of
profile u. You must prove the first sentence in code before you rely on it.

Do this:
1. Write `paper_b/near_zero_bank.py` and `paper_b/test_near_zero_bank.py`. Test that, for every cohort
   country, the chosen/rejected labels of its bank-2 rows built with the country's real z equal those of
   its profile unit (`factorial.label_row`). Then build the reduced bank for one country.
2. Declare the subset now, by a rule that uses training exposure only and no score of any kind. Journey
   wording: "one multi-member profile and one singleton". Rule: among cohort countries with at least one
   dimension where |z| < 0.10, take the singleton-profile country with the most near-zero training rows,
   and the multi-member-profile country with the most near-zero training rows. Ties go to the
   alphabetically first ISO3 code. Report the two countries, their profiles, rows kept and rows dropped.
3. Write `planning/sprint_2026-10-11/paper-b-tier1/C6_DESIGN.md` with:
   - the definition above and the result of the label-equality test;
   - the subset rule, the two countries, and the row counts;
   - the training plan: same configuration as the bank-2 profile adapters (Llama-3.1-8B-Instruct, LoRA
     r=16, 1 epoch, lr 1e-4, beta 0.1, max_length 768, TRAIN_FRAC 0.80, SEED 42; read `paper_b/config.py`
     and `paper_b/protocol_bank2.py` and state how the smaller row count changes the split);
   - the Hub paths for the new adapters, under `bank2/<bank run id>/near_zero/<CC>/` in
     `Bonorinoa/SCA2-paper-b-adapters` (never `adapters/<CC>`), and a new scoring run id
     `bank2-nearzero-strict-v1-<date>` for the strict battery;
   - the comparison: per strict surface, refit composite minus baseline composite, in units of the SD of
     the 64 profile composites. Reading, from C6: if an imprint surface moves against the profile's
     intended direction, say so and do not promote the filter; if not, the margin stays a footnote;
   - the exact commands that the engineer will run.
4. Build the two reduced banks locally under
   /Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/near_zero/<CC>/ with a manifest (row counts,
   SHA-256). Do not train and do not upload.
5. When the note is complete, REQUEST REVIEW on this card (`hermes kanban request-review`). Do not
   complete it. The orchestrator approves the design before any GPU spend.

Write boundary: the two new .py files, `C6_DESIGN.md`, and the local near_zero folder. Do not commit.
