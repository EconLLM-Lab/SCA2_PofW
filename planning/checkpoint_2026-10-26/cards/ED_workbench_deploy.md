## ED · Deploy workbench v1.6 to the Space (sca)

**Root:** `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/.worktrees/adapter-brain-vizualization`.

**Precondition (fail fast).** Read the first line of `workbench/plans/WB8_VERIFICATION.md`. Deploy only on `PASS` or
`PASS-WITH-NOTES` whose notes are not about data. On anything else, `kanban_block` with `kind=needs_input` and quote
the verdict. Do not fix code yourself.

**Goal.** Deploy the candidate sha named in `workbench/plans/WB8_CANDIDATE.md` to the public static Space
`EconLLM/sca2-workbench`, following the `interpretability-visual-workbench` skill,
`references/hf-private-static-space-deploy.md` (deploy from this worktree, upload with `delete_patterns`, never set
`app_file`, keep storage ≤ 0.95 GB). Use the `HF_TOKEN` in your profile `.env`; never print it.

**After the upload:** compare the Space file by file (path, size, sha256) with the manifest; confirm stage RUNNING
and `private: false`; load the landing page and confirm the new footer text; record cold landing time and console
errors. Append a "v1.6 deploy" section to `workbench/README.md` (commit, file count, storage, verifier card, date)
and commit it by explicit path. Do not push the git branch.

**Artifact:** `workbench/plans/WB8_DEPLOY.md` with the checks above. Never open `data/`.

**Budget:** about 30 tool calls.
