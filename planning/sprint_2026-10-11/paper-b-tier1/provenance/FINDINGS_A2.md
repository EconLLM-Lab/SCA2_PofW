# A2 independent verification of Paper B archive provenance claims (A1 = t_ef474f3c)

Verifier: verifier profile, task t_c5131cd3. Route: anthropic / claude-opus-5-5. This is not the producer's openai-codex route.

All A2 code, raw outputs and logs are in `/Users/bonorinoa/.hermes/profiles/verifier/cache/scratch/a2/` (scratch; pruned after 24 h idle). A2 did not execute any A1 script. A1's raw replay JSON numbers are read as data in only two places (2c and 2d), and both are labeled.

Started 2026-10-18 ~08:47 MST. This file is the only thing A2 wrote under the project root.

## VERDICT: BLOCK (narrow)

Two acceptance criteria fail as literally written: check 3 (finding F3) and check 4 (finding F4). Both are low severity and cheap to resolve, and neither touches the science.

The core conclusions survive independent re-derivation:
- The writer SHA is unresolvable.
- Prompts are byte-identical.
- NF4 is the cause of the dominant discrepancy, and an independent native-bnb run confirms it.
- The blast-radius pipelines are traced correctly.
- The recommendation is supported, with one caveat (F5).

The block clears when the PM:
(a) reclassifies one blast-radius row (F3); and
(b) either cleans up or explicitly waives the four disclosed `.pyc` writes (F4). A2 may not do (b) itself; it is outside A2's fence.

## Check 1: writer SHA (HOLDS)

- **A1's claim.** The producing git SHA is unresolved. The manifest field `code_revision_sha256=f3279d6c…` is a bundle digest, not a commit. 86fbf10 is only a proxy.
- **Run metadata.** All 43 manifests in `paper-b-20261011/hub/runs/paper-b-20261011/manifests/` carry:
  - `code_revision_sha256 = f3279d6c85524a14dc0d591c1d169553e2380d839dd28062f5214b4984f1ba12`;
  - `spec_sha256 = ed3bb964…`;
  - `adapter_revision = 7550fd4c…` (the 42 adapter manifests).

  Base was persisted at 2026-10-12T04:19:55Z; USA at 04:57:51Z.
