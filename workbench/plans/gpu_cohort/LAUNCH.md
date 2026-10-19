# Phase 1 launch, monitor, resume and abort

> **Executed path (2026-10-18/19): the Mac, not Colab.** After the device benchmark
> (`benchmark/BENCHMARK.md`), Augusto ran the cohort locally on the frozen T4 instrument
> (`frozen_nf4_t4/`) with `runner/mac_queue.py --local`. The exact command is in `c2_launch_cmd.txt`;
> the outcome is in `../../AUDIT.md` §16 (988/989 pass, 0 CU). The Colab A100 steps below
> are the documented alternative. They were reviewed (A4 GO for the pilot) but never executed.
> If you use them, read A4 F1 and F3 first.

For Augusto to execute AFTER A4 review and a spending decision. A3 has NOT run
these GPU commands. Scientific target is decided: nf4_dequant. The private store
is 401 from this worker; real Hub writes and the CUDA bootstrap must pass on the
VM. CPU-green is not permission to skip the GPU pilot.

## 0. Read-only / local preflight, before spending

From the worktree root:

    cd "$(git rev-parse --show-toplevel)"   # the Adapter-Brain-Vizualization worktree root
    export P=workbench/plans/gpu_cohort
    export SESSION=wb-cohort-a100
    env -u PYTHONPATH uv run --project workbench python "$P/runner/bootstrap.py" --check-local
    env -u PYTHONPATH uv run --project workbench --with bitsandbytes==0.50.2 --with psutil pytest workbench/tests -q --basetemp "$P/test_tmp_acceptance"
    npm --prefix workbench/viewer run build
    env -u PYTHONPATH colab sessions

Checklist (do not substitute a successful CLI exit for the expected marker):

- A4 findings accepted; DECISIONS.md names Augusto's NF4 choice, not PENDING.
- `models.json`: 43 models / 42 cohort-1 adapters, pinned SHA/config hashes.
  `items.json`: 23 strict questions, model-only archive rows; no human data.
- Review `ESTIMATE.md`. The current NO-SPEEDUP envelope is ~30.31 A100 h /
  ~396.47 CU at an assumed 13.08 CU/h (`estimate.json`, rebuilt by
  `runner/estimate.py`). This exceeds a nominal 100-CU allowance, so the ONLY spend
  this document authorizes before a budget review is the pilot in step 1
  (envelope 24.66 CU, caps below). Read live balance/rate in Colab and note the
  starting balance; this worker did not inspect or spend it.
- The new output prefix in `runner/colab_setup.py` is
  `workbench_cohort/phase1_nf4_20261018_a3`. For changed code, weights, dtype, item
  set or quantization instrument, choose a NEW prefix before bundling. Do not
  overwrite an earlier run or anything under adapters/<CC>.
- Colab secret `HF_TOKEN` present AND `whoami` OK. In Colab Secrets,
  create/authorize `HF_TOKEN` with gated-Llama read and private artifact-dataset
  WRITE scope; enable notebook access. Never put the value into a script, tarball,
  command line, chat, or another profile's env file. The VM entry point is
  `userdata.get("HF_TOKEN")`. This cannot be tested without a runtime, so
  `colab_setup.py` checks both first: it raises "Colab secret HF_TOKEN missing"
  (`bootstrap.py:33`) and calls `HfApi.whoami()` (`bootstrap.py:70`), before it
  prints `DURABLE_PREFLIGHT_PASS`. A 401/403 there is a failed preflight: abort.
  (The 401 on the private artifacts repo seen from the Mac is expected; the Mac
  has no token.)
- Do not stop or commandeer a session listed for someone else's job. This task
  permits only one model process at a time, with decimal 16 GB resident-RAM stop.
- Plan >=100 GB free VM disk and enough remote quota. Bootstrap proves destination
  write/read capability before loading the model; quota capacity still needs an
  account-side check. A100 availability, driver compatibility and package download
  availability must be checked on the real VM, not inferred from this Mac.

Build the final uncommitted code bundle only after the last patch:

    env -u PYTHONPATH uv run --project workbench python "$P/runner/bundle.py" --out "$P/cohort.tar.gz"

This creates `cohort.tar.gz` and `cohort.manifest.json`. The strict allowlist
contains workbench Python source, runners, model/item registry, calibrated gates
and estimate. No .env, credentials, respondent files, paper_b modules, local
weights, prior exports, caches or source-control metadata are included. Source
identity is the actual file hash manifest, not an invented git commit for this
uncommitted package. Keep both files together.

## 1. A100 pilot: setup, then ARG x all 23 items, with a CU cap

Step 1 is the pilot and nothing else. It replaces the no-speedup envelope with
measured A100 numbers before any cohort budget is committed. Pilot = NF4 base x 23
items + ARG x 23 items = 46 units (`ESTIMATE.md`, "A100 pilot"). Caps:

- queue cap in code: stops between units above 35 CU of queue time
  (`runner/vm_job.py` PILOT_MAX_CU);
