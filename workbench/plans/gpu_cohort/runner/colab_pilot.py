"""CLI exec cell: launch the detached GPU pilot, then attach keepalive.py separately."""
import sys
sys.path.insert(0, "/content/workbench/plans/gpu_cohort/runner")
from vm_job import launch
launch("pilot")
