"""Trace every permitted numbers-table row without opening its human-data inputs."""
import csv
import hashlib
import json
from pathlib import Path

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
TABLE = ROOT/'planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv'
rows = list(csv.DictReader(TABLE.open()))
ledger = [json.loads(s) for s in (ROOT/'paper_b/compute/ledger.jsonl').read_text().splitlines() if s.strip()]
freeze = json.loads((ROOT/'paper_b/heldout/FREEZE.json').read_text())

# Source-traced dispatch, not inferred from numerical similarity.
def pipeline(run):
    if run == 'paper-b-20261011':
        return 'paper_b/colab/vm_cohort.py -> score_cohort.score_model_questions -> sequence_logprob', 'archive manifest + vm_cohort.py:125-139,184-192; bundle identity unresolved'
    if run == 'n/a (file hash)':
        return 'paper_b/build_numbers_table.py (hashlib/git show; no model)', 'build_numbers_table.py:hash_rows'
    if 'signprompt' in run:
        driver = 'vm_score_t4.py' if 'strict-v1-20261018' in run else 'vm_score_units.py'
        return 'paper_b/colab/'+driver+' -> paper_b/score_sign_profiles.py -> score_cohort.load_base_model_and_tokenizer/sequence_logprob', 'score_plan.CONDITIONS + driver dispatch; freeze spec pins where present'
    driver = 'vm_score_t4.py' if ('replicate' in run or 'nearzero' in run) else 'vm_score_units.py'
    return 'paper_b/colab/'+driver+' -> paper_b/score_cohort.py --model-only -> load_base_model_and_tokenizer/sequence_logprob', 'score_plan.CONDITIONS + driver dispatch; freeze spec pins where present'

fields = list(rows[0])+['scoring_pipeline','pipeline_evidence','could_move_on_unquantized_rescore','scope_of_claim','ledger_sources','stack']
for row in rows:
    runs = row['run_id'].split('; ')
    entries = [pipeline(r) for r in runs]
    row['scoring_pipeline'] = '; '.join(e[0] for e in entries)
    row['pipeline_evidence'] = '; '.join(e[1] for e in entries)
    row['ledger_sources'] = '; '.join(sorted({e['source'] for e in ledger if e.get('provenance',{}).get('run_id') in runs}))
    if row['run_id']=='n/a (file hash)':
        row['could_move_on_unquantized_rescore'] = 'NO: content hash is model-independent; unchanged input bytes imply unchanged hash'
        row['stack'] = 'no inference'
    else:
        row['could_move_on_unquantized_rescore'] = 'YES/POSSIBLE: model outputs, derived selection, or selection-conditioned criterion; no magnitude estimated'
        row['stack'] = 'frozen NF4/double quant/fp16; not the unquantized workbench reference'
    row['scope_of_claim'] = 'Historical artifact unchanged; sensitivity concerns a new counterfactual rescore, not an authorized paper-number amendment'
