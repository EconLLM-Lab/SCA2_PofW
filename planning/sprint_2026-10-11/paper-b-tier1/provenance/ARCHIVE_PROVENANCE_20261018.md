# Paper B archive provenance — 2026-10-18

Verdict: NOT REPRODUCED.

The premise needs a configuration correction. The workbench calls the same scoring
function on an unquantized model; today's production Colab scorer still loads NF4,
double quantization, and fp16 Linear compute. Function parity is not model-configuration
parity. NF4 explains the dominant discrepancy in this CPU experiment, including the
near-deterministic Q81 USA answer, but the historical CUDA pipeline has not been
reproduced on the complete panel at the required probability tolerance of 1e-3.

This is an elimination memo, not a change to the paper's canonical scores. No paper
number, loader, lock, or workbench source was edited. No GPU or Colab was used.
Model route: openai-codex / gpt-6.1-sol.

## Writer identity and chain of custody

- Run: `paper-b-20261011`. Original model-only scores were persisted by the
  path represented by `paper_b/colab/vm_cohort.py` -> `score_cohort.score_model_questions`
  -> `sequence_logprob` -> `score_runtime.persist_unit_scores`.
- The producing git commit is **unresolved**. The manifest's
  `code_revision_sha256=f3279d6c85524a14dc0d591c1d169553e2380d839dd28062f5214b4984f1ba12` is a code-bundle
  digest, not a git SHA. `vm_cohort.running_code_id` hashes Python paths and bytes when
  running from a tarball without git metadata. It also permits an explicit supplied
  identifier; the original launch environment cannot be recovered here.
- None of the 67 available source snapshots examined by
  `inspect_provenance.py` matches that digest. The earliest tracked writer snapshot is
  `86fbf1030db9d126b6b354d2d424f3da1f130d37`, after the recorded run. It is a proxy,
  NOT a pinned producing commit. There is no honest historical checkout to name.
- Local manifest download metadata identifies the Hub snapshot
  `34dfeba3396b76602ae7065a2a144b7d394d6943`.
  Base persistence time: `2026-10-12T04:19:55Z`; USA:
  `2026-10-12T04:57:51Z`. Hub upload titles agree with the run.
- Private artifacts metadata returned HTTP 401. The process has no HF_TOKEN; no
  credential file or other profile was consulted. This blocks recovery of the exact
  historical source bundle and a fresh full audit of remote manifests, not cached
  CPU model-only inference.
- Original `scores_for_join` copier identity is also unresolved. Its numerical
  operation is verified: only `option_value` was added, option logprobs are unchanged,
  and the largest probability CSV round-trip difference is
  1.11022302e-16.
  This local copy cannot explain the discrepancy.
- USA revisions `7550fd4cfe514470bb8d80918a43c9ae424d26b5` and `c4b0f36eae0c15e508f72b606861798c8359131f` have identical
  adapter config and weight bytes. Weight SHA256: `7329c4a1e621d86fdc32c55b47b5fda047830404dc0d697ec468febe19717eef`.
  Bundle SHA256: `a35edd11a52d4a5fa49eece7e64b53112123e4a6691f6a87cd2df8611a197d3c`. This matches the archive manifest.

Sources: writer_inspection.json, writer_followup.json, worktree_add.log,
worktree_cleanup.json. The clean temporary proxy worktree has been removed.

## Model-free elimination

The proxy and current code render byte-identical prompt text, formatted UTF-8,
model prompt IDs, and completion IDs for all 5 selected items. Base and
USA use the same country-name-free prompt. Their strict spec SHA256 equals the
archive manifest's `ed3bb964b606a163c792a68eea2ea9e6cc679bb724ead6726c173f36d9a1fbf6`. No selected prompt is truncated.

Q81 completion IDs: `{"1": [220, 16], "2": [220, 17], "3": [220, 18], "4": [220, 19]}`. The common leading
space is retained. The readout sums completion-token log probabilities, does not
length-normalize, and applies the same temperature/option-code softmax. The same
option labels, ordering, system block, and pinned chat date follow from these equal
renders/constants. Old/new `sequence_logprob`, prompt preparation, and base loader
source are identical. The prompt builder gained optional variants, but its tested
primary output is unchanged.

These observations rule out the listed prompt/readout changes **between the tested
proxy and current source**, not in the inaccessible exact archived bundle. Because
all these completions share a leading-space token and equal token counts, taking a
mean would change the distribution's temperature rather than account for a
configuration mismatch; the inspected scorer explicitly uses sums.

Sources: prompts_old.json, prompts_new.json, prompt_comparison.json. The comparison
records `snapshot_is_verified_archive_bundle=false`; the old render must not be cited as
proof that the exact archived source was recovered.

## Full 5 × 2 comparison

“Today” below means the workbench's unquantized float32 reference using today's
`sequence_logprob`, NOT today's production Colab loader. The last column is an NF4
CPU diagnostic, **not a reproduced old pipeline**. Probabilities follow the listed
code order; full precision is in comparison_panel.csv and the replay JSONs.

