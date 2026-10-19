#!/bin/zsh
# Create the sca2-paper-b board and its ten cards. Bodies = shared rules + card text.
set -euo pipefail
# Card texts moved into the repo on 2026-10-19 (formerly ~/Hermes/Projects/SCA2/kanban_paper_b).
K="$(cd "$(dirname "$0")" && pwd)"
TMPB="$(mktemp -d)"   # generated card bodies stay out of the repo
REPO=/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW
WT=/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW-paper-b-draft
B="hermes kanban --board sca2-paper-b"
STRONG=(--model claude-sonnet-5-5 --provider anthropic)

hermes kanban boards create sca2-paper-b --name "SCA2 Paper B" \
  --description "Remaining Paper B tasks after Tier 1 (2026-10-18)" --default-workdir "$REPO" >/dev/null || true

body() { cat $K/00_common.md <(echo) $K/$1 > $TMPB/.body_$1; echo $TMPB/.body_$1; }
id() { python3 -c 'import json,sys; print(json.load(sys.stdin)["id"])'; }

T1=$(eval $B create "'T1 Per-dimension intervals for the held-out screen (C5)'" --assignee data-scientist \
  --workspace "dir:$REPO" --body-file $(body T1_per_dimension.md) --max-runtime 2h --created-by sca \
  --idempotency-key pb-t1 --json | id)
T2=$(eval $B create "'T2 Bank-2 transport on the strict battery (C3)'" --assignee data-scientist \
  --workspace "dir:$REPO" --body-file $(body T2_bank2_transport.md) --max-runtime 2h --created-by sca \
  --idempotency-key pb-t2 --json | id)
T3=$(eval $B create "'T3 Near-zero margin: design note, no GPU (C6)'" --assignee data-scientist \
  --workspace "dir:$REPO" --body-file $(body T3_c6_design.md) --max-runtime 3h --created-by sca \
  --idempotency-key pb-t3 ${STRONG[@]} --json | id)
T4=$(eval $B create "'T4 GPU A: score replicate + 64 sign-prompt profiles (strict)'" --assignee engineer \
  --workspace "dir:$REPO" --body-file $(body T4_gpu_a.md) --max-runtime 8h --max-retries 1 --created-by sca \
  --idempotency-key pb-t4 ${STRONG[@]} --json | id)
T5=$(eval $B create "'T5 GPU B: near-zero refits (C6)'" --assignee engineer --parent $T3 \
  --workspace "dir:$REPO" --body-file $(body T5_gpu_b.md) --max-runtime 8h --max-retries 1 --created-by sca \
  --idempotency-key pb-t5 ${STRONG[@]} --initial-status blocked --json | id)
T6=$(eval $B create "'T6 Analyze replicate + 64-cell sign-prompt factorial'" --assignee data-scientist --parent $T4 \
  --workspace "dir:$REPO" --body-file $(body T6_analyze_a.md) --max-runtime 2h --created-by sca \
  --idempotency-key pb-t6 --json | id)
T7=$(eval $B create "'T7 Analyze near-zero refits (C6)'" --assignee data-scientist --parent $T5 \
  --workspace "dir:$REPO" --body-file $(body T7_analyze_b.md) --max-runtime 2h --created-by sca \
  --idempotency-key pb-t7 --json | id)
T8=$(eval $B create "'T8 VERIFICATION.md + compute ledger'" --assignee engineer --parent $T4 --parent $T5 \
  --workspace "dir:$REPO" --body-file $(body T8_verification.md) --max-runtime 2h --created-by sca \
  --idempotency-key pb-t8 --json | id)
T9=$(eval $B create "'T9 Claim-lock amendment draft + numbers table (C7)'" --assignee data-scientist \
  --parent $T1 --parent $T2 --parent $T6 --parent $T7 \
  --workspace "dir:$REPO" --body-file $(body T9_claim_lock.md) --max-runtime 3h --created-by sca \
  --idempotency-key pb-t9 ${STRONG[@]} --json | id)
T10=$(eval $B create "'T10 Draft the Paper B manuscript (SMR)'" --assignee writer --parent $T9 \
  --workspace "dir:$WT" --body-file $(body T10_writer.md) --max-runtime 10h --created-by sca \
  --idempotency-key pb-t10 --skill augusto-academic-voice --skill latex-paper-revision \
  --goal --goal-max-turns 40 --initial-status blocked --json | id)

print "T1=$T1 T2=$T2 T3=$T3 T4=$T4 T5=$T5 T6=$T6 T7=$T7 T8=$T8 T9=$T9 T10=$T10" | tee $K/ids.txt
eval $B list