with (OUT/'blast_radius_numbers.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

# Record every body row in every markdown table of the claim-lock document.
lock = ROOT/'planning/TWO_PAPER_CLAIM_LOCK.md'
locked=[]
section=''
for lineno,line in enumerate(lock.read_text().splitlines(),1):
    if line.startswith('**'):
        section=line.strip('* ')
    if not line.startswith('|'):
        continue
    cells=[x.strip() for x in line.strip('|').split('|')]
    if all(not x or set(x)<=set(':- ') for x in cells) or cells[0] in ['Column','Quantity','Item']:
        continue
    subject=cells[0]
    if subject.startswith('1. 42 countries'):
        producing='paper_b/run_cohort.py (training); paper_b/colab/vm_cohort.py (scoring); cohort config'
        rid='paper-b-20261011'
        move='NO for declared country count; outcomes could change under a new rescore'
    elif subject.startswith('2. Second bank'):
        producing='paper_b/protocol_bank2.py (bank); paper_b/colab/vm_score_units.py (NF4 scoring)'
        rid='bank2-strict-v1-20261016'
        move='NO for design status; quantitative outcomes could change under a new rescore'
    elif subject.startswith('3. Sign-profile'):
        producing='paper_b/score_sign_profiles.py via paper_b/colab/vm_score_units.py or vm_score_t4.py'
        rid='bank2-signprompt-heldout-v1-20261016; bank2-signprompt-strict-v1-20261018'
        move='NO for declared cell count; quantitative outcomes could change under a new rescore'
    elif subject.startswith('4. Independent'):
        producing='claim-lock status declaration; no independent human-check pipeline exists in this claim'
        rid='not an active inference run'
        move='NO: quantization cannot supply the missing independent human check'
    elif subject.startswith('5. Optional'):
        producing='claim-lock scope declaration; no inference pipeline'
        rid='not an active inference run'
        move='N/A: scope decision, not a scored outcome'
    elif subject=='Encoding':
        producing='analysis/phase2/04_direction_cardinal.py (aggregation); original scoring notebooks/run identity not pinned in the lock'
        rid='legacy Paper A synthetic encoding jobs (not paper-b-20261011); exact writer SHA unresolved'
        move='POSSIBLE on rescoring legacy model outputs; no direct dependency on the Paper B archive; historical number remains locked'
    elif 'human' in subject.lower() and not any(t in subject.lower() for t in ['adapter','persona']):
        producing='analysis/phase2/22_paper_a_surface.py (human-only map aggregation; source inspected only, not run)'
        rid='locked Paper A human survey/GPS surface; no model inference run'
        move='NO direct scorer dependency for the fixed panel/items; any panel/item change is outside scope'
    elif subject in ['GPS \\(z\\)', 'Nomological / GDP', 'Assignment placebo', 'Egypt / Q69–Q71']:
        producing='claim-lock declaration / not recomputed / optional restriction; no citable active model number'
        rid='not an active inference run'
        move='N/A; do not manufacture a current result'
    else:
        producing='Paper A audit -> frozen panel/readout; analysis/phase2/22_paper_a_surface.py is partial current aggregator, not original inference writer'
        rid='ksenias_base8 + co2_8 (locked Paper A); exact inference source SHA unresolved; adapter+persona 0.67 explicitly unidentified'
        move='POSSIBLE if these historical jobs are rescored on another stack; not a dependency on paper-b-20261011; no amendment authorized'
    locked.append({'line':lineno,'table':section,'subject':subject,'locked_cells':json.dumps(cells[1:],ensure_ascii=False),
                   'producing_script':producing,'run_id':rid,'could_move':move,'provenance_limit':'source-level trace only; forbidden joins/means not opened'})
with (OUT/'blast_radius_locked.csv').open('w') as f:
    w=csv.DictWriter(f,fieldnames=list(locked[0]));w.writeheader();w.writerows(locked)
summary={'numbers_rows':len(rows),'claim_lock_table_rows':len(locked),'source_table_sha256':hashlib.sha256(TABLE.read_bytes()).hexdigest(),
         'source_lock_sha256':hashlib.sha256(lock.read_bytes()).hexdigest(),
         'run_groups':{r:sum(x['run_id']==r for x in rows) for r in sorted({x['run_id'] for x in rows})},
         'frozen_scoring_code_revision':freeze['scoring_code_revision'],
         'head':__import__('subprocess').check_output(['git','-C',str(ROOT),'rev-parse','HEAD'],text=True).strip(),
         'limits':['No human inputs, human means, or model-human joins opened.','Pipeline paths verified from source dispatch; missing private Hub manifests are not filled in by inference.','Every non-hash numbers-table value conservatively marked potentially sensitive; no claim its magnitude actually changes.']}
(OUT/'blast_radius_summary.json').write_text(json.dumps(summary,indent=2))
print(json.dumps(summary,indent=2))
