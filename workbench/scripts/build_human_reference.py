#!/usr/bin/env python3
"""WB7-H: build the descriptive human reference (World Values Survey wave 7, country-level shares).

Reads the weighted country x item x answer table that Paper A/B already computed
(population_response_distributions.csv, local-only, untracked) and writes ONE small aggregate file,
workbench/human_ref/human_reference.json. That file is gitignored; it never holds a respondent row.

  * Items: the seven workbench items (Q43 Q50 Q57 Q81 Q99 Q106 Q176), minus any item in the Paper B held-out pool.
    Held-out data is reached only through freeze.require_freeze(); only the pool's question ids are read.
  * Cells: only countries that have a shipped adapter run for that item (read from the built bundle's index.json).
  * A cell with unweighted n < 100 is dropped and listed.
  * Per cell: share of each answer (whole percent), unweighted n, most chosen answer, and, for ordered items,
    the weighted mean answer (one decimal).
  * --crosscheck recomputes a sample of cells from data/WVS/WVS_wave7.dta (needs pandas; the same coding as
    paper_b/eval_lib.build_population_distributions: weight = W_WEIGHT, valid = answer in the item's codes).

Prints aggregates only (counts), never shares.
"""
import argparse
import csv
import importlib.util
import json
import re
import sys
from collections import defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent          # workbench/
MAIN = Path('/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW')
CSV_DEFAULT = MAIN / 'planning/sprint_2026-10-11/paper-b-20261011/local_eval/population_response_distributions.csv'
DTA_DEFAULT = MAIN / 'data/WVS/WVS_wave7.dta'
HELDOUT = MAIN / 'paper_b/heldout'
ITEMS = ['Q43', 'Q50', 'Q57', 'Q81', 'Q99', 'Q106', 'Q176']
MIN_N = 100
SOURCE = 'World Values Survey wave 7, weighted; country-level shares'
SCHEMA = 'sca2-workbench/human-reference@1'


def heldout_ids(heldout: Path = HELDOUT) -> set:
    """Question ids in the Paper B held-out pool, read only after require_freeze() passes."""
    spec = importlib.util.spec_from_file_location('heldout_freeze', heldout / 'freeze.py')
    freeze = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(freeze)
    payload = freeze.require_freeze(heldout / 'FREEZE.json')
    ids = set()
    with open(payload['pool_path'], newline='') as f:
        ids |= {r['Question'] for r in csv.DictReader(f)}
    with open(payload['selection_path'], newline='') as f:
        ids |= {r['question_id'] for r in csv.DictReader(f)}
    return ids


def shipped_adapters(index_path: Path) -> dict:
    """item id (wvs_Q57) -> set of country codes that have an adapter run in the built bundle's index."""
    index = json.loads(Path(index_path).read_text())
    cc = {}
    for key, m in index['models'].items():
        label = m['label'] if isinstance(m, dict) else str(m)
        hit = re.search(r'\+ ([A-Z]{3}) LoRA', label)
        if hit:
            cc[key] = hit.group(1)
    out = defaultdict(set)
    for r in index['runs']:
        if r['model'] in cc:
            out[r['item_id']].add(cc[r['model']])
    return out


