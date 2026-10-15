# Review gate — 2026-09-25

Verified by recomputation from frozen files, not from the subagent summaries alone.

## Decisions

- Persona contrast leaves the abstract and the conclusion. Provenance verdict: not established. Checkpoint revision, tokenizer snapshot, completion-string whitespace, and the summation rule are not the same documented object for the adapter arm and the country-prompt arm. The saved wrapper text, aside from the country sentence, matches.
- 0.80 stays. The 0–1 composite moves trust adapter–GPS from 0.80 to 0.86. That is a two-decimal move of 0.06. Both intervals exclude zero. Not material under the locked rule. The 0–1 check is retrospective, so it is a sensitivity sentence, not a second primary.
- Trust sentence: coarse anchor-sign transfer. Seven countries above zero, nine below, none at zero. Rank-biserial of the adapter composite with the sign is 0.97, with one inversion (USA slightly below Argentina). Within-sign magnitude is not recovered. Do not write “country ordering.”
- Do not change the paper’s adapter-plus-persona 0.67. The frozen `adapter_persona` arm is 0.65. The caption says that row is a space-prefixed rescore. Leave the cell until that rescore is located.

## New fact, not in the locked edit rules

The 0.80 file is assembled from three scoring passes. A later USA adapter file does not match the frozen score: Q57 code 1 log-probability is −18.875 in the file that enters 0.80, and −26.375 in `ksenias_base8`. The frozen 0.80 still reproduces from the files that were actually used. Disclose the assembly. Do not drop 0.80.

## Not ready

Manuscript edits are not started. The three-pass sentence needs a yes before anyone rewrites the source.
