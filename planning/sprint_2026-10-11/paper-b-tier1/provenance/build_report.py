"""Build the elimination memo entirely from raw, local A1 evidence.

Only explicitly permitted model-only evidence and aggregate claim tables are read.
No model execution, network access, human records, or paper-number writes.
"""
import csv
import hashlib
import json
from pathlib import Path
import re

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
def read(name):
    return json.loads((OUT/name).read_text())
def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()
def num(value):
    return f'{value:.9g}'
def vector(values):
    return '['+', '.join(num(x) for x in values)+']'
def table(headers, rows):
    clean = lambda x: str(x).replace('|',r'\|').replace('\n',' ')
    return '\n'.join(['| '+' | '.join(clean(x) for x in headers)+' |',
                      '| '+' | '.join('---' for _ in headers)+' |',
                      *['| '+' | '.join(clean(x) for x in row)+' |' for row in rows]])

writer = read('writer_inspection.json')
follow = read('writer_followup.json')
prompts = read('prompt_comparison.json')
runtime = read('runtime_evidence.json')
fence = read('protected_mtime_audit.json')
radius = read('blast_radius_summary.json')
replays = {(mode,arm):read(f'replay_{mode}_{arm}.json')
           for mode in ['f32','f16','nf4'] for arm in ['base','USA_adapter']}
items = list(replays['f32','base']['items'])
arms = ['base','USA_adapter']
panel = []
for qid in items:
    for arm in arms:
        today = replays['f32',arm]['items'][qid]
        quant = replays['nf4',arm]['items'][qid]
        panel.append({'question_id':qid,'arm':arm,'codes':json.dumps(today['codes']),
                      'archive_probs':json.dumps(today['archive_probs']),
                      'today_probs':json.dumps(today['reductions']['float32']['probs']),
                      'nf4_diagnostic_probs':json.dumps(quant['reductions']['float32']['probs']),
                      'today_max_gap':today['reductions']['float32']['max_abs_probability_gap_vs_archive'],
                      'nf4_max_gap':quant['reductions']['float32']['max_abs_probability_gap_vs_archive']})
