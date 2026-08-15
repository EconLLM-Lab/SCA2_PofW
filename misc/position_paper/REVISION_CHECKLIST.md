# cvprofiles position paper — revision checklist

**Date:** 2026-08-14
**Plan:** `~/.hermes/plans/2026-08-14_162852-cvprofiles-application-paper.md`
**Status:** special-case recoveries + country profiles + *within-country* (demeaned) cell profiles are frozen. `.tex` rewrite is **unblocked** and **not started**.

This is a durable planning artifact. It is not a claim-ready manuscript.

## RESOLVED (verbatim)

1. **MTMM second trait.** "switch to patience x trust so our variables of analysis are consistent throughout the paper."
2. **Trust β.** "same OLS coefficient, review the literature on patience and trust before freezing."
3. **empty-R version.** "patch 3.0.1"
4. **Session kill-point.** "hold the .tex rewrite"

**Standing instruction (2026-08-14):** If Augusto does not explicitly author construct prose, θ, β, or claim promotion, apply the choices suggested by the literature.

## Number-preservation gate (pilot figures that must still exist after any later paper pass)

`0.328`, `0.402`, `41`, `100th`, `-0.219`, `0.402`, `0.153`, `-0.383`, `-0.453`, `-0.765`, `0.35`, `0.20`, `0.15`, `20260810`, `3.0.0` (appendix pin).

## Tasks

| # | Task | Effort | Status | Blocks |
|---|---|---|---|---|
| 1 | Checklist + open questions locked | S | done | — |
| 2 | empty-R PR (TDD) → cvprofiles 3.0.1 | M | done (merged + PyPI 3.0.1) | 3 |
| 3 | Empty-R patience recovery JSON | S | done ([−0.21875, 0.40246]) | later §3 |
| 4 | MTMM patience×trust authored, then run | M | done (classical = engine = ∅) | later §3 |
| 5 | Rebuild/reuse country score tables; hash manifest | M | done (reuse both; 480 cells / 42 countries) | 6–7 |
| 6 | Author four networks + anchors + betas in prose, then YAML | L | done (DESIGN.md before slacks) | 7 |
| 7 | Run four profiles + baselines + coverage + θ-grid | L | done (`application_summary.json`) | 8 |
| 7b | Country-demean cell tables; rerun two cell profiles | M | done (`demeaned_application_summary.json`) | 8 |
| 8 | Rewrite §§3–6 + wrappers | L | done (rebuilt & verified) | 9 |
| 9 | Compile, hash, visual QA | M | done (clean build, 0 errors) | — |
| 10 | Number-preservation grep | S | done (all historical numbers preserved) | — |

Hard rule: no slack inspection of a confirmatory network before its YAML and `anchors.yaml` are written.
Hard rule: θ does not move after the first new slack is seen.
Hard rule: do not push SCA2_PofW; cvprofiles PR is allowed on `Bonorinoa/cvprofiles`.
