#!/bin/zsh
# Provision a Paper B scoring VM: create -> setup -> token -> boot (pinned inputs) -> archive upload+check.
#
# Every step must emit its expected marker. A step that produces no marker, or exits non-zero, STOPS the
# script with PROVISION_FAILED. The previous version piped each step through grep with no check, so a
# pruned helper file made the token step a no-op, the boot step fail, and the script still print
# PROVISION_DONE on a half-built VM (2026-10-16: cost ~10 min of T4 and a failing chain).
#
# usage: provision_score_vm.sh <session>
#        PSKIP=new,setup provision_score_vm.sh pb-a     # recover an existing session, re-run the rest
set -u
cd /Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/ || exit 1
S=${1:?usage: provision_score_vm.sh <session> [PSKIP=step,step]}
SCR=/Users/bonorinoa/.hermes/profiles/sca/cache/scratch
ENVF=/Users/bonorinoa/.hermes/profiles/sca/.env
export PATH="$HOME/.local/bin:$PATH"
OUT=$SCR/prov_${S}.out
SKIP="${PSKIP:-}"
mkdir -p "$SCR"

# Refuse before spending a VM. The archive helpers used to live in scratch (pruned after 24h idle, which cost a
# provisioning attempt); since 2026-10-18 they are versioned as paper_b/colab/vm_{mk,check}archive.py.
ARCH=data/phase2/raw/wvs/ksenias_base8/model_option_probabilities_base_on_CHN.csv
for f in paper_b/colab/vm_setup.py paper_b/colab/vm_fact_boot.py paper_b/colab/vm_mkarchive.py \
         paper_b/colab/vm_checkarchive.py "$ARCH"; do
  [ -f "$f" ] || { echo "PROVISION_FAILED missing $f"; exit 1; }
done
grep -q '^HF_TOKEN=' "$ENVF" || { echo "PROVISION_FAILED no HF_TOKEN in $ENVF"; exit 1; }

# The token lives only in .env and in a mode-600 file that exists for the length of this script.
TOKF=$SCR/.setenv_${S}.py
umask 077
python3 - "$ENVF" "$TOKF" <<'PY' || { echo "PROVISION_FAILED could not build the token file"; exit 1; }
import pathlib, sys
envf, outf = sys.argv[1], sys.argv[2]
tok = next(l.split("=", 1)[1].strip().strip("'\"")
           for l in pathlib.Path(envf).read_text().splitlines() if l.startswith("HF_TOKEN="))
pathlib.Path(outf).write_text(
    "import os\n"
    f"os.environ['HF_TOKEN'] = {tok!r}\n"
    "print('HF_TOKEN set:', bool(os.environ.get('HF_TOKEN')))\n")
PY
trap 'rm -f "$TOKF"' EXIT INT TERM

step() {  # step <label> <expected-regex> <cmd...>
  local label=$1 pat=$2; shift 2
  if [[ ",$SKIP," == *",$label,"* ]]; then echo "--- skip $label"; return 0; fi
  : > "$OUT"
  "$@" > "$OUT" 2>&1
  local rc=$?
  grep -v zle "$OUT" | tail -2
  if [ $rc -ne 0 ]; then
    echo "PROVISION_FAILED $S at step '$label': exit $rc"; grep -v "HF_TOKEN' =" "$OUT" | tail -15; exit 1
  fi
  if ! grep -qE "$pat" "$OUT"; then
    echo "PROVISION_FAILED $S at step '$label': no match for /$pat/"
    grep -v "HF_TOKEN' =" "$OUT" | tail -20; exit 1
  fi
}

step new     'Session READY'      env -u PYTHONPATH colab new -s $S --gpu T4
step setup   'SETUP OK'           env -u PYTHONPATH colab exec -s $S -f paper_b/colab/vm_setup.py --timeout 1800
step token   'HF_TOKEN set: True' env -u PYTHONPATH colab exec -s $S -f "$TOKF" --timeout 150
step boot    'BOOT OK'            env -u PYTHONPATH colab exec -s $S -f paper_b/colab/vm_fact_boot.py --timeout 1200
step mkarch  'archive dir'        env -u PYTHONPATH colab exec -s $S -f paper_b/colab/vm_mkarchive.py --timeout 150
step upload  'Uploaded'           env -u PYTHONPATH colab upload -s $S data/phase2/raw/wvs/ksenias_base8/model_option_probabilities_base_on_CHN.csv /content/SCA2_PofW/data/phase2/raw/wvs/ksenias_base8/model_option_probabilities_base_on_CHN.csv
step chkarch 'archive sha256 ok'  env -u PYTHONPATH colab exec -s $S -f paper_b/colab/vm_checkarchive.py --timeout 150
echo PROVISION_DONE $S
