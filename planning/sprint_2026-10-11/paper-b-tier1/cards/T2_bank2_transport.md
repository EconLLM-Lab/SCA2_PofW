## Card T2 — Bank-robustness in the planned form (checkpoint C3)

Why: journey checkpoint C3 asks for adapter–GPS imprint correlations on bank 2, with profile-block
intervals, against the banked cohort-1 run `paper-b-20261011`. The current result
(`results/factorial/bank_robustness.csv`) only correlates the two banks with each other, without
intervals. Pass rule (journey C0): each imprint interval (trust, risktaking, posrecip, altruism) still
excludes 0 on bank 2. If one does not, the write-up names that dimension and drops its transport sentence.

Do this:
1. Read `paper_b/analyze_surface.py` and `paper_b/analyze_phase.py` first. They produced the cohort-1
   numbers (for example trust adapter–GPS 0.74 [0.50, 0.86], profile-block bootstrap, 2,000 draws,
   seed 20261011). Reuse their functions (`bootstrap_spearman`, recodes, `DEFAULT_GPS_JSON`). Reuse
   `paper_b/analyze_factorial.unit_composites` for composites. Do not write a second recode.
2. Write `paper_b/bank2_transport.py` and `paper_b/test_bank2_transport.py`.
3. Step one is a reproduction check: compute the cohort-1 adapter–GPS Spearman per surface over the 42
   countries from `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/cohort1_strict.csv`. Trust must
   give 0.74 [0.50, 0.86]. If it does not, stop and report the difference.
4. Step two: bank 2. Each of the 42 cohort countries gets the composite of its sign-profile unit
   (`factorial.unit_of_z` on the GPS z vector), from `adapter_strict_v1.csv` in the same folder. Compute
   Spearman with the GPS z of the surface's own dimension over the 42 countries, with the profile-block
   bootstrap (clusters = profile cell id, 2,000 draws, seed 20261011). Patience keeps two surfaces
   (Q43 and Q50).
5. Step three: add intervals to the bank-to-bank agreement. For the 26 shared cells, Pearson and Spearman
   between bank-1 cell means and bank-2 profile composites, with a 2,000-draw bootstrap over cells, seed
   20261011.
6. Outputs: `planning/sprint_2026-10-11/paper-b-tier1/results/bank2_transport_strict.json` and the note
   `planning/sprint_2026-10-11/paper-b-tier1/results/BANK2_TRANSPORT_20261018.md`, with one table of
   the seven surfaces (cohort-1 rho [CI], bank-2 rho [CI], C3 reading) and one table of the bank-to-bank
   agreement with intervals.

Write boundary: the two new .py files and the two output files. Do not commit.
