"""Hold the Colab kernel active while a detached queue runs. Does not provision a VM."""
from pathlib import Path
import time

if __name__ == "__main__":
    root = Path("/content/cohort_state")
    rc = root / "active.rc"
    while not rc.exists():
        print("COHORT_ACTIVE", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), flush=True)
        time.sleep(60)
    print("COHORT_EXIT", rc.read_text().strip(), flush=True)
