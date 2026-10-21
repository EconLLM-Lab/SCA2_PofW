#!/usr/bin/env python3
"""Build (never deploy) a fresh static site and byte-identical capture closure.

Both actual gzip bytes and uncompressed file payload must fit 950,000,000
bytes. The adjacent .tar.manifest.json describes every archive file, not itself.
No model loading, inference, weight copying, or source-capture rewriting occurs.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path, PureWindowsPath
import re
import shutil
import subprocess
import tarfile
import tempfile

HERE = Path(__file__).resolve().parent.parent
MAX_BYTES = 950_000_000
SCRATCH = Path.home() / '.hermes/profiles/engineer/cache/scratch/wb1'
IMAGES = ('ladder-1440.png', 'matrix-1440.png', 'object-1440.png', 'cohort-illustration.png')


def sha256(p: Path) -> str:
    h = hashlib.sha256()
    with p.open('rb') as stream:
        for block in iter(lambda: stream.read(1 << 20), b''):
            h.update(block)
    return h.hexdigest()


def safe_relative(value: str, *, flat: bool = False) -> Path:
    if not isinstance(value, str) or not value or '\\' in value:
        raise ValueError(f'Unsafe relative path: {value!r}')
    p = Path(value)
    if p.is_absolute() or PureWindowsPath(value).drive or '..' in p.parts or (flat and len(p.parts) != 1):
        raise ValueError(f'Unsafe relative path: {value!r}')
    return p


def public_metadata(value):
    """Reject local filesystem paths, without altering immutable capture bytes."""
    if isinstance(value, dict):
        for child in value.values():
            public_metadata(child)
    elif isinstance(value, list):
        for child in value:
            public_metadata(child)
    elif isinstance(value, str) and (value.startswith(('/', '~/', 'file://')) or PureWindowsPath(value).drive):
        raise ValueError(f'Absolute/private metadata path; fix source before bundling: {value!r}')


def read_json(path):
    return json.loads(path.read_text())


def unique(rows, key, wanted):
    matches = [row for row in rows if key(row) == wanted]
    if len(matches) != 1:
        raise ValueError(f'Expected exactly one dependency {wanted!r}; found {len(matches)}')
    return matches[0]


def select_prompt_features(featured, adapter_index, base):
    """Keep the largest saved adapter-margin gap for each sign bit."""
    margins = {(row['b'], row['item_id']): row['d_margin'] for row in adapter_index['pairs']
               if row['a'] == base}
    enriched = []
    for feature in featured:
        item = feature['item']
        models = [base + '_' + str(feature[side]).lower() for side in ('x', 'y')]
        try:
            gap = abs(margins[(models[1], item)] - margins[(models[0], item)])
        except KeyError as exc:
            raise ValueError(f'Missing adapter margin for prompt selection: {exc.args[0]!r}') from exc
        enriched.append(dict(feature, saved_margin_difference=gap))

    winners = {}
    for row in enriched:
        key = (row['saved_margin_difference'], row['item'], row['x'], row['y'])
        if row['bit'] not in winners or key > winners[row['bit']][0]:
            winners[row['bit']] = (key, row)
    kept = [row for row in enriched if winners[row['bit']][1] is row]
    dropped = [row for row in enriched if winners[row['bit']][1] is not row]
    return kept, dropped


def build_bundle(args) -> int:
    w = Path(args.workbench).resolve()
    viewer = w / 'viewer'
    out = Path(args.out).resolve() if args.out else w / 'dist/deploy_bundle.tar.gz'
    manifest_path = out.with_suffix('.manifest.json')
    limit = getattr(args, 'max_bytes', MAX_BYTES)
    if not 0 < limit <= MAX_BYTES:
        raise ValueError(f'--max-bytes must be between 1 and {MAX_BYTES}')
    # An output under the input/build tree could destroy inputs or ship itself.
    if out.is_relative_to(viewer) or out.is_relative_to(w / 'exports'):
        raise ValueError('Output must not be inside viewer or exports')
    SCRATCH.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='deploy-', dir=SCRATCH) as temp:
        stage = Path(temp) / 'site'
        stage.mkdir()
        entries = {}

        def copy(source, name, kind, **metadata):
            source = Path(source)
            rel = safe_relative(name)
            if source.is_symlink() or not source.is_file():
                raise FileNotFoundError(f'Missing or symlink dependency: {source}')
            # Reject symlinked parent directories too.
            if source.resolve() != source.absolute():
                raise ValueError(f'Symlink dependency: {source}')
            digest = sha256(source)
            if name in entries:
                if entries[name]['sha256'] != digest:
                    raise ValueError(f'Flattened filename collision: {name}')
                return
            target = stage / rel
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, target)
            if sha256(target) != digest:
                raise ValueError(f'Source changed while copying: {source}')
            entries[name] = dict(file=name, bytes=target.stat().st_size,
                                 sha256=digest, kind=kind, **metadata)

        # Never reuse a prior Vite output. npm failure propagates, no stale fallback.
        dist = viewer / 'dist'
        if dist.is_symlink():
            raise ValueError('viewer/dist must not be a symlink')
        if dist.exists():
            shutil.rmtree(dist)
        subprocess.run(['npm', 'run', 'build'], cwd=viewer, check=True)
        copy(dist / 'index.html', 'index.html', 'viewer')
        for p in sorted((dist / 'assets').rglob('*')):
            if p.is_file() or p.is_symlink():
                if p.suffix not in {'.js', '.css', '.svg', '.png', '.jpg', '.webp', '.woff', '.woff2'}:
                    raise ValueError(f'Unexpected static asset: {p}')
                copy(p, p.relative_to(dist).as_posix(), 'viewer')
        for name in ('index.html', 'sca2_data.json'):
            copy(dist / 'sca2' / name, 'sca2/' + name, 'story')
        for name in IMAGES:
            copy(viewer / 'screens/v3' / name, 'screens/v3/' + name, 'image')
        story = read_json(stage / 'sca2/sca2_data.json')
        public_metadata(story)
        export = story['export']
        source_dir = w / 'exports' / safe_relative(export['src'])
        prompt_source_dir = w / 'exports' / safe_relative(export['prompt_src'])
        base = export['base']
        selected = {(base, base + '_' + str(f[cc]).lower(), f['item'])
                    for f in story['featured'] for cc in ('x', 'y')}
        selected.update((base, base + '_' + u['cc'].lower(), u['item']) for u in export['default_units'])
        adapter_index = read_json(source_dir / 'index.json')
        prompt_features, dropped_prompt_features = select_prompt_features(
            story['featured'], adapter_index, base)
        prompt_selected = {(base, f['prompt_' + side], f['item'])
                           for f in prompt_features for side in ('x', 'y')}
        # Follow the actual viewer default; refuse a changed/unrecognizable declaration.
        main = (viewer / 'src/main.ts').read_text()
        default = re.search(r'export const DEFAULT\s*=\s*\{\s*a:\s*"([^"]+)",\s*b:\s*"([^"]+)",\s*item:\s*"([^"]+)"\s*\}', main)
        if not default:
            raise ValueError('Cannot resolve viewer DEFAULT from src/main.ts')
        curated = {'models': {}, 'runs': [], 'pairs': []}
        source_indexes = []
        schemas = set()
        for root, wanted in [(w / 'exports', {default.groups()}), (source_dir, selected),
                             (prompt_source_dir, prompt_selected)]:
            index_path = root / 'index.json'
            index = read_json(index_path)
            schemas.add(index['schema'])
            source_indexes.append({'file': index_path.relative_to(w).as_posix(), 'sha256': sha256(index_path), 'bytes': index_path.stat().st_size})
            runs = set()
            source_rows = []
            for a, b, item in sorted(wanted):
                row = unique(index['pairs'], lambda r: (r['a'], r['b'], r['item_id']), (a, b, item))
                expected = f'pair__{a}__{b}__{item}.json'
                if row['file'] != expected:
                    raise ValueError(f'Viewer filename contract mismatch: {row["file"]}')
                prior = [r for r in curated['pairs'] if (r['a'], r['b'], r['item_id']) == (a, b, item)]
                if prior and prior[0] != row:
                    raise ValueError(f'Conflicting pair metadata: {(a, b, item)}')
                if not prior:
                    curated['pairs'].append(row)
                source_rows.append(row)
                runs.update(((a, item), (b, item)))
            for model, item in sorted(runs):
                row = unique(index['runs'], lambda r: (r['model'], r['item_id']), (model, item))
                if row['file'] != f'run__{model}__{item}.json':
                    raise ValueError(f'Viewer filename contract mismatch: {row["file"]}')
                prior = [r for r in curated['runs'] if (r['model'], r['item_id']) == (model, item)]
                if prior and prior[0] != row:
                    raise ValueError(f'Conflicting run metadata: {(model, item)}')
                if not prior:
                    curated['runs'].append(row)
                source_rows.append(row)
                model_meta = index['models'][model]
                public_metadata(model_meta)
                if model in curated['models'] and curated['models'][model] != model_meta:
                    raise ValueError(f'Model key collision: {model}')
                curated['models'][model] = model_meta
            for row in source_rows:
                name = safe_relative(row['file'], flat=True).as_posix()
                capture = read_json(root / name)
                public_metadata(capture)
                if capture.get('schema') != index['schema']:
                    raise ValueError(f'Capture schema mismatch: {name}')
                if name.startswith('run__'):
                    valid = capture['kind'] == 'run' and capture['model']['key'] == row['model'] and capture['item']['item_id'] == row['item_id']
                else:
                    valid = capture['kind'] == 'pair' and all(capture[k] == row[k] for k in ('a', 'b', 'item_id'))
                if not valid:
                    raise ValueError(f'Capture/index identity mismatch: {name}')
                binary = safe_relative(capture['bin'], flat=True).as_posix()
                if binary != name.removesuffix('.json') + '.bin':
                    raise ValueError(f'Unexpected capture binary: {binary}')
                metadata = {'source_file': (root / name).relative_to(w).as_posix()}
                source_digest = capture.get('provenance', {}).get('source_digest')
                if source_digest:
                    metadata['source_digest'] = source_digest
                copy(root / name, 'exports/' + name, 'capture', **metadata)
                copy(root / binary, 'exports/' + binary, 'capture-binary')
                length = (stage / 'exports' / binary).stat().st_size
                for array in capture['arrays'].values():
                    if array['offset'] < 0 or array['nbytes'] < 0 or array['offset'] + array['nbytes'] > length:
                        raise ValueError(f'Array exceeds binary bounds: {name}')
        if len(schemas) != 1:
            raise ValueError('Incompatible source index schemas')
        curated['schema'] = schemas.pop()
        index_target = Path(temp) / 'index.json'
        index_target.write_text(json.dumps(curated, indent=1) + '\n')
        copy(index_target, 'exports/index.json', 'curated-index')
        files = sorted(entries.values(), key=lambda e: e['file'])
        payload = sum(e['bytes'] for e in files)
        if payload > limit:
            raise ValueError(f'Uncompressed payload {payload} exceeds {limit} bytes')
        archive = Path(temp) / 'bundle.tar.gz'
        with tarfile.open(archive, 'w:gz') as tar:
            for entry in files:
                tar.add(stage / entry['file'], arcname=entry['file'], recursive=False)
        compressed = archive.stat().st_size
        if compressed > limit:
            raise ValueError(f'Compressed archive {compressed} exceeds {limit} bytes')
        # Read the actual archive back, including every payload hash; no estimates.
        with tarfile.open(archive, 'r:gz') as tar:
            members = tar.getmembers()
            if [m.name for m in members] != [e['file'] for e in files]:
                raise ValueError('Archive member mismatch')
            for member, entry in zip(members, files):
                stream = tar.extractfile(member)
                h = hashlib.sha256()
                length = 0
                for block in iter(lambda: stream.read(1 << 20), b''):
                    h.update(block)
                    length += len(block)
                if length != entry['bytes'] or h.hexdigest() != entry['sha256']:
                    raise ValueError(f'Archive verification failed: {member.name}')
        manifest = dict(schema='sca2-workbench/deploy-bundle@1', target_max_bytes=limit,
                        payload_bytes=payload, archive_bytes=compressed,
                        archive_sha256=sha256(archive), files=files,
                        source_indexes=source_indexes, story_sources=story['sources'],
                        prompt_features_kept=prompt_features,
                        prompt_features_dropped=dropped_prompt_features,
                        selection_rule='story BASE versus all featured adapters; matching sign prompts only for the largest saved adapter-margin gap per sign bit; default country units; viewer DEFAULT; exact run/pair/binary closure',
                        deploy_status='NOT DEPLOYED')
        manifest_tmp = Path(temp) / 'manifest.json'
        manifest_tmp.write_text(json.dumps(manifest, indent=1) + '\n')
        out.parent.mkdir(parents=True, exist_ok=True)
        # Cross-filesystem safe publication after verification. Existing successful
        # output stays untouched on validation/build failure (not a fallback).
        for source, target in [(archive, out), (manifest_tmp, manifest_path)]:
            with tempfile.NamedTemporaryFile(prefix='.' + target.name, dir=out.parent, delete=False) as f:
                pending = Path(f.name)
                try:
                    with source.open('rb') as inp:
                        shutil.copyfileobj(inp, f)
                    f.flush()
                    os.fsync(f.fileno())
                    os.replace(pending, target)
                finally:
                    pending.unlink(missing_ok=True)
        print(f'bundle: {out} ({compressed} compressed bytes; {payload} payload bytes; {len(files)} files)')
        print(f'manifest: {manifest_path}; NOT DEPLOYED')
    return 0


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--workbench', type=Path, default=HERE)
    ap.add_argument('--out', type=Path)
    ap.add_argument('--max-bytes', type=int, default=MAX_BYTES)
    args = ap.parse_args()
    try:
        raise SystemExit(build_bundle(args))
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        ap.exit(1, f'deploy bundle failed: {exc}\n')
