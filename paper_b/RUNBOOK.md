# Paper B — runbook (frozen protocol 2026-10-09)

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

# ---- 7. teardown (units) ----
colab stop -s pb-a ; colab stop -s pb-b ; colab sessions
```

## Cost model

- **Ref cache**: 1052 forward passes, one session, ~1 GPU-hour class. Serves all 42.
- **Per adapter**: 526 pairs, 1 epoch, batch 1 × accum 16 → ~33 optimizer steps.
  **Measured by the pilot**, not guessed; the 42-country projection is 42 × pilot-minutes.
- Budget 100 units/mo (T4 ≈ 1 unit/hr); top-ups $9.99/100. Keep the top-up decision with Augusto.

## Resume rules

- Re-running any country command skips countries whose adapter/`run_record.json` exists.
- The ref-cache pass skips `(prompt, completion)` pairs already in the cache file.
- After any crash: sweep orphans (`colab sessions`, unassign `[?]`), then re-run.

## If the laptop sleeps

The VM keeps running (backend liveness). Output streaming stops; recover with
`colab log -s pb-a -o out.md` and read Drive. Do NOT re-launch blindly — the kernel
is likely still training; re-running only after confirming it stopped.