| Item / arm | Codes | Archive P | Today unquantized P | NF4 CPU P | max Δp: today / NF4 |
| --- | --- | --- | --- | --- | --- |
| Q57 / base | 1, 2 | [0.265880473, 0.734119527] | [0.0527926526, 0.947207347] | [0.262841837, 0.737158163] | 0.213087821 / 0.00303863573 |
| Q57 / USA_adapter | 1, 2 | [1, 6.1276482e-11] | [0.999999998, 2.08831574e-09] | [1, 6.22415649e-11] | 2.02703931e-09 / 9.65116875e-13 |
| Q58 / base | 1, 2, 3, 4 | [0.489295103, 0.504826996, 0.00487242027, 0.00100548075] | [0.434313693, 0.563262807, 0.00219079386, 0.000232706136] | [0.489295103, 0.504826996, 0.00487242027, 0.00100548075] | 0.0584358104 / 5.55111512e-17 |
| Q58 / USA_adapter | 1, 2, 3, 4 | [0.999999995, 4.94445048e-09, 4.84736868e-11, 3.77513453e-11] | [0.999998378, 1.62162706e-06, 3.24610207e-10, 1.58553399e-10] | [0.999999995, 4.57286916e-09, 4.58939643e-11, 3.5188123e-11] | 1.61707955e-06 / 3.76724207e-10 |
| Q81 / base | 1, 2, 3, 4 | [0.0689226122, 0.801198966, 0.128764392, 0.00111403027] | [0.00447135356, 0.789240484, 0.202825209, 0.00346295307] | [0.0687819335, 0.79956363, 0.130525175, 0.00112926187] | 0.0740608175 / 0.00176078288 |
| Q81 / USA_adapter | 1, 2, 3, 4 | [0.999994825, 5.17391877e-06, 6.58780857e-10, 1.88743876e-10] | [0.694823769, 0.305176128, 9.12402552e-08, 1.1527641e-08] | [0.999994905, 5.09371471e-06, 6.58782167e-10, 1.87275431e-10] | 0.305171056 / 8.02055188e-08 |
| Q106 / base | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 | [8.85151544e-05, 0.00284103521, 0.00736908462, 0.104956239, 0.441882273, 0.366333271, 0.072135298, 0.00426489898, 0.00012878879, 5.96410419e-07] | [0.000165187743, 0.00724345745, 0.0465791966, 0.177113053, 0.473701649, 0.215227668, 0.0671644239, 0.0119564821, 0.000834351145, 1.45308175e-05] | [8.79345018e-05, 0.00280043415, 0.00737816129, 0.105085516, 0.442426549, 0.366784492, 0.0711044171, 0.00420394958, 0.000127943945, 6.01828498e-07] | 0.151105603 / 0.00103088093 |
| Q106 / USA_adapter | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 | [1.46541799e-08, 0.000455192467, 0.000469641827, 0.263048929, 0.22854087, 0.507040081, 0.00042761375, 1.76497273e-05, 8.34970003e-09, 1.80846947e-12] | [8.91939571e-08, 5.58869722e-05, 0.00165196701, 0.285555481, 0.625671727, 0.086476398, 0.00057708135, 1.13485411e-05, 2.05634017e-08, 1.34741147e-11] | [1.44288569e-08, 0.000437811028, 0.000451708642, 0.265146392, 0.230363177, 0.503159439, 0.000424340999, 1.71089185e-05, 8.09385518e-09, 1.82467063e-12] | 0.420563683 / 0.00388064211 |
| Q107 / base | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 | [0.0148097399, 0.0470652561, 0.0225821567, 0.111153271, 0.262508921, 0.279439292, 0.124000434, 0.104418835, 0.0338998323, 0.000122261885] | [0.00833261289, 0.0391159915, 0.0888384078, 0.142311878, 0.257048483, 0.16528694, 0.123723028, 0.127313653, 0.0466147867, 0.00141421903] | [0.0147725861, 0.0469471816, 0.0225255039, 0.110874416, 0.265973898, 0.278738251, 0.123689349, 0.102542072, 0.0338147864, 0.000121955162] | 0.114152352 / 0.00346497634 |
| Q107 / USA_adapter | 1, 2, 3, 4, 5, 6, 7, 8, 9, 10 | [5.70507852e-08, 0.00914133359, 0.00127641617, 0.491362076, 0.247072368, 0.250963192, 0.000167429365, 1.71039864e-05, 2.4537237e-08, 1.30238489e-12] | [1.38796627e-07, 0.000365519882, 0.00534344073, 0.131877938, 0.540850612, 0.308350244, 0.0117711468, 0.00143824163, 2.71852351e-06, 2.11658636e-10] | [5.6139465e-08, 0.0095009423, 0.00128581272, 0.502773151, 0.245032064, 0.241233194, 0.000158443215, 1.63129417e-05, 2.39573829e-08, 1.29289434e-12] | 0.359484138 / 0.0114110749 |

