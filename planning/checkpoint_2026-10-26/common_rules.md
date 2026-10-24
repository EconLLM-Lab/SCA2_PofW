# Checkpoint 2026-10-26: rules every card follows

Augusto presents Paper B and the workbench internally on Monday 2026-10-26. He chose (2026-10-24) to finish a
checkpoint that can be trusted rather than present a draft. All cards close by **Sunday 2026-10-25 20:00 MST**.

## Positioning chosen by Augusto (option A, 2026-10-24)

Paper B is a preregistered evaluation of a language-model measurement instrument. Its contribution is to say
**where along the chain anchor (GPS) → instrument (sign-compiled adapters) → respondents (WVS-7) the instrument holds
and where it fails**:

- *Holds:* training installs the synthetic labels on unseen pairs (`C9_label_recovery_*`); the adapters keep the
  GPS order of countries on trust (`B2_cohort1_trust_rho`, `B2_bank2_trust_rho`, `B2_bank_to_bank_trust_spearman`,
  `RP_max_abs_surface_diff_sd`); naming the country does not (`PX_persona_trust_rho`, `PX_D_cohort1_trust`).
- *Must be said with it:* a prompt that states the same six signs also keeps the trust order
  (`PX_signprompt_trust_rho`) and the adapter-minus-sign-prompt contrast is unresolved (`SP_D_own`). The signs carry
  the trust order; the paper cannot credit the weights over the prompt.
- *Fails or is weak:* the dimensions are entangled, only trust is spared (`C9_W1_*`); the held-out screen is a weak,
  **retrospective** signal (`SCR_A_primary`, `SCR_p_perm`, `SCR_A_over_ceiling`) that ties with the comparators
  (`CMP_*`); adapter–human agreement is not detected (`C9_a_adapter_human_*`), and the GPS–human link on these
  items is itself loose (`C9_a_human_gps_*`).
- *Order versus distribution:* adapters keep the anchor's order of countries but sit farther from the survey's
  answer distributions than the base model (`C9_TVD_adapter_minus_base_profile_block`); the country-named prompt
  sits closer to the distributions (`C9_TVD_persona_minus_base_profile_block`) with no trust order. Say this as a
  descriptive contrast between two questions, never as "the persona matches respondents".
- *Untested:* pre-piloting and transport. No field route exists.

Forbidden framings: a positive tool paper for pre-piloting (option B) and a cautionary "fine-tuning drives agents
away from humans" paper (option C). Do not write that the anchor is "the bottleneck": the grouping test is
underpowered (`C9_c_*`). No new claim is earned; the claim lock (Amendments C7, C7.1, C8, C9, C9.1 in
`planning/TWO_PAPER_CLAIM_LOCK.md`) is unchanged.

## Locks

- Every Paper B number comes from `planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv` (562 rows, sha256
  `71ee7c8c…ce186a4`) through `\cl{}`/`\ci{}`/`\dc{}` macros. No new number in prose; design constants need a
  `DESIGN` entry.
- Say "retrospective" first for every held-out result; never "transport" for it. Results labelled C9 are
  descriptive and not preregistered.
- Paper B is the journal version of arXiv:2610.06562, not a sequel. The manuscript never cites the preprint, never
  says "earlier study", never names an author. The 16-country panel is "the development stage" of this study.
- Edit the supplement only through `supplement.tmpl.tex` and `tools/render_supplement.py`; never `supplement.tex`.
- Never open `data/` or any human respondent rows. Never print `HF_TOKEN`.
- No push, tag, merge to `main`, or publish. Commit by explicit path only (never `git add -A`) and only where the
  card says you may.
- Each command at most about 3 minutes. Append to your progress or review file after each numbered step, so a retry
  resumes instead of redoing.
- If the premise of your card looks wrong, say so in your handoff instead of complying silently.
