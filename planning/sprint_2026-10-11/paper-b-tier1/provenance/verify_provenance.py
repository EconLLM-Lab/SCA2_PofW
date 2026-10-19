"""Check completeness and numerical closure of the A1 evidence bundle."""
import csv
import hashlib
import json
import math
from pathlib import Path
import subprocess
import sys

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
checks=[]
def check(name,fn):
    try:
        detail=fn()
        checks.append({'name':name,'pass':True,'detail':detail})
    except Exception as e:
        checks.append({'name':name,'pass':False,'error':repr(e)})

def prompts():
    old=json.loads((OUT/'prompts_old.json').read_text())
    new=json.loads((OUT/'prompts_new.json').read_text())
    meta=json.loads((OUT/'writer_inspection.json').read_text())
    assert old['spec_sha256']==new['spec_sha256']==meta['manifests']['base']['spec_sha256']
    assert old['items']==new['items'] and len(new['items'])==5
    assert all(not x['prompt_was_truncated'] for x in new['items'].values())
    return {'items':len(new['items']),'spec_sha256':new['spec_sha256']}
check('byte-identical prompts/completions and archive spec',prompts)

def adapters():
    x=json.loads((OUT/'writer_inspection.json').read_text())
    a,b=x['adapter_revisions'].values()
    assert a==b
    assert a['bundle_sha256']==x['manifests']['USA_adapter']['adapter_sha256']
    return a['bundle_sha256']
check('adapter bytes/config both revisions',adapters)

def replays():
    results=[]
    for mode in ['f32','f16','nf4']:
        for arm in ['base','USA_adapter']:
            j=json.loads((OUT/f'replay_{mode}_{arm}.json').read_text())
            assert j['device']=='cpu' and set(j['items'])=={'Q57','Q58','Q81','Q106','Q107'}
            if mode=='nf4':
                assert j['quantized_weight_count']==224
            if arm=='USA_adapter' and mode in ['f16','nf4']:
                assert j['lora_tensors_restored_from_file']==256
            for q,r in j['items'].items():
                assert r['peak_rss_bytes']<=16_000_000_000
                assert abs(sum(r['archive_probs'])-1)<1e-12
                for red in r['reductions'].values():
                    assert len(red['probs'])==len(r['codes'])
                    assert all(math.isfinite(x) for x in red['scores']+red['probs'])
                    assert abs(sum(red['probs'])-1)<1e-12
                    gap=max(abs(x-y) for x,y in zip(red['probs'],r['archive_probs']))
                    assert gap==red['max_abs_probability_gap_vs_archive']
                if mode=='f32' and q=='Q81':
                    assert r['prefix_factorization_max_abs_score_gap']<1e-3
            results.append({'mode':mode,'arm':arm,'items':len(j['items'])})
    commands=json.loads((OUT/'replay_commands.json').read_text())
    assert len(commands)==6 and all(c['exit_code']==0 for c in commands)
    repair=json.loads((OUT/'repair_commands.json').read_text())
    assert len(repair)==5 and all(c['exit_code']==0 for c in repair)
    for cmd in repair:
        for record in cmd['superseded_raw_outputs']:
            assert hashlib.sha256((OUT/record['file']).read_bytes()).hexdigest()==record['sha256']
    return results
check('complete serial CPU replays, RSS and probability closure',replays)

def q262():
    res=[]
    for mode in ['f32','f16','nf4']:
        j=json.loads((OUT/f'q262_{mode}.json').read_text())
        assert j['prompt_byte_identical_to_archive']
        assert j['peak_rss_bytes']<=16_000_000_000
        assert j['n_options']==len(j['reductions']['float32']['rows'])
        res.append({'mode':mode,'n_options':j['n_options']})
    return res
check('supplemental Q262 model-only check',q262)

def radius():
    original=list(csv.DictReader((ROOT/'planning/sprint_2026-10-11/paper-b-tier1/NUMBERS_TABLE.csv').open()))
    annotated=list(csv.DictReader((OUT/'blast_radius_numbers.csv').open()))
    assert len(original)==len(annotated)
    assert [r['claim_id'] for r in original]==[r['claim_id'] for r in annotated]
    for a,b in zip(original,annotated):
        assert all(a[k]==b[k] for k in a)
        assert b['scoring_pipeline'] and b['could_move_on_unquantized_rescore']
    locked=list(csv.DictReader((OUT/'blast_radius_locked.csv').open()))
    expected=[]
    for n,line in enumerate((ROOT/'planning/TWO_PAPER_CLAIM_LOCK.md').read_text().splitlines(),1):
        if line.startswith('|'):
            cells=[x.strip() for x in line.strip('|').split('|')]
            if not all(not x or set(x)<=set(':- ') for x in cells) and cells[0] not in ['Column','Quantity','Item']:
                expected.append(str(n))
    assert [r['line'] for r in locked]==expected
    return {'numbers_rows':len(annotated),'claim_lock_rows':len(locked)}