NF4 Q81 USA max |Δp| is 8.02055188e-08. However, 6 of 10 default
NF4 item/arm rows still fail 1e-3; the worst is
Q107 /
USA_adapter at
0.0114110749. A saturated answer matching in probability
is not evidence that every underlying logprob matches. No per-row variant selection
or calibration was used to call a reproduction.

### Q81 logprob differences (nats)

| Arm | Code | Archive | Unquantized today | Today − archive |
| --- | --- | --- | --- | --- |
| base | 1 | -20 | -21.6792889 | -1.67928886 |
| base | 2 | -17.546875 | -16.505909 | 1.04096603 |
| base | 3 | -19.375 | -17.8646355 | 1.51036453 |
| base | 4 | -24.125 | -21.9348583 | 2.19014168 |
| USA_adapter | 1 | -27.921875 | -28.1614532 | -0.239578247 |
| USA_adapter | 2 | -40.09375 | -28.9842224 | 11.1095276 |
| USA_adapter | 3 | -49.0625 | -44.0071259 | 5.05537415 |
| USA_adapter | 4 | -50.3125 | -46.0758743 | 4.23662567 |

These are full completion scores. Large common shifts can cancel in the option
softmax; relative score shifts determine the probability discrepancy.

## Bounded isolation results

The full-panel variants change the base representation or forward dtype while
holding the prompt, option set, model revision, and adapter file fixed. Separate
fp32/fp16 output-logit reductions are saved so reduction precision is not confused
with weight quantization. Baseline f32 Q81 prefix factorization was checked against
the unmodified serial scorer; its recorded score gap is shown below. Other reduced-
precision prefix replays are diagnostics, not a claim of bit-identical serial CUDA
arithmetic.

| Forward | Arm | Logit reduction | Worst item | max \|Δp\| | Items passing 1e-3 |
| --- | --- | --- | --- | --- | --- |
| f32 | base | float32 | Q57 | 0.213087821 | 0/5 |
| f32 | base | float16 | Q57 | 0.21326152 | 0/5 |
| f32 | USA_adapter | float32 | Q106 | 0.420563683 | 2/5 |
| f32 | USA_adapter | float16 | Q106 | 0.421066071 | 2/5 |
| f16 | base | float32 | Q57 | 0.21326152 | 0/5 |
| f16 | base | float16 | Q57 | 0.212870701 | 0/5 |
| f16 | USA_adapter | float32 | Q106 | 0.421067499 | 2/5 |
| f16 | USA_adapter | float16 | Q106 | 0.421064539 | 2/5 |
| nf4 | base | float32 | Q107 | 0.00346497634 | 1/5 |
| nf4 | base | float16 | Q107 | 0.00346547923 | 1/5 |
| nf4 | USA_adapter | float32 | Q107 | 0.0114110749 | 3/5 |
| nf4 | USA_adapter | float16 | Q107 | 0.0114111497 | 3/5 |

Serial-factorization score gaps, Q81 float32: base
0, USA
0.
The unquantized fp16 runs remain far from the archive on unsaturated rows; merely
changing f32 arithmetic to f16 is not the dominant cause.

The following predeclared swaps each alter one NF4 configuration factor on Q57/Q81,
in both arms. They are a bounded sensitivity check, not a full-panel reproduction.
`compute_f32` casts only quantized Linear arithmetic to fp32 and returns fp16 outputs;
embeddings, norms, and residual dtype remain fp16. `fp4` changes the quantization
codebook; it is not the documented Paper B configuration.

| Swap | Arm | Item | Logit reduction | max \|Δp\| vs archive |
| --- | --- | --- | --- | --- |
| no_double_quant | base | Q57 | float32 | 0 |
| no_double_quant | base | Q57 | float16 | 0 |
| no_double_quant | base | Q81 | float32 | 0.00249073728 |
| no_double_quant | base | Q81 | float16 | 0.00249073728 |
| no_double_quant | USA_adapter | Q57 | float32 | 6.34849377e-12 |
| no_double_quant | USA_adapter | Q57 | float16 | 6.34859854e-12 |
| no_double_quant | USA_adapter | Q81 | float32 | 8.02760901e-08 |
| no_double_quant | USA_adapter | Q81 | float16 | 8.02774591e-08 |
| compute_f32 | base | Q57 | float32 | 0 |
| compute_f32 | base | Q57 | float16 | 0 |
| compute_f32 | base | Q81 | float32 | 0.00175846147 |
| compute_f32 | base | Q81 | float16 | 0.0017607826 |
| compute_f32 | USA_adapter | Q57 | float32 | 1.16875726e-16 |
| compute_f32 | USA_adapter | Q57 | float16 | 9.50017842e-13 |
| compute_f32 | USA_adapter | Q81 | float32 | 8.02069761e-08 |
| compute_f32 | USA_adapter | Q81 | float16 | 8.02269066e-08 |
| fp4 | base | Q57 | float32 | 0.183512161 |
| fp4 | base | Q57 | float16 | 0.183512161 |
| fp4 | base | Q81 | float32 | 0.139766106 |
| fp4 | base | Q81 | float16 | 0.139766106 |
| fp4 | USA_adapter | Q57 | float32 | 3.32041835e-08 |
| fp4 | USA_adapter | Q57 | float16 | 3.32040565e-08 |
| fp4 | USA_adapter | Q81 | float32 | 0.0222812211 |
| fp4 | USA_adapter | Q81 | float16 | 0.0219432887 |

