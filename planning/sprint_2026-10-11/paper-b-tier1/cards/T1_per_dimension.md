## Card T1 — Per-dimension intervals for the held-out screen (checkpoint C5)

Why: journey checkpoint C5 says that an imprint dimension whose interval includes 0 "is not transport".
The held-out results give the statistic A per dimension, but without intervals. The paper cannot write a
per-dimension transport sentence until this card is done.

Do this:
1. Write `paper_b/heldout/per_dimension.py` and `paper_b/heldout/test_per_dimension.py`.
2. Read human data only through `freeze.require_freeze(paper_b/heldout/FREEZE.json)`. Build the human
   surface with `run_screen.human_surface(pool)` (registered rule, `MIN_N = 1`) and GPS with
   `run_screen.load_gps()`. Use `screen_test.item_agreement` for a_i. Reuse `analyze_heldout.route`,
   `analyze_heldout.adapter_route` and `analyze_heldout.REPAIRED` (Amendment 2: the 12 repaired items
   leave both comparator routes).
3. For each route and each dimension that the route assigns, compute A_d (mean a_i over the items of
   that dimension), the number of items, and a 95% percentile interval from 2,000 country-bootstrap
   resamples of the 42 countries with seed 20261015 (`screen_test.PERM_SEED`). Routes:
   - adapter primary (56 items, `paper_b/heldout/selection_amended_20261016.csv`, `primary_selected`)
   - adapter secondary rule (185 items, `secondary_selected`)
   - sign-prompt primary (`planning/sprint_2026-10-11/paper-b-tier1/results/signprompt_selection_20261017.csv`)
   - face-valid (`paper_b/heldout/face_valid.csv`, imprint dimensions, Q82 removed)
   - Jev majority (`paper_b/heldout/jev/majority_face_valid_jev.csv`, imprint dimensions, Q82 removed)
4. Descriptive only (label it "not registered"): a one-sided permutation p per dimension. Draw as many
   pool items as the dimension has, give them that dimension and the selected items' signs in random
   order, 10,000 draws, seed 20261015.
5. Test: the same seed gives identical intervals on a small synthetic frame, and the dimension grouping
   matches the selection file.
6. Outputs: `planning/sprint_2026-10-11/paper-b-tier1/results/heldout_per_dimension.json` and the note
   `planning/sprint_2026-10-11/paper-b-tier1/results/HELDOUT_PER_DIMENSION_20261018.md`. The note has
   one table per route and one line per adapter dimension with the C5 reading: "interval excludes 0:
   transport" or "interval includes 0: not transport".

Expected scale, for a sanity check only: adapter primary A per dimension was risktaking 0.158 (13
items), altruism 0.069 (20), trust 0.062 (12), posrecip -0.071 (11). Your A_d values must equal these.
If they do not, find the cause before you report.

Write boundary: the two new .py files and the two output files. Do not commit.
