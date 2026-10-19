"""Run diagnostic variants serially and capture child exit codes without a pipe."""
import json
import os
from pathlib import Path
import subprocess
import sys

os.environ['PYTHONDONTWRITEBYTECODE'] = '1'

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
commands = json.loads((OUT/'replay_commands.json').read_text()) if (OUT/'replay_commands.json').exists() else []
commands = [c for c in commands if c['exit_code']==0]
for mode in ['f32','f16','nf4']:
    for arm in ['base','USA_adapter']:
        cmd = ['env','-u','PYTHONPATH','uv','run','--frozen','--no-sync','--project',
               str(ROOT/'.worktrees/adapter-brain-vizualization/workbench'),
               '--with','pandas','--with','bitsandbytes','python',str(OUT/'evaluate_stream.py'),
               '--mode',mode,'--arm',arm]
        if mode == 'f32':
            cmd += ['--check-serial']
        if any(c['command']==cmd and c['exit_code']==0 for c in commands):
            continue
        with (OUT/f'replay_{mode}_{arm}.log').open('w') as log:
            done = subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
        commands.append({'command':cmd,'exit_code':done.returncode})
        (OUT/'replay_commands.json').write_text(json.dumps(commands,indent=2))
        print(mode,arm,'exit',done.returncode,flush=True)
        if done.returncode:
            sys.exit(done.returncode)

supplement=[]
for mode in ['f32','f16','nf4']:
    cmd=['env','-u','PYTHONPATH','uv','run','--frozen','--no-sync','--project',
         str(ROOT/'.worktrees/adapter-brain-vizualization/workbench'),
         '--with','pandas','--with','bitsandbytes','python',str(OUT/'evaluate_q262.py'),'--mode',mode]
    with (OUT/f'q262_{mode}.log').open('w') as log:
        done=subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    supplement.append({'command':cmd,'exit_code':done.returncode})
    (OUT/'q262_commands.json').write_text(json.dumps(supplement,indent=2))
    print('Q262',mode,'exit',done.returncode,flush=True)
    if done.returncode:
        sys.exit(done.returncode)
