#!/bin/bash
# usage: run_device.sh NAME GPU [--high-mem]   (env: B0_ONLY B0_MAC_FIRST B0_SHIP_NF4)
# Checked sequence: every step must exit 0; the session is always stopped at the end.
set -o pipefail
export PATH="$HOME/.local/bin:$PATH"; unset PYTHONPATH
NAME=$1; GPU=$2; HM=$3
R=$(cd "$(dirname "$0")/.." && pwd)   # gpu_cohort/, from this script's location
B=$R/benchmark; OUT=$B/$NAME; mkdir -p "$OUT"; rm -f "$OUT/STOPPED"
SESSION=b0-$NAME
ENVF=${HF_ENV_FILE:?set HF_ENV_FILE to a file holding one HF_TOKEN=... line (never committed)}
SETENV=$(mktemp "${TMPDIR:-/tmp}/b0setenv.XXXXXX"); chmod 600 "$SETENV"
trap 'rm -f "$SETENV"' EXIT
log() { echo "$(date +%H:%M:%S) $*" | tee -a "$OUT/run.log"; }
fail() { log "FAILED: $*"; colab stop -s "$SESSION" >>"$OUT/run.log" 2>&1; touch "$OUT/STOPPED"; colab usage | tee -a "$OUT/run.log"; exit 1; }
# preflight (before spending a VM)
for f in "$R/cohort.tar.gz" "$R/cohort.manifest.json" "$B/vm_all.py" "$B/bench_units.py" "$B/prepare_nf4_bench.py"; do [ -f "$f" ] || { echo "MISSING $f"; exit 2; }; done
TOK=$(grep -m1 '^HF_TOKEN=' "$ENVF" | cut -d= -f2- | tr -d '"')
[ -n "$TOK" ] || { echo "no HF token in env file"; exit 2; }
cat > "$SETENV" <<PY
import os
os.environ["HF_TOKEN"] = "$TOK"
os.environ["B0_LABEL"] = "$NAME"
os.environ["B0_ONLY"] = "${B0_ONLY:-both}"
os.environ["B0_MAC_FIRST"] = "${B0_MAC_FIRST:-}"
os.environ["B0_SHIP_NF4"] = "${B0_SHIP_NF4:-0}"
print("TOKEN_SET", bool(os.environ["HF_TOKEN"]))
PY
unset TOK
log "usage before:"; colab usage | tee -a "$OUT/run.log"
colab sessions 2>&1 | tee "$OUT/sessions_before.txt"
log "colab new $SESSION --gpu $GPU $HM"
colab new -s "$SESSION" --gpu "$GPU" $HM 2>&1 | tee "$OUT/new.log"
[ "${PIPESTATUS[0]}" = 0 ] || { log "provision failed (recorded): $(tail -c 600 "$OUT/new.log")"; touch "$OUT/STOPPED"; colab usage | tee -a "$OUT/run.log"; exit 3; }
log "session created"; date +%s > "$OUT/t_created"
for pair in "$R/cohort.tar.gz:/content/cohort.tar.gz" "$R/cohort.manifest.json:/content/cohort.manifest.json" \
            "$B/vm_all.py:/content/vm_all.py" "$B/bench_units.py:/content/bench_units.py" "$B/prepare_nf4_bench.py:/content/prepare_nf4_bench.py"; do
  colab upload -s "$SESSION" "${pair%%:*}" "${pair##*:}" >>"$OUT/run.log" 2>&1 || fail "upload ${pair##*:}"
done
log "uploads done"
colab exec -s "$SESSION" -f "$SETENV" --timeout 120 2>&1 | tee "$OUT/setenv.out" | grep -q TOKEN_SET.True || fail "token step produced no marker"
rm -f "$SETENV"
log "token set; starting vm_all"
colab exec -s "$SESSION" -f "$B/vm_all.py" --timeout 1500 2>&1 | tee "$OUT/vm_all.out"
log "vm_all exec exit ${PIPESTATUS[0]}"
colab download -s "$SESSION" /content/bench_small.tar.gz "$OUT/bench_small.tar.gz" >>"$OUT/run.log" 2>&1; log "download tar exit $?"
log "usage before stop:"; colab usage | tee -a "$OUT/run.log"
colab stop -s "$SESSION" 2>&1 | tee -a "$OUT/run.log"; log "stop exit ${PIPESTATUS[0]}"
touch "$OUT/STOPPED"
colab sessions 2>&1 | tee "$OUT/sessions_after.txt"; colab usage | tee -a "$OUT/run.log"
[ -f "$OUT/bench_small.tar.gz" ] && (cd "$OUT" && tar xzf bench_small.tar.gz && log "extracted") 
