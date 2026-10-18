#!/bin/bash
# Waits for the 8B download, then runs every pass (own process each: per-pass wall time + peak RSS),
# the Paper B parity pass, the analysis and the export. Log: plans/scripts/out/run8b.log
cd "$(dirname "$0")/../.."
O=$HOME/.hermes/profiles/engineer/cache/scratch/s8b
mkdir -p "$O"
while ! grep -q "^SNAPSHOT" plans/scripts/out/dl_8b.log 2>/dev/null; do sleep 20; done
SNAP=$(ls -d $HOME/.cache/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/*)
ITEMS="wvs_Q81 bank_USA_00023ac74dac"
PY="env -u PYTHONPATH uv run --project . --with pandas python"
echo "download done $(date)"
for it in $ITEMS; do for dt in float64 float32; do
  echo "=== capture $it $dt $(date +%T)"
  caffeinate -i $PY plans/scripts/stream8b.py capture --snapshot $SNAP --item $it --dtype $dt --out $O/${it}_${dt}.pt 2>&1 | grep -v "Redirects"
  echo "exit=${PIPESTATUS[0]}"
done; done
echo "=== parity $(date +%T)"
caffeinate -i $PY plans/scripts/stream8b.py parity --snapshot $SNAP --items $ITEMS --out $O/parity.pt 2>&1 | grep -v "Redirects"
echo "exit=${PIPESTATUS[0]}"
echo "=== analyze $(date +%T)"
$PY plans/scripts/analyze8b.py --dir $O --snapshot $SNAP --key llama31_8b --items $ITEMS --export 2>&1 | grep -v "Redirects"
echo "exit=${PIPESTATUS[0]} ALL_DONE $(date)"
