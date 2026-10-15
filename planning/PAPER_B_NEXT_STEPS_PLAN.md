# Paper B — next steps: analysis, data generation, and the arXiv→journal transition

Drafted 2026-10-10 by Hermes (SCA profile). Planning document; no claim here
overrides `TWO_PAPER_CLAIM_LOCK.md` (claims) or `PAPER_B_PROTOCOL_DRAFT.md` (the run).

---

## 0. Where the cohort actually stands (verified live from Drive, 2026-10-10)

- **34 / 42 adapters complete** (weights + `run_record.json` on Drive).
- **Pending 8:** GRC, GTM, IDN, IND, IRN, IRQ, JOR, JPN — all of wave 1's last
  8. There is an **active T4 session `pb-c`** and an untracked
  `paper_b/colab/vm_rerun9.py` (GBR + the 8); nothing has landed yet.
- The wave-1 log shows **JOR and JPN saved**, but neither is on Drive. Root
  cause: the checkpoint dirs filled the Drive quota (commit `da6bb6c`), and
  FUSE uploads stalled silently. Fixed going forward by pruning checkpoints
  inside each adapter. **GBR still has `checkpoint-*` dirs** and should be
  swept.
- **No scoring stage exists for the cohort.** `paper_b/` ends at training.
  The WVS readout that produces the actual Paper B product was, for Paper A,
  notebook-driven (`DPO_eval_WVS/*.ipynb` → `survey_question_metrics_all_models.csv`).
  This is the real gap, not the last 8 adapters.
- Human side is ready: `analysis/phase2/outputs/paper_a/human_item_means_42.csv`
  (all 42 countries, strict item means) and the 42-country human–GPS map.

ASCII of the pipeline and what exists:

```
bank (658) ─► ref cache ─► prepare ─► TRAIN (42 adapters) ─► SCORE (WVS readout) ─► ANALYSIS ─► PAPER
   done         done        done     34/42  ◄ gap            MISSING for cohort     16-country only
```

---

## 0b. Decisions locked 2026-10-10 (Augusto)

1. **Transition depth = Option 2 (medium rewrite).** The 42-country surface
   becomes primary; the locked 16-country numbers move to a development /
   robustness subsection. Requires a dated amendment to `TWO_PAPER_CLAIM_LOCK.md`
   when the headline moves.
2. **Gate 4 (human check)** is re-scoped at the next strategy session:
   existing public microdata vs a collaborator's secured fielding pipeline.
   Until then Paper B's human-criterion claim stays unproven.
3. **Gate 2 route** (second bank vs sign-retrain) is decided **after** the
   42-country surface is scored — sequence the scorer before committing
   compute to a second wave.

Sequencing implied: close cohort → score → analyze 42 → amend claim lock →
gate-4 strategy session → gate-2 decision → rewrite.

---

## 1. Current arXiv version (Paper A) — what is published

- **Title:** *Synthetic Cultural Agents from Aggregate Anchors* — arXiv:2610.06562v1,
  2026-10-05 (econ.GN + cs.CL), ~8.1k words, "Working paper — September 2026".
- **Object:** an inspectable compiler from declared GPS `sign(z)` → a shared
  658-pair A/B bank → one joint QLoRA-DPO adapter per group
  (*anchored synthetic choice policy*). Evaluation prompts omit country names.
- **Three separate columns:** human–GPS (map coherence), adapter–GPS (anchor
  retention on new text), adapter–human (agreement with people); encoding of
  held-out synthetic pairs is a construction check, not GPS recovery.
- **Headline surface:** a 16-country purposively selected development panel
  from two saved jobs; 23-item strict rectangle; 13 sign profiles; 3 twins.
- **Locked numbers:** encoding recovery 0.942 / accuracy 0.819 (2,112 cells);
  trust adapter–GPS **0.74 [0.44, 0.88]**; persona −0.07; adapter−persona 0.81;
  adapter–human 0.32 [−0.22, 0.77] (unresolved); human–GPS 0.39 [−0.18, 0.79];
  42-country human–GPS 0.35 [0.09, 0.56]; adapter TVD 0.487 vs base 0.369;
  trust rank-biserial 1.00.
- **Honest frame:** underpowered, wide intervals, human agreement unresolved,
  pre-piloting prospective. Its own text flags the discretionary 16-country
  set as the weakness a later study must fix.

---

## 2. Goal version for journal submission (Paper B, SMR after coauthor sign-off)

**Shift of object:** from "can an anchored policy retain a declared aggregate
signal" to "the same compiler as a **scoring instrument for new item text**,
with a human criterion on items the probe selects."

**Required evidence (claim lock §Paper B), none of which Paper A has:**

| # | Gate | State |
|---|---|---|
| 1 | No discretionary country set: train all 42 (or predeclared random sample) | 34/42 trained; twins become a reliability contrast |
| 2 | Sign-retrain (relabel + refit) **and/or** a second scenario bank | not started |
| 3 | Sign-profile prompt cell (same info, different route) | not started |
| 4 | **Independent human check of probe-selected items** | **blocker** |
| 5 | Magnitude / per-dimension adapters | optional; separate protocol paper |

**Claims unlocked only with that evidence:** a new battery's adapter–GPS is
readable as anchor transport after calibration vs human–GPS; pre-piloting
changes item selection relative to a human-only path.

