# C9-4 cross-family verification: experiments A and B

**Overall verdict: ACCEPT.**

Verified 2026-10-20 18:18 MST on branch `feat/paper-b-cohort`, commit
`918a183a539558cb13d50644457cedbd560e42a6`, using route
`openai-codex / gpt-5.6-sol`. The producer was the Claude-family orchestrator; this audit is cross-family.
The repository fence was read-only except for this report and the required temporary mutation in check 5, which was
restored byte-for-byte before the audit ended. No GPU was used and no spend was incurred.

The Hub was read with the token placed only in the downloader process environment. The token was not printed or
copied. Licensed human respondent rows were not read, printed, or copied. The TVD recomputation read only the same
local aggregate response-distribution input named by `paper_b/c9_tvd.py`.

## Verdict by acceptance check

| Check | Verdict | Evidence |
|---|---|---|
| 1. Provenance and gates | **PASS** | Experiment A: 42/42 score CSVs and 42/42 manifests; experiment B: 42/42 log-probability files. Both summaries say `units_expected: 42`, `units_missing: []`. Local driver SHA-256 values equal the hashes in the Hub gates. All specified gates pass with plausible nonzero effects and exact/near-exact parity. |
| 2. Correct conditions | **PASS** | A sets each country's pinned cohort-1 adapter and supplies that same country to the C8 persona prompt. B deterministically reconstructs the 526/132 shared split and scores `eval_sorted`, using the current country's `chosen` and `rejected` fields. Independent bank inspection found 658 shared prompts, 526 train, 132 held out, 26 held-out label signatures matching the 26 sign profiles, and no target-country name in any model-visible bank prompt or completion. |
| 3. Independent recomputation | **PASS** | An independent scratch implementation imported no producer module. The four country-equal TVD means, interaction, recovery, accuracy, base accuracy, margin shift, and all audited intervals match `NUMBERS_TABLE.csv`; maximum numeric difference was `3.47e-18` (floating-point noise), hence all match at printed precision. |
| 4. Intervals | **PASS** | Code inspection and an independent seeded recomputation show that the profile-block bootstrap samples 26 profile IDs with replacement and moves every member of a sampled profile together; the country bootstrap samples 42 countries separately. Seeded intervals match the table exactly to floating precision. |
| 5. Tests bite | **PASS** | Full suite: `613 passed`. Replacing the recovery rule with the accuracy rule made the targeted test fail (`1 failed`, inner pytest exit 1). Restoring the original bytes returned the file to the same SHA-256, and the unmutated targeted test passed. |
| 6. Claim-lock text | **PASS** | Amendment C9's append-only correction and Amendment C9.1 label the rows descriptive/not preregistered, call experiment B a construction check, preserve the retrospective-screen restriction, and explicitly state that no claim is earned. No reading exceeds the banked rows. |

## 1. Provenance and gates

### Experiment A: `adapter-persona-strict-v1-20261019`

Current Hub inventory under the run prefix contains exactly:

- `gates.json`;
- 42 manifests, one for every cohort country;
- 42 synthetic option-probability CSVs, one for every cohort country;
- `run_summary.json`.

That is 86 files total. There are no missing or extra cohort countries. Independent validation of every manifest and
CSV found:

- manifest model name `<CC>_adapter_persona` and matching CSV model name;
- adapter revision `7550fd4cfe514470bb8d80918a43c9ae424d26b5` in all 42 manifests;
- spec SHA-256 `ed3bb964b606a163c792a68eea2ea9e6cc679bb724ead6726c173f36d9a1fbf6` in all 42 manifests;
- 140 option rows and 23 distinct strict-battery questions in every country file;
- each question's model probabilities sum to one within `1e-12`;
- every manifest's recorded CSV SHA-256 equals the downloaded bytes;
- every manifest records the same uploaded-driver hash as `gates.json`.

