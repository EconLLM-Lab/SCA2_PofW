"""Local writer trail and numeric-copy audit; reads only model-only CSVs/metadata."""
import csv
import hashlib
import json
from pathlib import Path
import subprocess

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
BASE=ROOT/'planning/sprint_2026-10-11/paper-b-20261011'
result={'copies':{},'download_metadata':{},'score_upload_records':[], 'git_writer_history':[]}
for arm in ['base','USA_adapter']:
    source=BASE/f'hub/runs/paper-b-20261011/synthetic/{arm}_option_probabilities.csv'
    copied=BASE/f'scores_for_join/{arm}_option_probabilities.csv'
    a=list(csv.DictReader(source.open()))
    b=list(csv.DictReader(copied.open()))
    key=lambda r:(r['question_id'],r['option_code'])
    ad={key(r):r for r in a};bd={key(r):r for r in b}
    assert ad.keys()==bd.keys()
    gaps={c:max(abs(float(ad[k][c])-float(bd[k][c])) for k in ad) for c in ['option_logprob','model_prob','option_token_count']}
    assert gaps['option_logprob']==0 and gaps['option_token_count']==0
    assert gaps['model_prob']<1e-14, gaps
    assert all(float(r['option_value'])==float(r['option_code']) for r in b)
    result['copies'][arm]={'source':str(source.relative_to(ROOT)),'copy':str(copied.relative_to(ROOT)),
                         'n_rows':len(a),'max_numeric_gaps':gaps,'copy_added_columns':sorted(set(b[0])-set(a[0])),
                         'origin_of_local_copy_script':'not found in tracked Python source; numeric transformation verified, original copier identity unresolved'}
    path=BASE/f'hub/.cache/huggingface/download/runs/paper-b-20261011/manifests/{arm}_manifest.json.metadata'
    if path.exists():
        result['download_metadata'][str(path.relative_to(ROOT))]=path.read_text().splitlines()
commits=json.loads((ROOT/'paper_b/compute/sources/score_commits.json').read_text())
result['score_upload_records']=[r for r in commits if r['title'] in ['paper-b-20261011: base option probabilities','paper-b-20261011: USA_adapter option probabilities']]
result['git_writer_history']=subprocess.check_output(['git','-C',str(ROOT),'log','--all','--format=%H %ad %s','--date=iso-strict','--','paper_b/colab/vm_cohort.py'],text=True).splitlines()
result['frozen_stack_text']=(ROOT/'planning/sprint_2026-10-11/PAPER_B_STACK_FREEZE.md').read_text()
result['bank2_report_only_text']=(ROOT/'planning/sprint_2026-10-11/paper-b-tier1/review/PAPER_WORDING_CHECKLIST.md').read_text().split('## 5.')[1].split('## 6.')[0]
# Preserve source-dispatch evidence without executing these launchers.
source_files=['paper_b/colab/vm_cohort.py','paper_b/score_cohort.py','paper_b/eval_config.py','paper_b/colab/vm_score_units.py','paper_b/colab/vm_score_t4.py','paper_b/score_sign_profiles.py','paper_b/score_plan.py','paper_b/colab/vm_gate_factorial.py']
result['source_hashes']={n:hashlib.sha256((ROOT/n).read_bytes()).hexdigest() for n in source_files}
(OUT/'writer_followup.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
