# C8 — Country-named persona arm on the 42-country cohort: design lock (before scoring)

2026-10-18. Status: LOCKED BEFORE SCORING. Nothing has been scored for this arm when this file is committed.
Decision: Augusto, 2026-10-18 ("2"): the SMR manuscript is the journal version of arXiv:2610.06562, not a
sequel. It stops citing the preprint as prior work, so the preprint's main comparison (country adapters vs a
prompt that names the country) must be re-run inside the journal version, on all 42 countries and on the
Paper B frozen stack.

## 0. Why a re-run and not a transcription

The preprint's persona column (trust persona–GPS −0.07, adapter−persona 0.81 [0.16, 1.31], 16 countries)
cannot be carried into Paper B as is:

1. Different panel: 16 purposively chosen countries versus the predeclared 42-country GPS ∩ WVS7 cohort.
2. Different stack: Paper B scores on its own frozen stack (`PAPER_B_STACK_FREEZE.md`); the preprint's
   persona pass has no recorded model revision, tokenizer or scorer (`planning/pre_arxiv_checks/provenance/
   VERDICT.md`: verdict `not_established`).
3. Different adapters: the preprint's adapters are not the Paper B cohort-1 or bank-2 adapters.

Scoring the persona prompt on the Paper B stack makes the persona column comparable to every Paper B adapter
column by construction: same base weights, same loader, same spec, same readout. The two banked Paper B
base-model strict runs (`paper-b-20261011`, `bank2-strict-v1-20261016`) agree bit for bit (140 option rows,
max |Δ log p| = 0.0), so the stack is deterministic; G3 below checks it again on the persona VM.

## 1. The arm

| Item | Value |
|---|---|
| Model | meta-llama/Llama-3.1-8B-Instruct, no adapter, Paper B loader (`score_cohort.load_base_model_and_tokenizer`) |
| Prompt | strict-battery prompt `v1` with its first sentence replaced by "Answer this questionnaire as a typical adult living in [country name]." (`eval_lib.build_survey_user_prompt`, `prompt_country=cc`); this is the preprint's wording |
| Country names | `eval_config.COUNTRY_NAMES` (42 entries, frozen in the repository before this note) |
| Battery / spec | strict 23-item battery; spec pin `ed3bb964…fbf6` (the same spec as `strict_v1`; the country sentence is inserted at scoring time and is not part of the spec) |
| Readout | unchanged: space-prefixed option log probability, normalized over supplied codes, `E[recode]` |
| Units | the 42 cohort countries, one persona each |
| Condition / run id | `persona_strict_v1` / `persona-strict-v1-20261019` (Hub `Bonorinoa/SCA2-paper-b-artifacts`, `runs/<run_id>/`) |

Model-only: no respondent file is opened on the VM. Human data play no role in this arm.

## 2. Gates, all fatal, in order, before any persona unit is scored

- **G1 spec.** The driver rebuilds the spec and refuses unless its SHA-256 equals the pin.
- **G2 stack gate.** The existing adapter-path gate (`vm_gate_factorial.py`) runs on one real profile unit at
  the pinned adapter revision and writes the marker `score_cohort --model-only` requires. As for the sign-prompt
  cell, no adapter is loaded for the scored arm; the marker certifies the stack and the Hub write path.
- **G3 base parity.** The driver scores the unconditioned base model on the strict battery under the persona
  run id and compares it with the banked base of `bank2-strict-v1-20261016`. It stops before any persona unit
  if any option differs by more than 1e-2 in log probability or 1e-4 in probability (the Paper B base
  tolerances). The exact maximum gap is recorded whatever it is.
- **Completion.** "Done" means the Hub holds, for each of the 42 personas, the CSV and a manifest recording the
  pinned spec. The driver exits non-zero otherwise. An exhaustive per-unit audit (rows, option grids,
  probability sums, spec hash) runs before analysis.

## 3. Estimands (strict battery, 42 countries, the seven surfaces of `bank2_transport.SURFACES`)

Notation: ρ_R(s) is the country-equal Spearman correlation between route R's surface-s composite and the
GPS z of s's dimension over the 42 countries. Routes: C1 = cohort-1 country adapters (bank 1); B2 = bank-2
profile adapters mapped to countries; SP = sign-profile prompt (64 cells mapped to countries); P = persona.
C1, B2 and SP are banked; their composites come from the same files and code as the C3 analysis
(`paper_b/bank2_transport.py`, `AF.unit_composites`).

- **E1, persona column.** ρ_P(s) for each surface.
- **E2, primary contrast (one test).** D = ρ_C1(trust) − ρ_P(trust), the analogue of the preprint's
  adapter−persona contrast. Paired profile-block bootstrap: 26 sign-profile clusters
  (`analyze_surface.sign_profiles`), 2,000 draws, seed 20261011, percentile 95% interval; each draw recomputes
  both correlations on the same resampled countries. Reading: interval above 0 → the country adapters track
  the GPS trust order more closely than the named-country prompt; below 0 → the reverse; covering 0 →
  unresolved.
- **E3, secondary (descriptive, no test).** The same paired difference for every other surface with C1, for
  all seven surfaces with B2 and with SP, all with the E2 bootstrap. Reported with 95% intervals and labeled
  descriptive; no sentence may treat one of them as a test.
- **E4, resampling sensitivity.** E1 and E2 again under a plain country bootstrap (seed 20260905, the
  preprint's convention). The persona column alone has no shared-profile structure, so the country bootstrap
  is its natural interval; the profile-block version is the primary only because the paired contrast needs
  one resampling model for both columns and the adapter column needs the blocks.
- **E5, development-panel bridge (descriptive).** ρ_C1(trust) and ρ_P(trust) on the preprint's 16 development
  countries (CHN JPN GBR USA MEX ARG DEU RUS IND IDN NGA EGY TUR NLD BRA GRC), country bootstrap. These are
  Paper B stack numbers on that panel. No difference against the preprint's own numbers is computed; they come
  from another stack.

The persona composite is per country, so ρ_P is defined; the unconditioned base model has one composite for
all countries and stays without a correlation (base comparisons remain paired distances, as before).

## 4. Replay checks the analysis must pass before reading the persona numbers

- ρ_C1(s) and its interval reproduce `B2_cohort1_<s>_rho` exactly (same function, seed, clusters).
- ρ_B2(s) and its interval reproduce `B2_bank2_<s>_rho` exactly.
- The sign-prompt composites reproduce the factorial's sign-prompt cells on the 64 units.
- A synthetic fixture with a persona column equal to the C1 column gives D = 0 with a degenerate-free
  interval containing 0, and a column equal to the GPS gives ρ_P = 1.

## 5. What the result can and cannot change

- It adds a comparator. It does not earn either additional Paper B claim (transport, pre-piloting) and does
  not move any registered held-out number. The held-out screen keeps its registered comparators: the
  persona prompt has no sign-profile structure, so the registered probe (defined on 64 profile cells) does not
  apply to it, and this note does not extend the screen.
- The manuscript drops `gonzalezbonorino2026` as prior work, describes the 16-country stage as this study's
  development stage, and reports E1–E3 (main text: E1 and E2 for trust; supplement: all of them, E4, E5).
- New numbers enter only through `NUMBERS_TABLE.csv` (rows `PX_*`, built by `build_numbers_table.py` from
  the analysis JSON), with a dated claim-lock amendment C8 that records the new table hash.

## 6. Cost

Projected only after the first unit is measured (one persona = one base-model forward set over the strict
battery). The run is one T4 session: provision, G2, G3, 42 personas.
