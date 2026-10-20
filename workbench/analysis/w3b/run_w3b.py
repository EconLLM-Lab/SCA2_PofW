"""W3b real-weight runner: executes W3b_PREREG.md sections 2-6 on the pinned bank-2 adapters.

Reproduce (from workbench/analysis/):

    env -u PYTHONPATH ../.venv/bin/python -m w3b.run_w3b --out out

Order: (1) pytest on w3b/tests, tee'd into W3b_run.log; any failure -> exit with pytest's code, nothing else
is written.  (2) load all inventoried adapters with sha256 verification (mismatch -> exit 3).  (3) every pair.
(4) primary statistic + permutation null.  (5) reuse analyses.  (6) Hamming vs overlap.  (7) k/d reference.
The pre-registration is only ever read.  Helper functions are import-safe (no work at import time).
"""
from __future__ import annotations

import argparse
import collections
import csv
import hashlib
import json
import platform
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np

from w3b import core, stats

REL_TOL = 1e-6
N_PERM = 10000
SEED_PRIMARY = 20261019
SEED_DEGREE_MATCHED = 20261020
DM_BURN_IN, DM_THIN, DM_DRAWS = 1000, 100, 10000
PROJS = ("q_proj", "k_proj", "v_proj", "o_proj")
EXIT_SHA, EXIT_PIN = 3, 4


# ----------------------------------------------------------------------------- small helpers
def key(a, b):
    return tuple(sorted((a, b)))


def short(mod: str) -> str:
    m = re.search(r"layers\.(\d+)\.self_attn\.(\w+)$", mod)
    return f"L{int(m.group(1)):02d}_{m.group(2)}" if m else mod


def lopo_table(S, one, non, profiles):
    """Prereg 6(2): drop a profile and every pair containing it; T_{-i} and mean S of remaining non-one-bit pairs.

    No p-value (the pre-registration attaches none).  Returns (rows, summary)."""
    rows = []
    for p in profiles:
        one_k = [x for x in one if p not in x]
        non_k = [x for x in non if p not in x]
        rows.append({
            "profile": p,
            "one_bit_pairs_containing": len(one) - len(one_k),
            "one_bit_remaining": len(one_k),
            "non_one_bit_remaining": len(non_k),
            "T_minus_i": float(np.mean([S[x] for x in one_k])) if one_k else None,
            "mean_S_non_one_bit_remaining": float(np.mean([S[x] for x in non_k])) if non_k else None,
        })
    ok = [r for r in rows if r["T_minus_i"] is not None]
    lo = min(ok, key=lambda r: r["T_minus_i"])
    hi = max(ok, key=lambda r: r["T_minus_i"])
    return rows, {"min": lo["T_minus_i"], "min_profile": lo["profile"],
                  "max": hi["T_minus_i"], "max_profile": hi["profile"]}


def find_degree_matched_subset(profiles, pool_edges, degrees):
    """Same exact backtracking as w3b_inventory.exact_degree_matched_feasible (same branching rule and edge
    order), but returns the edge subset it finds (the inventory version returns only a bool).  None if none."""
    need = {p: degrees.get(p, 0) for p in profiles}
    adj = collections.defaultdict(list)
    for a, b in sorted(pool_edges):
        adj[a].append(b)
        adj[b].append(a)
    sys.setrecursionlimit(10000)
    chosen: list = []

    def go(remaining):
        if all(v == 0 for v in need.values()):
            return True
        n = max(need, key=lambda x: need[x])
        if need[n] > sum(1 for b in adj[n] if key(n, b) in remaining and need[b] > 0):
            return False
        for b in sorted(adj[n]):
            e = key(n, b)
            if e in remaining and need[b] > 0:
                need[n] -= 1
                need[b] -= 1
                chosen.append(e)
                if go(remaining - {e}):
                    return True
                chosen.pop()
                need[n] += 1
                need[b] += 1
        return False

    return list(chosen) if go(frozenset(key(*e) for e in pool_edges)) else None


