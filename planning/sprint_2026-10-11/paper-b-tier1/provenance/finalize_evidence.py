"""Final model-free checks; persist exact commands and unpiped exit codes."""
import json
from pathlib import Path
import subprocess
import sys

OUT = Path(__file__).resolve().parent
ROOT = OUT.parents[3]
WB = ROOT/'.worktrees/adapter-brain-vizualization/workbench'
local = ['env','-u','PYTHONPATH','PYTHONDONTWRITEBYTECODE=1',str(ROOT/'.venv/bin/python')]
workbench = ['env','-u','PYTHONPATH','PYTHONDONTWRITEBYTECODE=1','uv','run','--frozen','--no-sync','--project',str(WB),
             '--with','pandas','--with','bitsandbytes','python']
steps = [('test_diagnostic_cli.py',workbench,'cli_final.log'),
         ('test_restore_lora.py',workbench,'lora_final.log'),
         ('test_trace.py',local,'trace_final.log'),
         ('inspect_runtime.py',workbench,'runtime_evidence.log'),
         ('audit_fence.py',local,'protected_mtime_audit.log'),
         ('build_report.py',local,'build_report.log'),
         ('verify_provenance.py',local,'verification.log')]
records=[]
for script, interpreter, logname in steps:
    cmd = [*interpreter,str(OUT/script)]
    with (OUT/logname).open('w') as log:
        done = subprocess.run(cmd,cwd=ROOT,stdout=log,stderr=subprocess.STDOUT)
    records.append({'command':cmd,'exit_code':done.returncode,'output_file':logname})
    (OUT/'final_commands.json').write_text(json.dumps(records,indent=2))
    print(script,'exit',done.returncode,flush=True)
    if done.returncode:
        sys.exit(done.returncode)