Every tested parameter-swap configuration still fails the probability threshold on
at least one base-model item, under either reported logit reduction. That is enough
to reject it as a uniform reproduction of the combined panel without expanding a
failed candidate to all remaining items.

### Diagnostic implementation correction

The saved USA adapter contains F32 tensors. The streaming scaffold casts LoRA tensors
to the requested model dtype; promoting those rounded fp16 tensors back to fp32 does
not recover the file. Self-review found this error in the initial f16/NF4 USA
replays. Those raw files are preserved as `rounded_lora_replay_*`; they are not used
in the comparison table. `restore_lora.py` now reloads the exact file tensors,
asserts equality, and reports
256 restored tensors.
All affected USA variants were rerun serially; commands and superseded-file hashes
are in repair_commands.json. The small-tensor regression failed before this repair
and passed after it (lora_red.log / lora_green.log). Base and unquantized-f32 results
were not affected. No workbench source was changed.

### CPU/CUDA boundary

CPU runtime packages: {"bitsandbytes": "0.50.2", "huggingface-hub": "2.2.0", "peft": "0.21.2", "torch": "2.14.1", "transformers": "5.20.1"}.
The frozen historical versions are recorded verbatim in writer_followup.json and
planning/sprint_2026-10-11/PAPER_B_STACK_FREEZE.md. The CPU probe uses bitsandbytes
quantize/dequantize on individual Linear weights, followed by dense CPU operations;
it does NOT execute the historical CUDA BNB matmul or frozen attention kernels.
The diagnostic quantizes 224 Linear
weights, excluding embeddings/norms/lm_head, with block size 64. All runs stayed
CPU-only, one model process at a time; highest recorded item peak RSS was
4848041984 bytes, below the 16000000000 byte stop limit.

Ruled out locally: adapter revision bytes/config, CSV-copy corruption, tested
prompt/spec/date/labels/order/truncation/completion conventions, unquantized forward
dtype alone, and a gross serial-factorization bug on the checked float32 reference.
Not ruled out: exact original source-bundle differences, frozen package/attention
arithmetic, CUDA versus CPU quantization/dequantization/matmul, serial versus
prefix-factorized reduced-precision rounding, and original launch settings not
captured by accessible manifests. The bounded swaps do not identify one of those
as the remaining cause. The stop rule is now applied: no additional search.

## Q262 / bank-2 archive gate: related, not the same demonstrated cause

Q262 is absent from the cohort-1 strict archive, so it cannot replace one of the
five cohort items without changing the run. A separate model-only legacy
base-on-CHN Q262 diagnostic was run, with archive prompt bytes verified directly.
It is neither a rerun of the bank-2 gate nor a USA-adapter observation.

| Forward | Logit reduction | Options | max \|Δlogprob\| | max \|Δp\| |
| --- | --- | --- | --- | --- |
| f32 | float32 | 80 | 4.4462738 | 0.0376925082 |
| f32 | float16 | 80 | 4.453125 | 0.0377786232 |
| f16 | float32 | 80 | 4.43025017 | 0.0366517225 |
| f16 | float16 | 80 | 4.421875 | 0.0366516659 |
| nf4 | float32 | 80 | 0.393501282 | 0.00988749673 |
| nf4 | float16 | 80 | 0.375 | 0.00988733564 |

The existing report-only gate's recorded statement is:

> The bank-2 gate archive check (report-only)  Per `PAPER_B_STACK_FREEZE.md`, the base-versus-archive comparison is report-only: 343 rows, `max |dlogprob| 0.46875`, `max |dprob| 0.0558`, worst rows on Q262. The adapter-path and switch-back checks are fatal and passed. - **Write:** the gap and its magnitude, attributed to stack drift between the archive and this run. - **Do not write:** that the archive check passed, or imply the tolerance was met.

That comparison was already made on the frozen NF4 path versus an unpinned legacy
archive. Its residual cannot simply be labeled the workbench's “unquantized versus
NF4” mechanism. The supplemental CPU NF4 result moves toward the legacy logprobs
but still misses the probability target. Shared susceptibility to stack arithmetic
is plausible; identity of the remaining cause is **not established**. The existing
report-only policy remains unchanged.

