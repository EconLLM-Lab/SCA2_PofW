"""Correct only USA runs affected by scaffold LoRA fp16 rounding.

Preserve old raw files; the original replays remain an auditable failed diagnostic,
not the memo's canonical comparison. No base or unquantized-f32 replay is repeated.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
WB = ROOT/'.worktrees/adapter-brain-vizualization/workbench'
processes = subprocess.check_output(['ps','-axo','pid,command'],text=True)
if any('python' in line and ('/evaluate_stream.py' in line or '/evaluate_q262.py' in line)
       for line in processes.splitlines()):
    raise SystemExit('STOP: another 8B diagnostic process is active')
variants = [('f16',None,[]),('nf4',None,[]),
            ('nf4','no_double_quant',['--no-double-quant']),
            ('nf4','compute_f32',['--compute-dtype','float32']),
            ('nf4','fp4',['--quant-type','fp4'])]
commands = []
for mode, tag, flags in variants:
    suffix = f'_{tag}' if tag else ''
    stem = f'replay_{mode}_USA_adapter{suffix}'
    preserved = []
    for ext in ['json','log']:
        src = OUT/f'{stem}.{ext}'
        dst = OUT/f'rounded_lora_{stem}.{ext}'
        assert not dst.exists(), f'fail closed: already archived {dst}'
        contents = src.read_bytes()
        dst.write_bytes(contents)
        preserved.append({'file':dst.name,'sha256':hashlib.sha256(contents).hexdigest()})
    cmd = ['env','-u','PYTHONPATH','uv','run','--frozen','--no-sync','--project',str(WB),
           '--with','pandas','--with','bitsandbytes','python',str(OUT/'evaluate_stream.py'),
           '--mode',mode,'--arm','USA_adapter',*flags]
    if tag:
        cmd += ['--items','Q57','Q81','--tag',tag]
    with (OUT/f'{stem}.log').open('w') as log:
        done = subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    commands.append({'command':cmd,'exit_code':done.returncode,'superseded_raw_outputs':preserved,
                     'script_sha256':hashlib.sha256((OUT/'evaluate_stream.py').read_bytes()).hexdigest(),
                     'restore_script_sha256':hashlib.sha256((OUT/'restore_lora.py').read_bytes()).hexdigest()})
    (OUT/'repair_commands.json').write_text(json.dumps(commands,indent=2))
    print(mode,tag,'USA_adapter','exit',done.returncode,flush=True)
    if done.returncode:
        sys.exit(done.returncode)
