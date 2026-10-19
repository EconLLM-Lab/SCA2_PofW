## Card T7 — Analyze the near-zero refits (checkpoint C6)

Starts when card T5 is done. Follow the comparison that
`planning/sprint_2026-10-11/paper-b-tier1/C6_DESIGN.md` defines. Do not change it.

Do this:
1. Write `paper_b/analyze_near_zero.py` and its test.
2. For each of the two refit countries: per strict surface, refit composite minus the baseline profile
   composite, in SD units of the 64 profile composites, with the direction that the profile intends.
3. Apply the C6 reading from the design note: an imprint surface that moves against the intended
   direction is reported as such, and the filter is not promoted; otherwise the margin stays a footnote.
4. Note: `planning/sprint_2026-10-11/paper-b-tier1/results/NEAR_ZERO_20261018.md` with the table and
   the reading.

Write boundary: the new .py files and the note. Do not commit.
