# Walkthrough: the paper protocol as a CLI

This is the tutorial that belongs with `feat/sca2-protocol-cli`.
The scientific object is `protocols/gps_sign_dpo_wvs.toml`.
The CLI only runs it.

```
PYTHONPATH=".:synthetic_generation" python -m sca2 <verb> \
  --protocol protocols/gps_sign_dpo_wvs.toml
```

## The operator, one table at a time

| Letter | Protocol table | Verb | What actually happens today |
|---|---|---|---|
| \(Z\) | `[anchor]` | (input) | Falk 2018 country z, 76 complete vectors |
| \(R\) | `[profile]` | unused by sign-relabel | country name stripped if you ever render |
| \(G\) | `[generation]` | `generate` then `label` | inspect hashed bank; flip A/B by `sign(z)` |
| \(S\) | `[qc]` | inside `generate` | inherited scores; polarity warning; no gate |
| \(Q\) | `[prompts]` | declared | `country_conditioning = false` |
| \(A\) | `[train]` | `train` | freeze DPO/QLoRA knobs; refuse `--execute` |
| \(E\) | `[eval]` | `eval` | freeze WVS item map; refuse `--execute` |

`report` stitches the four stage receipts by protocol hash.

## Commands

```bash
PYTHONPATH=".:synthetic_generation" python -m sca2 show     --protocol protocols/gps_sign_dpo_wvs.toml
PYTHONPATH=".:synthetic_generation" python -m sca2 generate --protocol protocols/gps_sign_dpo_wvs.toml
PYTHONPATH=".:synthetic_generation" python -m sca2 label    --protocol protocols/gps_sign_dpo_wvs.toml
PYTHONPATH=".:synthetic_generation" python -m sca2 train    --protocol protocols/gps_sign_dpo_wvs.toml --countries USA MEX
PYTHONPATH=".:synthetic_generation" python -m sca2 eval     --protocol protocols/gps_sign_dpo_wvs.toml
PYTHONPATH=".:synthetic_generation" python -m sca2 report   --protocol protocols/gps_sign_dpo_wvs.toml
```

`generate --materialize`, `train --execute`, and `eval --execute` exit 2
on purpose. A new bank or a local GPU trainer is a new protocol, not a flag.

## What each receipt is allowed to mean

- **generate `bank_reused`** — the June 23 A/B file is present and
  polarity-checked. It is not a new sample of scenarios.
- **label `ok`** — `chosen = A` iff \(z\ge 0\). Intensity \(|z|\) is unused.
- **train `planned`** — knobs match `DPO_train.ipynb`. No adapter was fit.
- **eval `planned`** — 35 items, 30 mapped, 5 demographic. Matched-vs-cross
  is fixed-policy proximity, not country-conditioned inference.
- **report `chained`** — those four receipts share one protocol hash.
  The file is a citation object, not a result.

## Notebooks

Leave Drive paths in `DPO_train_test/*.ipynb` alone.
Optional client: [`../DPO_train_test/SCA2_PROTOCOL_CLIENT.md`](../DPO_train_test/SCA2_PROTOCOL_CLIENT.md).

## Tests

```bash
PYTHONPATH=".:synthetic_generation" python sca2/tests/run_tests.py
PYTHONPATH=".:synthetic_generation" python -m pytest synthetic_generation/tests/test_relabel.py -q
```