- session cap by you: stop the runtime if the Colab balance has fallen by more
  than 50 CU since `colab new` (2x the 24.66 CU envelope, setup included).

The following starts paid compute; it was NOT executed by A3:

    env -u PYTHONPATH colab new -s "$SESSION" --gpu A100 --high-mem
    env -u PYTHONPATH colab upload -s "$SESSION" "$P/cohort.tar.gz" /content/cohort.tar.gz
    env -u PYTHONPATH colab upload -s "$SESSION" "$P/cohort.manifest.json" /content/cohort.manifest.json
    env -u PYTHONPATH colab exec -s "$SESSION" -f "$P/runner/colab_setup.py" --timeout 3600

Stop on the FIRST failure. Require all of:

    LOCAL_PREFLIGHT_PASS
    GPU ... A100 ...
    NF4_REMOTE_VERIFIED <commit>   (or NF4_RESTORED 224 on a recovery)
    DURABLE_PREFLIGHT_PASS
    PROVISION_DONE

Setup verifies the bundle/file hashes, installs separate pinned preparation and
capture interpreters, obtains the Colab secret, verifies the destination, runs
the frozen production NF4 loader on the A100, persists all 224 quantized Linear
code/state files, then reads the exact remote commit back and hashes it. No
Drive mount is needed. It records actual CUDA/driver/package metadata.

If setup is quiet, inspect its state/log before retrying. Do not attach the
keepalive while setup execs remain: a busy keepalive queues every later exec.
A package/version/hardware/401/403 failure is a failed preflight, not a reason to
switch model, GPU or precision silently. Abort the paid runtime below.

### 1b. Start the pilot

    env -u PYTHONPATH colab exec -s "$SESSION" -f "$P/runner/colab_pilot.py" --timeout 120
    env -u PYTHONPATH colab exec -s "$SESSION" -f "$P/runner/keepalive.py" --timeout 3600

`colab_pilot.py` detaches the queue on the VM. The keepalive is a SEPARATE blocking
exec, attached only after setup and launch return. It prints a liveness line each
minute and exits when `/content/cohort_state/active.rc` exists. The pilot is NF4
base + ARG on all 23 items (46 units). A quiet/idle kernel does not prove a detached job stopped;
check logs and durable markers. A dead keepalive client likewise does not prove
the VM died; check `colab sessions` and the Hub.

In a SECOND local terminal while keepalive is busy (no queued kernel exec):

    env -u PYTHONPATH colab sessions
    env -u PYTHONPATH colab download -s "$SESSION" /content/cohort_state/pilot.log "$P/pilot_remote.log"
    env -u PYTHONPATH colab download -s "$SESSION" /content/cohort_state/pilot.rc "$P/pilot_remote.rc"
    env -u PYTHONPATH uv run --project workbench python "$P/runner/monitor.py" --prefix workbench_cohort/phase1_nf4_20261018_a3

A missing .rc while the log advances means still running. Require `PILOT_DONE`, `monitor.py`
reporting `"done": 46, "failed": 0` (its `expected: 989` is the full cohort, not
the pilot), remote per-unit digest verification and rc 0; a `colab exec` wrapper returning 0
alone is NOT proof. The archive's report-only parity (tau = 4 fp16 ulp) can fail without making
conservation fail; read it honestly. A fatal gate failure or OOM is an abort.

## 2. Pilot review gate (no GPU spend)

After `PILOT_DONE`, either stop the session (idle bills; a later restart repeats
setup, assumed 0.5 h, and restores the frozen NF4 from the Hub) or keep it only if
the budget decision is immediate. Stop command, if stopping:

    env -u PYTHONPATH colab stop -s "$SESSION"

Before scale: inspect the pilot attempt `.rc.json` and timing JSONs in the Hub
prefix, recompute estimate seconds/hours/CU using actual CUDA timing and actual
upload/readback speed, and have Augusto approve the spend. Do not just divide
Mac time by a theoretical A100 speedup. The current runner retains the conservative
103.519 s per-unit allowance (stop above 207.039 s); if replacing that allowance,
update `estimate.json`, rebuild/upload the bundle and re-check the new bundle
manifest before launch. Estimate changes do not change capture source identity.

## 3. Launch Phase 1, only after the pilot review gate and Augusto's budget approval

    env -u PYTHONPATH colab exec -s "$SESSION" -f "$P/runner/colab_cohort.py" --timeout 120
    env -u PYTHONPATH colab exec -s "$SESSION" -f "$P/runner/keepalive.py" --timeout 3600

Run the long keepalive in its own local terminal (or a properly supervised
background terminal). Keep the Mac awake/on AC if relying on its connection.
Do not run a second capture process or start a Phase-2 precision study. Pilot
units that already pass under this prefix are skipped, so the cohort starts at
the first unit the pilot did not cover.

