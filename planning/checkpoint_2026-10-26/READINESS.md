VERDICT: ready

# CP26-R readiness check: checkpoint 2026-10-26 (Paper B rewrite + workbench v1.6 + replication)

Card `t_7979b64d`, run 159, route claude-opus-5-5 (anthropic). Checked 2026-10-24 (MST) against live files, git, the HF
API and the rendered Space. Card summaries were not used as evidence. Nothing was committed. `data/` and
`.replication_2026-10-25/human/` were not opened. `HF_TOKEN` was blank for the test run.

Paths: `PW` = `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW-paper-b-draft` (branch `paper/paper-b-draft`, HEAD
`36d154f`), `MW` = `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW` (branch `feat/paper-b-cohort`),
`WB` = `MW/.worktrees/adapter-brain-vizualization` (branch `Adapter-Brain-Vizualization`).

| check | evidence | status |
|---|---|---|
| 1. MV verdict, findings, audits, anonymity | **MV verdict.** `head -1 PW/misc/paper_b/MANUSCRIPT_REVIEW_2026-10-25.md` gives `VERDICT: PASS-WITH-WORDING` (GLM-5.3, cross-family).<br><br>**Findings.** Each one is either fixed in the files or left to Augusto:<br>• W1 fixed: `sed -n 73p results.tex` contains "no detectable departure from additivity".<br>• W2 fixed: line 83 contains "labels do not carry the cross-talk".<br>• W3 fixed: `abstract.tex` contains "The instrument can complement human pretesting".<br>• N2 and N4 applied in the PM pass (`REWRITE_LOG.md` §"PM pass after MV", lines 268–286). The cover-letter diff shows the new title.<br>• N1 (intended-use positioning) and N3 (11,526 words against the 9–10k target) are listed for Augusto.<br><br>**Number audits**, run by me in `PW/misc/paper_b` with output to scratch:<br>• `HF_TOKEN= env -u PYTHONPATH MW/.venv/bin/python tools/audit_numbers.py --out $S/NUMBER_AUDIT.txt` gives exit 0: "Statistics: 405 printed, 405 PASS, 0 FAIL … Unexplained numerals: 0 … RESULT: PASS". The output is identical to the working-copy `NUMBER_AUDIT.txt`.<br>• `… tools/audit_numbers.py --files supplement.tex --out $S/SUPP.txt` gives exit 0: "551 printed, 551 PASS, 0 FAIL … RESULT: PASS".<br><br>**Anonymity grep:** `pdftotext {main,supplement}.pdf - \| grep -iE "gonzalez\|bonorino\|capra\|econllm\|2610\.06562\|arizona state\|chapman\|augusto\|monica"` returns grep exit 1 (no match) for both PDFs. The same grep on `references.bib` also has no match.<br><br>Caveat: the PM pass at 16:26 (W1–W3, N2, N4) came after MV (16:02) and was not re-verified cross-family. These re-runs cover numbers and anonymity on the post-pass files. | PASS |
| 2. Paper worktree state | `git -C PW status` shows the branch up to date with origin and the following changes:<br>• 18 modified files, all part of the rewrite: abstract, background, conclusion, design, discussion, instrument, introduction, main.tex/pdf, references.bib, results, supplement.tmpl/tex/pdf, title_page, COVER_LETTER_DRAFT.md (PM N4), and NUMBER_AUDIT.txt plus SUPPLEMENT_NUMBER_AUDIT.txt (rewritten by the gates).<br>• 3 untracked items: REWRITE_LOG.md, MANUSCRIPT_REVIEW_2026-10-25.md, review_probes/.<br>Nothing outside `misc/paper_b/` changed. No staged changes. | PASS |
| 3. Workbench deploy | **EV verdict.** `head -1 WB/workbench/plans/WB8_VERIFICATION.md` gives `VERDICT: PASS-WITH-NOTES` (GLM-5.3, card t_3a5c9a4c).<br><br>**ED record** (`WB8_DEPLOY.md`): "v1.6 from 4984189 … -> Space commit **77e3e612e5608ccd0605b4c558475350839ea4f1**", with 376/376 files matching.<br><br>**Live state.** `curl https://huggingface.co/api/spaces/EconLLM/sca2-workbench` returns sha `77e3e612e5608ccd0605b4c558475350839ea4f1`, stage RUNNING, private False, lastModified 2026-10-24T22:47:11Z.<br><br>**Footer.** The rendered `<footer>` at https://econllm-sca2-workbench.static.hf.space/index.html reads: "SCA2 is Synthetic Cultural Agents from Aggregate Anchors (Paper A: arXiv:2610.06562). Paper B, the journal version in preparation, evaluates the method as a scoring instrument on a 42-country cohort; this workbench is its companion." | PASS |
| 4. Test suite | `cd MW && HF_TOKEN= env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest paper_b -q -p no:cacheprovider` gives `613 passed in 126.34s (0:02:06)`. | PASS |
| 5. Novelty wording | **N1 verdict.** `head -1 MW/planning/checkpoint_2026-10-26/NOVELTY_AUDIT.md` reads: "VERDICT: partly novel — what is new is the instrument … Distribution-matching fine-tuning, country-persona prompting, … cross-dimension "entanglement" … must be cited, not claimed."<br><br>**Introduction, ¶3** (`introduction.tex:9`): "What is specific to the construction is its training signal, which consists of six declared signs and no human answers, together with the unnamed group at evaluation."<br><br>**Introduction, line 15**: "Entanglement across cultural dimensions has been reported for activation steering \citep{dangmasud2026}, and the factorial here measures it for trained adapters and for a prompt."<br><br>**Cited prior work** (`introduction.tex:5`) includes cao2025, suh2025, santurkar2023 and durmus2024. | PASS |
| 6. Replication (binding addition, PM 2026-10-24 16:05) | `head -1` of each file in `MW/planning/checkpoint_2026-10-26/replication/`:<br>• `REPLICATION_model_only.md`: "RESULT: REPRODUCED-WITH-NOTES"<br>• `REPLICATION_human.md`: "RESULT: REPRODUCED-WITH-NOTES"<br>• `REPLICATION_VERIFICATION.md`: "VERDICT: PASS-WITH-NOTES" (GLM-5.3, cross-family)<br>Neither replication says NOT-REPRODUCED. | PASS |