The local driver SHA-256 is
`d0ccd3ddadc7a29f9713fd274ebbf8835df3fab43cc33bb2648aad1e4d1118c8`, exactly the Hub gate's
`driver_sha256`.

Gate details:

- G1/spec: recorded spec SHA-256 is exactly the `persona_strict_v1` pin in `paper_b/score_plan_pins.json`.
- G3/base parity: 140 rows; max absolute log-probability gap `0.0`; max probability gap
  `1.1102230246251565e-16`; 0 rows over tolerance; pass.
- G2/ARG adapter parity: 140 rows; max absolute log-probability gap `0.0`; max probability gap
  `1.1102230246251565e-16`; 0 rows over tolerance; pass.
- G2/adapter effect: max probability change `0.516886736701937`, above the `0.001` minimum.
- G2/switchback: max log-probability and probability gaps are both `0.0`; pass.
- Overall `gate_pass: true`.

These values are plausible: the base and banked path are effectively identical, the adapter has a large observable
effect, and disabling it returns exactly to base.

### Experiment B: `label-recovery-cohort1-v1-20261019`

Current Hub inventory under the run prefix contains exactly:

- `gates.json`;
- 42 `logps/<CC>.jsonl` files, one for every cohort country;
- `run_summary.json`.

That is 44 files total. Each country file has exactly 132 rows, unique IDs `0..131`, the five required fields, and
only finite log probabilities. There are no missing or extra cohort countries.

The local driver SHA-256 is
`ddbb5d45b37d15c02b4fde6d43360b189d609f3a63eebd79a9676ab4c1c29cfe`, exactly the Hub gate's
`driver_sha256`. The gate records adapter revision
`7550fd4cfe514470bb8d80918a43c9ae424d26b5` and bank run
`gps_sign_relabel_all_20260816_004545Z`.

Gate details:

- GB1/reference-cache parity: first 20 training completions; max absolute gap `0.0` against
  `cohort1/shared_reference_logps.jsonl`; tolerance `0.01`; pass. The reference manifest records seed 42,
  train fraction 0.8, 526 train prompts, 1,052 completion log probabilities, and the expected bank run ID.
- GB2/ARG adapter effect: max absolute change `71.0` nats, above the `0.001` minimum.
- GB2/switchback: max absolute gap `0.0`; pass.
- Overall `gate_pass: true`.

## 2. Correct-condition audit

### A applies both the adapter and the C8 persona

The executed driver's hash is the local driver's hash above. In
`paper_b/colab/vm_c9_adapter_persona.py`:

1. It refuses the bank-2 configuration and requires `SCA2_PB_UNITS=countries`.
2. It resolves every adapter as `adapters/<CC>` at the full pinned cohort-1 revision.
3. It loads/sets adapter `<CC>` and checks `peft.active_adapter == cc`.
4. It calls the scorer with `prompt_country=cc` for `<CC>_adapter_persona`.
5. Its no-persona gate calls the same scorer with `prompt_country=None`.

`paper_b/eval_lib.py` maps `prompt_country=cc` to the exact C8 wording:

`Answer this questionnaire as a typical adult living in [country name].`

That matches `C8_PERSONA_DESIGN.md`. The country name is therefore present only where this comparator requires it;
the adapter-only parity gate uses the neutral prompt. The spec is the same pinned strict-v1 spec, with the persona
sentence inserted only at scoring time.

### B uses the held-out split and each country's labels

The executed driver's hash is the local driver's hash above. The driver:

1. loads all country-specific bank-1 files;
2. verifies a shared prompt set and response pair for all countries;
3. calls the shared split with `TRAIN_FRAC=0.80`, `SEED=42`;
4. sorts and scores `eval_prompts`, refusing unless there are 132;
5. for every country and held-out prompt uses `by_prompt_all[cc][p]` and scores that row's `chosen` and `rejected`
   completions—not the reference country's orientation and not the train prompts.

