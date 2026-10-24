## EV · Independent check of the workbench v1.6 candidate (verifier, cross-family)

**Root:** `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization`. Read
`workbench/plans/WB8_CANDIDATE.md` (card E1, produced by a Claude model; you are a different family on purpose).

**Check, appending each result to the review file:**
1. The diff from `a291f3b` to the candidate sha touches only the wording, the bundle builder (+ test), `.gitignore`
   and curated screenshots. No W3b file was committed or changed.
2. The new footer text and every other changed sentence describe Paper B as the journal version, not an
   extension or sequel; the Eq. 6 citations to arXiv:2610.06562 remain.
3. Re-run the viewer tests and `tsc` yourself; rebuild the bundle from the candidate sha into your own scratch dir
   and compare its manifest with E1's: same file list and sha256s.
4. Every data file (`sca2_data.json`, exports) is byte-identical to the v1.5 deploy manifest; only copy/code files
   differ. List any other difference as a BLOCK.
5. Serve the bundle with `python3 -m http.server --bind 127.0.0.1 <port>`, load the landing page, the Ladder and
   the Cohort tab headlessly, and confirm 0 console errors and the new footer in the DOM.

**Artifact:** `workbench/plans/WB8_VERIFICATION.md`, first line `VERDICT: PASS | PASS-WITH-NOTES | BLOCK`, findings
with file:line. Do not edit code; do not commit; do not deploy.

**Fence:** read-only except the review file and your scratch dir. Never open `data/`.

**Budget:** about 40 tool calls.
