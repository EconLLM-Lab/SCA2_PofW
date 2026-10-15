# Ease of replication — second bank and prompt cell, 2026-10-11

Two things were attempted: a new shared scenario bank (C2), and a sign-profile prompt cell (C1). C2 is blocked. C1 ran. Both experiences are recorded here as-is.

## C1 — sign-profile prompt cell: ran, 29.6 minutes

Replicable, but not the first time. What it took:

| Attempt | Outcome |
|---|---|
| 1 | Session `pb-signprompt`. Frozen stack installed, then the control connection died mid-launch and Colab pruned the VM. Install lost. |
| 2 | Session `pb-sig2`. Job launched in the foreground; the client died again before the child started. No log file. |
| 3 | Same session. Launched the child **detached** with its stdout redirected to a VM file. Ran clean. |

Three mechanical lessons, now encoded in the scripts:

1. **Launch detached.** A foreground `colab exec` dies with its client. `subprocess.Popen(..., start_new_session=True)` with stdout to a file survives it.
2. **Never import `transformers` before pinning it.** The Colab image carries 5.18.0; importing it first put 5.x in `sys.modules` and the 4.46.3 pin silently did nothing. Check with `importlib.metadata.version`, not `import`.
3. **A stale bundle is a silent wrong run.** The first detached launch used the pre-patch script, because the tarball was packed before the last edit. The launcher now greps the extracted file for a symbol that only the patched copy has.

Measured: 23 questions, 140 option rows per profile. One pilot profile through the frozen path took 4.98 min including model load; the full 26 profiles took 29.58 min, about 1.1 min each. Probabilities summed to 1 within 7.8e-16. 26/26 files uploaded to the Hub and read back locally.

## C2 — second bank: blocked on token scope

The documented generator is `synthetic_generation/run.py`. It calls dedicated Hugging Face inference endpoints named in `sca2_datagen/config.py`:

- teacher `llama-3-3-70b-instruct-gguf-fnk` — facet and scenario generation
- generator `qwen3-32b-chm` — fixed triplet generation
- scorer `phi-4-uid` — optional diagnostic, not used by a sign-rule bank

Probed 2026-10-11 with the SCA profile token (value never recorded here):

| Endpoint / URL form | No token | With the profile token |
|---|---|---|
| teacher, bare host | 401 | 403 `missing permissions: inference.endpoints.infer.write` |
| teacher, bare host + `/v1` | — | 403 same |
| teacher, `us-east-1.aws` + `/v1` (the form in config) | 401 | 403 same |
| generator, `us-east-2.aws` + `/v1` | 401 | 403 same |
| scorer | 401 | 403 same |

Every host answers, so nothing has been undeployed. The token that scores and uploads Paper B adapters lacks `inference.endpoints.infer.write`. The supplied 70B URL is the same deployment already in `config.py`; the URL was never the blocker.

**One model is not enough even with a working token.** The pipeline uses the teacher for scenarios (two call sites) and the generator for triplets (one call site). The scorer is genuinely optional for a sign-rule bank. Pointing the generator stage at the 70B would confound "new wording" with "new model", so it belongs in the notes, not in the run.

**Generation did not start. No pairs were written. Nothing was padded or trimmed.**

## What a permitted token would run

From `synthetic_generation/`:

```
python build_bank2.py --out-root outputs/bank2_20261011
```

That wrapper runs generation at `--scenarios-per-dim 110` (the setting that produced the source bank's 658 triplets) then `relabel.py` under `deterministic_sign`, and prints the exact gate command. Or by hand:

```
python run.py --scenarios-per-dim 110 --scenario-batch-size 6 --concurrency 4 \
  --labeling deterministic_sign --countries USA --use-anchors True \
  --output-dir outputs/bank2_raw_20261011
python -m sca2_datagen.relabel \
  --checkpoint outputs/bank2_raw_20261011/checkpoint_raw_pairs.jsonl \
  --output-dir outputs/gps_sign_relabel_bank2
```

Then from the repo root:

```
python paper_b/verify_gates.py --bank-dir synthetic_generation/outputs/gps_sign_relabel_bank2 --scan-text
```

If that count is not 658, stop. Do not trim the file to force the gate.

## Friction worth fixing

- `run.py` has no triplets-only mode. A sign-rule bank pays for a scorer endpoint it never reads. A `--skip-scoring` flag would remove one of three endpoint dependencies.
- The token needs `inference.endpoints.infer.write`. This is the single blocking item for C2.
