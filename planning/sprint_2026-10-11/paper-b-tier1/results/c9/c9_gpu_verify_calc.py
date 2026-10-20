#!/usr/bin/env python3
"""C9-GV verifier calculation (read-only against producer files; no human rows, no secrets).

Run from the repo root:
    env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python \
        planning/sprint_2026-10-11/paper-b-tier1/results/c9/c9_gpu_verify_calc.py

Writes nothing under the repo. Mutation probes run in a scratch copy under $TMPDIR.
Checks:
  1. Independent recomputation of the per-country and pooled recovery/accuracy from the 16-country fixture
     and comparison with c9_label_recovery.json (full precision, no rounding before pooling).
  2. Profile-block bootstrap (country-equal mean over profile clusters), independent implementation.
  3. Presence of any adapter-loading / forward-pass code in paper_b/c9_gpu_jobs.py.
  4. Count of countries/cells in the producer outputs vs the 42 x 132 requirement.
  5. CSV interval-per-row check (a single pooled CI repeated on every country row).
  6. Red-capability: mutants (non-resampling bootstrap; adapter+persona without any loader) vs the producer tests.
"""
import csv, json, math, os, pathlib, random, re, shutil, subprocess, sys, tempfile

ROOT = pathlib.Path(".").resolve()
FIX = ROOT / "analysis/phase2/outputs/gps_reward_recovery_long.csv"
JSN = ROOT / "planning/sprint_2026-10-11/paper-b-tier1/results/c9/c9_label_recovery.json"
CSVO = ROOT / "planning/sprint_2026-10-11/paper-b-tier1/results/c9/c9_label_recovery.csv"
GPUJ = ROOT / "paper_b/c9_gpu_jobs.py"
Z = ROOT / "synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json"
DIMS = ["trust", "risktaking", "patience", "altruism", "posrecip", "negrecip"]
out = []


def say(*a):
    s = " ".join(str(x) for x in a)
    print(s)
    out.append(s)


# ---- 1. independent per-country recompute -------------------------------------------------
cells = {}
with open(FIX, newline="") as f:
    for r in csv.DictReader(f):
        k = (r["bank"], r["model_country"])
        am, rm = float(r["adapter_margin"]), float(r["ref_margin"])
        c = cells.setdefault(k, [0, 0, 0])
        c[0] += 1
        c[1] += am > rm
        c[2] += am > 0
say("fixture groups (bank,country):", len(cells), "cells:", sum(c[0] for c in cells.values()),
    "distinct countries:", len({k[1] for k in cells}), "banks:", sorted({k[0] for k in cells}))
rec = {k: c[1] / c[0] for k, c in cells.items()}
acc = {k: c[2] / c[0] for k, c in cells.items()}
pooled_rec = sum(rec.values()) / len(rec)
pooled_acc = sum(acc.values()) / len(acc)
say(f"independent pooled recovery={pooled_rec:.10f} accuracy={pooled_acc:.10f}")
prod = json.loads(JSN.read_text())
say("producer pooled:", {k: prod["pooled"][k] for k in ("pooled_recovery", "pooled_accuracy", "n_countries", "total_cells")})
mism = []
for r in prod["per_country"]:
    k = (r["bank"], r["country"])
    if abs(r["recovery_rate"] - rec[k]) > 5e-5 or abs(r["accuracy_rate"] - acc[k]) > 5e-5:
        mism.append(k)
say("per-country mismatches beyond 5e-5:", mism)
rounded_max = max(abs(r["recovery_rate"] - rec[(r["bank"], r["country"])]) for r in prod["per_country"])
say(f"producer per-country values are rounded to 4 dp before pooling; max rounding error in recovery = {rounded_max:.2e}")
say(f"pooled from rounded values vs exact: {sum(r['recovery_rate'] for r in prod['per_country'])/16:.10f} vs {pooled_rec:.10f}")

# ---- 2. profile-block bootstrap, independent --------------------------------------------
zv = json.loads(Z.read_text())
prof = {cc: tuple(1 if float(v[d]) > 0 else -1 for d in DIMS) for cc, v in zv.items()}
say("sign-profile clusters over all", len(prof), "countries in z-vector file:", len(set(prof.values())))
ccs = sorted({k[1] for k in cells})
fix_prof = {cc: prof[cc] for cc in ccs}
say("clusters represented among the 16 fixture countries:", len(set(fix_prof.values())),
    "(the task's 26-cluster resample needs all 42 countries)")