def degree_matched_chain(start_edges, pool_edges, S, n_draws, burn_in, thin, seed, max_proposals=50_000_000):
    """Prereg 6(3): degree-preserving edge-swap chain inside the non-one-bit pool.

    Move: pick two distinct edges (a,b),(c,d) uniformly, orient the second at random, propose
    (a,d),(c,b); accept only if a!=d, c!=b, both new pairs are in the pool and not already in the set.
    burn_in accepted swaps, then draw 1; then `thin` accepted swaps before each further draw.
    Returns (T_star array, info)."""
    pool = {key(*e) for e in pool_edges}
    edges = [key(*e) for e in start_edges]
    inset = set(edges)
    rng = np.random.default_rng(seed)
    n = len(edges)
    state = {"proposals": 0, "accepted": 0}

    def advance(n_accept):
        done = 0
        while done < n_accept:
            state["proposals"] += 1
            if state["proposals"] > max_proposals:
                raise RuntimeError("edge-swap chain exceeded max_proposals (stuck)")
            i, j = rng.choice(n, size=2, replace=False)
            a, b = edges[i]
            c, d = edges[j]
            if rng.integers(2):
                c, d = d, c
            if a == d or c == b:
                continue
            e1, e2 = key(a, d), key(c, b)
            if e1 == e2 or e1 not in pool or e2 not in pool or e1 in inset or e2 in inset:
                continue
            inset.discard(edges[i])
            inset.discard(edges[j])
            edges[i], edges[j] = e1, e2
            inset.add(e1)
            inset.add(e2)
            done += 1
            state["accepted"] += 1

    advance(burn_in)
    out = np.empty(n_draws)
    distinct = set()
    for t in range(n_draws):
        if t:
            advance(thin)
        out[t] = np.mean([S[e] for e in edges])
        distinct.add(frozenset(edges))
    info = {"proposals": state["proposals"], "accepted": state["accepted"],
            "acceptance_rate": state["accepted"] / state["proposals"], "distinct_subsets_drawn": len(distinct)}
    return out, info


def degree_seq(edges):
    c = collections.Counter()
    for a, b in edges:
        c.update((a, b))
    return dict(c)


# ----------------------------------------------------------------------------- logging
class Log:
    def __init__(self, path: Path | None):
        self.fh = open(path, "w") if path else None

    def __call__(self, msg: str = ""):
        print(msg, flush=True)
        if self.fh:
            self.fh.write(msg + "\n")
            self.fh.flush()


def sha256_text(path: Path) -> str:
    return core.sha256_file(path)


def git(args, cwd):
    return subprocess.run(["git", *args], cwd=cwd, capture_output=True, text=True).stdout.strip()