with (OUT/'comparison_panel.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(panel[0])); w.writeheader(); w.writerows(panel)

mode_summary=[]
for mode in ['f32','f16','nf4']:
    for arm in arms:
        for red in ['float32','float16']:
            gaps={q:r['reductions'][red]['max_abs_probability_gap_vs_archive']
                  for q,r in replays[mode,arm]['items'].items()}
            worst=max(gaps,key=lambda q:gaps[q])
            mode_summary.append({'mode':mode,'arm':arm,'reduction':red,'worst_item':worst,
                                 'max_probability_gap':gaps[worst],
                                 'passing_items_at_1e_3':sum(g<=1e-3 for g in gaps.values())})
variants=[]
for tag in ['no_double_quant','compute_f32','fp4']:
    for arm in arms:
        j=read(f'replay_nf4_{arm}_{tag}.json')
        for q,r in j['items'].items():
            for red in ['float32','float16']:
                variants.append({'swap':tag,'arm':arm,'item':q,'reduction':red,
                                 'max_probability_gap':r['reductions'][red]['max_abs_probability_gap_vs_archive']})
assert all(any(r['max_probability_gap']>1e-3 for r in variants if r['swap']==tag and r['reduction']==red)
           for tag in ['no_double_quant','compute_f32','fp4'] for red in ['float32','float16'])
q262=[]
for mode in ['f32','f16','nf4']:
    j=read(f'q262_{mode}.json')
    for red,r in j['reductions'].items():
        q262.append({'mode':mode,'reduction':red,'options':j['n_options'],
                     'max_abs_dlogprob':r['max_abs_dlogprob'],'max_abs_dprob':r['max_abs_dprob']})

numbers=list(csv.DictReader((OUT/'blast_radius_numbers.csv').open()))
locked=list(csv.DictReader((OUT/'blast_radius_locked.csv').open()))
run_groups=[]
for run in sorted({r['run_id'] for r in numbers}):
    group=[r for r in numbers if r['run_id']==run]
    run_groups.append({'run_id':run,'rows':len(group),
                       'scoring_pipeline':group[0]['scoring_pipeline'],
                       'producing_scripts':sorted({r['producing_script'] for r in group}),
                       'could_move':group[0]['could_move_on_unquantized_rescore']})
assert sum(g['rows'] for g in run_groups)==len(numbers)==radius['numbers_rows']
assert len(locked)==radius['claim_lock_table_rows']
base_manifest=writer['manifests']['base']
usa_manifest=writer['manifests']['USA_adapter']
revision_records=list(writer['adapter_revisions'].items())
assert revision_records[0][1]==revision_records[1][1]
failed=[r for r in panel if float(r['nf4_max_gap'])>1e-3]
# Full reproduction requires one uniform, verified pipeline, not per-row best-of variants.
# The only full-panel historical-configuration diagnostic is the default NF4 replay.
verdict='NOT REPRODUCED'
assert failed, 'Re-evaluate verdict: the full-panel CPU diagnostic now meets tolerance'
peak=max(r['peak_rss_bytes'] for j in [*replays.values(),
          *[read(f'replay_nf4_{a}_{t}.json') for a in arms for t in ['no_double_quant','compute_f32','fp4']]]
         for r in j['items'].values())
peak=max([peak,*[read(f'q262_{m}.json')['peak_rss_bytes'] for m in ['f32','f16','nf4']],
          *[r['peak_rss_bytes'] for p in OUT.glob('rounded_lora_replay_*.json')
            for r in read(p.name)['items'].values()]])
q81_nats=[]
for arm in arms:
    row=replays['f32',arm]['items']['Q81']
    for code,archive,today in zip(row['codes'],row['archive_scores'],row['reductions']['float32']['scores']):
        q81_nats.append([arm,code,num(archive),num(today),num(today-archive)])

lock_text=(ROOT/'planning/TWO_PAPER_CLAIM_LOCK.md').read_text()
lock_declaration=re.search(r'NUMBERS_TABLE.csv` \((\d+) rows, sha256 `([^`]+)`',lock_text)
assert lock_declaration
lock_rows=int(lock_declaration.group(1))
assert lock_rows==len(numbers)
q81_completion=prompts['items']['Q81']['completion_ids']
archived_adapter_hash=revision_records[0][1]['adapter_model.safetensors']['sha256']
rounding_records=read('repair_commands.json')
assert len(rounding_records)==5 and all(r['exit_code']==0 for r in rounding_records)
assert replays['nf4','USA_adapter']['lora_tensors_restored_from_file']==256
q81_usa=replays['nf4','USA_adapter']['items']['Q81']['reductions']['float32']['max_abs_probability_gap_vs_archive']

sections=[]
sections.append(f'''# Paper B archive provenance — 2026-10-18

Verdict: {verdict}.

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

- Run: `{base_manifest['run_id']}`. Original model-only scores were persisted by the
  path represented by `paper_b/colab/vm_cohort.py` -> `score_cohort.score_model_questions`
  -> `sequence_logprob` -> `score_runtime.persist_unit_scores`.
- The producing git commit is **unresolved**. The manifest's
  `code_revision_sha256={base_manifest['code_revision_sha256']}` is a code-bundle
  digest, not a git SHA. `vm_cohort.running_code_id` hashes Python paths and bytes when
  running from a tarball without git metadata. It also permits an explicit supplied
  identifier; the original launch environment cannot be recovered here.
- None of the {len(writer['bundle_hashes'])} available source snapshots examined by
  `inspect_provenance.py` matches that digest. The earliest tracked writer snapshot is
  `{writer['earliest_tracked_snapshot']}`, after the recorded run. It is a proxy,
  NOT a pinned producing commit. There is no honest historical checkout to name.
- Local manifest download metadata identifies the Hub snapshot
  `{follow['download_metadata'][next(iter(follow['download_metadata']))][0]}`.
  Base persistence time: `{base_manifest['persisted_at_utc']}`; USA:
  `{usa_manifest['persisted_at_utc']}`. Hub upload titles agree with the run.
- Private artifacts metadata returned HTTP 401. The process has no HF_TOKEN; no
  credential file or other profile was consulted. This blocks recovery of the exact
  historical source bundle and a fresh full audit of remote manifests, not cached
  CPU model-only inference.
- Original `scores_for_join` copier identity is also unresolved. Its numerical
  operation is verified: only `option_value` was added, option logprobs are unchanged,
  and the largest probability CSV round-trip difference is
  {num(max(v['max_numeric_gaps']['model_prob'] for v in follow['copies'].values()))}.
  This local copy cannot explain the discrepancy.
- USA revisions `{revision_records[0][0]}` and `{revision_records[1][0]}` have identical
  adapter config and weight bytes. Weight SHA256: `{archived_adapter_hash}`.
  Bundle SHA256: `{usa_manifest['adapter_sha256']}`. This matches the archive manifest.

Sources: writer_inspection.json, writer_followup.json, worktree_add.log,
worktree_cleanup.json. The clean temporary proxy worktree has been removed.
''')
sections.append(f'''## Model-free elimination

The proxy and current code render byte-identical prompt text, formatted UTF-8,
model prompt IDs, and completion IDs for all {len(items)} selected items. Base and
USA use the same country-name-free prompt. Their strict spec SHA256 equals the
archive manifest's `{base_manifest['spec_sha256']}`. No selected prompt is truncated.

Q81 completion IDs: `{json.dumps(q81_completion,sort_keys=True)}`. The common leading
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
''')
sections.append(f'''## Full {len(items)} × {len(arms)} comparison

“Today” below means the workbench's unquantized float32 reference using today's
`sequence_logprob`, NOT today's production Colab loader. The last column is an NF4
CPU diagnostic, **not a reproduced old pipeline**. Probabilities follow the listed
code order; full precision is in comparison_panel.csv and the replay JSONs.

'''+table(['Item / arm','Codes','Archive P','Today unquantized P','NF4 CPU P','max Δp: today / NF4'],
[[r['question_id']+' / '+r['arm'],', '.join(json.loads(r['codes'])),
  vector(json.loads(r['archive_probs'])),vector(json.loads(r['today_probs'])),
  vector(json.loads(r['nf4_diagnostic_probs'])),num(r['today_max_gap'])+' / '+num(r['nf4_max_gap'])] for r in panel])+f'''

NF4 Q81 USA max |Δp| is {num(q81_usa)}. However, {len(failed)} of {len(panel)} default
NF4 item/arm rows still fail 1e-3; the worst is
{max(panel,key=lambda r:r['nf4_max_gap'])['question_id']} /
{max(panel,key=lambda r:r['nf4_max_gap'])['arm']} at
{num(max(r['nf4_max_gap'] for r in panel))}. A saturated answer matching in probability
is not evidence that every underlying logprob matches. No per-row variant selection
or calibration was used to call a reproduction.

### Q81 logprob differences (nats)

'''+table(['Arm','Code','Archive','Unquantized today','Today − archive'],q81_nats)+'''

These are full completion scores. Large common shifts can cancel in the option
softmax; relative score shifts determine the probability discrepancy.
''')
sections.append('''## Bounded isolation results

The full-panel variants change the base representation or forward dtype while
holding the prompt, option set, model revision, and adapter file fixed. Separate
fp32/fp16 output-logit reductions are saved so reduction precision is not confused
with weight quantization. Baseline f32 Q81 prefix factorization was checked against
the unmodified serial scorer; its recorded score gap is shown below. Other reduced-
precision prefix replays are diagnostics, not a claim of bit-identical serial CUDA
arithmetic.

'''+table(['Forward','Arm','Logit reduction','Worst item','max |Δp|','Items passing 1e-3'],
[[r['mode'],r['arm'],r['reduction'],r['worst_item'],num(r['max_probability_gap']),
  str(r['passing_items_at_1e_3'])+'/'+str(len(items))] for r in mode_summary])+f'''

Serial-factorization score gaps, Q81 float32: base
{num(replays['f32','base']['items']['Q81']['prefix_factorization_max_abs_score_gap'])}, USA
{num(replays['f32','USA_adapter']['items']['Q81']['prefix_factorization_max_abs_score_gap'])}.
The unquantized fp16 runs remain far from the archive on unsaturated rows; merely
changing f32 arithmetic to f16 is not the dominant cause.

The following predeclared swaps each alter one NF4 configuration factor on Q57/Q81,
in both arms. They are a bounded sensitivity check, not a full-panel reproduction.
`compute_f32` casts only quantized Linear arithmetic to fp32 and returns fp16 outputs;
embeddings, norms, and residual dtype remain fp16. `fp4` changes the quantization
codebook; it is not the documented Paper B configuration.

'''+table(['Swap','Arm','Item','Logit reduction','max |Δp| vs archive'],
[[r['swap'],r['arm'],r['item'],r['reduction'],num(r['max_probability_gap'])] for r in variants])+f'''

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
{replays['nf4','USA_adapter']['lora_tensors_restored_from_file']} restored tensors.
All affected USA variants were rerun serially; commands and superseded-file hashes
are in repair_commands.json. The small-tensor regression failed before this repair
and passed after it (lora_red.log / lora_green.log). Base and unquantized-f32 results
were not affected. No workbench source was changed.

### CPU/CUDA boundary

CPU runtime packages: {json.dumps(runtime['packages'],sort_keys=True)}.
The frozen historical versions are recorded verbatim in writer_followup.json and
planning/sprint_2026-10-11/PAPER_B_STACK_FREEZE.md. The CPU probe uses bitsandbytes
quantize/dequantize on individual Linear weights, followed by dense CPU operations;
it does NOT execute the historical CUDA BNB matmul or frozen attention kernels.
The diagnostic quantizes {replays['nf4','base']['quantized_weight_count']} Linear
weights, excluding embeddings/norms/lm_head, with block size 64. All runs stayed
CPU-only, one model process at a time; highest recorded item peak RSS was
{peak} bytes, below the {16_000_000_000} byte stop limit.

Ruled out locally: adapter revision bytes/config, CSV-copy corruption, tested
prompt/spec/date/labels/order/truncation/completion conventions, unquantized forward
dtype alone, and a gross serial-factorization bug on the checked float32 reference.
Not ruled out: exact original source-bundle differences, frozen package/attention
arithmetic, CUDA versus CPU quantization/dequantization/matmul, serial versus
prefix-factorized reduced-precision rounding, and original launch settings not
captured by accessible manifests. The bounded swaps do not identify one of those
as the remaining cause. The stop rule is now applied: no additional search.
''')
sections.append('''## Q262 / bank-2 archive gate: related, not the same demonstrated cause

Q262 is absent from the cohort-1 strict archive, so it cannot replace one of the
five cohort items without changing the run. A separate model-only legacy
base-on-CHN Q262 diagnostic was run, with archive prompt bytes verified directly.
It is neither a rerun of the bank-2 gate nor a USA-adapter observation.

'''+table(['Forward','Logit reduction','Options','max |Δlogprob|','max |Δp|'],
[[r['mode'],r['reduction'],r['options'],num(r['max_abs_dlogprob']),num(r['max_abs_dprob'])] for r in q262])+f'''

The existing report-only gate's recorded statement is:

> {follow['bank2_report_only_text'].strip().replace(chr(10),' ')}

That comparison was already made on the frozen NF4 path versus an unpinned legacy
archive. Its residual cannot simply be labeled the workbench's “unquantized versus
NF4” mechanism. The supplemental CPU NF4 result moves toward the legacy logprobs
but still misses the probability target. Shared susceptibility to stack arithmetic
is plausible; identity of the remaining cause is **not established**. The existing
report-only policy remains unchanged.

Sources: q262_*.json/.log, q262_commands.json, writer_followup.json.
''')
sections.append(f'''## Blast radius: every permitted aggregate row and locked table

Coverage: {len(numbers)} NUMBERS_TABLE rows; {len(locked)} claim-lock table body rows.
The exact per-claim mapping is in blast_radius_numbers.csv: every original column,
including `claim_id`, `producing_script`, and `run_id`, is retained, with source-traced
scoring paths appended. This avoids mistaking an analysis script for an inference
writer. Grouped coverage is below; row counts partition the full table.

'''+table(['Run ID(s)','Rows','Scoring pipeline','Could move under unquantized rescore?'],
[[r['run_id'],r['rows'],r['scoring_pipeline'],r['could_move']] for r in run_groups])+f'''

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

'''+table(['Lock line / subject','Producing script / provenance limit','Run ID','Could move?'],
[[str(r['line'])+' / '+r['subject'],r['producing_script'],r['run_id'],r['could_move']] for r in locked])+f'''

Paper A legacy inference writer commits remain unresolved. Its adapter+persona
cell is explicitly unidentified by the lock itself. These are provenance gaps,
not licenses to rerun its paper numbers. Human-only fixed-panel correlations have
no direct scorer dependency. Bank/training/cell-count status declarations are not
new inference results.

Current source table SHA256: `{radius['source_table_sha256']}`.
Current lock SHA256: `{radius['source_lock_sha256']}`.
C7 declares {lock_rows} rows and digest `{lock_declaration.group(2)}`; the final table
matches that declaration. An earlier mismatch was observed while another session
updated the table; PROGRESS.md and the card preserve that event. A1 did not rebuild
or edit it. Current inspected root HEAD: `{radius['head']}`.
''')
sections.append('''## Canonical capture recommendation — Augusto decides

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
''')
sections.append(f'''## Fence audit — incidental bytecode exception

Source diffs and recorded source hashes are unchanged by A1, but this was **not a
literally zero-write read-only run**. Initial Python imports refreshed
{len(fence['likely_A1_bytecode_paths'])} Python bytecode cache files under paper_b:

{chr(10).join('- `'+p+'`' for p in fence['likely_A1_bytecode_paths'])}

These are an incidental fence exception, not paper-source or paper-number edits.
They have not been deleted: cleaning outside the fence would be another unauthorized
write. Subsequent subprocess launchers disable bytecode generation through
PYTHONDONTWRITEBYTECODE. The raw metadata audit also records concurrent source edits
from the C7 commit and other-runtime caches; mtime alone cannot attribute those to
A1. A2's literal newer-than-artifact scan will therefore not be empty. Review this
exception explicitly rather than treating a clean git diff as proof of no writes.
Evidence: protected_mtime_audit.json/.log. No forbidden human-data files were opened.
''')
body='\n'.join(sections)
(OUT/'ARCHIVE_PROVENANCE_20261018.md').write_text(body)
evidence_names=['writer_inspection.json','writer_followup.json','prompt_comparison.json',
                'prompts_old.json','prompts_new.json','runtime_evidence.json','adapter_tensor_dtypes.json',
                'comparison_panel.csv','blast_radius_summary.json','blast_radius_numbers.csv','blast_radius_locked.csv',
                'worktree_cleanup.json','replay_commands.json','q262_commands.json','isolation_commands.json','repair_commands.json',
                'protected_mtime_audit.json']
evidence_names += [f'replay_{m}_{a}.json' for m in ['f32','f16','nf4'] for a in arms]
evidence_names += [f'replay_nf4_{a}_{t}.json' for a in arms for t in ['no_double_quant','compute_f32','fp4']]
evidence_names += [f'q262_{m}.json' for m in ['f32','f16','nf4']]
summary={'verdict':verdict,'rows':len(panel),'failed_nf4_rows':len(failed),
         'fence_exception_bytecode_paths':fence['likely_A1_bytecode_paths'],
         'mode_summary':mode_summary,'parameter_swaps':variants,'q262':q262,'run_groups':run_groups,
         'peak_rss_bytes':peak,'q81_usa_nf4_probability_gap':q81_usa,
         'memo_sha256':hashlib.sha256(body.encode()).hexdigest(),
         'evidence_sha256':{n:digest(OUT/n) for n in evidence_names}}
(OUT/'report_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps({k:v for k,v in summary.items() if k not in ['evidence_sha256','run_groups','parameter_swaps']},indent=2))
