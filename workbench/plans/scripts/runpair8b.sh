#!/bin/bash
# First 8B pair (t_df388a80): layer check, 2 pair captures, Paper B parity with the adapter, export.
# Each pass in its own process (per-pass wall time + peak RSS). Log: plans/scripts/out/pair8b.log
cd "$(dirname "$0")/../.."
O=$HOME/.hermes/profiles/engineer/cache/scratch/s8b          # base captures + parity.pt of t_7d7ad93e
SNAP=$(ls -d $HOME/.cache/huggingface/hub/models--meta-llama--Llama-3.1-8B-Instruct/snapshots/*)
AD=$HOME/.cache/huggingface/hub/datasets--Bonorinoa--SCA2-paper-b-adapters/snapshots/$(cat $HOME/.cache/huggingface/hub/datasets--Bonorinoa--SCA2-paper-b-adapters/refs/main)/adapters/USA
ITEMS="wvs_Q81 bank_USA_00023ac74dac"
PY="env -u PYTHONPATH uv run --project . --with pandas python"
S=plans/scripts/pair8b.py
run() { echo "=== $1 $(date +%T)"; shift; caffeinate -i "$@"; echo "exit=$?"; }
echo "start $(date)  snapshot=$SNAP  adapter=$AD"
run layercheck $PY $S layercheck --snapshot $SNAP --adapter $AD --layers 0 15 --out plans/scripts/out/pair8b_layercheck.json
for it in $ITEMS; do
  run "capture $it" $PY $S capture --snapshot $SNAP --adapter $AD --item $it --out $O/pair_${it}.pt
done
run parity $PY $S parity --snapshot $SNAP --adapter $AD --items $ITEMS --out $O/parity_usa.pt
run export $PY $S export --snapshot $SNAP --adapter $AD --items $ITEMS --dir $O
echo "ALL_DONE $(date)"
