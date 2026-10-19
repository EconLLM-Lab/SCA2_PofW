"""Supplement: Q262 model-only August archive, not the cohort-1 strict run.
Run only after run_replays.py exits; never concurrent 8B forwards.
"""
import argparse
import csv
import json
from pathlib import Path
import resource
import sys
import time

import torch

p=argparse.ArgumentParser()
p.add_argument('--mode',choices=['f32','f16','nf4'],required=True)
a=p.parse_args()
OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
sys.path[:0]=[str(ROOT/'paper_b'),str(ROOT/'.worktrees/adapter-brain-vizualization/workbench/src')]
from sca2_workbench.offload_hf import build_offloaded_hf
from sca2_workbench.stream_capture import SafetensorsSource
import sca2_workbench.offload_hf as OH
from transformers import AutoTokenizer
import score_cohort as S

class DiagnosticSource(SafetensorsSource):
    def __init__(self,snapshot,dtype):
        super().__init__(snapshot,torch.float32)
        self.dtype=dtype
OH.SafetensorsSource=DiagnosticSource

archive=ROOT/'data/phase2/raw/wvs/ksenias_base8/model_option_probabilities_base_on_CHN.csv'
rows=sorted([r for r in csv.DictReader(archive.open()) if r['question_id']=='Q262'],key=lambda r:int(r['option_index']))
assert rows and all(not k.startswith(('population_','human_')) for k in rows[0])
snap=Path.home()/'.cache/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/0e9e39f249a16976918f6564b8830bc894c89659'
tok=AutoTokenizer.from_pretrained(snap,local_files_only=True)
prepared=S.prepare_prompt_for_model(tok,rows[0]['prompt_text'])
assert prepared['formatted_prompt']==rows[0]['formatted_prompt']
assert prepared['model_prompt_text']==rows[0]['complete_prompt_model_received']
completions=[tok(' '+r['option_code'],add_special_tokens=False).input_ids for r in rows]
prefix=completions[0][:-1]
assert all(c[:-1]==prefix for c in completions)

def guard(*_):
    if resource.getrusage(resource.RUSAGE_SELF).ru_maxrss>16_000_000_000:
        raise SystemExit('STOP: RSS limit')

if a.mode=='nf4':
    import bitsandbytes.functional as F
    original=SafetensorsSource._get
    def nf4_get(self,name):
        w=original(self,name)
        if name.startswith('model.layers.') and ('.self_attn.' in name or '.mlp.' in name) and name.endswith('.weight'):
            q,s=F.quantize_4bit(w.contiguous(),quant_type='nf4',blocksize=64,compress_statistics=True)
            w=F.dequantize_4bit(q,s).reshape_as(w)
        guard()
        return w
    SafetensorsSource._get=nf4_get
torch.set_num_threads(8)
model=build_offloaded_hf(snap,torch.float32 if a.mode=='f32' else torch.float16)
for m in model.modules():
    m.register_forward_hook(guard)
t0=time.monotonic()
with torch.no_grad():
    logits=model(input_ids=torch.tensor([prepared['model_prompt_ids']+prefix])).logits[0]
result={'mode':a.mode,'archive_file':str(archive.relative_to(ROOT)),
        'archive_run':'legacy August/Paper A base-on-CHN; NOT paper-b-20261011; NOT a re-run of bank2 gate',
        'prompt_byte_identical_to_archive':True,'n_options':len(rows),'reductions':{},
        'peak_rss_bytes':resource.getrusage(resource.RUSAGE_SELF).ru_maxrss,'elapsed_seconds':time.monotonic()-t0}
for label,dtype in [('float32',torch.float32),('float16',torch.float16)]:
    lp=torch.log_softmax(logits.to(dtype),dim=-1)
    shared=sum(lp[len(prepared['model_prompt_ids'])-1+i,t] for i,t in enumerate(prefix))
    scores=[float(shared+lp[-1,c[-1]]) for c in completions]
    probs=torch.softmax(torch.tensor(scores,dtype=torch.float64),dim=-1).tolist()
    result['reductions'][label]={'rows':[{**{k:r[k] for k in ['question_id','option_code','option_logprob','model_prob']},'today_logprob':s,'today_prob':pr} for r,s,pr in zip(rows,scores,probs)],
        'max_abs_dlogprob':max(abs(s-float(r['option_logprob'])) for r,s in zip(rows,scores)),
        'max_abs_dprob':max(abs(pr-float(r['model_prob'])) for r,pr in zip(rows,probs))}
(OUT/f'q262_{a.mode}.json').write_text(json.dumps(result,indent=2))
print(json.dumps({k:v for k,v in result.items() if k!='reductions'}))
for k,v in result['reductions'].items():
    print(k,{x:y for x,y in v.items() if x!='rows'})
