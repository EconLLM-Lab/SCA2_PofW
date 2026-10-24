## E1 · Workbench v1.6 candidate: journal-version wording, bundle path fix, tree hygiene (engineer)

**Root:** `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization`
(branch `Adapter-Brain-Vizualization`, HEAD `a291f3b`, the source of deployed v1.5 at `890ead3` + docs).

**Goal.** Three fixes, then a verified-ready production bundle. No data or capture changes.
1. **Wording.** `workbench/viewer/src/landing.ts:95` says "Paper B extends the method to a 42-country cohort".
   Paper B is the *journal version* of the preprint, not an extension. Replace with: "Paper B, the journal version
   in preparation, evaluates the method as a scoring instrument on a 42-country cohort; this workbench is its
   companion." Grep the whole viewer source, the story JSON builder and the Space README for any other
   "extends", "sequel", "follow-up study" or "Paper B builds on" phrasing about Paper B and fix it the same way. Keep
   the arXiv:2610.06562 citations for Eq. 6 and the SCA2 name; they are correct.
2. **Bundle builder (WB3.1-V N3).** `build_deploy_bundle.py` hard-codes an engineer scratch path; resolve it from
   an argument or a repo-relative default, resolve symlinked scratch, and add a test.
3. **Tree hygiene.** Untracked: `workbench/viewer/screens/sca2/{verified,wb3v,wb31v,wb4v}/` and
   `workbench/analysis/out/w3v_*`. Commit the curated `verified/` screenshots if they document the shipped
   release; add anchored `.gitignore` rules for the iteration folders. Delete nothing. **Do not touch the W3b
   files** (`analysis/w3b/run_w3b.py` modification, `analysis/out/W3b_*`, `analysis/w3b/plot_w3b.py`,
   `analysis/w3b/tests/`, `analysis/out/_discarded_W3/`): they wait on Augusto's decision.

Then build a fresh production bundle into scratch (≤ 0.95 GB), check its manifest and that the data JSON
(`sca2_data.json`) and every export are byte-identical to v1.5's manifest except the files the wording change
touches; run the viewer tests, `tsc`, and a headless screenshot of the landing page at 1440×860 showing the new
footer. Use the `interpretability-visual-workbench` skill's §7 procedure.

**Artifact:** commits on `Adapter-Brain-Vizualization` (explicit paths only), plus
`workbench/plans/WB8_CANDIDATE.md`: commit sha, bundle path, manifest file count, sha256 of the manifest, the list of
files that differ from v1.5 and why, test/tsc results, screenshot path. **Do not push and do not deploy.**

**Fence:** only the workbench worktree. Never open `data/`. Never print `HF_TOKEN`.

**Budget:** about 50 tool calls. Commit after each fix that passes its tests.
