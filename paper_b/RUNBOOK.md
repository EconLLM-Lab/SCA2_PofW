# Paper B — runbook (frozen protocol 2026-10-09)

> **Updated 2026-10-19.** This runbook records how cohort 1 was trained (2026-10-09 to 10-11). Since 2026-10-15
> the Hugging Face Hub is the only artifact store (`paper_b/hub_io.py`); Drive is an archive. Wherever the steps
> below say Drive or `drivemount`, later runs use the Hub-only launchers in `paper_b/colab/` instead.
> What exists now: [STATUS.md](../STATUS.md).

How we take the 42-country cohort from nothing to trained adapters. Everything is
resumable; any interruption costs at most the in-flight country.

## Machine layout

```
Laptop (control)                    Colab VM (disposable, T4)         Google Drive (durable)
  colab CLI 0.7.4  ──── tunnel ────►  kernel: training + ref pass  ──►  SCA2_paper_b/
  builds paper_b/                     /content/SCA2_PofW (git clone)     prepared/ adapters/ logs/
```

- **Code + bank** come from the git repo (`synthetic_generation/outputs/gps_sign_relabel_all/`
  is tracked) — the VM clones `feat/paper-b-cohort`.
- **Durable state** is Drive only. The VM is disposable.
- **No local keep-alive daemon** (CLI ≥0.7.4 uses backend activity-based liveness), so a
  client disconnect does not kill the VM; results still land on Drive.

## Manual steps that need a human (once)

1. `HF_TOKEN` — the Llama weights are gated. Export it into the kernel before any
   GPU step (kernel restarts wipe env vars).
2. `colab drivemount` — the OAuth consent is interactive.

## Sequence

```bash
# ---- 0. gates (laptop, free) ----
python paper_b/verify_gates.py                 # expect ALL GATES PASS

# ---- 1. provision one T4 ----
colab new -s pb-a --gpu T4
# (mount Drive once per VM)
colab drivemount -s pb-a

# ---- 2. get code + data onto the VM ----
colab exec -s pb-a -f setup_vm.py              # clones repo, pip-installs pinned stack
colab exec -s pb-a -f setenv.py                # exports HF_TOKEN into the kernel

# ---- 3. smoke test (validates the whole path cheaply) ----
colab exec -s pb-a -f smoke_test.py            # GPU check + 2-pair ref pass + gates

# ---- 4. reference cache — ONCE for the cohort (~1052 forward passes) ----
colab exec -s pb-a -f run_refcache.py --timeout 5400

# ---- 5. pilot one country, then measure ----
colab exec -s pb-a -f run_pilot.py --timeout 7200   # ARG, end-to-end

# ---- 6. full batch in two waves (2 sessions max on Pro) ----
colab new -s pb-b --gpu T4                     # second session for wave 2
colab exec -s pb-a -f run_wave1.py --timeout 36000 &
colab exec -s pb-b -f run_wave2.py --timeout 36000 &
# poll:  colab status -s pb-a ; colab status -s pb-b
# a died exec does NOT stop the kernel — check Drive + the tee'd log, then re-run
# the same command (it skips finished countries).

# ---- 7. score the cohort (the Paper B product; reuse the same rocket) ----
colab exec -s pb-a -f paper_b/colab/vm_score.py --timeout 14400
# first, check availability:  python paper_b/score_cohort.py --inventory
#   -> prints hub / Drive / UNION counts. Do not score until UNION is 42/42.
# runs the base-on-CHN GPU gate first and refuses to score if it fails;
# SCORE_ARMS=base,adapter,persona adds the country-named comparator arm

# ---- 8. teardown (units) ----
colab stop -s pb-a ; colab stop -s pb-b ; colab sessions
```

## Scoring stage

`paper_b/score_cohort.py` reproduces the Paper A WVS readout for the 42-country
cohort. Before trusting it, run BOTH gates on the laptop/VM:

- `--gate-cpu` (no GPU, no token): recomputes the archived Paper A population
  distributions and every per-question metric from the archived model
  probabilities. Verified 2026-10-10: population to 1e-16, metrics to 1e-11.
- `--gate` (GPU): re-scores the base model on the CHN grid and must match the
  archived `model_option_probabilities_base_on_CHN.csv`.

Adapter source (changed 2026-10-10). Adapters are now pushed to the HF dataset
repo `Bonorinoa/SCA2-paper-b-adapters` at `adapters/<CC>/` straight from the VM.
`score_cohort.py` resolves each adapter **hub first, Drive second**, downloading
to a local scratch dir (never the Drive FUSE), and records the source per country
in `score_manifest.json`. Run `--inventory` to see the split: while a training run
is live, neither source alone is complete and only the UNION is the truth.

Two fidelity traps this stage pins down:
- the numeric-open grids (Q261/Q262) are the *observed* support inside the
  scored country set — 82/80 on the archived eight, 89/85 on the 42. They are
  not in the 23-item rectangle; the gate pins the archived grid explicitly.
- cells with no valid responses are SKIPPED (Great Britain/ Q174, Egypt/
  Q69-Q71), matching the archived surface, and drop out of the join.

## Cost model

Citable clocks are in `paper_b/compute/publication_estimate.json`, rebuilt by `compute_ledger.py publish`. Each clock names what it includes.

- **Surviving adapters:** `train_minutes` in each `run_record.json` is `trainer.train()` only. Load, save, and upload sit outside it.
- **Ref cache:** `elapsed_min` in the reference manifest is the forward-pass loop after the model has loaded.
- **Score uploads:** Hub commit times bound the span after the first score file lands. They do not include model load or base scoring before that commit.
- **Planning pad:** `vm_status.py` still adds 3 minutes per remaining adapter as an operator pad. That pad is not a measured load and is not a publication number.
- Budget 100 units/mo (T4 ≈ 1 unit/hr on the Colab Pro plan); top-ups $9.99/100. `colab usage` reports a remaining balance, not consumption. Keep the top-up decision with Augusto.

## Resume rules

- Re-running any country command skips countries whose adapter/`run_record.json` exists.
- The ref-cache pass skips `(prompt, completion)` pairs already in the cache file.
- After any crash: sweep orphans (`colab sessions`, unassign `[?]`), then re-run.

## If the laptop sleeps

The VM keeps running (backend liveness). Output streaming stops; recover with
`colab log -s pb-a -o out.md` and read Drive. Do NOT re-launch blindly — the kernel
is likely still training; re-running only after confirming it stopped.
