## Card T4 — GPU session A: score the replicate and the 64 sign-prompt profiles (strict battery)

Why: two planned results have no data.
- The unseeded retrain (replicate `r1`, one profile unit) is banked on the Hub but never scored.
- The strict-battery sign-prompt cell has only the 26 cohort profiles. The factorial needs all 64.

Compute: Colab Pro, T4, account agonz439@asu.edu, through the `colab` CLI. Budget for this card: at most
12 compute units. Run `env -u PYTHONPATH -u VIRTUAL_ENV colab usage` before and after and report both.

Read first (all of them): the colab-cli-headless-runs skill, the experiment-launch-validation skill,
llm-pipeline-engineering and its dpo-adapter-batch-workflow reference (paths in the shared rules).
Hard lessons from earlier runs, from those skills:
- The VM clones the PUSHED branch, not the local tree.
- Never run `colab restart-kernel` on a session that holds the keep-alive. Use `colab stop -s <name>`
  and provision again.
- Launch scoring only after the boot step has finished and printed its marker.
- Per-unit upload to the Hub is the only resume mechanism. Resume must check each manifest's
  `spec_sha256`, never file presence.
- Foreground terminal calls stop after about 420 s. Run long chains as background terminals.

Do this:
1. Code, test first. In `paper_b/score_plan.py` add three conditions and append their pins to
   `paper_b/score_plan_pins.json` (append only; existing entries must stay byte-identical):
   - `signprompt_strict_v1`: all 64 sign-prompt profiles (`score_sign_profiles.py --units all64`),
     strict spec (pinned hash starts `ed3bb964`), run id `bank2-signprompt-strict-v1-20261018`.
   - `replicate_strict_v1` and `replicate_heldout_v1`: the replicate adapter, strict spec and
     heldout_v1 spec (pinned hash starts `46447de6`), run ids `bank2-replicate-r1-strict-v1-20261018`
     and `bank2-replicate-r1-heldout-v1-20261018`. Find the replicate unit by listing
     `bank2/*/replicates/r1/profiles/` in `Bonorinoa/SCA2-paper-b-adapters`. The replicate switch is
     `replicate_tag()` in `paper_b/protocol_bank2.py`.
   Tests: every existing condition keeps its run id and spec pin; the new conditions resolve to the
   pinned spec hashes; the replicate condition resolves to the `replicates/r1` Hub prefix.
2. Run the full test suite (baseline in the shared rules).
3. You MAY commit and push for this card, because the VM clones the pushed branch. Rules: `git status`
   first; `git add` only your own files; one commit with a clear message; `git push origin
   feat/paper-b-cohort`; never force-push; never touch another branch.
4. Provision ONE VM with `paper_b/colab/provision_score_vm.sh pb-e` (it stops with PROVISION_FAILED if
   any step fails). Run the scoring with `paper_b/colab/vm_score_units.py`, the same way
   `paper_b/colab/vm_run_half_a.py` launches it. Attach `paper_b/colab/vm_fact_keepalive.py` as a
   background `colab exec`.
5. Verify on the Hub (`Bonorinoa/SCA2-paper-b-artifacts`): 64 sign-prompt files and 64 manifests under
   the new run id, all with the strict spec; the replicate files for both conditions with the right spec.
6. Stop the VM (`colab stop -s pb-e`) and confirm that `colab sessions` lists no `pb-` session.
7. If a step fails twice, stop the VM, block the card, and write the exact error. Do not improvise
   around a gate.

Write boundary: `paper_b/score_plan.py`, `paper_b/score_plan_pins.json` (append), new or changed tests
for them, new files under `paper_b/colab/`. Nothing else.
