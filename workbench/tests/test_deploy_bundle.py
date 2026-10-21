"""Synthetic exports only; no inference, credentials or real payload changes."""
import argparse
import hashlib
import importlib.util
import json
import shutil
import subprocess
import tarfile
import tempfile
from pathlib import Path

import pytest

SPEC = importlib.util.spec_from_file_location(
    "deploy_bundle", Path(__file__).resolve().parents[1] / "scripts/build_deploy_bundle.py"
)
builder = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(builder)
SCRATCH = Path.home() / '.hermes/profiles/engineer/cache/scratch/wb1'


def put(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data))


@pytest.fixture
def fixture(monkeypatch):
    SCRATCH.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=SCRATCH) as temp:
        w = Path(temp) / 'workbench'
        story = {'export': {'src': 'phase1_nf4_t4', 'prompt_src': 'phase1_promptroute_nf4_t4', 'base': 'BASE',
                           'default_units': [{'cc': 'USA', 'item': 'wvs_Q81'}]},
                 'featured': [{'x': 'ARG', 'y': 'BRA', 'item': 'wvs_Q57',
                               'prompt_x': 'PROMPT_arg', 'prompt_y': 'PROMPT_bra'}],
                 'sources': [{'path': 'relative/source.csv', 'sha256': 'a' * 64}]}
        put(w / 'viewer/public/sca2/sca2_data.json', story)
        (w / 'viewer/public/sca2/index.html').write_text('<h1>Story</h1>')
        (w / 'viewer/src').mkdir()
        (w / 'viewer/src/main.ts').write_text('export const DEFAULT = { a: "smol_inst", b: "smol_inst_usa_e3", item: "wvs_Q81" };')
        for name in ['ladder', 'matrix', 'object']:
            p = w / f'viewer/screens/v3/{name}-1440.png'
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(b'synthetic image')
        (w / 'viewer/screens/v3/not-allowed.png').write_bytes(b'not shipped')
        (w / 'viewer/screens/v3/cohort-illustration.png').write_bytes(b'synthetic cohort')
        for folder, pairs in [('', [('smol_inst', 'smol_inst_usa_e3', 'wvs_Q81')]),
                              ('phase1_nf4_t4', [('BASE', 'BASE_arg', 'wvs_Q57'),
                               ('BASE', 'BASE_bra', 'wvs_Q57'), ('BASE', 'BASE_usa', 'wvs_Q81'),
                               ('BASE', 'BASE_unused', 'wvs_Q99')]),
                              ('phase1_promptroute_nf4_t4', [('BASE', 'PROMPT_arg', 'wvs_Q57'),
                               ('BASE', 'PROMPT_bra', 'wvs_Q57')])]:
            root = w / 'exports' / folder
            index = {'schema': 'sca2-workbench/capture@1.1', 'models': {}, 'runs': [], 'pairs': []}
            for a, b, item in pairs:
                for key in [a, b]:
                    index['models'][key] = {'model_id': 'synthetic', 'adapter': None if key == a else 'adapters/test', 'label': key}
                    name = f'run__{key}__{item}.json'
                    if not any(r['file'] == name for r in index['runs']):
                        index['runs'].append({'file': name, 'model': key, 'item_id': item})
                        put(root / name, {'schema': index['schema'], 'kind': 'run', 'model': {'key': key, 'adapter': None}, 'item': {'item_id': item}, 'bin': name.replace('.json', '.bin'), 'arrays': {}, 'provenance': {'source_digest': 'b' * 64}})
                        (root / name.replace('.json', '.bin')).write_bytes(b'\0' * 128)
                name = f'pair__{a}__{b}__{item}.json'
                index['pairs'].append({'file': name, 'a': a, 'b': b, 'item_id': item})
                put(root / name, {'schema': index['schema'], 'kind': 'pair', 'a': a, 'b': b, 'item_id': item, 'arrays': {}, 'bin': name.replace('.json', '.bin')})
                (root / name.replace('.json', '.bin')).write_bytes(b'\0' * 128)
            put(root / 'index.json', index)
        stale = w / 'viewer/dist/stale.txt'
        stale.parent.mkdir(parents=True)
        stale.write_text('old build')
        calls = []

        def npm(command, cwd, check, **kwargs):
            assert command == ['npm', 'run', 'build'] and check
            assert Path(cwd) == w / 'viewer'
            assert not stale.exists()
            calls.append(command)
            dist = w / 'viewer/dist'
            dist.mkdir(exist_ok=True)
            (dist / 'index.html').write_text('<script src="/assets/app.js"></script>')
            (dist / 'assets').mkdir()
            (dist / 'assets/app.js').write_text('/* synthetic static build */')
            shutil.copytree(w / 'viewer/public/sca2', dist / 'sca2')
        monkeypatch.setattr(subprocess, 'run', npm)
        args = argparse.Namespace(workbench=w, out=None, max_bytes=1_500_000_000)
        yield w, args, calls


