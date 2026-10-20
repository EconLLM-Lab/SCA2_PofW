#!/usr/bin/env bash
# Runs the W3b suite with random-matrix stubs injected into w3b.core / w3b.stats.
# Exit status is pytest's: NON-ZERO means the suite detected the stub (expected).
# Zero would mean the suite cannot tell a random stub from the real algebra (bug).
set -u
HERE="$(cd "$(dirname "$0")" && pwd)"
WB="$(cd "$HERE/../../.." && pwd)"                 # workbench/
cd "$WB" || exit 99
W3B_INJECT_STUB=1 env -u PYTHONPATH "$WB/.venv/bin/python" -m pytest analysis/w3b/tests -q -p no:cacheprovider
rc=$?
if [ "$rc" -eq 0 ]; then echo "STUB NOT DETECTED (pytest exit 0)"; else echo "STUB DETECTED (pytest exit $rc)"; fi
exit "$rc"
