# VM-side: sync code only (git fetch/reset), no pip. Use after the first vm_setup.
# colab exec -s pb-a -f paper_b/colab/vm_sync.py --timeout 300
import subprocess
REPO = "/content/SCA2_PofW"
BRANCH = "feat/paper-b-cohort"
subprocess.check_call(["git", "-C", REPO, "fetch", "origin", BRANCH])
subprocess.check_call(["git", "-C", REPO, "checkout", BRANCH])
subprocess.check_call(["git", "-C", REPO, "reset", "--hard", f"origin/{BRANCH}"])
print("synced:", subprocess.check_output(["git", "-C", REPO, "log", "-1", "--oneline"]).decode().strip())
