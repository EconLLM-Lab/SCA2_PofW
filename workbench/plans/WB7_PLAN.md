# WB7: last wave before sharing (2026-10-21)

Owner request (Augusto, 2026-10-21, after v1.4 went live), condensed. He reads these as the four deliverables:

1. **Ground truth.** "Did most humans of the selected country answer closer to what the model believes?"
2. **What is a clamped run?** It must be explained in plain words where it appears.
3. **How to read each view.** The "details" and "?" pop-ups must say how to read every chart and metric in that view.
4. **Q57 everywhere.** "Could we get the infamous Q57 in the workbench?" Each adapter currently shows a different set of
   questions (CHN has Q57, USA does not), and he asked whether that is by design. It is a bundle-size choice, not an
   experiment design: see below.

He also flagged one interpretation problem, which this wave fixes:

5. **Many-option questions.** On a 10-point question (Q176, base vs USA adapter) the headline says "B leans further
   toward '1' than A: +9.83", while the most likely answer moves from 5 to 6, away from "1". The cause: the headline
   reports log P("1")/P("10"), the two end answers, and both are near zero.

Routing: Codex and Grok are out of quota. Producers on open models run through OpenRouter (DeepSeek v4.1 Flash, GLM 5.3).
The OpenRouter credit is about $13. Licensed human data goes only to the ASU Claude seat (`anthropic`). Verifiers come
from a different family than the producer. `sca` triages this wave and later integrates and deploys it.

## Why each adapter shows different questions (answer for item 4)

Every adapter was scored on every item. The exports on disk include Q57 for the base model, all 42 country adapters
and all 26 six-sign prompts. A full capture is about 22 MB per run, and the Space has a 1 GB storage cap (v1.4 uses
0.916 GB). So `scripts/build_deploy_bundle.py` ships a sample. The sample covers the story's featured adapters on
their featured questions, plus matching sign prompts, but only for the largest adapter-margin gap per sign. That is why
CHN and BGD have Q57 and USA does not. About 2.5 MB of a run file feeds every view except the 3D tab and pinned-head
attention. That light part is what makes "Q57 for every country" fit.

## Cards

| Card | Profile, model | Worktree / branch | Depends on |
|---|---|---|---|
| WB7-0 triage | `sca`, Claude (ASU seat) | read only | none |
| WB7-Q Q57 for all 42 adapters and 26 sign prompts (light runs) | `engineer`, DeepSeek v4.1 Flash | `adapter-brain-vizualization` (real exports) | WB7-0 |
| WB7-H ground truth (country-level WVS-7 shares) | `creative`, Claude Sonnet (ASU seat) | same worktree, after WB7-Q | WB7-Q, WB7-R |
| WB7-W how-to-read pop-ups, clamped run, many-option headline | `writer`, Claude Sonnet (ASU seat) | `.worktrees/wb7-words`, branch `wb7-words` | WB7-0 |
| WB7-R data-rights check (public sources only) | `verifier`, GLM 5.3 | read only; writes `plans/WB7_DATA_RIGHTS.md` | WB7-0 |
| WB7-I integrate and build the candidate (no deploy) | `sca`, Claude (ASU seat) | `adapter-brain-vizualization` | WB7-Q, WB7-H, WB7-W |
| WB7-V verify the integrated build | `verifier`, DeepSeek v4.1 Flash (cross-family to the Claude producers) | read only | WB7-I |
| WB7-D deploy v1.5, live check, records | `sca`, Claude (ASU seat) | `adapter-brain-vizualization` | WB7-V |

The DeepSeek verifier also covers WB7-Q, which a DeepSeek model produced. For that part it checks only deterministic
facts (byte identity, index numbers against export JSON, storage), not judgment calls, and the PM reads its diff.

## Gates (every card repeats the ones that apply)

- **Storage.** The total Space payload stays at or under 0.95 GB (the cap is 1 GB). Check the
  `deploy_bundle.tar.manifest.json` byte total.
- **Number parity.** The 33 parity URLs show the same numbers as v1.4. Only changes this plan names are allowed: the
  many-option headline, and new rows or panels.
- **No human rows.** At most one country-level aggregate per (country, question, answer), rounded to whole percent,
  with n and the WVS-7 source. Nothing ships unless WB7-R rules it "permitted" or "permitted with attribution". If
  WB7-R rules "unclear" or "not permitted", the build ships without the human layer (a build flag, off by default).
  The PM then tells Augusto, who would consult the ASU data steward.
- **Held-out items.** Human figures come only for items outside the Paper B held-out pool (`paper_b/heldout/`). The
  seven workbench items are mapped development items. WB7-H confirms that in code.
- **Wording.** Model output is a probability, never what people "say". Human figures read "In the World Values Survey
  (wave 7), X% of respondents in <country> chose …". Say "descriptive", never "validation" or "accuracy". No Paper B
  claim is strengthened. Paper B numbers come only from `NUMBERS_TABLE.csv`.
- **Locks.** `HF_TOKEN=` blank in tests. Commit by explicit path. Never `git add` the symlinks. No push or deploy
  except by WB7-D after WB7-V passes. No country name in evaluation prompts (nothing here re-runs a model).

## Card ids (board `sca2-paper-b`)

WB7-0 `t_65abd013` · WB7-Q `t_7f9ce31a` · WB7-W `t_91b4bfea` · WB7-R `t_7b5d88a3` · WB7-H `t_63edca34` ·
WB7-I `t_67420af5` · WB7-V `t_ab5d175a` · WB7-D `t_689970a1`. Worktree `.worktrees/wb7-words` (branch `wb7-words`) is WB7-W's.