- **How the digest is computed.** `paper_b/colab/vm_cohort.py:62-79` (`running_code_id`) takes sha256 over path, NUL and bytes for the sorted `paper_b/**/*.py` when no `.git` exists. Its docstring says the scorer files were untracked at the time.
- **Independent recomputation.** `a2/digest_search.py` applies the same digest to every commit in `git rev-list --all` (292 commits; 61 distinct paper_b/*.py trees) and to the working tree. Exit 0. **0 matches.** The working-tree digest is c8003e03….
- **Git history.** `git log --all --diff-filter=A -- paper_b/colab/vm_cohort.py paper_b/score_cohort.py` shows both files first added in 86fbf10 (2026-10-14 18:04 -0700), after the run. The reflog has no commit between 38ed2ee (2026-10-10 10:05) and 2026-10-14, so HEAD at run time was 38ed2ee, which lacks the writer.
- **Result.** A1 names no producing commit, and that is the correct finding: no commit can be named. The bundle digest is the only identity, and 86fbf10 is correctly labeled a proxy.
  - Trivial difference: A1 says "67 snapshots"; A2 counts 61 distinct trees (68 commits touch paper_b). Both find 0 matches, so the difference is immaterial.

## Check 2: the cause (A1 verdict NOT REPRODUCED: HOLDS at 1e-3; NF4 lead cause independently CONFIRMED)

### 2a. Prompt/completion diff, re-derived with A2 code

Commands:
- `git archive 86fbf10|HEAD paper_b DPO_eval_WVS/question_map_wvs_edited.csv | tar -x -C scratch`. Read-only extraction; imports never touch the repo.
- `a2/render_diff.py` for each tree, then `a2/compare_render.py`.

Result: exit 0 for all three runs (log: `compare_render.log`).
- Spec sha256 is `ed3bb964…` under both trees, which equals the manifest value.
- All **23** strict items (A1 checked 5) render identically under the proxy and HEAD: prompt text, chat-formatted text, prompt ids, and completion ids.
- A2's own `apply_chat_template` render equals the production `prepare_prompt_for_model` render on all 23 items in both trees.
- No item is truncated (maximum 213 tokens against a 768 cap).
- Constants are identical: `" "` prefix, temperature 1.0, no length normalization, chat date `26 Jul 2024`.
- Function source is identical for `sequence_logprob`, `prepare_prompt_for_model`, `load_base_model_and_tokenizer`, `score_model_questions` and `stable_softmax`. `build_survey_user_prompt` source differs, but its output is identical on all 23 items.
- The archive's code grid and `option_token_count` match the spec for all 23 items, in both base and USA (0 mismatches).
- A2's prompt and completion ids equal A1's `prompts_new.json` for Q57, Q58, Q81, Q106 and Q107.
- Q81 completion ids are `{1:[220,16], 2:[220,17], 3:[220,18], 4:[220,19]}`.

Limit (same as A1's): the exact archived bundle is unrecoverable. These renders prove proxy = HEAD and spec = archive spec, not bundle = proxy.

### 2b. Hypothesis A1 did not list, #1: base-model snapshot revision drift (RULED OUT)

- The production loader passes no `revision`, so Colab resolved `main` on 2026-10-11.
- The public API (`curl https://huggingface.co/api/models/meta-llama/Llama-3.1-8B-Instruct`) returns `sha=0e9e39f249a16976918f6564b8830bc894c89659` and `lastModified=2024-09-25`. `main` has therefore not moved since well before the run.
- The local `refs/main` equals that sha. `shasum -a 256` of all 4 local safetensors shards equals their LFS blob ids (exit 0).
- The base weights used locally are therefore exactly what the archive run loaded.

### 2c. Hypothesis A1 did not list, #2: the residual is at the archive's fp16 resolution floor (SUPPORTED)

Script: `a2/fp16_grid.py`, exit 0 (log: `fp16_grid.log`). It reads the archive CSVs and A1's raw replay JSON numbers as data.

- **6020/6020** archived option logprobs (43 files) lie exactly on the fp16 grid; only 16.1% lie on the bf16 grid. The archive was written from fp16 logits and log-softmax. This is consistent with the NF4 + fp16-compute loader and inconsistent with an fp32 or bf16 reference.
- A single fp16-ulp change in one option score moves the archive's own probabilities by **2.5e-3 to 3.9e-3** on every unsaturated item (Q57, Q58, Q81 base, Q106, Q107). The card's 1e-3 probability tolerance is therefore **below the archive's representational resolution**. It can be met only by bit-identical kernels.
- Measured in median-centred fp16 ulps of the archived score:
  - A1's NF4 residuals are 0.0 to 3.0 ulp on all 10 rows.
  - The unquantized-f32 residuals are 60 to 313 ulp.

### 2d. Independent re-run of the NF4 diagnostic on 2 of the 5 items per arm (A2 code, different implementation)

Command: `env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 HF_HUB_OFFLINE=1 uv run --frozen --no-sync --project <workbench> --with pandas --with bitsandbytes --with peft --with accelerate python a2/native_nf4.py Q57,Q107 Q81,Q107`. Exit 0 (`native_nf4.log`, `native_nf4.json`); post-analysis `a2/native_ulps.py`, exit 0.

Implementation (independent of A1's code):
- The stock HF loader with bnb `Linear4bit` (224 modules), NF4, double quant, fp16 compute, and `dtype=float16`, which mirrors transformers 4.46's override of `torch_dtype=None`. A1 instead dequantized into a dense streamed scaffold.
- The USA adapter is loaded through peft; LoRA parameters are float32.
- Serial scoring: one full prompt+completion forward per option, no KV cache. CPU only.
- One 8B process at a time. Peak RSS was 11,839,406,080 bytes, below 16e9.

| arm / item | A2 max abs dp | A1 max abs dp | A2 vs archive (ulp) | A1 vs archive (ulp) | A2 vs A1 (ulp) |
|---|---|---|---|---|---|
| base Q57 | 3.039e-03 | 3.039e-03 | 0.5 | 0.5 | 0.0 |
| base Q107 | 2.886e-03 | 3.465e-03 | 1.0 | 1.0 | 2.0 |
| USA Q81 | 8.021e-08 | 8.021e-08 | 0.8 | 0.8 | 1.0 |
| USA Q107 | 5.908e-03 | 1.141e-02 | 2.0 | 3.0 | 4.0 |

Reading:
- A1's NF4 numbers reproduce independently: identical on Q57 base and Q81 USA.
- The two CPU NF4 implementations disagree **with each other** by up to 4 ulp, which is as much as either disagrees with the archive. The residual is implementation-arithmetic noise, not a missing configuration factor.

### 2-result

- A1's **NOT REPRODUCED** is correct as defined: nothing meets 1e-3, including A2's run.
- The memo understates the strength of the NF4 finding. At the archive's own fp16 resolution, NF4 matches to within 0–3 ulp, and the unquantized reference misses by 60–313 ulp.
- Severity: informational, not a block. Suggested memo note: "reproduced within fp16 rounding; 1e-3 is unattainable without bit-identical kernels".

## Check 3: blast radius (FAILS on one "cannot move" row)

Script: `a2/blast_sample.py`, exit 0 (`blast_sample.log`, `blast_sample.json`). Stratified sample of **31 rows over all 19 claim families** (claim prefix × run_id × producing_script), plus every row A1 marked "NO".
- A2 traced each run_id to its driver with its own map: `paper_b/score_plan.py:27-61`, `paper_b/colab/vm_cohort.py:30`, `paper_b/heldout/FREEZE.json`.
- Every scoring driver reaches the NF4 loader. The loader is at `paper_b/score_cohort.py:354` (`BitsAndBytesConfig(load_in_4bit=True, nf4, fp16 compute, double quant)`), and the sign-profile route uses it via `paper_b/score_sign_profiles.py:155`.
- `grep -rn from_pretrained paper_b` finds every model load in paper_b to be NF4: `score_cohort`, `compute_ref_cache`, `train_country` and `vm_smoke`. No unquantized scoring path exists.
- `git log -S'bnb_4bit_use_double_quant=True)' -- paper_b/score_cohort.py` shows the NF4 loader has been unchanged since 86fbf10. It is present verbatim at FREEZE's `scoring_code_revision` 2126045d and at `code_revision` 357adde4.
- A1's `blast_radius_numbers.csv` keeps all 11 original columns identical to NUMBERS_TABLE.csv (220/220 rows; sha `90f0f467…`).
- Lock-table rows A1 marked NO all hold: 48, 78, 79 and 83 (human–GPS only) and 182–186 (status/design counts). Lock sha is `5fb0fff0…`, unchanged.

**F3 (severity LOW–MEDIUM; criterion "every row marked cannot-move must hold" fails for 1 row).**
- Row: `HASH_selection_amended_20261016` (value `782b7d21…`, output `paper_b/heldout/selection_amended_20261016.csv`).
- A1's classification: `NO: content hash is model-independent`.
- Why that is wrong: the file is the output of `paper_b/heldout/probe_select.py:101` (`df["primary_selected"] = dichotomize(df)`). That selection is computed from per-item adapter effects (`b_*`, `t_*` columns) estimated on bank2-heldout-v1 model scores. FREEZE.json lists heldout_v1 and the other heldout run_ids as its inputs.
- A1 itself marks the SCR/PD rows "YES/POSSIBLE … derived selection". By A1's own counterfactual standard, the selection, and so its hash, could move.
- The other 5 HASH rows hold (pool skeleton built "from metadata + questionnaire text only" per commit 9902564; `overrides.json` is text repairs).
- Required fix: reclassify this row to YES/POSSIBLE (only if the selection is re-derived; the frozen registration value itself is fixed).

## Check 4: fence (FAILS literally: 4 A1 writes; disclosed and benign)

Reference: A1's first artifact is `provenance/inspect_provenance.py` (birth 07:54:20; A1 run 30 started 07:52:00).

Command: `find paper_b planning/TWO_PAPER_CLAIM_LOCK.md data -newer planning/sprint_2026-10-11/paper-b-tier1/provenance/inspect_provenance.py -type f`. Exit 0, **13 files** (`a2/fence_find.txt`). Attribution:

**4 files are A1's writes, so the criterion fails:** `paper_b/__pycache__/{score_cohort,eval_config,config,eval_lib}.cpython-312.pyc` (08:01:23–24).
- Python 3.12 is the workbench uv interpreter (`workbench/.venv/bin/python -V` = 3.12.12; repo `.venv` = 3.14.4).
- A1's `evaluate_stream.py:30` puts `ROOT/paper_b` on `sys.path` and imports `score_cohort`, which matches A1's f32 replay window (`replay_f32_base.json` written at 08:03:58).
- The `.pyc` headers match the current, unchanged sources exactly (mtime and size for all 4), so they are pure derived caches with no semantic effect.
- A1 disclosed them in the memo, in `verification.json` and on the card.

**9 files are not A1's:**
- `paper_b/build_numbers_table.py`, `paper_b/test_build_numbers_table.py`, `paper_b/heldout/per_dimension.py`, `paper_b/heldout/test_per_dimension.py` and `planning/TWO_PAPER_CLAIM_LOCK.md` are all in commit a1d75ae (Augusto, 2026-10-18 08:16:43, C7). `git status --porcelain -- paper_b planning/TWO_PAPER_CLAIM_LOCK.md data` is empty.
- The 4 `cpython-314` caches (two of them `-pytest-9.1.1`) belong to the C7 test runs. No A1 script imports `build_numbers_table` or `per_dimension`.
- Nothing is under `data/`.

**Data grep:**
- `grep -nE 'data/WVS|data/GPS|data/EVS' provenance/*.py` returns exit 1 (no hits).
- `grep -nF '.env' provenance/*.py`: every hit is `os.environ`. Excluding those leaves exit 1 (no hits). There are no dotenv or credential-file reads.
- `HF_TOKEN` is only tested for presence as a boolean and never printed (`inspect_provenance.py:28-36`, `inspect_runtime.py:19`).

A1's `git worktree add/remove` was authorized by A1's card, and the worktree has been removed.

**F4 (severity LOW).** The criterion "must show nothing A1 wrote" fails on 4 derived `.pyc` files.
- Remedy (PM decision; outside both A1's and A2's fences): delete the four `.pyc` files, or record an explicit waiver.
- Process fix: every diagnostic launcher should export `PYTHONDONTWRITEBYTECODE=1` from the first command. A1 adopted this only after the fact.

## Check 5: recommendation (SUPPORTED, with one caveat)

A1 recommends two things:
- Keep frozen NF4 as Paper B's canonical instrument, and do not rebuild tables because the unquantized workbench disagrees.
- For the explanation capture, prefer production-NF4-dequantized weights with parity and conservation gates. Augusto decides.

The evidence supports this:
- Every Paper B scoring path is NF4 (check 3).
- The archive is fp16-grid (2c).
- NF4 closes the gap from 60–313 ulp to 0–3 ulp in two independent implementations (2c, 2d).
- The unquantized reference explains a materially different model. Q81 USA is P(1)=0.695 unquantized against 1.000 archived.

**F5 (severity MEDIUM for the follow-on capture, not for A1's artifact).** A1's "output-parity gate" has no tolerance unit.
- If the gate inherits 1e-3 in probability, it fails by construction for any non-bit-identical path, including a correct NF4-derived one. A2's run and A1's run already disagree by up to 5.5e-3 with each other (2c, 2d).
- Recommendation: state the parity gate in fp16 ulps of the option logprob (for example ≤ 4 ulp) or in nats. Report probability gaps descriptively.
- This decision belongs to Augusto or the PM.

## Required to clear the block

1. Reclassify `HASH_selection_amended_20261016` in `blast_radius_numbers.csv` and in the memo's blast-radius table (F3).
2. The PM deletes the 4 `paper_b/__pycache__/*.cpython-312.pyc` files or records a waiver (F4).

Optional and non-blocking: add the 2c/2d resolution-floor note to the memo, and give F5 a parity-gate unit.
