# Paper B scorer — launch-readiness audit

> **Record, not status.** Written 2026-10-11. Lines about what is done, blocked or next describe that date, not today. Current status: [STATUS.md](../../STATUS.md). "Existing scores: none" was true that day only.

Repo `SCA2_PofW` @ `feat/paper-b-cohort` 38ed2ee; scorer files untracked (read-only audit, nothing edited).
Verified today: `env -u PYTHONPATH .venv/bin/python -m pytest paper_b/test_eval_lib.py -q` → **9 passed**.
Existing scores: none for the cohort — `data/paper_b/` does not exist locally; only the archived 8-country surface (`data/phase2/raw/wvs/ksenias_base8/`). No duplicate work risk; nothing to reuse except the archive.

## Severity-ranked findings

### S1 — Guaranteed end-of-run crash: inner-join row-loss on skipped population cells
`score_cohort.py:541` / `eval_lib.py:337-348` (`join_option_evaluation`).
The population builder correctly skips cells with no valid responses (GBR/Q174, EGY/Q69-Q71, `eval_lib.py:200-203`). But model scores are broadcast to every eval country (`build_pairs`, `score_cohort.py:394-408`), so every model carries GBR/Q174 rows. The `how="inner"` merge then drops them and the guard `if len(merged) != len(model_scores): raise AssertionError` fires — **after all GPU scoring is done**, in the default `--pairs matched` run (GBR adapter on GBR) and worse under `--pairs all`. The docstring claims skipped cells "fall out of the join for free"; the assertion contradicts it.
**Minimum fix:** make the join tolerant of population-missing cells — e.g. left-join, drop `model_prob` rows with no population counterpart *only* when that (eval_country, question_id) is a recorded skip, and count/report the dropped cells instead of asserting. Keep a hard error for any other row loss.

### S2 — Silent fallback to stale Drive adapters + no bank-run provenance check
`score_cohort.py:95-119` (`resolve_adapter`), `colab/vm_score.py` (never sets/validates `HF_TOKEN`).
If the hub listing/download fails (missing token, transient network), resolution silently falls to `C.ADAPTER_DIR` on Drive — which the canonical record says is **stale for any country retrained after the hub switch and has lost data twice**. A "from drive" line buried in the log is the only trace; the manifest then records it, but nothing stops the run.
Also: neither `resolve_adapter` nor `inventory()` reads `run_record.json` to verify each adapter's `bank_run_id == C.BANK_RUN_ID` (`config.py:26`). Presence of `adapter_model.safetensors` is not the provenance gate.
**Minimum fix:** (a) in `resolve_adapter`, when the hub path fails, require an explicit env flag (e.g. `SCA2_PB_ALLOW_DRIVE_FALLBACK=1`) before using Drive, else raise; (b) after resolution, if `run_record.json` exists under the adapter dir, assert its `bank_run_id` matches `C.BANK_RUN_ID` (hard-fail on mismatch, warn-if-absent listed in the manifest as `provenance_checked: false`).

### S3 — Cache/resume keyed only by row count
`score_cohort.py:383-391` (`_load_or_skip`).
A cached CSV is accepted if its row count equals `expected_rows(specs)`. That key omits: question-map hash, numeric-grid content, prompt/config constants, adapter revision (a country retrained and re-uploaded to the hub after a partial run would be silently skipped because the stale CSV has the right length), and protocol constants. Crash-resume correctness currently rests on nothing else changing — unverifiable.
**Minimum fix:** stamp each per-model CSV with a sidecar (`{model}_manifest.json`: hash of `(n_questions, per-question code lists, COMPLETION_PREFIX, temperature, length_normalize, adapter source+revision)`) or write a small header manifest keyed the same way; on `_load_or_skip`, recompute and compare, rescore on mismatch.

### S4 — dtype round-trip breaks the cached-CSV join
`score_cohort.py:386` (`pd.read_csv(path)` with no dtypes).
Fresh rows carry `option_code` as strings; a cached CSV re-read infers `int64` for all-numeric codes. The join in `eval_lib.py:339-343` is on `option_code` (population side is `str`) → key mismatch → row loss → the S1 assertion (or, post-S1-fix, silently missing metrics for every cached model). Same latent issue for `option_value`/`option_index` is benign, but `option_code` is a join key.
**Minimum fix:** `pd.read_csv(path, dtype={"option_code": str})` in `_load_or_skip` (and anywhere cached scorer CSVs are re-read).