check('every numbers-table and claim-lock table row accounted for',radius)

def protected():
    cmd=['git','-C',str(ROOT),'diff','--exit-code','HEAD','--','paper_b','planning/TWO_PAPER_CLAIM_LOCK.md']
    done=subprocess.run(cmd,capture_output=True,text=True)
    assert done.returncode==0,done.stdout+done.stderr
    source=json.loads((OUT/'writer_followup.json').read_text())
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h for n,h in source['source_hashes'].items())
    return {'command':cmd,'exit_code':done.returncode}
check('protected source and claim lock unchanged',protected)

def isolations():
    results=[]
    for tag in ['no_double_quant','compute_f32','fp4']:
        for arm in ['base','USA_adapter']:
            j=json.loads((OUT/f'replay_nf4_{arm}_{tag}.json').read_text())
            assert j['device']=='cpu' and set(j['items'])=={'Q57','Q81'}
            assert j['quantized_weight_count']==224
            assert j['quant_type']==('fp4' if tag=='fp4' else 'nf4')
            assert j['double_quant']==(tag!='no_double_quant')
            assert j['linear_compute_dtype']==('float32' if tag=='compute_f32' else 'float16')
            if arm=='USA_adapter':
                assert j['lora_tensors_restored_from_file']==256
            assert all(r['peak_rss_bytes']<=16_000_000_000 for r in j['items'].values())
            results.append({'tag':tag,'arm':arm,'items':len(j['items'])})
    commands=json.loads((OUT/'isolation_commands.json').read_text())
    assert len(commands)==6 and all(c['exit_code']==0 for c in commands)
    return results
check('bounded one-factor CPU parameter swaps complete',isolations)

def cleanup():
    j=json.loads((OUT/'worktree_cleanup.json').read_text())
    assert all(c['exit_code']==0 for c in j)
    active=subprocess.check_output(['git','-C',str(ROOT),'worktree','list'],text=True)
    assert '/scratch/pb-archive ' not in active
    runtime=json.loads((OUT/'runtime_evidence.json').read_text())
    assert all(hashlib.sha256((ROOT/n).read_bytes()).hexdigest()==h['sha256']
               for n,h in runtime['sources'].items())
    return {'worktree_removed':True,'runtime_packages':runtime['packages']}
check('temporary worktree removed and source evidence current',cleanup)

def memo():
    assert (OUT/'ARCHIVE_PROVENANCE_20261018.md').is_file()
    j=json.loads((OUT/'report_summary.json').read_text())
    assert j['rows']==10
    assert j['verdict'] in ['REPRODUCED','NOT REPRODUCED']
    assert hashlib.sha256((OUT/'ARCHIVE_PROVENANCE_20261018.md').read_bytes()).hexdigest()==j['memo_sha256']
    assert all(hashlib.sha256((OUT/n).read_bytes()).hexdigest()==h for n,h in j['evidence_sha256'].items())
    panel=list(csv.DictReader((OUT/'comparison_panel.csv').open()))
    assert len(panel)==j['rows']
    for row in panel:
        for mode,col in [('f32','today_probs'),('nf4','nf4_diagnostic_probs')]:
            item=json.loads((OUT/f'replay_{mode}_{row["arm"]}.json').read_text())['items'][row['question_id']]
            assert json.loads(row[col])==item['reductions']['float32']['probs']
            assert json.loads(row['archive_probs'])==item['archive_probs']
    return j['verdict']
check('completed evidence-derived memo',memo)

fence=json.loads((OUT/'protected_mtime_audit.json').read_text())
result={'checks':checks,'passed':sum(c['pass'] for c in checks),'total':len(checks),
        'fence_status':'INCIDENTAL BYTECODE WRITES DISCLOSED; not a zero-write audit',
        'fence_exception_bytecode_paths':fence['likely_A1_bytecode_paths']}
(OUT/'verification.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
sys.exit(0 if all(c['pass'] for c in checks) else 1)