I independently reconstructed the split without importing `paper_b.lib`:

- 658 normalized shared prompts;
- 526 train prompts;
- 132 held-out prompts;
- zero country prompt-set mismatches;
- zero response-pair mismatches;
- zero rows whose country metadata disagrees with the file's country;
- 26 distinct held-out chosen/rejected orientation signatures, exactly matching the 26 sign profiles;
- zero within-profile label-signature mismatches;
- zero occurrences of any of the 42 official country names in the model-visible shared prompts or completions.

The uploaded B rows deliberately retain only integer `i` rather than prompt text. Direct prompt identity is therefore
established by the executed driver's matching hash and deterministic code path, not by a prompt column in each output.
This is sufficient for this audit; adding a prompt hash to future output rows would make that provenance easier to
check without relying on the driver hash.

## 3. Independent recomputation

The scratch recomputation loaded Hub model outputs, local cohort-1 model probabilities, the local persona score file,
and the local aggregate survey response distributions. It did not import `paper_b/c9_tvd.py`,
`paper_b/c9_label_recovery.py`, or another producer module.

### Four TVD cells and interaction

TVD is `0.5 * sum(abs(model_prob - human_prob))` over the union of option codes for each country-item cell. All four
cells cover 42 countries and 965 observed country-item cells. The only absent human cell is `JOR/Q178`.

| Cell / contrast | Independent value | Printed | Table match |
|---|---:|---:|---|
| Base, country-equal mean TVD | 0.470046650620059 | 0.470 | exact |
| Adapter, country-equal mean TVD | 0.5154766417741424 | 0.515 | exact |
| Persona, country-equal mean TVD | 0.3649046586151852 | 0.365 | exact |
| Adapter + persona, country-equal mean TVD | 0.41950116386997005 | 0.420 | exact |
| Interaction `(AP - persona) - (adapter - base)` | 0.009166514100701484 | 0.009 | within `3.47e-18` |

Interaction intervals from the independent seeded bootstrap:

- profile-block, seed 20261011: `[-0.003299910511075615, 0.022368632285632305]`;
- country, seed 20260905: `[-0.0007327323228584682, 0.019099617928255208]`.

They match `C9_TVD_interaction_profile_block` and `C9_TVD_interaction_country` to floating precision.

### Held-out label recovery

For every country and pair I independently formed:

- adapter margin = `adapter_chosen - adapter_rejected`;
- base margin = `ref_chosen - ref_rejected`;
- recovery = mean of `adapter margin > base margin`;
- accuracy = mean of `adapter margin > 0`;
- base accuracy = mean of `base margin > 0`;
- margin shift = mean of `adapter margin - base margin`.

| Quantity | Independent mean | Profile-block 95%, seed 20261011 | Country 95%, seed 20260905 | Table match |
|---|---:|---:|---:|---|
| Recovery | 0.9397546897546898 | [0.925674732747101, 0.95191970727685] | [0.9300144300144301, 0.9494994588744591] | exact |
| Accuracy | 0.8161976911976913 | [0.770530492898914, 0.8560726950354609] | [0.7858901515151515, 0.8484848484848484] | exact |
| Base accuracy | 0.4893578643578645 | [0.4714657572037891, 0.5055975274725275] | [0.4763708513708514, 0.5012626262626263] | exact |
| Mean margin shift, nats | 40.2823942550505 | [28.2455748023476, 54.06282406309061] | [32.612234792117604, 49.52614735524891] | exact |

All eight `C9_label_recovery_*` rows match. `NUMBERS_TABLE.csv` itself has 562 rows and SHA-256
`71ee7c8c68eb856bf7215165dd836aef7cc3f67993a6523790cee4b22ce186a4`, matching Amendment C9.1.

## 4. Interval implementation

The producer's `c9_tvd.bootstrap_mean` uses two distinct branches:

