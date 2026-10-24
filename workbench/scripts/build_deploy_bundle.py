#!/usr/bin/env python3
"""Build (never deploy) a fresh static site and byte-identical capture closure.

Both actual gzip bytes and uncompressed file payload must fit 950,000,000
bytes. The adjacent .tar.manifest.json describes every archive file, not itself.
No model loading, inference, weight copying, or source-capture rewriting occurs.
"""
from __future__ import annotations

import argparse
import copy
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


def resolve_scratch(arg, workbench: Path) -> Path:
    """Stage dir: --scratch, else $SCA2_BUNDLE_SCRATCH, else <workbench>/dist/.bundle-scratch (gitignored).

    Resolved, so a symlinked scratch root (macOS /var -> /private/var) cannot trip the symlink guard.
    """
    chosen = arg or os.environ.get('SCA2_BUNDLE_SCRATCH') or Path(workbench) / 'dist/.bundle-scratch'
    return Path(chosen).expanduser().resolve()


IMAGES = ('v4/ladder-1440.png', 'v4/matrix-1440.png', 'v4/object-1440.png', 'v4/cohort-1440.png',
          'v3/cohort-illustration.png')
Q57_ITEM = 'wvs_Q57'
# A light run keeps every array of the source run except these six (about 19.0 of 21.5 MB).
HEAVY_ARRAYS = ('attn_topk_idx', 'attn_topk_val', 'attn_topk_mass', 'g_last', 'u_last', 'c_last')
# PM decision (WB7-Q, comment 157): a light run also leaves out the two arrays only the 3D object reads.
# neuron_attr (1.8 MB) sums per layer to mlp_attr, which is kept, so the browser re-sum still closes;
# q3_write_norm is read by no 2D view.
LIGHT_DROP = HEAVY_ARRAYS + ('neuron_attr', 'q3_write_norm')
# A pair of a *new* Q57 comparator ships without this array (540,672 of 617,232 bytes), read only by the
# Matrix per-head panel and the 3D object. Pairs already in the v1.4 selection stay byte-identical.
PAIR_DROP = ('d_head_norm',)
PIN = r'export const {}\s*=\s*\{{\s*a:\s*"([^"]+)",\s*b:\s*"([^"]+)",\s*item:\s*"([^"]+)"\s*\}}'


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


def compact_capture(capture: dict, keep, data: bytes, *, light: bool = True) -> tuple[dict, bytes]:
    """A derived capture: only the arrays named in `keep`, re-packed from offset 0.

    The array bytes are copied unchanged and only their offsets move, so every value is identical to
    its source. `bin` points at the new, shorter binary, or is None when no array is kept.
    """
    unpacked = copy.deepcopy(capture)
    arrays, blob, offset = {}, bytearray(), 0
    for name, meta in capture['arrays'].items():
        if name not in keep:
            continue
        chunk = data[meta['offset']:meta['offset'] + meta['nbytes']]
        if len(chunk) != meta['nbytes']:
            raise ValueError(f'Array {name} runs past the source binary')
        arrays[name] = dict(meta, offset=offset)
        blob += chunk
        offset += meta['nbytes']
    unpacked['arrays'] = arrays
    unpacked['bin'] = None if not arrays else capture['bin']
    if light and arrays:
        # Only a derived capture that actually carries the light arrays is a light capture.
        unpacked['light'] = True
    return unpacked, bytes(blob)


def check_light(capture: dict, blob: bytes) -> None:
    """The closure rules of a light run: no heavy array, every array inside the binary, size = table."""
    heavy = set(capture['arrays']) & set(HEAVY_ARRAYS)
    if heavy:
        raise ValueError(f'Light capture lists heavy arrays: {sorted(heavy)}')
    if sum(a['nbytes'] for a in capture['arrays'].values()) != len(blob):
        raise ValueError('Light binary size does not match its array table')
    for name, a in capture['arrays'].items():
        if a['offset'] < 0 or a['nbytes'] < 0 or a['offset'] + a['nbytes'] > len(blob):
            raise ValueError(f'Light array exceeds binary bounds: {name}')