Sources: q262_*.json/.log, q262_commands.json, writer_followup.json.

## Blast radius: every permitted aggregate row and locked table

Coverage: 220 NUMBERS_TABLE rows; 23 claim-lock table body rows.
The exact per-claim mapping is in blast_radius_numbers.csv: every original column,
including `claim_id`, `producing_script`, and `run_id`, is retained, with source-traced
scoring paths appended. This avoids mistaking an analysis script for an inference
writer. Grouped coverage is below; row counts partition the full table.

| Run ID(s) | Rows | Scoring pipeline | Could move under unquantized rescore? |
| --- | --- | --- | --- |
| bank2-heldout-para-a-20261016 | 3 | paper_b/colab/vm_score_units.py -> paper_b/score_cohort.py --model-only -> load_base_model_and_tokenizer/sequence_logprob | YES/POSSIBLE: model outputs, derived selection, or selection-conditioned criterion; no magnitude estimated |
| bank2-heldout-para-b-20261016 | 3 | paper_b/colab/vm_score_units.py -> paper_b/score_cohort.py --model-only -> load_base_model_and_tokenizer/sequence_logprob | YES/POSSIBLE: model outputs, derived selection, or selection-conditioned criterion; no magnitude estimated |
| bank2-heldout-reverse-20261016 | 3 | paper_b/colab/vm_score_units.py -> paper_b/score_cohort.py --model-only -> load_base_model_and_tokenizer/sequence_logprob | YES/POSSIBLE: model outputs, derived selection, or selection-conditioned criterion; no magnitude estimated |
| bank2-heldout-v1-20261016 | 57 | paper_b/colab/vm_score_units.py -> paper_b/score_cohort.py --model-only -> load_base_model_and_tokenizer/sequence_logprob | YES/POSSIBLE: model outputs, derived selection, or selection-conditioned criterion; no magnitude estimated |
| bank2-nearzero-strict-v1-20261018 | 32 | paper_b/colab/vm_score_t4.py -> paper_b/score_cohort.py --model-only -> load_base_model_and_tokenizer/sequence_logprob | YES/POSSIBLE: model outputs, derived selection, or selection-conditioned criterion; no magnitude estimated |
| bank2-replicate-r1-strict-v1-20261018; bank2-replicate-r1-heldout-v1-20261018 | 17 | paper_b/colab/vm_score_t4.py -> paper_b/score_cohort.py --model-only -> load_base_model_and_tokenizer/sequence_logprob; paper_b/colab/vm_score_t4.py -> paper_b/score_cohort.py --model-only -> load_base_model_and_tokenizer/sequence_logprob | YES/POSSIBLE: model outputs, derived selection, or selection-conditioned criterion; no magnitude estimated |
| bank2-signprompt-heldout-v1-20261016 | 7 | paper_b/colab/vm_score_units.py -> paper_b/score_sign_profiles.py -> score_cohort.load_base_model_and_tokenizer/sequence_logprob | YES/POSSIBLE: model outputs, derived selection, or selection-conditioned criterion; no magnitude estimated |
| bank2-signprompt-strict-v1-20261018 | 32 | paper_b/colab/vm_score_t4.py -> paper_b/score_sign_profiles.py -> score_cohort.load_base_model_and_tokenizer/sequence_logprob | YES/POSSIBLE: model outputs, derived selection, or selection-conditioned criterion; no magnitude estimated |
| bank2-strict-v1-20261016 | 39 | paper_b/colab/vm_score_units.py -> paper_b/score_cohort.py --model-only -> load_base_model_and_tokenizer/sequence_logprob | YES/POSSIBLE: model outputs, derived selection, or selection-conditioned criterion; no magnitude estimated |
| n/a (file hash) | 6 | paper_b/build_numbers_table.py (hashlib/git show; no model) | NO: content hash is model-independent; unchanged input bytes imply unchanged hash |
| paper-b-20261011 | 7 | paper_b/colab/vm_cohort.py -> score_cohort.score_model_questions -> sequence_logprob | YES/POSSIBLE: model outputs, derived selection, or selection-conditioned criterion; no magnitude estimated |
| paper-b-20261011; bank2-strict-v1-20261016 | 14 | paper_b/colab/vm_cohort.py -> score_cohort.score_model_questions -> sequence_logprob; paper_b/colab/vm_score_units.py -> paper_b/score_cohort.py --model-only -> load_base_model_and_tokenizer/sequence_logprob | YES/POSSIBLE: model outputs, derived selection, or selection-conditioned criterion; no magnitude estimated |

All Paper B model-score paths traced in source use the frozen NF4 loader: cohort,
bank-2 strict/heldout/reversed/paraphrased, sign-profile prompts, replicate, and
near-zero. No table row was found to depend on the unquantized workbench outputs.
This establishes source-level configuration consistency, not a fresh manifest-by-
manifest audit of every historical VM. Private artifacts access is unavailable.
Existing archived paper outputs do not change merely because this diagnostic ran.