Monitor out of band:

    env -u PYTHONPATH colab sessions
    env -u PYTHONPATH colab download -s "$SESSION" /content/cohort_state/cohort.log "$P/cohort_remote.log"
    env -u PYTHONPATH colab download -s "$SESSION" /content/cohort_state/cohort.rc "$P/cohort_remote.rc"
    env -u PYTHONPATH uv run --project workbench python "$P/runner/monitor.py" --prefix workbench_cohort/phase1_nf4_20261018_a3

`monitor.py` counts absolute logical units from a pinned Hub snapshot, not a
sliding commit-history window. Complete means 989 passing markers / 0 failures
(23 base + 966 adapter/item units), not 989 arbitrary files. A listing/auth error
aborts rather than reporting zero completed units. It validates unit membership;
individual uploads already read back and checked every export digest.
At completion require rc 0, `COHORT_DONE` and this independent completion check:

    env -u PYTHONPATH uv run --project workbench python "$P/runner/monitor.py" --prefix workbench_cohort/phase1_nf4_20261018_a3 --expect-complete

Then stop YOUR completed paid session promptly; IDLE still bills:

    env -u PYTHONPATH colab stop -s "$SESSION"

## 4. Abort criteria and exact abort steps

Abort immediately on any of:

- Fatal conservation/reference/pair failure rate >0 (one failure is sufficient).
  Failed JSON/bin and failed marker are retained and uploaded before queue abort.
- OOM, decimal process RSS >16,000,000,000 bytes, non-A100 fallback, unexpected
  package version/weight digest/device mismatch, or a corrupt/missing unit marker.
- Pilot: queue time above 35 CU (stops itself) or Colab balance down more than
  50 CU since `colab new` (you stop it).
- Unit wall time above 2× configured estimate; cohort elapsed projected cost above
  2× the approved estimate (for the cohort this is a manual check against the
  Colab balance; only the pilot has an in-code CU cap). The unit RSS/time supervisor kills the model and logs
  its real exit code. Setup/sync hangs also need an operator stop, not infinite retry.
- Destination upload/readback failure after retries, 401/403, quota/write denial,
  or a prolonged absence of durable progress after checking the session/client.

Archive probability parity is report-only and is NOT a fatal conservation gate.
Never widen a fatal tau or discard a failed export to continue the cohort.

If the runtime is alive, rescue the small diagnostic logs first if that takes
seconds, not minutes; then STOP this session. Do not queue a new exec behind the
keepalive just to abort, and do not restart its kernel:

    env -u PYTHONPATH colab download -s "$SESSION" /content/cohort_state/cohort.log "$P/abort_remote.log"
    env -u PYTHONPATH colab download -s "$SESSION" /content/nf4_prepare.log "$P/abort_prepare.log"
    env -u PYTHONPATH colab stop -s "$SESSION"
    env -u PYTHONPATH colab sessions

For a pilot failure download `pilot.log` instead. If a log is missing or download
fails, still run the stop command; do not connect these lines with `&&` or let a
failed rescue prevent teardown. Do not stop other people's sessions or unnamed
runtimes you cannot tie to this launch.

## 5. Resume after reclamation / client loss

First establish whether the runtime is really gone using sessions + fresh durable
progress. If only the client died while uploads advance, reattach keepalive; do
NOT create duplicate compute. If the VM is gone, repeat user-authorized setup on
a new A100 under the SAME prefix and same exact bundle. Bootstrap restores the
saved CUDA codes/state; it does not substitute Mac CPU codes. Re-run the small
pilot (already verified units are skipped), then resume the cohort. The queue
restores exports/markers from the Hub before compute, verifies their hashes,
rebuilds index.json including failures, and skips only passing units with matching
source/runtime identity. Loss costs at most one in-flight unit plus reprovisioning.
A failed existing marker intentionally stops instead of being silently retried;
investigate before choosing a new diagnostic namespace.

## Local recheck / viewer

A fresh local end-to-end check (CPU only, one new directory):

    env -u PYTHONPATH uv run --project workbench --with bitsandbytes==0.50.2 --with psutil python "$P/runner/verify_local.py" --model ARG --item wvs_Q57 --weights nf4_dequant --out "$P/dry_run_recheck_$(date +%s)" --publish-viewer

This really SIGKILLs the worker at layer 8, resumes and compares all immutable
bytes, then verifies a completed-unit skip. A4 should use a different country/item
and a fresh directory. Local default Hub token resolution/caches are allowed; no
.env is read. CPU codes are explicitly diagnostic, not an archived CUDA replay.

Serve the viewer in one terminal, then sweep it in another:

    npm --prefix workbench/viewer run serve -- --host 127.0.0.1 --port 5178
    node workbench/viewer/screens/v3/sweep.mjs workbench/exports/index.json

Version/device/instrument-qualified files coexist in the local index; intentional
corruption fixtures stay visibly red rather than being dropped. They are not
production cohort inputs. The capture arrays are geometry-driven; some pre-existing
viewer tutorial prose still uses the old 135M/USA examples (not the measured array
shapes). That copy cleanup is not a new measurement or a reason to rewrite exports.
