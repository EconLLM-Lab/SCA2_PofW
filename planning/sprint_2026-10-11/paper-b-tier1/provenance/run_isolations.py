"""Bounded CPU isolation: two diagnostic items, three one-factor swaps, both arms.

Not a search or a fit. The default NF4+double-quant+fp16 comparison is already
recorded over the full five-item panel. No CUDA or MPS path is selected.
"""
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
WB = ROOT/'.worktrees/adapter-brain-vizualization/workbench'
# Fail closed rather than compete with a previous replay.
processes = subprocess.check_output(['ps','-axo','pid,command'], text=True)
if any('python' in line and ('/evaluate_stream.py' in line or '/evaluate_q262.py' in line)
       for line in processes.splitlines()):
    raise SystemExit('STOP: another 8B diagnostic process is active')
commands = []
for tag, flags in [('no_double_quant',['--no-double-quant']),
                   ('compute_f32',['--compute-dtype','float32']),
                   ('fp4',['--quant-type','fp4'])]:
    for arm in ['base','USA_adapter']:
        cmd = ['env','-u','PYTHONPATH','uv','run','--frozen','--no-sync','--project',str(WB),
               '--with','pandas','--with','bitsandbytes','python',str(OUT/'evaluate_stream.py'),
               '--mode','nf4','--arm',arm,'--items','Q57','Q81','--tag',tag,*flags]
        with (OUT/f'replay_nf4_{arm}_{tag}.log').open('w') as log:
            done = subprocess.run(cmd, cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        commands.append({'command':cmd,'exit_code':done.returncode})
        (OUT/'isolation_commands.json').write_text(json.dumps(commands,indent=2))
        print(tag,arm,'exit',done.returncode,flush=True)
        if done.returncode:
            sys.exit(done.returncode)