- profile-block: build positions for each unique profile ID, draw 26 profile IDs with replacement, concatenate all
  member-country positions for every sampled profile, then average the resulting countries;
- country: draw 42 country positions with replacement and average them.

`c9_label_recovery.summarize` supplies the profile series to the first call and `None` to the second. This is a real
cluster bootstrap: a multi-country profile's members are never split within a draw. It is not a profile-equal
estimand; larger sampled profiles contribute all their member countries, as documented.

My independent implementation rebuilt the 26 profiles directly from the signs in `gps_z_vectors.json`, then repeated
both bootstrap branches with NumPy's seeded generator. The interaction intervals and all eight label-recovery table
intervals above match the producer/table output exactly (apart from at most `3.47e-18` floating-point noise).

## 5. Test evidence and mutation check

Full-suite command:

```text
HF_TOKEN= env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest paper_b -q
```

Captured exit code: **0**. Result: **613 passed in 145.55s**.

Mutation: in a temporary `try/finally` harness, changed only

```text
recovery = mean(adapter_margin > base_margin)
```

to the incorrect accuracy rule

```text
recovery = mean(adapter_margin > 0)
```

and ran:

```text
HF_TOKEN= env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 \
  .venv/bin/python -m pytest \
  paper_b/test_c9_label_recovery.py::test_recovery_and_accuracy_are_different_rules -q
```

Inner pytest exit code: **1**, as required. The assertion caught the mutant because the second fixture expects accuracy
1.0 and recovery 0.0, while the mutant returned recovery 1.0.

The harness restored the original bytes in `finally`:

- SHA-256 before: `c83d307bf17cda6c6cc8dbee09cd3191843cc50fe39a862c4305ef2b9a6d24a6`;
- SHA-256 after:  `c83d307bf17cda6c6cc8dbee09cd3191843cc50fe39a862c4305ef2b9a6d24a6`;
- `RESTORED=True`.

The same targeted test after restoration passed (exit 0, `1 passed`), and `git status` showed no modified producer
file.

## 6. Claim-text audit

Amendment C9 defines every C9 row as `DESCRIPTIVE / NOT PREREGISTERED` and says none is a test or earns a claim.
Its append-only correction explicitly supersedes the earlier pending-state bullets for experiment A without changing
a value, interval, label, or claim. Amendment C9.1 then:

- identifies experiment B as 42 cohort-1 adapters by 132 held-out pairs;
- reports the four country-equal means and profile-block intervals that match the table;
- calls the result a construction check;
- limits the reading to installation of synthetic labels on unseen scenarios;
- says it establishes neither GPS country ordering nor human agreement;
- keeps transport and pre-piloting unearned;
- states again that no claim is earned.

The TVD text also stays within the banked rows: adapter+persona is a fourth descriptive cell, the interaction asks
whether the two shifts add, and the text does not promote that interaction into a test or mechanism. The construction
and descriptive wording is therefore supported by, and no broader than, the rows.

## Commands and captured exit codes

| Command / harness | Exit |
|---|---:|
| `git status --short --branch && git rev-parse HEAD && git branch --show-current && git diff --stat` | 0 |
| Hub downloader for both run prefixes (token process-local, no token output) | 0 |
| Independent audit/recomputation script (no producer-module imports) | 0 |
| `HF_TOKEN= env -u PYTHONPATH PYTHONDONTWRITEBYTECODE=1 .venv/bin/python -m pytest paper_b -q` | 0 |
| Mutated targeted pytest (inner test process; failure required) | 1 |
| Mutation audit harness, including exact restoration check | 0 |
| Restored targeted pytest plus clean-status check | 0 |

## Final ruling

**ACCEPT.** Both genuine 42-country experiments have complete current Hub artifacts, the executed driver hashes match
the audited source, all required gates pass, the conditions are implemented as specified, the independent point and
interval recomputations match the 562-row table, the tests detect the named wrong implementation, and the claim-lock
text does not overreach.