### S5 — No hub revision pinning on adapter downloads
`score_cohort.py:107-109`. `snapshot_download` with no `revision=` downloads whatever is HEAD of `Bonorinoa/SCA2-paper-b-adapters` at run time. The dataset bank is pinned to revision `7550fd4c…`, but the adapter bus is mutable; a mid-run retrain+reupload yields a mixed-provenance cohort with no way to reconstruct it.
**Minimum fix:** resolve the repo's current commit SHA once at start (`HfApi().repo_info(...)`, record in manifest), pass `revision=<sha>` to every `snapshot_download`, and record the SHA per adapter in the manifest.

### S6 — No independent adapter-path gate (GPU)
`--gate` scores **base only** (`score_cohort.py:456-468`). It validates prompt/readout/population plumbing, not the PeftModel wrapper: adapter load (`PeftModel.from_pretrained` on a 4-bit-quantized base), `load_adapter`/`set_adapter` switching, and unload hygiene. A base-pass green is exactly the false go-ahead the claim lock warns about.
**Minimum fix:** add a `--gate-adapter`: score one adapter with an archived counterpart (e.g. CHN — archived file `model_option_probabilities_CHN_adapter_on_CHN.csv` exists in `ksenias_base8`) using the same pinned CHN numeric grid, and require max |dlogprob| within the same tolerance family as the base gate (logprob tolerance cannot be 1e-2-tight across 4-bit nondeterminism — set it explicitly, e.g. |dlogprob| ≤ 0.05 and |dprob| ≤ 5e-3, and record the actual max). This must run in `vm_score.py` **before** the cohort loop.

### S7 — Drive dependencies remain in the launch path (user wants Drive-free)
- `colab/vm_score.py:9,10,13`: `DATA=/content/drive/MyDrive/SCA2_paper_b` — scores, logs, and (via default `_default_adapter_cache` fallback) cache live on the FUSE that stalls silently.
- No upload/persistence step for outputs: nothing ships `SCORE_DIR` anywhere durable; on Drive it would persist, Drive-free it evaporates with the VM.
**Minimum fix (Drive-free launch recipe):**
1. `SCA2_PB_DATA_ROOT=/content/paper_b_data` (local disk) and `SCA2_PB_ADAPTER_CACHE=/content/adapter_cache` (already the Colab default) — zero Drive mounts.
2. Repo + `data/wvs_eval_full` parquets must reach the VM without Drive: they are gitignored, so add a one-time upload of the 42 parquets to a private HF dataset repo (e.g. `Bonorinoa/SCA2-paper-b-wvs-eval`) and a bootstrap step in `vm_score.py` that `snapshot_download`s them; alternatively rsync/scp. Question map and archive gate CSVs are tracked in git — `git clone` suffices for those.
3. After a successful run, `upload_folder` `SCORE_DIR` + `logs/` to a private HF dataset repo (e.g. `Bonorinoa/SCA2-paper-b-scores/<run_id>/`). Without this, a Colab recycle loses everything.
4. `HF_TOKEN` must be exported before `vm_score.py` runs (it is currently assumed, never checked) — assert it at script start.

### S8 — Minor
- `score_cohort.py:462`: the `--gate` merge is on `(question_id, option_index)` only, without `option_code`; add `option_code` to the merge keys (both sides carry it) so a grid-order surprise fails loudly.
- `vm_score.py:15`: `TRANSFORMERS_NO_BF16` is not a transformers env var; harmless but misleading — the fp16 behavior actually comes from `torch_dtype=torch.float16` in `load_base_model_and_tokenizer`.
- Prompt left-truncation (`prepare_prompt_for_model`, keeps the *last* 768 tokens) would cut the chat header/instructions first; prompts are far below 768 tokens for the mapped items, but the manifest should record `prompt_was_truncated` counts — it does per row; add a run-level warning if any row truncated.
- Generated-answer arm doubles runtime per question; consider `SAVE_GENERATED_ANSWERS` behind a flag for the 42-country run (metrics don't use it).
- Manifest (`score_cohort.py:546-562`) lacks: hub revision (S5), provenance-check flag (S2), numeric-grid hash per question. Add all three.

## What already checks out
- Prompt anti-leakage: unconditioned prompt contains no country name (tested, `test_prompt_has_no_country_status`); persona arm names come from a 42-entry validated map.
- Numeric grids: observed support within `NUMERIC_VALID_RANGES` bounds (Q261 ≤ 111 values, Q262 ≤ 96) — `MAX_NUMERIC_SUPPORT=150` cannot trip; the gate pins the archived CHN grid.
- No false completion leakage: `generated_answer_code` is validity-gated and used in no metric.
- CPU parity and 9 unit tests green today.
- Adapter switching pattern (`load_adapter` + `set_adapter` per country, `del peft` after) is structurally sound for inference; base/persona arms run before the PEFT wrap mutates `base_model`.
