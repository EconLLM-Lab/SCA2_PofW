# Drive-free VM entrypoint. Scores synthetic option probabilities only.
# Respondent files are not read and Google Drive is not mounted.
#
# Required environment:
#   HF_TOKEN
#   SCORE_SPEC=/content/paper_b_data/scoring_spec.json
#   SCORE_RUN_ID
#   SCORE_GATE_MARKER=/content/paper_b_data/adapter_gate.json
# Optional:
#   SCORE_COUNTRIES="CHN ARG"
#   SCORE_ADAPTER_REVISION=<40-hex SHA>
#   SCORE_FORCE=1
import os
import subprocess
import sys

REPO = os.environ.get("SCA2_REPO", "/content/SCA2_PofW")
DATA = os.environ.get("SCA2_PB_DATA_ROOT", "/content/paper_b_data")
LOG = os.path.join(DATA, "logs", "score.log")


def require(name):
    value = os.environ.get(name, "").strip()
    if not value:
        print(f"refusing: {name} is required; no model will be loaded")
        sys.exit(2)
    return value


def main():
    token = require("HF_TOKEN")
    spec = require("SCORE_SPEC")
    run_id = require("SCORE_RUN_ID")
    marker = require("SCORE_GATE_MARKER")
    if "/content/drive" in DATA or DATA.startswith("/drive"):
        print("refusing: data root must be local VM disk, not Google Drive")
        sys.exit(2)
    os.makedirs(os.path.dirname(LOG), exist_ok=True)
    cmd = [
        sys.executable, "paper_b/score_cohort.py", "--model-only",
        "--spec-file", spec, "--run-id", run_id, "--gate-marker", marker,
        "--artifact-repo", "Bonorinoa/SCA2-paper-b-artifacts",
    ]
    revision = os.environ.get("SCORE_ADAPTER_REVISION", "").strip()
    if revision:
        cmd.extend(["--adapter-revision", revision])
    countries = os.environ.get("SCORE_COUNTRIES", "").split()
    if countries:
        cmd.extend(["--countries", *countries])
    if os.environ.get("SCORE_FORCE") == "1":
        cmd.append("--force")
    env = dict(os.environ, HF_TOKEN=token, SCA2_PB_DATA_ROOT=DATA, PYTHONUNBUFFERED="1")
    with open(LOG, "a") as handle:
        handle.write(f"\n=== {' '.join(cmd[1:])} ===\n")
        handle.flush()
        rc = subprocess.run(cmd, cwd=REPO, env=env, stdout=handle, stderr=subprocess.STDOUT).returncode
    print("score rc:", rc, "| log:", LOG)
    sys.exit(rc)


if __name__ == "__main__":
    main()