“YES/POSSIBLE” is a conservative sensitivity bound: a counterfactual rescore can
change model outputs, probe membership, or a selection-conditioned criterion. It is
NOT a measured effect on every aggregate, nor a claim that all design counts or
fixed-human subsets must change. Fixed input content hashes do not depend on a
scoring kernel. No new correlations, human means, or model–human joins were computed
or opened.

### Every claim-lock table body row

| Lock line / subject | Producing script / provenance limit | Run ID | Could move? |
| --- | --- | --- | --- |
| 47 / GPS \(z\) | claim-lock declaration / not recomputed / optional restriction; no citable active model number | not an active inference run | N/A; do not manufacture a current result |
| 48 / Human–GPS | analysis/phase2/22_paper_a_surface.py (human-only map aggregation; source inspected only, not run) | locked Paper A human survey/GPS surface; no model inference run | NO direct scorer dependency for the fixed panel/items; any panel/item change is outside scope |
| 49 / Adapter–GPS | Paper A audit -> frozen panel/readout; analysis/phase2/22_paper_a_surface.py is partial current aggregator, not original inference writer | ksenias_base8 + co2_8 (locked Paper A); exact inference source SHA unresolved; adapter+persona 0.67 explicitly unidentified | POSSIBLE if these historical jobs are rescored on another stack; not a dependency on paper-b-20261011; no amendment authorized |
| 50 / Adapter–human | Paper A audit -> frozen panel/readout; analysis/phase2/22_paper_a_surface.py is partial current aggregator, not original inference writer | ksenias_base8 + co2_8 (locked Paper A); exact inference source SHA unresolved; adapter+persona 0.67 explicitly unidentified | POSSIBLE if these historical jobs are rescored on another stack; not a dependency on paper-b-20261011; no amendment authorized |
| 51 / Nomological / GDP | claim-lock declaration / not recomputed / optional restriction; no citable active model number | not an active inference run | N/A; do not manufacture a current result |
| 73 / Encoding | analysis/phase2/04_direction_cardinal.py (aggregation); original scoring notebooks/run identity not pinned in the lock | legacy Paper A synthetic encoding jobs (not paper-b-20261011); exact writer SHA unresolved | POSSIBLE on rescoring legacy model outputs; no direct dependency on the Paper B archive; historical number remains locked |
| 74 / Trust adapter–GPS | Paper A audit -> frozen panel/readout; analysis/phase2/22_paper_a_surface.py is partial current aggregator, not original inference writer | ksenias_base8 + co2_8 (locked Paper A); exact inference source SHA unresolved; adapter+persona 0.67 explicitly unidentified | POSSIBLE if these historical jobs are rescored on another stack; not a dependency on paper-b-20261011; no amendment authorized |
| 75 / Trust persona–GPS | Paper A audit -> frozen panel/readout; analysis/phase2/22_paper_a_surface.py is partial current aggregator, not original inference writer | ksenias_base8 + co2_8 (locked Paper A); exact inference source SHA unresolved; adapter+persona 0.67 explicitly unidentified | POSSIBLE if these historical jobs are rescored on another stack; not a dependency on paper-b-20261011; no amendment authorized |
| 76 / Trust adapter−persona | Paper A audit -> frozen panel/readout; analysis/phase2/22_paper_a_surface.py is partial current aggregator, not original inference writer | ksenias_base8 + co2_8 (locked Paper A); exact inference source SHA unresolved; adapter+persona 0.67 explicitly unidentified | POSSIBLE if these historical jobs are rescored on another stack; not a dependency on paper-b-20261011; no amendment authorized |
| 77 / Trust adapter–human | Paper A audit -> frozen panel/readout; analysis/phase2/22_paper_a_surface.py is partial current aggregator, not original inference writer | ksenias_base8 + co2_8 (locked Paper A); exact inference source SHA unresolved; adapter+persona 0.67 explicitly unidentified | POSSIBLE if these historical jobs are rescored on another stack; not a dependency on paper-b-20261011; no amendment authorized |
| 78 / Trust human–GPS | analysis/phase2/22_paper_a_surface.py (human-only map aggregation; source inspected only, not run) | locked Paper A human survey/GPS surface; no model inference run | NO direct scorer dependency for the fixed panel/items; any panel/item change is outside scope |
| 79 / Q57 human–GPS (this panel) | analysis/phase2/22_paper_a_surface.py (human-only map aggregation; source inspected only, not run) | locked Paper A human survey/GPS surface; no model inference run | NO direct scorer dependency for the fixed panel/items; any panel/item change is outside scope |
| 80 / Risk adapter–GPS | Paper A audit -> frozen panel/readout; analysis/phase2/22_paper_a_surface.py is partial current aggregator, not original inference writer | ksenias_base8 + co2_8 (locked Paper A); exact inference source SHA unresolved; adapter+persona 0.67 explicitly unidentified | POSSIBLE if these historical jobs are rescored on another stack; not a dependency on paper-b-20261011; no amendment authorized |
| 81 / Risk adapter–human | Paper A audit -> frozen panel/readout; analysis/phase2/22_paper_a_surface.py is partial current aggregator, not original inference writer | ksenias_base8 + co2_8 (locked Paper A); exact inference source SHA unresolved; adapter+persona 0.67 explicitly unidentified | POSSIBLE if these historical jobs are rescored on another stack; not a dependency on paper-b-20261011; no amendment authorized |
| 82 / 2×2 trust–GPS / mean TVD | Paper A audit -> frozen panel/readout; analysis/phase2/22_paper_a_surface.py is partial current aggregator, not original inference writer | ksenias_base8 + co2_8 (locked Paper A); exact inference source SHA unresolved; adapter+persona 0.67 explicitly unidentified | POSSIBLE if these historical jobs are rescored on another stack; not a dependency on paper-b-20261011; no amendment authorized |
| 83 / Patience human–GPS | analysis/phase2/22_paper_a_surface.py (human-only map aggregation; source inspected only, not run) | locked Paper A human survey/GPS surface; no model inference run | NO direct scorer dependency for the fixed panel/items; any panel/item change is outside scope |
| 84 / Assignment placebo | claim-lock declaration / not recomputed / optional restriction; no citable active model number | not an active inference run | N/A; do not manufacture a current result |
| 85 / Egypt / Q69–Q71 | claim-lock declaration / not recomputed / optional restriction; no citable active model number | not an active inference run | N/A; do not manufacture a current result |
| 182 / 1. 42 countries | paper_b/run_cohort.py (training); paper_b/colab/vm_cohort.py (scoring); cohort config | paper-b-20261011 | NO for declared country count; outcomes could change under a new rescore |
| 183 / 2. Second bank | paper_b/protocol_bank2.py (bank); paper_b/colab/vm_score_units.py (NF4 scoring) | bank2-strict-v1-20261016 | NO for design status; quantitative outcomes could change under a new rescore |
| 184 / 3. Sign-profile prompt cell | paper_b/score_sign_profiles.py via paper_b/colab/vm_score_units.py or vm_score_t4.py | bank2-signprompt-heldout-v1-20261016; bank2-signprompt-strict-v1-20261018 | NO for declared cell count; quantitative outcomes could change under a new rescore |
| 185 / 4. Independent human check | claim-lock status declaration; no independent human-check pipeline exists in this claim | not an active inference run | NO: quantization cannot supply the missing independent human check |
| 186 / 5. Optional protocol papers | claim-lock scope declaration; no inference pipeline | not an active inference run | N/A: scope decision, not a scored outcome |

