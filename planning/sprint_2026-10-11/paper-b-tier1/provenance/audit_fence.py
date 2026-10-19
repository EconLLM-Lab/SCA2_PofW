"""Metadata-only fence audit; do not delete or open protected data files."""
import json
import os
from pathlib import Path
import subprocess

OUT=Path(__file__).resolve().parent
ROOT=OUT.parents[3]
cutoff=(OUT/'inspect_provenance.py').stat().st_mtime
rows=[]
for root in [ROOT/'paper_b',ROOT/'.worktrees/adapter-brain-vizualization/workbench']:
    for parent,dirs,files in os.walk(root):
        dirs[:]=[d for d in dirs if d not in {'.venv','node_modules','.git'}]
        for name in files:
            p=Path(parent)/name
            if p.stat().st_mtime>cutoff:
                rows.append({'path':str(p.relative_to(ROOT)),'mtime':p.stat().st_mtime,
                             'kind':'bytecode' if p.suffix=='.pyc' else 'other'})
command=['git','show','--format=fuller','--stat','a1d75aec34837b6a3ba4dbac93786fc5bdb2447d','--','paper_b']
done=subprocess.run(command,cwd=ROOT,capture_output=True,text=True)
assert done.returncode==0
result={'cutoff_mtime':cutoff,'newer_protected_files':rows,
        'likely_A1_bytecode_paths':[r['path'] for r in rows if r['path'].startswith('paper_b/__pycache__/') and r['path'].endswith('.cpython-312.pyc')],
        'concurrent_source_change_evidence':{'command':command,'exit_code':done.returncode,'stdout':done.stdout},
        'limits':['Mtime alone cannot attribute every concurrent write.','A1 imported the Python 3.12 scorer modules; bytecode is a disclosed incidental fence exception.','No bytecode or external file was deleted to hide this exception.']}
(OUT/'protected_mtime_audit.json').write_text(json.dumps(result,indent=2))
print(json.dumps(result,indent=2))
