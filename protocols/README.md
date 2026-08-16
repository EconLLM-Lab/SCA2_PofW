# SCA2 protocol files

A protocol file is the scientific object. The CLI only *runs* it.
The paper application (`gps_sign_dpo_wvs.toml`) is one frozen instance of

```
P = (Z, R, G, S, Q, A, E)
```

mapped onto the code that already exists in this repo.

## CLI surface (progress)

Work through these in order. Do not skip ahead to train/eval wiring
until `label` and `generate` both write a receipt.

| # | Surface | Status |
|---|---------|--------|
| 1 | Protocol file as the declared operator | done |
| 2 | CLI skeleton (`python -m sca2`) + run directory / receipt | done |
| 3 | `sca2 label` (deterministic sign-relabel) | done |
| 4 | `sca2 generate` (inspect/reuse frozen bank; no HF) | done |
| 5 | `sca2 train` (DPO / QLoRA) | not started |
| 6 | `sca2 eval` (WVS / placebos) | not started |
| 7 | Manifest hash-chain + `report.json` | not started |
| 8 | Notebooks as thin clients (no Drive-path breakage) | not started |

## Ownership

Researcher vs pipeline degrees of freedom: [`DEGREES_OF_FREEDOM.md`](DEGREES_OF_FREEDOM.md).

## Layout

```
protocols/gps_sign_dpo_wvs.toml   # paper special case (this folder)
sca2/                             # CLI package (repo root)
runs/<run_id>/                    # created by a CLI invocation; gitignored
```

## Rule

Changing a field in the protocol is a new scientific object.
Do not “just tweak the notebook.” Copy the file, bump the name, freeze again.