Paper A legacy inference writer commits remain unresolved. Its adapter+persona
cell is explicitly unidentified by the lock itself. These are provenance gaps,
not licenses to rerun its paper numbers. Human-only fixed-panel correlations have
no direct scorer dependency. Bank/training/cell-count status declarations are not
new inference results.

Current source table SHA256: `90f0f467ccd9f92e762d906d434059f4105c7c5e5522eaa731a42a8aeff0ec1f`.
Current lock SHA256: `5fb0fff001c8c81d59ada41e675e487cd37619231f691b9616341ce2444af1c3`.
C7 declares 220 rows and digest `90f0f467…0ec1f`; the final table
matches that declaration. An earlier mismatch was observed while another session
updated the table; PROGRESS.md and the card preserve that event. A1 did not rebuild
or edit it. Current inspected root HEAD: `a1d75aec34837b6a3ba4dbac93786fc5bdb2447d`.

## Canonical capture recommendation — Augusto decides

For a capture presented as explaining Paper B, prefer **the archived NF4 instrument**,
not the unquantized checkpoint. First preserve the actual production quantized
codes, quantization state/scales, base revision, exact adapter tensors, prompt/spec,
and image versions. Then dequantize those same frozen weights for an f32/f64
explanation path. Do not requantize a different device's checkpoint and call it the
same archive. Keep LoRA unmerged and use the declared completion readout.

Two choices have different meanings:

| Option | Benefit | Cost / limitation |
| --- | --- | --- |
| Unquantized bf16 checkpoint upcast to f32/f64 (current workbench) | Clean deterministic high-precision reference; existing explanation/conservation machinery applies | Explains a different weight representation, so it must not be labeled an explanation of Paper B archive probabilities |
| Production NF4-dequantized weights upcast to f32/f64 | Explains the effective quantized instrument; avoids the dominant representation mismatch | Dequantized high-precision algebra is not bit-identical to production fp16/CUDA execution; serialization and output-parity gates are prerequisites |

Conservation/completeness gates remain necessary for either deterministic reference
forward. They show that an explanation accounts for that forward; they do not prove
archive fidelity. Revalidate both internal conservation and external score parity
on the chosen NF4-derived reference. “Exact explanation” can describe the selected
high-precision reference's algebra, not automatically its equality to historical
CUDA probabilities. This memo has not built or certified that capture path.

