# IRQ x wvs_Q177: `paper_b_parity` miss is on the float32 reference side

Phase-1 run `exports/phase1_nf4_t4` (frozen T4 NF4 instrument, float64 capture): 988/989 units pass every fatal gate.
IRQ x wvs_Q177 fails one check, `paper_b_parity`: max |p_capture - p_reference| = 1.168e-4 against the absolute tau 1e-4
(`stream_export.py:46-48`). Conservation and the pair export pass.

The reference is an independent HF forward on the same effective weights, hard-coded to float32 (`cohort.py:259-263`).
`irq_q177_reference_probe.py` reruns only that reference, once per precision (2026-10-19, Mac CPU, bnb 0.50.2):

| reference | max abs prob gap to the float64 capture |
|---|---:|
| HF float32 (as the gate ran) | 1.168e-04 (reproduced exactly) |
| HF float64 | 1.573e-06 |

Cohort distribution of the same check: median 4.5e-6, p99 2.9e-5, 1 unit over 1e-4 (this one).

Verdict: the float64 capture is consistent with an independent float64 forward; the miss is float32 rounding in the
reference on a 10-option item with a 0.72 mode. The unit stays FAILED and visibly red: gates are not relaxed after the fact.
Changing `cohort.py` now would also change every unit's `source_digest` and break resume identity for the finished run.

Proposal for the next capture version: run the reference forward in the capture dtype (float64 when capturing float64),
keeping tau = 1e-4; record it as a new instrument version, not a patch to this run.

Reproduce (workbench worktree root): `env -u PYTHONPATH uv run --project workbench --with bitsandbytes==0.50.2 python
workbench/plans/gpu_cohort/diagnostics/irq_q177_reference_probe.py "$PWD/workbench"`