**The gate that decides everything is #4.** Memory and the protocol agree there
is no secured self-collection channel. Paper B's central claim needs a human
criterion on probe-selected items, which must come from existing public
microdata or a collaborator's secured pipeline. Without it, Paper B can still
report the 42-country surface + gates 2–3, but the "scoring instrument with a
human criterion" claim stays weak and pre-piloting stays prospective.

---

## 3. The compute/analysis track after training closes

### 3.1 Close the cohort (ops)
1. Re-run `vm_rerun9` to completion; confirm 42/42 weights + records.
2. Sweep stale `checkpoint-*` dirs (GBR and any pre-fix adapter).
3. Build a cohort provenance manifest: per country read `run_record.json`
   (beta, lr, r, bank_run_id, train_minutes), hash the bank and each adapter,
   log git SHA. This replaces the "unverified checkpoint-to-run" caveat.
4. Re-run `verify_gates.py`; assert twin groups and the shared split.

### 3.2 Scoring stage (new code — the critical path)
- New `paper_b/score_cohort.py`: for each of 42 adapters (and the base and
  persona arms), score the 23 common-support WVS items with the frozen readout
  (leading-space option-code logprob, softmax over supplied codes, no country
  name) plus the GPS recovery items; write
  `model_option_probabilities_{CC}.csv` and `survey_question_metrics_{CC}.csv`.
- **Regression gate before trusting anything:** re-score one Paper A country
  (e.g. CHN) and match its row in the saved
  `survey_question_metrics_all_models.csv`. If it does not reproduce, stop.
- Cost: minutes per adapter; well under a session. Cheap.

### 3.3 Analysis on the 42 (mostly CPU; reuse `analysis/phase2`)
- Parameterize the hardcoded `C16` to the full 42 (scripts 13, 16, 19, 22).
- adapter–GPS and adapter–human on 42 with country bootstrap; human–GPS on the
  full strict set.
- **Twin reliability contrast:** 12 twin groups / 26 distinct profiles →
  variance of the fitted scores within a sign profile = fitting noise under a
  frozen protocol. Report as a decomposition, not a country difference.
- **Near-zero robustness:** recompute with `|z| ≥ 0.10` for affected countries;
  print per-country exposure alongside.
- New figures: associations at n=42, twin reliability, near-zero sensitivity.

### 3.4 Paper B gates (new science — needs GPU budget)
- Gate 2 options: (a) second scenario bank (regenerate the 658 pairs with a
  new generator), (b) sign-retrain (relabel from raw GPS with a new rule/seed
  and refit 42). Either ~doubles training ≈ 15 T4-units → top-up decision.
- Gate 3: sign-profile prompt cell — same signs delivered by prompt; isolates
  "route" from "information".
- Gate 4: field the human check (blocked — see §2).

---

## 4. Transition: arXiv → journal. Depth options.

The 16-country surface is superseded as the *headline* by the 42-country
surface, and the paper itself names the discretionary set as its weakness. That
makes a light append dishonest-looking to reviewers; it is not a copy-paste job.

| Option | What happens | Cost | Risk |
|---|---|---|---|
| **1. Light append** | Keep 16-country as primary; add 42 + gates as sections | ~2–3 wks | Paper fails to update its own flagged weakness |
| **2. Medium rewrite (recommended)** | Promote **42 = primary**; demote 16 to development/robustness; add gate results; rewrite abstract/intro/results/discussion; keep methodology + appendix protocol | ~4–6 wks | Needs a dated claim-lock amendment (headline changes) |
| **3. Full standalone** | New paper citing the preprint as the construction paper | ~8–10 wks | Loses momentum; two objects to maintain |

**Recommendation: Option 2.** It is the smallest change that makes the paper
defensible, it loses nothing (the locked numbers survive as the development
panel), and the 42-cohort was built by the frozen protocol precisely to answer
this critique. Option 2 is conditional on gate 4; if the human check cannot be
fielded, fall back to Option 1 (append 42 + gates 2–3, pre-piloting stays
prospective) and be explicit about it.

### Models for writing
- **Structure, claim discipline, figure/table specs, transitions:** this
  session (Hermes, claim-lock loaded). Deterministic; no model writes a number.
- **Narrative prose passes (voice):** a frontier long-context writer driven by
  the `augusto-academic-voice` skill — Claude Opus/Sonnet-class or equivalent.
  Constraint: positive claims only, no ", not Y" kickers, no humanizer, spare
  statistics in the abstract.
- **Substantial code (score_cohort.py, analysis plumbing):** Codex in VSCode
  (your preference), given scoped prompts.
- **Every reported number:** `reproduce_tables.py` + HASHES gate. Never a model.

---

## 5. Immediate checklist (before the 42 finish)

- [ ] Let `vm_rerun9` finish; confirm 42/42; sweep checkpoints.
- [ ] Write `score_cohort.py` + the CHN regression gate.  ← do this next
- [ ] Draft the cohort provenance manifest spec.
- [ ] Score the 42 and freeze the surface (unblocks the gate-2 decision).
- [ ] Schedule the gate-4 strategy session (public microdata vs collaborator).
- [ ] Decide gate-2 route after scoring; budget the top-up.
- [ ] Dated amendment to the claim lock as the headline moves to 42.
