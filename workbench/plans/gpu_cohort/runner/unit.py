"""One idempotent (model, item) unit, guarded by a 16 GB RSS watchdog."""
import os
from pathlib import Path
import sys

os.environ["PYTHONDONTWRITEBYTECODE"] = "1"
sys.dont_write_bytecode = True
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from sca2_workbench.cohort import main

if __name__ == "__main__":
    main()
