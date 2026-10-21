#!/usr/bin/env python3
"""Compare a built bundle manifest with the v1.4 file hashes (deploy/v1.4_file_hashes.json).

Every v1.4 file must be present with the same sha256 and size. The only files allowed to differ
are index.json, index.html (any folder) and assets/*, which the viewer build and the new index
rewrite. Exit 0 when nothing else differs, 1 otherwise.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

BASELINE = Path(__file__).resolve().parent.parent / 'deploy/v1.4_file_hashes.json'


def allowed_to_differ(name: str) -> bool:
    return name.rsplit('/', 1)[-1] in ('index.json', 'index.html') or name.startswith('assets/')


def compare(baseline: dict, manifest: dict) -> dict:
    """{'checked', 'identical', 'allowed_changed', 'violations'} for v1.4 file name -> new manifest."""
    new = {f['file']: f for f in manifest['files']}
    result = {'checked': 0, 'identical': 0, 'allowed_changed': [], 'violations': []}
    for name, old in sorted(baseline['files'].items()):
        result['checked'] += 1
        got = new.get(name)
        if got and got['sha256'] == old['sha256'] and got['bytes'] == old['bytes']:
            result['identical'] += 1
        elif allowed_to_differ(name):
            result['allowed_changed'].append(name)
        else:
            result['violations'].append(name + (' (missing)' if got is None else ' (changed)'))
    return result


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('manifest', type=Path, help='deploy_bundle.tar.manifest.json of the new build')
    ap.add_argument('--baseline', type=Path, default=BASELINE)
    args = ap.parse_args()
    result = compare(json.loads(args.baseline.read_text()), json.loads(args.manifest.read_text()))
    print(json.dumps(result, indent=1))
    raise SystemExit(1 if result['violations'] else 0)