def comparator_identity(model: str, base: str) -> dict:
    """Adapter (country code) or sign prompt (six bits), read from the run key."""
    sign = re.search(r'_base_sp([01]{6})$', model)
    if sign:
        return {'kind': 'sign_prompt', 'bits': sign.group(1)}
    adapter = re.fullmatch(re.escape(base) + r'_([a-z]{3})', model)
    if adapter:
        return {'kind': 'adapter', 'cc': adapter.group(1).upper()}
    raise ValueError(f'Q57 comparator is neither an adapter of {base} nor a sign prompt: {model}')


def check_human_reference(path: Path) -> dict:
    """The human reference holds country-level aggregates only: right schema, no cell under n=100, no row-level keys."""
    if path.is_symlink() or not path.is_file():
        raise FileNotFoundError(f'Missing or symlink human reference: {path}')
    ref = json.loads(path.read_text())
    if ref.get('schema') != 'sca2-workbench/human-reference@1':
        raise ValueError('human reference: unknown schema')
    allowed = {'n', 'shares', 'top', 'mean'}
    cells = 0
    for iid, item in ref['items'].items():
        for cc, cell in item['cells'].items():
            if set(cell) - allowed or cell['n'] < 100 or set(cell['shares']) != set(item['codes']):
                raise ValueError(f'human reference: bad cell {iid}/{cc}')
            cells += 1
    return {'items': len(ref['items']), 'cells': cells, 'source': ref['source']}


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
    scratch = resolve_scratch(getattr(args, 'scratch', None), w)
    scratch.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='deploy-', dir=scratch) as temp:
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

        def write_bytes(payload_bytes: bytes, name, kind, **metadata):
            """Register a file this build derives (never a byte copy of a source file)."""
            target = stage / safe_relative(name)
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(payload_bytes)
            entries[name] = dict(file=name, bytes=len(payload_bytes),
                                 sha256=hashlib.sha256(payload_bytes).hexdigest(), kind=kind, **metadata)

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
            copy(viewer / 'screens' / name, 'screens/' + name, 'image')
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
        # Follow the actual viewer default (required) and teaching pair (optional); each must exist in
        # exactly one export folder, and is shipped from there. Refuse a changed/unrecognizable declaration.
        main = (viewer / 'src/main.ts').read_text()
        default = re.search(PIN.format('DEFAULT'), main)
        if not default:
            raise ValueError('Cannot resolve viewer DEFAULT from src/main.ts')
        teaching = re.search(PIN.format('TEACHING'), main)
        roots = {w / 'exports': set(), source_dir: selected, prompt_source_dir: prompt_selected}
        for pin in [default] + ([teaching] if teaching else []):
            homes = [root for root in roots
                     if any((r['a'], r['b'], r['item_id']) == pin.groups()
                            for r in read_json(root / 'index.json')['pairs'])]
            if len(homes) != 1:
                raise ValueError(f'Viewer pin {pin.groups()} found in {len(homes)} export folders, need exactly 1')
            roots[homes[0]] = roots[homes[0]] | {pin.groups()}
        # ---- Q57 panel (WB7-Q): every comparator of the base on the trust item, for the Cohort tab.
        # A comparator already selected above keeps its full capture. A new one gets its pair without
        # PAIR_DROP and a derived run capture: the light run (every array but LIGHT_DROP)
        # if the byte budget allows, else the run's numbers only (`arrays: {}`, `bin: null`), so the
        # pair's run references still close. Allocation order: country adapters first, then sign
        # prompts, largest |d_margin| first within each group.
        legacy_pairs = {key for wanted in roots.values() for key in wanted}
        legacy_runs = {(a, item) for wanted in roots.values() for a, _, item in wanted}
        legacy_runs |= {(b, item) for wanted in roots.values() for _, b, item in wanted}
        q57_rank, q57_pair = {}, {}
        for group, root in enumerate((source_dir, prompt_source_dir)):
            for row in read_json(root / 'index.json')['pairs']:
                if row['item_id'] != Q57_ITEM:
                    continue
                q57_rank[(row['b'], row['item_id'])] = (group, -abs(row['d_margin']), row['b'])
                q57_pair[(row['b'], row['item_id'])] = row['file']
                roots.setdefault(root, set()).add((row['a'], row['b'], row['item_id']))
        derived = []   # run captures shipped at a reduced tier: numbers now, upgraded to light if it fits
        curated = {'models': {}, 'runs': [], 'pairs': []}
        source_indexes = []
        schemas = set()
        for root, wanted in roots.items():
            if not wanted:
                continue
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
                if name.startswith('run__') and (row['model'], row['item_id']) not in legacy_runs:
                    # A new Q57 comparator: its numbers now; the light arrays are added once the byte
                    # budget is known, so a build that does not fit never writes a file it then drops.
                    numbers, _ = compact_capture(capture, (), b'')
                    body = json.dumps(numbers, separators=(',', ':')).encode()
                    write_bytes(body, 'exports/' + name, 'capture', **metadata)
                    derived.append({'name': name, 'binary': binary, 'capture': capture, 'source_bin': root / binary,
                                    'metadata': metadata, 'model': row['model'], 'item_id': row['item_id'],
                                    'numbers_bytes': len(body)})
                    continue
                if name.startswith('pair__') and (row['a'], row['b'], row['item_id']) not in legacy_pairs:
                    keep = tuple(n for n in capture['arrays'] if n not in PAIR_DROP)
                    slim, blob = compact_capture(capture, keep, (root / binary).read_bytes(), light=False)
                    write_bytes(json.dumps(slim, separators=(',', ':')).encode(), 'exports/' + name, 'capture', **metadata)
                    write_bytes(blob, 'exports/' + binary, 'capture-binary')
                    continue
                copy(root / name, 'exports/' + name, 'capture', **metadata)
                copy(root / binary, 'exports/' + binary, 'capture-binary')
                length = (stage / 'exports' / binary).stat().st_size
                for array in capture['arrays'].values():
                    if array['offset'] < 0 or array['nbytes'] < 0 or array['offset'] + array['nbytes'] > length:
                        raise ValueError(f'Array exceeds binary bounds: {name}')
        if len(schemas) != 1:
            raise ValueError('Incompatible source index schemas')
        curated['schema'] = schemas.pop()
        # ---- index.json lists every Q57 comparator. Its size is counted at the widest spelling (every
        # comparator at the 'numbers' tier), so the final index, written after the allocation, cannot
        # push the payload over the cap.
        identities = {key: comparator_identity(key[0], base) for key in q57_rank}
        full_keys = {(m, i) for m, i in q57_rank if (m, i) in legacy_runs}

        def listing(tiers):
            rows = []
            for key in sorted(q57_rank, key=lambda k: (q57_rank[k][0], str(identities[k].get('cc') or identities[k]['bits']))):
                model, item = key
                tier = tiers.get(key, 'numbers')
                rows.append(dict(model=model, item_id=item, **identities[key], tier=tier, light=tier == 'light',
                                 run=f'run__{model}__{item}.json', pair=q57_pair[key]))
            return rows

        def index_bytes(tiers):
            return (json.dumps(dict(curated, comparators=listing(tiers)), indent=1) + '\n').encode()

        # ---- WB7-H: the optional descriptive human reference (off by default). Counted before the byte budget.
        human = None
        if getattr(args, 'human_reference', None):
            human = check_human_reference(Path(args.human_reference))
            write_bytes(Path(args.human_reference).read_bytes(), 'exports/human_reference.json', 'human-reference')
        widest = len(index_bytes({k: 'numbers' for k in q57_rank if k not in full_keys} | {k: 'full' for k in full_keys}))
        budget = limit - widest - sum(e['bytes'] for e in entries.values())
        # ---- byte budget: upgrade the derived run captures to light runs, in `q57_rank` order
        # (adapters first, then sign prompts). Whatever does not fit keeps its numbers only.
        tiers = {k: 'full' for k in full_keys}
        upgraded = []
        for d in sorted(derived, key=lambda d: q57_rank[(d['model'], d['item_id'])]):
            keep = tuple(n for n in d['capture']['arrays'] if n not in LIGHT_DROP)
            light, blob = compact_capture(d['capture'], keep, d['source_bin'].read_bytes())
            if not blob:
                continue   # nothing to keep: the capture stays numbers only
            check_light(light, blob)
            body = json.dumps(light, separators=(',', ':')).encode()
            extra = len(blob) + len(body) - d['numbers_bytes']
            if extra > budget:
                continue
            write_bytes(body, 'exports/' + d['name'], 'capture', **d['metadata'])
            write_bytes(blob, 'exports/' + d['binary'], 'capture-binary')
            budget -= extra
            tiers[(d['model'], d['item_id'])] = 'light'
            upgraded.append((d, extra, len(blob) + len(body)))
        tiers = {k: tiers.get(k, 'numbers') for k in q57_rank}
        write_bytes(index_bytes(tiers), 'exports/index.json', 'curated-index')
        order = sorted(q57_rank, key=q57_rank.get)
        q57_report = None
        if q57_rank:
            q57_report = {'item': Q57_ITEM, 'comparators': len(q57_rank),
                          'allocation_order': [m for m, _ in order],
                          'shipped_full': sorted(m for m, _ in full_keys),
                          'shipped_light': [m for m, i in order if tiers[(m, i)] == 'light'],
                          'pairs_only': [m for m, i in order if tiers[(m, i)] == 'numbers'],
                          'light_rule': 'every array of the source run except light_drop (the heavy arrays plus the 3D-only ones)',
                          'heavy_arrays': list(HEAVY_ARRAYS),
                          'light_drop': list(LIGHT_DROP),
                          'new_pairs_drop': list(PAIR_DROP),
                          'light_run_bytes': {d['model']: size for d, _, size in upgraded},
                          'upgrade_bytes': sum(extra for _, extra, _ in upgraded),
                          'budget_left_bytes': budget}
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
                        selection_rule=('story BASE versus all featured adapters; matching sign prompts only for the largest '
                                        'saved adapter-margin gap per sign bit; default country units; viewer DEFAULT; '
                                        'every Q57 comparator of the base (all country adapters, then all sign prompts, '
                                        'largest |d_margin| first): its pair without d_head_norm (Matrix per-head detail) and its run as a light run '
                                        '(every array but the six heavy ones, neuron_attr and q3_write_norm) while the 0.95 GB cap allows, else the '
                                        'run numbers only (pairs-only); index.json lists every comparator with its '
                                        'light flag; v1.4 captures stay byte-identical; exact run/pair/binary closure'),
                        q57=q57_report,
                        human_reference=human,
                        deploy_status='NOT DEPLOYED')
        manifest_tmp = Path(temp) / 'manifest.json'
        manifest_tmp.write_text(json.dumps(manifest, indent=1) + '\n')
        if q57_report:
            print(f'Q57: {q57_report["comparators"]} comparators; full {len(q57_report["shipped_full"])}, '
                  f'light {len(q57_report["shipped_light"])}, pairs only {len(q57_report["pairs_only"])}; '
                  f'{q57_report["budget_left_bytes"]} bytes of headroom left')
            print('Q57 light runs (allocation order):', ', '.join(q57_report['shipped_light']) or 'none')
            print('Q57 pairs only (allocation order):', ', '.join(q57_report['pairs_only']) or 'none')
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
    ap.add_argument('--scratch', type=Path, default=None,
                    help='staging dir (default: $SCA2_BUNDLE_SCRATCH, else <workbench>/dist/.bundle-scratch)')
    ap.add_argument('--human-reference', type=Path, default=None,
                    help='WB7-H: copy this aggregate file into the bundle as exports/human_reference.json (off by default)')
    args = ap.parse_args()
    try:
        raise SystemExit(build_bundle(args))
    except (ValueError, OSError, KeyError, subprocess.CalledProcessError) as exc:
        ap.exit(1, f'deploy bundle failed: {exc}\n')
