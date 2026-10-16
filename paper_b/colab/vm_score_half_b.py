# VM-side: launch the whole scoring plan for half B DETACHED: gate, then every condition in priority order.
# colab exec -s pb-b -f paper_b/colab/vm_score_half_b.py --timeout 120
import sys; sys.path.insert(0, "/content/SCA2_PofW/paper_b/colab"); sys.path.insert(0, "/content/SCA2_PofW/paper_b")
from vm_fact_common import launch_detached
import score_plan as SPL
REV = SPL.ADAPTER_REVISION
steps = [("score_gate", ["paper_b/colab/vm_gate_factorial.py"],
          {"GATE_UNIT": "P_1_1_1_1_1_1" if "B" == "A" else "P_0_0_0_0_0_0", "SCA2_PB_ADAPTER_REVISION": REV,
            "SCORE_RUN_ID": "gate-bank2-B-20261016"})]
for cond in SPL.ORDER:
    steps.append((f"score_{cond}_B", ["paper_b/colab/vm_score_units.py", cond, "B"], {}))
launch_detached(steps)