def test_real_archive_closure_and_manifest(fixture):
    w, args, calls = fixture
    assert builder.build_bundle(args) == 0
    out = w / 'dist/deploy_bundle.tar.gz'
    manifest = json.loads(out.with_suffix('.manifest.json').read_text())
    with tarfile.open(out) as tar:
        files = {m.name: tar.extractfile(m).read() for m in tar if m.isfile()}
    assert calls == [['npm', 'run', 'build']]
    assert set(files) == {e['file'] for e in manifest['files']}
    assert manifest['payload_bytes'] == sum(map(len, files.values()))
    assert manifest['archive_bytes'] == out.stat().st_size
    assert manifest['archive_sha256'] == hashlib.sha256(out.read_bytes()).hexdigest()
    for entry in manifest['files']:
        assert entry['bytes'] == len(files[entry['file']])
        assert entry['sha256'] == hashlib.sha256(files[entry['file']]).hexdigest()
    index = json.loads(files['exports/index.json'])
    assert len(index['pairs']) == 6 and len(index['runs']) == 9
    assert set(index['models']) == {'BASE', 'BASE_arg', 'BASE_bra', 'BASE_usa', 'PROMPT_arg', 'PROMPT_bra',
                                    'smol_inst', 'smol_inst_usa_e3'}
    for row in index['runs'] + index['pairs']:
        name = row['file']
        folder = '' if 'smol_inst' in name else ('phase1_promptroute_nf4_t4' if 'PROMPT' in name else 'phase1_nf4_t4')
        source = w / 'exports' / folder / name
        assert files['exports/' + name] == source.read_bytes()
        binary = json.loads(files['exports/' + name])['bin']
        assert files['exports/' + binary] == (source.parent / binary).read_bytes()
    assert 'screens/v3/ladder-1440.png' in files and 'screens/v3/cohort-illustration.png' in files
    assert not any('unused' in x or 'stale' in x or 'not-allowed' in x for x in files)
    assert len(manifest['source_indexes']) == 3
    assert manifest['story_sources'][0]['sha256'] == 'a' * 64
    assert any(e.get('source_digest') == 'b' * 64 for e in manifest['files'])


@pytest.mark.parametrize('failure', ['binary', 'run', 'pair', 'image', 'absolute', 'traversal', 'oversize', 'npm', 'bounds', 'index-pair', 'story-path', 'symlink'])
def test_fail_closed(fixture, monkeypatch, failure):
    w, args, _ = fixture
    root = w / 'exports/phase1_nf4_t4'
    if failure in {'binary', 'run', 'pair'}:
        prefix = 'pair' if failure == 'pair' else 'run'
        p = next(root.glob(f'{prefix}__*wvs_Q57.json'))
        (p.with_suffix('.bin') if failure == 'binary' else p).unlink()
    elif failure == 'image':
        (w / 'viewer/screens/v3/object-1440.png').unlink()
    elif failure in {'absolute', 'traversal'}:
        p = next(root.glob('run__*wvs_Q57.json'))
        data = json.loads(p.read_text())
        if failure == 'absolute':
            data['model']['adapter'] = {'dir': '/private/local/adapter', 'sha256': 'c' * 64}
        else:
            data['bin'] = '../outside.bin'
        put(p, data)
    elif failure == 'bounds':
        p = next(root.glob('run__*wvs_Q57.json'))
        data = json.loads(p.read_text())
        data['arrays'] = {'test': {'offset': 128, 'nbytes': 4}}
        put(p, data)
    elif failure == 'index-pair':
        p = root / 'index.json'
        data = json.loads(p.read_text())
        data['pairs'] = [r for r in data['pairs'] if r['b'] != 'BASE_arg']
        put(p, data)
    elif failure == 'story-path':
        p = w / 'viewer/public/sca2/sca2_data.json'
        data = json.loads(p.read_text())
        data['sources'][0]['path'] = '/Users/private/source.csv'
        put(p, data)
    elif failure == 'symlink':
        p = next(root.glob('run__*wvs_Q57.bin'))
        target = p.with_suffix('.original')
        p.rename(target)
        p.symlink_to(target)
    elif failure == 'oversize':
        args.max_bytes = 100
    else:
        def fail(*a, **k):
            raise subprocess.CalledProcessError(1, 'npm')
        monkeypatch.setattr(subprocess, 'run', fail)
    with pytest.raises((ValueError, FileNotFoundError, subprocess.CalledProcessError)):
        builder.build_bundle(args)
    assert not (w / 'dist/deploy_bundle.tar.gz').exists()
    assert not (w / 'dist/deploy_bundle.tar.manifest.json').exists()


def test_custom_output_and_rebuild_no_stale_files(fixture):
    w, args, _ = fixture
    args.out = w / 'custom/bundle.tar.gz'
    builder.build_bundle(args)
    (w / 'viewer/dist/injected.txt').write_text('stale')
    builder.build_bundle(args)
    with tarfile.open(args.out) as tar:
        assert 'injected.txt' not in tar.getnames()
    assert args.out.with_suffix('.manifest.json').exists()


def test_compressed_limit_measured_separately(fixture, monkeypatch):
    w, args, _ = fixture
    builder.build_bundle(args)
    out = w / 'dist/deploy_bundle.tar.gz'
    before = out.read_bytes()
    report = out.with_suffix('.manifest.json')
    previous_manifest = report.read_bytes()
    args.max_bytes = json.loads(previous_manifest)['payload_bytes'] + 1
    original_open = tarfile.open

    def uncompressed_gzip(name, mode='r', **kwargs):
        if mode == 'w:gz':
            kwargs['compresslevel'] = 0
        return original_open(name, mode, **kwargs)

    monkeypatch.setattr(tarfile, 'open', uncompressed_gzip)
    with pytest.raises(ValueError, match='Compressed archive'):
        builder.build_bundle(args)
    assert out.read_bytes() == before
    assert report.read_bytes() == previous_manifest