## Open for Augusto (judgment calls, not blockers)

- **MV N1: positioning.** The four intended-use sentences (discussion.tex `\paragraph{Intended use.}`, conclusion.tex:7,
  abstract.tex:2, introduction.tex:26) come closest to forbidden option B. MV judged them inside the lock, but Augusto should read them.
- **MV N3: length.** The main text is 11,526 words against a 9,000–10,000 target.
- **Workbench footer.** It still says "(Paper A: arXiv:2610.06562)". This was an EV/ED note and needs a wording decision.
- **N1 bibliography.** Before the commit, check the CultureManager author line, the PMLR volume for wallach2025, and the Tao et al. arXiv-vs-OUP version.
- **RV data/ inventory.** RV noted that some data/ files are already tracked in git (metadata only). Route this to the data steward.
- **Re-verification.** The PM pass after MV was not re-verified cross-family. Numbers and anonymity were re-checked here; the prose changes were not.

## PM remaining actions (the PM commits, merges and pushes; explicit paths, never `git add -A`)

1. **Commit, paper worktree** (`paper/paper-b-draft`): the 18 modified `misc/paper_b/` files plus `REWRITE_LOG.md`,
   `MANUSCRIPT_REVIEW_2026-10-25.md` and `review_probes/`.
2. **Commit, main worktree** (`feat/paper-b-cohort`, already ahead of origin by 2): `planning/checkpoint_2026-10-26/NOVELTY_AUDIT.md`,
   `replication/REPLICATION_VERIFICATION.md`, `replication/probes_rv/` and this `READINESS.md`.
3. **Commit, workbench worktree**: `workbench/plans/WB8_DEPLOY.md` and `WB8_VERIFICATION.md` only. Leave out the unrelated
   in-progress W3b files (`analysis/w3b/run_w3b.py` modified, `analysis/out/W3b_*` and `_discarded_W3/` untracked).
4. **Merge** `feat/paper-b-cohort` into `paper/paper-b-draft`, as in the existing merge pattern. Do not merge to `main`
   unless Augusto decides to.
5. **Push** `paper/paper-b-draft`, `feat/paper-b-cohort`, and `Adapter-Brain-Vizualization` (ahead 5, includes 2dded0f).
6. **Update STATUS.md**: workbench v1.6 live (Space 77e3e612 from 4984189); manuscript rewrite at PASS-WITH-WORDING, with
   the wording applied; replication REPRODUCED-WITH-NOTES ×2 with RV PASS-WITH-NOTES. Add a `planning/DECISIONS.md` row
   for the checkpoint and the new working title.
7. **Sync Overleaf** from `paper/paper-b-draft` after the push: the new title, rewritten sections, references.bib, and the
   supplement rendered from `supplement.tmpl.tex`.