Do not rebuild Paper B tables solely because the unquantized workbench disagrees:
today's production scoring source already specifies NF4. Keep the frozen paper
pipeline canonical pending independent review. A genuinely changed production
image or canonical rescore would require the existing freeze/amendment process,
not an A1 convenience decision.

## Remaining open items and handoff

- Exact producing git SHA/source bundle and local copier identity remain unknown.
  The bundle digest is the available identity; the proxy SHA is not a substitute.
- CPU experiments do not reproduce the full panel within the required tolerance.
  Historical CUDA arithmetic is untestable within this task's no-GPU/no-Colab fence.
- Retrieve private manifests/source bundle only through an authorized future
  environment. HF_TOKEN is absent here; no credentials are requested or exposed.
- Augusto must choose the capture's scientific target. No capture implementation,
  paper-number amendment, or extra board card was created by A1.
- A2 independently checks this NOT REPRODUCED verdict and the provenance limits.

## Reproduction and verification

From the repository root, using the committed project environments:

    env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python planning/sprint_2026-10-11/paper-b-tier1/provenance/build_report.py
    env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python planning/sprint_2026-10-11/paper-b-tier1/provenance/verify_provenance.py

The full model commands and captured child exit codes are in replay_commands.json,
q262_commands.json, isolation_commands.json, and repair_commands.json. The latter
supersedes affected initial USA results without deleting their raw evidence.
Model-free RED/GREEN logs cover diagnostic CLI flags, claim-lock trace, and exact
LoRA restoration. final_commands.json and verification.json record final execution
rather than an assumed test outcome. Source/runtime hashes in this bundle detect
later changes; no commit or push was performed.

## Fence audit — incidental bytecode exception

Source diffs and recorded source hashes are unchanged by A1, but this was **not a
literally zero-write read-only run**. Initial Python imports refreshed
4 Python bytecode cache files under paper_b:

- `paper_b/__pycache__/eval_config.cpython-312.pyc`
- `paper_b/__pycache__/config.cpython-312.pyc`
- `paper_b/__pycache__/eval_lib.cpython-312.pyc`
- `paper_b/__pycache__/score_cohort.cpython-312.pyc`

These are an incidental fence exception, not paper-source or paper-number edits.
They have not been deleted: cleaning outside the fence would be another unauthorized
write. Subsequent subprocess launchers disable bytecode generation through
PYTHONDONTWRITEBYTECODE. The raw metadata audit also records concurrent source edits
from the C7 commit and other-runtime caches; mtime alone cannot attribute those to
A1. A2's literal newer-than-artifact scan will therefore not be empty. Review this
exception explicitly rather than treating a clean git diff as proof of no writes.
Evidence: protected_mtime_audit.json/.log. No forbidden human-data files were opened.

## PM addendum after A2 (2026-10-18)

A2 (`t_c5131cd3`, Claude Opus, independent code) issued a narrow BLOCK. Full record: `FINDINGS_A2.md`. Dispositions:

- **F3, accepted and fixed.** `HASH_selection_amended_20261016` is reclassified from "NO" to **YES/POSSIBLE** in `blast_radius_numbers.csv`. The hashed file comes from `paper_b/heldout/probe_select.py:101`, which selects items from adapter effects estimated on bank2-heldout-v1 NF4 scores. In the grouped table above, the "n/a (file hash)" group therefore reads **5 rows NO + 1 row YES/POSSIBLE**. The frozen registered hash is unchanged; only a re-derived selection could move it. Pre-fix copy: `~/.hermes/cache/scratch/blast_radius_numbers.pre_F3.csv`.
- **F4, resolved.** The 4 `paper_b/__pycache__/*.cpython-312.pyc` files A1 wrote are derived caches: gitignored (`.gitignore:3`), with headers matching the unchanged sources. They were deleted, and Python regenerates them on demand. Diagnostic launchers must export `PYTHONDONTWRITEBYTECODE=1` from the first command.
- **A2 point 2c, recorded.** The archive probabilities sit on an fp16 grid. The NF4 replays land within 0–3 fp16 ulp of the archive in two independent implementations, against 60–313 ulp unquantized. The remaining gap is at the archive's resolution floor, so NOT REPRODUCED at 1e-3 in probability is a statement about the unit of the threshold, not about an unknown cause.
- **F5, passed forward.** The capture's archive-parity gate is report-only and stated in fp16 ulp of the option logprob, with nats alongside; probability gaps are descriptive only (A3 card `t_d65297a1`).
- **Capture target, decided by Augusto:** `nf4_dequant` for phase 1. The adapters were QLoRA-trained on the NF4 base (`paper_b/train_country.py:40-47`). Unquantized is a phase-2 precision study.

Verdict after addendum: NF4 is established as the cause of the dominant archive gap. Paper B numbers are internally consistent; no table rebuild.
