"""CLI exec cell: launch Phase 1 only after a remotely verified GPU pilot."""
import sys
sys.path.insert(0, "/content/workbench/plans/gpu_cohort/runner")
from vm_job import launch
launch("cohort")
