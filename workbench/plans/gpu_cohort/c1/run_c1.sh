#!/bin/bash
# C1: one T4 session. Checked sequence; session always stopped at the end.
set -o pipefail
export PATH="$HOME/.local/bin:$PATH"; unset PYTHONPATH
R=$(cd "$(dirname "$0")/.." && pwd)   # gpu_cohort/, from this script's location
C=$R/c1; OUT=$C/run; mkdir -p "$OUT"; rm -f "$OUT/STOPPED"
S=c1-t4; ENVF=${HF_ENV_FILE:?set HF_ENV_FILE to a file holding one HF_TOKEN=... line (never committed)}
SETENV=$(mktemp "${TMPDIR:-/tmp}/c1setenv.XXXXXX"); chmod 600 "$SETENV"; trap 'rm -f "$SETENV"' EXIT
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$OUT/run.log"; }
fail() { log "FAILED: $*"; colab stop -s "$S" >>"$OUT/run.log" 2>&1; touch "$OUT/STOPPED"; colab usage | tee -a "$OUT/run.log"; exit 1; }
for f in "$R/cohort.tar.gz" "$R/cohort.manifest.json" "$C/vm_c1.py" "$C/decode_check.py" "$R/benchmark/prepare_nf4_bench.py"; do [ -f "$f" ] || { echo MISSING $f; exit 2; }; done
TOK=$(grep -m1 '^HF_TOKEN=' "$ENVF" | cut -d= -f2- | tr -d '"'); [ -n "$TOK" ] || { echo no token; exit 2; }
printf 'import os\nos.environ["HF_TOKEN"] = "%s"\nprint("TOKEN_SET", bool(os.environ["HF_TOKEN"]))\n' "$TOK" > "$SETENV"; unset TOK
log "usage before:"; colab usage | tee -a "$OUT/run.log"
colab sessions 2>&1 | tee "$OUT/sessions_before.txt"
colab new -s "$S" --gpu T4 2>&1 | tee "$OUT/new.log"
[ "${PIPESTATUS[0]}" = 0 ] || { log "provision failed: $(tail -c 500 "$OUT/new.log")"; touch "$OUT/STOPPED"; colab usage | tee -a "$OUT/run.log"; exit 3; }
log "session created"
for pair in "$R/cohort.tar.gz:/content/cohort.tar.gz" "$R/cohort.manifest.json:/content/cohort.manifest.json" "$C/vm_c1.py:/content/vm_c1.py" "$C/decode_check.py:/content/decode_check.py" "$R/benchmark/prepare_nf4_bench.py:/content/prepare_nf4_bench.py"; do
  colab upload -s "$S" "${pair%%:*}" "${pair##*:}" >>"$OUT/run.log" 2>&1 || fail "upload ${pair##*:}"
done
log "uploads done"
colab exec -s "$S" -f "$SETENV" --timeout 120 2>&1 | tee "$OUT/setenv.out" | grep -q TOKEN_SET.True || fail "token step no marker"
rm -f "$SETENV"; log "token set; starting vm_c1"
colab exec -s "$S" -f "$C/vm_c1.py" --timeout 2400 2>&1 | tee "$OUT/vm_c1.out"
log "vm_c1 exec exit ${PIPESTATUS[0]}"
grep -q C1_VM_DONE "$OUT/vm_c1.out" || { colab download -s "$S" /content/c1_out/install.log "$OUT/install.log" >/dev/null 2>&1; fail "no C1_VM_DONE marker"; }
colab download -s "$S" /content/c1_records.tar.gz "$OUT/c1_records.tar.gz" >>"$OUT/run.log" 2>&1; log "records download exit $?"
mkdir -p "$OUT/parts"
colab download -s "$S" /content/c1_parts/PARTS.json "$OUT/parts/PARTS.json" >>"$OUT/run.log" 2>&1 || fail "PARTS.json download"
export S OUT
dl_one() { n=$1; for try in 1 2 3 4; do colab download -s "$S" /content/c1_parts/$n "$OUT/parts/$n" >/dev/null 2>&1 && return 0; sleep 3; done; echo "FAIL $n"; return 1; }
export -f dl_one
python3 -c "import json;print('\n'.join(json.load(open('$OUT/parts/PARTS.json'))['parts']))" | xargs -P 4 -I{} bash -c 'dl_one {}' >>"$OUT/run.log" 2>&1 || fail "parallel part download"
NP=$(ls "$OUT/parts" | grep -c '^part_')
log "parts downloaded: $NP"
python3 - <<PY || fail "part verification"
import hashlib, json, pathlib
d = pathlib.Path("$OUT/parts"); m = json.loads((d/"PARTS.json").read_text())
with open("$OUT/frozen_nf4_t4.tar", "wb") as o:
    for n, h in m["parts"].items():
        b = (d/n).read_bytes(); assert hashlib.sha256(b).hexdigest() == h, n; o.write(b)
assert pathlib.Path("$OUT/frozen_nf4_t4.tar").stat().st_size == m["tar_bytes"]
print("PARTS_VERIFIED", len(m["parts"]))
PY
log "instrument tar reassembled + part hashes verified"
ls -l "$OUT"/*.tar* | tee -a "$OUT/run.log"
log "usage before stop:"; colab usage | tee -a "$OUT/run.log"
colab stop -s "$S" 2>&1 | tee -a "$OUT/run.log"; log "stop exit ${PIPESTATUS[0]}"
touch "$OUT/STOPPED"; colab sessions 2>&1 | tee "$OUT/sessions_after.txt"; colab usage | tee -a "$OUT/run.log"