def boot(per_cc, seed=20261011, n=2000, country_equal=True):
    groups = {}
    for cc, v in per_cc.items():
        groups.setdefault(fix_prof[cc], []).append(v)
    keys = sorted(groups)
    rng = random.Random(seed)
    s = []
    for _ in range(n):
        picks = [keys[rng.randrange(len(keys))] for _ in keys]
        vals = [v for p in picks for v in groups[p]]
        s.append(sum(vals) / len(vals))
    s.sort()
    return s[int(0.025 * n)], s[int(0.975 * n) - 1]


by_cc_rec = {}
by_cc_acc = {}
for (b, cc), v in rec.items():
    by_cc_rec.setdefault(cc, []).append(v)
    by_cc_acc.setdefault(cc, []).append(acc[(b, cc)])
cc_rec = {cc: sum(v) / len(v) for cc, v in by_cc_rec.items()}
cc_acc = {cc: sum(v) / len(v) for cc, v in by_cc_acc.items()}
say("independent profile-resample CI (recovery) [pooled over 16 countries]:", boot(cc_rec))
say("independent profile-resample CI (accuracy):", boot(cc_acc))
say("producer CI recovery:", prod["pooled"]["recovery_95ci_lower"], prod["pooled"]["recovery_95ci_upper"],
    "accuracy:", prod["pooled"]["accuracy_95ci_lower"], prod["pooled"]["accuracy_95ci_upper"])

# ---- 3. adapter-loading code in the producer driver ----------------------------------------
src = GPUJ.read_text()
pat = r"PeftModel|from_pretrained|load_adapter|safetensors|BitsAndBytes|AutoModelForCausalLM|snapshot_download|hf_hub_download|torch|forward\("
hits = [(i + 1, l.strip()[:90]) for i, l in enumerate(src.splitlines()) if re.search(pat, l)]
say("lines in paper_b/c9_gpu_jobs.py that load a model/adapter or run a forward pass:", hits)
say("subprocess/colab launch code in c9_gpu_jobs.py:", [i + 1 for i, l in enumerate(src.splitlines())
                                                       if re.search(r"subprocess|colab (new|exec|stop)", l) and "print" not in l])

# ---- 4. counts vs requirement --------------------------------------------------------------
say("producer per_country rows:", len(prod["per_country"]), "distinct countries:",
    len({r["country"] for r in prod["per_country"]}), "required: 42 countries x 132 pairs = 5544 cells; got",
    prod["pooled"]["total_cells"])
say("producer run_id in JSON:", prod["run_id"], "| note field says:", prod["note"][:110], "...")

# ---- 5. CSV intervals ----------------------------------------------------------------------
rows = list(csv.DictReader(open(CSVO, newline="")))
ci_pairs = {(r["recovery_95ci_lower"], r["recovery_95ci_upper"]) for r in rows}
say("CSV rows:", len(rows), "| distinct recovery CI pairs across rows:", len(ci_pairs),
    "(1 => one pooled CI stamped on every country row)")

# ---- 6. red-capability (mutation) ---------------------------------------------------------
scratch = pathlib.Path(tempfile.mkdtemp(prefix="c9gv_", dir=os.environ.get("TMPDIR")))
(scratch / "paper_b").mkdir()
for d in ("analysis", "synthetic_generation"):
    os.symlink(ROOT / d, scratch / d)
shutil.copy(ROOT / "paper_b/test_c9_gpu_jobs.py", scratch / "paper_b/")
(scratch / "paper_b/__init__.py").write_text("")


def run_mutant(name, old, new):
    assert old in src, name
    (scratch / "paper_b/c9_gpu_jobs.py").write_text(src.replace(old, new))
    env = {k: v for k, v in os.environ.items() if k != "PYTHONPATH"}
    env["HF_TOKEN"] = ""
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    p = subprocess.run([sys.executable, "-m", "pytest", "paper_b/test_c9_gpu_jobs.py", "-q", "-p", "no:cacheprovider"],
                       cwd=scratch, env=env, capture_output=True, text=True)
    say(f"mutant {name}: pytest exit={p.returncode} ->", p.stdout.strip().splitlines()[-1])


run_mutant("M1 non-resampling bootstrap (picks = every cluster once)",
           "picks = [random.choice(present_clusters) for _ in present_clusters]", "picks = list(present_clusters)")
run_mutant("M2 bootstrap draws=1 constant interval", "draws=2000", "draws=1")
run_mutant("M3 recovery uses accuracy rule (adapter_margin>0) instead of > ref_margin",
           'rec_sum = sum(1 for r in filtered if r["adapter_margin"] > r["ref_margin"])',
           'rec_sum = sum(1 for r in filtered if r["adapter_margin"] > 0)')
run_mutant("M4 adapter+persona wrapper keeps the words but loads nothing (already the case in baseline)",
           '"description": "DECLARED COMPARATOR (C8)', '"description": "DECLARED COMPARATOR (C8)')
shutil.rmtree(scratch, ignore_errors=True)
