"""Every live copy of the WVS recode rules must agree with sca2.recodes.

Live scripts are read with ``ast`` (no import, so no data loading or side
effects): the module-level recode sets are evaluated with literal_eval and the
recode function is compiled and run in a small namespace. Synthetic codes only.
"""

import ast
from pathlib import Path

import pandas as pd
import pytest

from sca2 import recodes as R

REPO = Path(__file__).resolve().parents[2]
SET_NAMES = {"INVERT_1_4", "INVERT_10", "BINARY", "BINARY_TRUST"}
# (file, function name)
LIVE = [
    ("paper_b/analyze_surface.py", "recode_value"),
    ("paper_a/06_construct_bridge.py", "recode"),
    ("paper_a/08_twin_geometry_reliability_trust.py", "recode_trust"),
    ("paper_a/10_development_restrictions.py", "recode"),
    ("paper_a/13_unified_comparison.py", "recode_value"),
    ("paper_a/14_report_figures.py", "recode_value"),
    ("paper_a/16_non_llm_baseline.py", "recode"),
    ("paper_a/17_anchor_permutation_placebo.py", "recode"),
    ("paper_a/18_2x2_analysis.py", "recode"),
    ("paper_a/22_paper_a_surface.py", "recode_value"),
]
CODES = [float(c) for c in range(0, 12)]
PAPER_B_ITEMS = [  # items Paper B scores (STRICT_ITEMS plus Q69-71)
    "Q57", "Q58", "Q59", "Q60", "Q61", "Q62", "Q63", "Q64", "Q73", "Q69", "Q70",
    "Q71", "Q43", "Q50", "Q106", "Q107", "Q109", "Q178", "Q81", "Q176", "Q177",
    "Q179", "Q195", "Q99", "Q101", "Q103",
]

# Known, intentional differences: items a script never scores, where it falls
# through to the raw value while sca2.recodes has a rule.
_TRUST_ONLY = {"Q81", "Q177", "Q179", "Q12", "Q13", "Q14", "Q174"}  # 08/17/18: 12 trust items only
ALLOWED_DIFF = {
    # Paper B (locked) never scores Q12-14 / Q174, so it has no rule for them.
    "paper_b/analyze_surface.py": {"Q12", "Q13", "Q14", "Q174"},
    # Paper A surface: strict items + Q69-71 only; no Q12-14.
    "paper_a/22_paper_a_surface.py": {"Q12", "Q13", "Q14"},
    "paper_a/08_twin_geometry_reliability_trust.py": _TRUST_ONLY,
    "paper_a/17_anchor_permutation_placebo.py": _TRUST_ONLY,
    "paper_a/18_2x2_analysis.py": _TRUST_ONLY,
}


def _load(relpath, fname):
    tree = ast.parse((REPO / relpath).read_text())
    ns = {"pd": pd, "np": __import__("numpy")}
    sets = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.module == "sca2.recodes":
            # refactored script: names come from the single source of truth
            for a in node.names:
                ns[a.asname or a.name] = getattr(R, a.name)
                if a.name in {"INVERT_1_4", "INVERT_10", "BINARY"}:
                    sets[a.asname or a.name] = set(getattr(R, a.name))
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            t = node.targets[0]
            if isinstance(t, ast.Name) and t.id in SET_NAMES:
                val = ast.literal_eval(node.value)
                sets[t.id] = set(val)  # dict -> keys
                ns[t.id] = val
            elif isinstance(t, ast.Name) and t.id == fname and isinstance(node.value, ast.Name):
                ns[fname] = ns[node.value.id]  # e.g. recode = recode_value
    fns = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == fname]
    if fns:
        fn = fns[0]
        fn.decorator_list = []
        fn.returns = None  # avoid evaluating annotations
        for a in fn.args.args:
            a.annotation = None
        exec(compile(ast.Module([fn], []), relpath, "exec"), ns)
    assert fname in ns, f"{fname} neither defined nor imported in {relpath}"
    return ns[fname], sets


def _apply(fn, code, item, series_style):
    if series_style:
        return float(fn(pd.Series([code]), item).iloc[0])
    return float(fn(code, item))


SERIES_STYLE = {
    "paper_a/06_construct_bridge.py",
    "paper_a/08_twin_geometry_reliability_trust.py",
    "paper_a/10_development_restrictions.py",
}


def _union_items(sets_by_file):
    items = set(PAPER_B_ITEMS) | R.INVERT_1_4 | R.INVERT_10 | R.BINARY
    for s in sets_by_file.values():
        for v in s.values():
            items |= v
    return sorted(items)


def test_canonical_matches_paper_b_exactly():
    fn, sets = _load("paper_b/analyze_surface.py", "recode_value")
    assert sets["INVERT_1_4"] == set(R.INVERT_1_4)
    assert sets["INVERT_10"] == set(R.INVERT_10)
    assert sets["BINARY"] <= set(R.BINARY)
    for item in PAPER_B_ITEMS:
        for c in CODES:
            assert R.recode_value(c, item) == fn(c, item), (item, c)


def test_q174_is_binary():
    assert R.recode_value(1, "Q174") == 1.0
    assert R.recode_value(2, "Q174") == 0.0


@pytest.mark.parametrize("relpath,fname", LIVE)
def test_live_copy_matches_canonical(relpath, fname):
    fn, sets = _load(relpath, fname)
    assert sets or relpath.endswith("14_report_figures.py"), f"no recode sets in {relpath}"  # 14 only imports recode_value
    items = _union_items({relpath: sets})
    allowed = ALLOWED_DIFF.get(relpath, set())
    bad = []
    for item in items:
        for c in CODES:
            got = _apply(fn, c, item, relpath in SERIES_STYLE)
            want = R.recode_value(c, item)
            if got != want and item not in allowed:
                bad.append((item, c, got, want))
    assert not bad, f"{relpath} diverges from sca2.recodes: {bad[:6]}"


@pytest.mark.parametrize("relpath,fname", LIVE)
def test_allowlist_is_not_stale(relpath, fname):
    """An allowlisted item must actually differ, so the list cannot rot."""
    allowed = ALLOWED_DIFF.get(relpath, set())
    if not allowed:
        return
    fn, _ = _load(relpath, fname)
    for item in allowed:
        diffs = [c for c in CODES
                 if _apply(fn, c, item, relpath in SERIES_STYLE) != R.recode_value(c, item)]
        assert diffs, f"{relpath}: {item} no longer differs; drop it from ALLOWED_DIFF"