# ----------------------------------------------------------------------------- main
def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="out", help="output dir holding W3b_{inventory,pairs,PREREG} and receiving results")
    ap.add_argument("--skip-tests", action="store_true", help="NOT for the real run (recorded in the log if used)")
    args = ap.parse_args(argv)
    out = Path(args.out).resolve()
    analysis = Path(__file__).resolve().parents[1]
    workbench = analysis.parent
    log = Log(out / "W3b_run.log")
    t0 = time.time()
    command = "cd workbench/analysis && env -u PYTHONPATH ../.venv/bin/python -m w3b.run_w3b " + " ".join(sys.argv[1:] if argv is None else argv)
    log(f"# W3b run  {time.strftime('%Y-%m-%dT%H:%M:%S%z')}\n# command: {command}")

    # ---- step 1: tests
    if args.skip_tests:
        log("# WARNING --skip-tests used; this is not an acceptance run")
    else:
        log("# ===== step 1: pytest analysis/w3b/tests =====")
        cmd = [sys.executable, "-m", "pytest", "analysis/w3b/tests", "-q", "-p", "no:cacheprovider"]
        env = {k: v for k, v in __import__("os").environ.items() if k != "PYTHONPATH"}
        pr = subprocess.run(cmd, cwd=workbench, capture_output=True, text=True, env=env)
        log(pr.stdout + pr.stderr)
        log(f"# pytest exit code: {pr.returncode}")
        if pr.returncode != 0:
            log("# ABORT: tests failed; nothing else written")
            return pr.returncode

    # ---- pins
    inv_p, pairs_p, pre_p = out / "W3b_inventory.json", out / "W3b_pairs.json", out / "W3b_PREREG.md"
    shas = {"inventory": sha256_text(inv_p), "pairs": sha256_text(pairs_p), "prereg": sha256_text(pre_p)}
    pre_text = pre_p.read_text()
    pinned = {n: re.search(rf"{lab}:\s+\S+\s+sha256 ([0-9a-f]{{64}})", pre_text).group(1)
              for n, lab in (("inventory", "Inventory"), ("pairs", "Pairs"))}
    commit_txt = (out / "W3b_PREREG_COMMIT.txt").read_text() if (out / "W3b_PREREG_COMMIT.txt").exists() else ""
    pre_commit_sha = re.search(r"W3b_PREREG.md sha256 ([0-9a-f]{64})", commit_txt)
    pre_commit_sha = pre_commit_sha.group(1) if pre_commit_sha else None
    for n in ("inventory", "pairs"):
        if shas[n] != pinned[n]:
            log(f"# ABORT: {n} sha {shas[n]} != prereg-pinned {pinned[n]}")
            return EXIT_PIN
    if pre_commit_sha != shas["prereg"]:
        log(f"# ABORT: prereg sha {shas['prereg']} != recorded at freeze {pre_commit_sha}")
        return EXIT_PIN
    log(f"# inputs: inventory {shas['inventory']}\n#         pairs     {shas['pairs']}\n#         prereg    {shas['prereg']} (matches freeze record)")

    inv = json.loads(inv_p.read_text())
    prs = json.loads(pairs_p.read_text())
    modules = inv["intersected_modules"]
    dims = inv["intersected_module_dims"]
    profiles = [p["profile_id"] for p in inv["profiles"] if p["status"] == "included"]
    if (len(profiles), len(modules), prs["n_one_bit"], prs["n_non_one_bit"], prs["n_pairs_total"]) != (17, 128, 30, 106, 136):
        log("# ABORT: counts differ from prereg constants (17 profiles / 128 modules / 30 / 106 / 136)")
        return EXIT_PIN

    # ---- step 2: load with sha verification
    log("\n# ===== step 2: load adapters (sha256 verified against inventory) =====")
    adapters, load_rows = {}, []
    for rec in inv["profiles"]:
        pid = rec["profile_id"]
        try:
            ad = core.load_adapter(rec["path"], rec["sha256"], modules=modules)
        except core.ShaMismatchError as e:
            log(f"# ABORT sha mismatch: {e}")
            return EXIT_SHA
        r_set = {v["r"] for v in ad.values()}
        a_set = {v["alpha"] for v in ad.values()}
        row = {"profile": pid, "path": rec["path"], "sha256": rec["sha256"], "n_modules": len(ad),
               "r": sorted(r_set), "alpha": sorted(a_set)}
        if len(ad) != 128 or r_set != {16} or a_set != {32.0}:
            log(f"# ABORT: {pid} modules/r/alpha {row} differ from prereg (128 / 16 / 32)")
            return EXIT_PIN
        adapters[pid] = ad
        load_rows.append(row)
        log(f"{pid}  sha256={rec['sha256']}  modules={len(ad)}  r={row['r'][0]}  alpha={row['alpha'][0]:g}  path={rec['path']}")

    # ---- step 3: every pair
    log("\n# ===== step 3: all 136 pairs (rel_tol=1e-6, unweighted mean over 128 modules) =====")
    rows, S = [], {}
    k_all = []
    for n, p in enumerate(prs["pairs"], 1):
        a, b = p["a"], p["b"]
        res = core.pair_overlap(adapters[a], adapters[b], modules, rel_tol=REL_TOL)  # default aggregate = unweighted mean
        per = res["per_module"]
        ov = {m: per[m]["overlap"] for m in modules}
        ang = {m: per[m]["min_angle"] for m in modules}
        by_proj = {pj: float(np.mean([ov[m] for m in modules if m.endswith(pj)])) for pj in PROJS}
        ref = float(np.mean([max(per[m]["k_x"], per[m]["k_y"]) / dims[m]["d_out"] for m in modules]))
        k_all += [per[m]["k_x"] for m in modules] + [per[m]["k_y"] for m in modules]
        S[key(a, b)] = res["aggregate"]
        rows.append({"a": a, "b": b, "hamming": p["hamming"], "one_bit": p["label"] == "one_bit",
                     "differing_bit": p["differing_bit"], "aggregate_overlap": res["aggregate"],
                     "smallest_angle_rad": res["min_angle"], "smallest_angle_deg": float(np.degrees(res["min_angle"])),
                     "mean_theta_min_rad": float(np.mean(list(ang.values()))),
                     "overlap_by_projection": by_proj, "random_reference_pair": ref,
                     "per_module_overlap": ov, "per_module_min_angle_rad": ang,
                     "per_module_k": {m: [per[m]["k_x"], per[m]["k_y"]] for m in modules}})
        if n % 10 == 0 or n == len(prs["pairs"]):
            log(f"  pair {n:3d}/{len(prs['pairs'])}  {a} ~ {b}  ham={p['hamming']}  S={res['aggregate']:.6f}  [{time.time() - t0:.0f}s]")
    dropped = sum(1 for k in k_all if k == 0)  # core raises on k=0, so this is 0 by construction
    k_summary = {"min": int(min(k_all)), "max": int(max(k_all)), "n_modules_dropped_zero_rank": dropped}
    log(f"# realised k per module: min {k_summary['min']}, max {k_summary['max']}; zero-rank modules dropped: {dropped}")

    one = [key(p["a"], p["b"]) for p in prs["pairs"] if p["label"] == "one_bit"]
    non = [key(p["a"], p["b"]) for p in prs["pairs"] if p["label"] == "non_one_bit"]

    # ---- step 4: primary statistic + permutation null (stats.permutation_null; draws rng.choice(106,30,replace=False) in order)
    log("\n# ===== step 4: primary statistic and permutation null =====")
    pn = stats.permutation_null(S, one, non, N_PERM, SEED_PRIMARY)
    null = pn["null"]
    T = pn["observed"]
    primary = {"T": T, "p_one_sided_greater": pn["p_value"], "n_perm": N_PERM, "seed": SEED_PRIMARY,
               "n_one_bit": pn["n_one_bit"], "n_pool": pn["n_pool"],
               "null_mean": float(null.mean()), "null_sd": float(null.std(ddof=1)),
               "null_q025": float(np.quantile(null, 0.025)), "null_q975": float(np.quantile(null, 0.975)),
               "T_minus_null_mean": float(T - null.mean()), "n_null_ge_T": int(np.sum(null >= T)),
               "mean_S_non_one_bit_pool": float(np.mean([S[x] for x in non]))}
    log(f"  T = {T:.8f}   null mean {primary['null_mean']:.8f} sd {primary['null_sd']:.8f}   "
        f"q2.5/97.5 {primary['null_q025']:.8f}/{primary['null_q975']:.8f}")
    log(f"  #(null >= T) = {primary['n_null_ge_T']}   p (one-sided, +1) = {primary['p_one_sided_greater']:.6f}")

    # ---- step 5: reuse analyses
    log("\n# ===== step 5: pair-reuse analyses =====")
    reuse = stats.profile_reuse_counts(one)
    if reuse != prs["one_bit_reuse_per_profile"]:
        log("# ABORT: reuse counts differ from W3b_pairs.json")
        return EXIT_PIN
    lopo_rows, lopo_sum = lopo_table(S, one, non, profiles)
    for r in lopo_rows:
        log(f"  drop {r['profile']}  one-bit pairs lost {r['one_bit_pairs_containing']}  T_-i={r['T_minus_i']:.6f}  mean S non-one-bit={r['mean_S_non_one_bit_remaining']:.6f}")
    log(f"  LOPO T_-i range: {lopo_sum['min']:.6f} ({lopo_sum['min_profile']}) .. {lopo_sum['max']:.6f} ({lopo_sum['max_profile']})")

    deviations = [{
        "id": "D1", "kind": "task_text_vs_prereg",
        "what": "Task step 5 asks for a LOPO p-value per profile. W3b_PREREG.md section 6(2) says 'No p-value' and section 5 says "
                "'No other p-value is computed'. The binding pre-registration wins: no LOPO p-values were computed.",
        "effect": "lopo.rows hold T_-i and mean S of remaining non-one-bit pairs, with min/max; p-values absent. "
                  "stats.leave_one_profile_out (which would compute them) was not called. Adding them is an exploratory, "
                  "dated addition that needs Augusto's decision."}]
    dm_edges = find_degree_matched_subset(profiles, set(non), reuse)
    degree_matched: dict
    if prs["degree_matched_null_feasible_exact_search"] is not True:
        degree_matched = {"run": False, "reason": "prereg 6(3): feasibility not established by exact search"}
        log("  degree-matched null: NOT RUN (infeasible)")
    elif dm_edges is None or degree_seq(dm_edges) != reuse or len(dm_edges) != 30 or not set(dm_edges) <= set(non):
        log("# ABORT: prereg says degree-matched start subset is feasible but re-search failed")
        return EXIT_PIN
    else:
        log(f"  degree-matched start subset found ({len(dm_edges)} edges, degrees == one-bit degrees); chain: burn-in {DM_BURN_IN}, "
            f"thin {DM_THIN}, draws {DM_DRAWS}, seed {SEED_DEGREE_MATCHED}")
        t1 = time.time()
        dm_null, info = degree_matched_chain(dm_edges, non, S, DM_DRAWS, DM_BURN_IN, DM_THIN, SEED_DEGREE_MATCHED)
        p_dm = (1 + int(np.sum(dm_null >= T))) / (DM_DRAWS + 1)
        degree_matched = {"run": True, "start_subset": [list(e) for e in dm_edges],
                          "start_subset_T": float(np.mean([S[e] for e in dm_edges])),
                          "burn_in_accepted": DM_BURN_IN, "thin_accepted": DM_THIN, "n_draws": DM_DRAWS, "seed": SEED_DEGREE_MATCHED,
                          "p_one_sided_greater": p_dm, "n_null_ge_T": int(np.sum(dm_null >= T)),
                          "null_mean": float(dm_null.mean()), "null_sd": float(dm_null.std(ddof=1)),
                          "null_q025": float(np.quantile(dm_null, 0.025)), "null_q975": float(np.quantile(dm_null, 0.975)),
                          "chain": info, "null_samples": [float(x) for x in dm_null],
                          "agrees_with_primary_on_p_lt_0.05": bool((p_dm < 0.05) == (pn["p_value"] < 0.05)),
                          "note": "connectivity/mixing not proven (prereg 6(3)); allowed to disagree with primary; disagreement is reported not resolved. "
                                  "Unspecified in prereg and chosen here: pair of edges chosen uniformly, second edge's orientation random; "
                                  "draw 1 taken right after burn-in."}
        log(f"  degree-matched: null mean {degree_matched['null_mean']:.8f} sd {degree_matched['null_sd']:.8f}  p = {p_dm:.6f}  "
            f"accept rate {info['acceptance_rate']:.3f}  distinct subsets {info['distinct_subsets_drawn']}  [{time.time() - t1:.0f}s]")

    # ---- step 6: Hamming vs overlap (descriptive only)
    by_h = collections.defaultdict(list)
    for r in rows:
        by_h[r["hamming"]].append(r["aggregate_overlap"])
    ham = {"descriptive_only": True,
           "points": [{"a": r["a"], "b": r["b"], "hamming": r["hamming"], "aggregate_overlap": r["aggregate_overlap"]} for r in rows],
           "by_hamming": {str(h): {"n": len(v), "mean": float(np.mean(v)), "sd": float(np.std(v, ddof=1)) if len(v) > 1 else None,
                                   "min": float(min(v)), "max": float(max(v))} for h, v in sorted(by_h.items())}}
    log("\n# ===== step 6: aggregate overlap by Hamming distance (descriptive) =====")
    for h, d in ham["by_hamming"].items():
        log(f"  hamming {h}: n={d['n']:3d}  mean={d['mean']:.6f}  min={d['min']:.6f}  max={d['max']:.6f}")

    # ---- step 7: random-subspace reference
    ref_pair = [r["random_reference_pair"] for r in rows]
    nominal = {pj: 16 / next(dims[m]["d_out"] for m in modules if m.endswith(pj)) for pj in PROJS}
    kd = {"definition": "prereg section 4: E[O] = max(k1,k2)/d_out per module; aggregate = unweighted mean over the 128 modules",
          "nominal_k16_by_projection": nominal,
          "nominal_k16_aggregate": float(np.mean([16 / dims[m]["d_out"] for m in modules])),
          "realised_aggregate_mean_over_pairs": float(np.mean(ref_pair)),
          "realised_aggregate_min_max_over_pairs": [float(min(ref_pair)), float(max(ref_pair))]}
    log(f"\n# k/d reference: nominal aggregate {kd['nominal_k16_aggregate']:.5f} (q,o {nominal['q_proj']:.5f}; k,v {nominal['k_proj']:.5f}); "
        f"realised {kd['realised_aggregate_mean_over_pairs']:.5f}")

    # ---- write outputs
    commit = git(["rev-parse", "HEAD"], workbench)
    dirty = git(["status", "--porcelain", "--", "analysis/w3b"], workbench)
    pre_dirty = git(["status", "--porcelain", "--", "analysis/out/W3b_PREREG.md"], workbench)
    results = {
        "task": "t_7fd92a07 (W3b real-weight run)", "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "command": command, "git_commit": commit, "w3b_code_dirty": bool(dirty), "prereg_file_dirty_vs_git": bool(pre_dirty),
        "environment": {"python": platform.python_version(), "numpy": np.__version__, "platform": platform.platform()},
        "constants": {"rel_tol": REL_TOL, "n_perm": N_PERM, "seed_primary": SEED_PRIMARY, "seed_degree_matched": SEED_DEGREE_MATCHED,
                      "n_modules": len(modules), "r": 16, "alpha": 32, "aggregation": "unweighted mean over 128 modules"},
        "input_sha256": {"inventory": shas["inventory"], "pairs": shas["pairs"], "prereg": shas["prereg"],
                         "prereg_frozen_at_commit_file": pre_commit_sha,
                         "adapters": {r["profile"]: r["sha256"] for r in load_rows}},
        "adapters_loaded": load_rows, "k_summary": k_summary,
        "pairs": rows,
        "primary": primary, "null_samples": [float(x) for x in null],
        "reuse": {"counts_one_bit": reuse, "lopo": {"rows": lopo_rows, "range": lopo_sum}, "degree_matched": degree_matched},
        "k_over_d": kd, "hamming_vs_overlap": ham,
        "deviations": deviations,
        "interpretation_scope": "prereg section 7: answers the single one-bit-vs-farther overlap question only; not a mechanism claim",
    }
    tmp = out / "W3b_results.json.tmp"
    tmp.write_text(json.dumps(results, indent=1))
    tmp.replace(out / "W3b_results.json")
    cols = ["a", "b", "hamming", "one_bit", "differing_bit", "aggregate_overlap", "smallest_angle_rad", "smallest_angle_deg",
            "mean_theta_min_rad", "overlap_q_proj", "overlap_k_proj", "overlap_v_proj", "overlap_o_proj", "random_reference_pair"]
    with open(out / "W3b_per_pair.csv", "w", newline="") as fh:
        w = csv.writer(fh)
        w.writerow(cols + [f"ov_{short(m)}" for m in modules])
        for r in rows:
            w.writerow([r[c] if c in r else "" for c in cols[:9]] + [r["overlap_by_projection"][pj] for pj in PROJS]
                       + [r["random_reference_pair"]] + [r["per_module_overlap"][m] for m in modules])
    log("\n# ===== final summary =====")
    log(f"  T={T:.8f}  p={primary['p_one_sided_greater']:.6f}  (null mean {primary['null_mean']:.8f}, sd {primary['null_sd']:.8f})")
    if degree_matched.get("run"):
        log(f"  degree-matched p={degree_matched['p_one_sided_greater']:.6f}")
    log(f"  LOPO T_-i range {lopo_sum['min']:.6f}..{lopo_sum['max']:.6f}   deviations: {len(deviations)}")
    log(f"  git commit {commit}  w3b code dirty: {bool(dirty)}   prereg dirty vs git: {bool(pre_dirty)}")
    log(f"  wrote {out/'W3b_results.json'}\n        {out/'W3b_per_pair.csv'}\n        {out/'W3b_run.log'}  ({time.time() - t0:.0f}s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
