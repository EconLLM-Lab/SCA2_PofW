# VM-side: verify the ref cache on Drive (coverage + manifest).
import json, os, sys
sys.path.insert(0, "/content/SCA2_PofW/paper_b")
os.environ.setdefault("SCA2_PB_DATA_ROOT", "/content/drive/MyDrive/SCA2_paper_b")
import config as C
from lib import load_country, make_shared_split, response_pair, verify_shared_questions

print("cache file:", C.REF_CACHE_FILE)
print("exists:", C.REF_CACHE_FILE.exists())
if not C.REF_CACHE_FILE.exists():
    raise SystemExit("MISSING")

n = 0
have = set()
vals = []
for line in open(C.REF_CACHE_FILE):
    if line.strip():
        r = json.loads(line)
        have.add((r["prompt"], r["completion"]))
        n += 1
        if len(vals) < 3:
            vals.append(r["ref_logp"])
print("cache rows:", n)
print("unique pairs:", len(have))
print("sample ref_logp:", vals)

# expected coverage
by_prompt_all = {}
for cc in C.COHORT:
    _, bp = load_country(C.BANK_DIR / C.BANK_FILE.format(cc=cc))
    by_prompt_all[cc] = bp
allp = verify_shared_questions(by_prompt_all, C.COHORT[0])
train, ev = make_shared_split(allp, C.TRAIN_FRAC, C.SEED)
pairs = {p: response_pair(by_prompt_all[C.COHORT[0]][p]) for p in allp}
need = {(p, c) for p in train for c in pairs[p]}
print(f"expected train pairs: {len(need)} | missing: {len(need - have)} | extra: {len(have - need)}")

if C.REF_MANIFEST_FILE.exists():
    print("manifest:", json.dumps(json.loads(C.REF_MANIFEST_FILE.read_text()), indent=1)[:600])

print("CACHE OK" if not (need - have) else "CACHE INCOMPLETE")
