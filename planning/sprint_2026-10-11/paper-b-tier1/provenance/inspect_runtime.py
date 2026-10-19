"""Record runtime/version and source configuration evidence without loading weights."""
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
paths = ['paper_b/score_cohort.py','paper_b/score_sign_profiles.py','paper_b/colab/vm_cohort.py',
         'paper_b/colab/vm_score_units.py','paper_b/colab/vm_score_t4.py','paper_b/score_plan.py',
         'planning/sprint_2026-10-11/PAPER_B_STACK_FREEZE.md',
         '.worktrees/adapter-brain-vizualization/workbench/src/sca2_workbench/offload_hf.py',
         '.worktrees/adapter-brain-vizualization/workbench/plans/scripts/pair8b.py']
result = {'python':sys.version, 'packages':{n:importlib.metadata.version(n) for n in
          ['torch','transformers','peft','bitsandbytes','huggingface-hub']},
          'HF_TOKEN_present':bool(os.environ.get('HF_TOKEN')), 'sources':{}}
for name in paths:
    p = ROOT/name
    result['sources'][name] = {'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    lines = p.read_text().splitlines()
    needles = ['BitsAndBytesConfig(', 'bnb_4bit_', 'load_base_model_and_tokenizer(',
               'score_cohort.py', 'score_sign_profiles.py', 'torch.float32', 'torch.float64',
               'load_in_4bit', 'NF4', 'frozen']
    result['sources'][name]['relevant_lines'] = [f'{i}: {line}' for i,line in enumerate(lines,1)
                                                if any(s in line for s in needles)]
for label, cmd in [('root_head',['git','rev-parse','HEAD']),
                   ('workbench_head',['git','-C',str(ROOT/'.worktrees/adapter-brain-vizualization'),'rev-parse','HEAD'])]:
    done = subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    result[label] = {'command':cmd,'exit_code':done.returncode,'stdout':done.stdout.strip()}
    assert done.returncode==0
(OUT/'runtime_evidence.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