def build(csv_path: Path, index_path: Path, items=ITEMS, heldout: Path = HELDOUT, min_n: int = MIN_N) -> dict:
    pool = heldout_ids(heldout)
    dropped_items = {q: 'in the Paper B held-out pool or selection' for q in items if q in pool}
    keep = [q for q in items if q not in pool]
    ships = shipped_adapters(index_path)
    table = defaultdict(list)
    with open(csv_path, newline='') as f:
        for r in csv.DictReader(f):
            if r['question_id'] in keep:
                table[(r['question_id'], r['eval_country'])].append(r)
    out_items, dropped_cells = {}, []
    for q in keep:
        iid = 'wvs_' + q
        countries = sorted(ships.get(iid, ()))
        if not countries:
            dropped_items[q] = 'no shipped adapter run for this item'
            continue
        cells, meta = {}, None
        for cc in countries:
            rows = sorted(table.get((q, cc), []), key=lambda r: int(r['option_index']))
            if not rows:
                dropped_cells.append({'item': iid, 'country': cc, 'why': 'no survey data'})
                continue
            n = int(rows[0]['n_valid'])
            if n < min_n:
                dropped_cells.append({'item': iid, 'country': cc, 'why': f'n={n} < {min_n}'})
                continue
            codes = [r['option_code'] for r in rows]
            labels = [r['option_label'] for r in rows]
            ordered = rows[0]['is_ordered'] == 'True'
            if meta is None:
                meta = {'codes': codes, 'labels': labels, 'ordered': ordered}
            elif meta['codes'] != codes:
                raise ValueError(f'{iid}: answer codes differ between countries')
            p = [float(r['population_prob']) for r in rows]
            assert abs(sum(p) - 1) < 1e-6, (iid, cc)
            cell = {'n': n, 'shares': {c: round(v * 100) for c, v in zip(codes, p)},
                    'top': codes[max(range(len(p)), key=p.__getitem__)]}
            if ordered:
                cell['mean'] = round(sum(float(r['option_value']) * v for r, v in zip(rows, p)), 1)
            cells[cc] = cell
        if cells:
            out_items[iid] = dict(meta, cells=cells)
    return {'schema': SCHEMA, 'source': SOURCE, 'items': out_items,
            'dropped_cells': dropped_cells, 'dropped_items': dropped_items}


def crosscheck(csv_path: Path, dta: Path, ref: dict, per_item: int = 3) -> tuple[int, int]:
    """Recompute a sample of cells from the .dta (weighted) and compare with the CSV-derived reference."""
    import numpy as np
    import pandas as pd
    codes_of = {iid: [float(c) for c in it['codes']] for iid, it in ref['items'].items()}
    wanted = sorted({'B_COUNTRY_ALPHA', 'W_WEIGHT', *[i.split('_', 1)[1] for i in ref['items']]})
    df = pd.read_stata(dta, columns=wanted, convert_categoricals=False)
    done = bad = 0
    for iid, it in ref['items'].items():
        q = iid.split('_', 1)[1]
        for cc in sorted(it['cells'])[:per_item]:
            sub = df[df['B_COUNTRY_ALPHA'] == cc]
            w = pd.to_numeric(sub['W_WEIGHT'], errors='coerce')
            w = w.where(np.isfinite(w) & (w > 0))
            a = pd.to_numeric(sub[q], errors='coerce')
            valid = a.isin(codes_of[iid]) & w.notna()
            shares = {c: round(float(w[valid & a.eq(float(c))].sum()) / float(w[valid].sum()) * 100) for c in it['codes']}
            cell = it['cells'][cc]
            ok = shares == cell['shares'] and int(valid.sum()) == cell['n']
            if 'mean' in cell:
                ok = ok and round(float((a[valid] * w[valid]).sum() / w[valid].sum()), 1) == cell['mean']
            done += 1
            bad += not ok
    return done, bad


def main(argv=None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--index', type=Path, required=True, help="the built bundle's exports/index.json")
    ap.add_argument('--csv', type=Path, default=CSV_DEFAULT)
    ap.add_argument('--out', type=Path, default=HERE / 'human_ref/human_reference.json')
    ap.add_argument('--crosscheck', type=Path, nargs='?', const=DTA_DEFAULT, help='recompute a sample from the .dta (needs pandas)')
    args = ap.parse_args(argv)
    ref = build(args.csv, args.index)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(ref, indent=1, sort_keys=True) + '\n')
    cells = sum(len(i['cells']) for i in ref['items'].values())
    print(f"human reference: {len(ref['items'])} items, {cells} cells -> {args.out}")
    print('items kept:', ', '.join(f"{k} ({len(v['cells'])} countries)" for k, v in ref['items'].items()) or 'none')
    print('items dropped:', ref['dropped_items'] or 'none')
    print(f"cells dropped (n < {MIN_N} or no data): {len(ref['dropped_cells'])}", ref['dropped_cells'] or '')
    if args.crosscheck:
        done, bad = crosscheck(args.csv, args.crosscheck, ref)
        print(f'cross-check against the .dta: {done} cells recomputed, {bad} differ')
        if bad:
            return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
