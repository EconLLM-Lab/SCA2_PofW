# Paper B scorer integration status

2026-10-11. Parent-owned integration after the interrupted worker. No GPU session was started and no score file was uploaded.

## Verified locally

- Full `paper_b` suite: 167 passed.
- `--gate-cpu` still reproduces the archived population and metric surface.
- Real strict spec export: 23 questions, sha256 prefix `ed3bb964b606a163`.
- `score_cohort.py --model-only --dry-run-spec` accepts that spec and exits before loading a model.
- Default CLI now refuses the old population-join path before importing the model.
- Model-only scoring without an adapter-path gate marker exits `BLOCKED` before loading a model.
- `HuggingFaceArtifactStore.commit_files` calls `HfApi.create_commit` with `CommitOperationAdd` for the CSV and manifest together. A fake API exercised that signature. This does not by itself prove a live score upload.
- `paper_b/colab/vm_score.py` no longer points at Google Drive. It requires `HF_TOKEN`, a local spec, a run id, and a gate marker, then calls `--model-only`.

## Still not established

- The exact-weights adapter gate has not been run on a GPU.
- No cohort score has been produced or uploaded.
- A green CLI dry run does not establish that LoRA loading, switching, or probability readout match the archived instrument.
