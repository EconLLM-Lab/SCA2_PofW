# B0 device benchmark: Mac vs Colab GPUs for the 43-model workbench cohort

Measured 2026-10-18 by `sca` (card `t_2a09b675`, claude-sonnet-5-5). The worker was interrupted (exit 130) twice after the measurements and projections were on disk. The PM assembled this report from the raw files in this directory and added no numbers. Per-unit and per-device tables are in `tables.md`; projections are in `projection.json` / `proj_out.txt`.

**Spend:** 3.16 CU (186.66 → 183.50). After the run, 0 sessions and rate 0.00/hr (PM check, `colab sessions` / `colab usage`).
**H100:** not entitled on this account (`h100/new.log`: "Backend rejected accelerator 'H100'").

## 1. Measurements

Benchmark set: base + ARG × {Q57 (K=2), Q81 (K=4), Q107 (K=10)}, `nf4_dequant` float64, plus ARG × {Q57, Q107} in float32.

| device | setup min | CU/h measured | ARG f64 s/unit | base f64 s/unit | f64 gates | f32 gates | max parity ulp (f64) |
|---|---:|---:|---:|---:|---|---|---:|
| Mac M4 Pro (CPU codes) | 0 | 0 | 65.3 | 32.5 | 6/6 | **0/2** | 5.07 |
| A100-80GB high-mem | 2.6 | 6.77 | 80.4 | 59.2 | 6/6 | 1/2 | 4.66 |
| L4 | 2.7 | 1.54 | 110.9 | 73.4 | 6/6 | 1/2 | 4.66 |
| T4 | 9.8 | 1.07 | 212.7 (n=1, rest skipped by the 3×-Mac rule) | n/a | 1/1 | 1/2 | 2.12 |
| G4 (RTX PRO 6000 Blackwell) | 2.0 | 8.90 | **30.5** | **21.1** | 6/6 | **0/2** | 4.66 |

Observations:
- **The A100 is slower per unit than the Mac.** Capture alone takes 25 s versus the Mac's 34–43 s, but process load (13.7 s) and the float32 HF reference forwards plus writes (41 s) dominate the A100's wall time. A3's "A100 pilot" assumption is therefore not the cost-efficient choice.
- **float32 fails the pair-attribution gates** (`d_attr_gap*`) on 5 of 10 units across devices, and on every Mac and G4 unit. f32 is not a viable cohort mode. **float64 stays.**

## 2. NF4 code equality (decision-critical)

`nf4_compare.json`, `nf4_effect.json`, `nf4_cross_cuda_devices.json`:
- **The 4-bit codes are bitwise identical** between CPU (Mac, bnb 0.50.2) and CUDA (A100) in every tensor checked.
- **The double-quantized absmax differs** in about 0.1–0.17% of blocks. All 224 quantized Linear files therefore differ by sha. The largest dequantized weight difference is 0.0043; the RMS difference is about 3e-6 to 1e-5, roughly 0.5% of the NF4 quantization error itself.
- **Readout effect, Mac CPU codes vs A100 codes:** at most 0.021 nats and at most 0.00096 in probability across the 6 units.
- **Across CUDA devices:** A100, L4 and G4 are identical (224/224). **T4 differs from A100 in 16 of 224 files.** The Paper B archive was scored on a **Tesla T4** (`paper_b/compute/publication_estimate.json`), so T4-quantized weights are the closest match to the production instrument. T4 also gives the best parity (≤2.12 ulp vs ≥4.66 elsewhere, on the one unit pair measured).

## 3. Projection: 989 units (23 base + 966 adapter), f64, 183.50 CU available

| device | wall h central (upper) | CU incl. Hub sync, central (upper) | fits |
|---|---:|---:|---|
| **Mac** | **17.7 (21.2)** | **0** | n/a |
| **G4** | **8.3 (9.3)** | **91 (100)** | yes, using about half the balance |
| L4 | 30.2 (32.4) | 52 (55) | yes |
| T4 | 58.4 | 68 | yes |
| A100 | 21.9 (22.1) | 167 (168) | barely; uses about 91% of the balance |

Not included: reclaim overhead. That is about 3 min re-provision plus NF4 re-prep per loss, with losses every ~4 h or more on Colab; it applies to Colab rows only.

## 4. Recommendation (PM). Augusto decides.

**Mac capture on frozen T4-CUDA NF4 weights: 0 CU, about 18–21 h, float64.**
1. Quantize the base once on a **T4** (about 10 min setup, about 0.2 CU), and export the quant state (codes, absmax, nested state). That is A3's "frozen NF4 instrument" (`DECISIONS.md`), now pinned to the archive's own device.
2. **Precondition check (cheap, not yet measured):** dequantizing the same frozen state on CPU must equal dequantizing it on CUDA bit for bit. Dequantization is a deterministic lookup × scale, so this is expected, but run it before relying on it.
3. Run the 989 units on the Mac with `runner/unit.py`, one 8B process at a time (7–8 GB RSS), under `caffeinate` and on AC power. The runner's per-unit resume makes interruptions cheap. Then upload to the Hub with one authenticated sync.

Why: it costs nothing, it uses the exact production quantization, it has no Colab reclaim risk, and the Mac's f64 speed is competitive.

Trade-offs:
- The Mac is busy for about a day; light use is fine.
- A Mac sleep pauses the run, but does not lose work.
- About 25 GB of exports must be uploaded from home bandwidth.

**Fast alternative: G4, about 8–9 h, about 91–100 CU.** Use the same frozen T4 state, uploaded to the VM. A **hybrid** (Mac and G4 splitting the queue) gives about 6 h for about 45 CU.

**Not recommended:**
- A100: the most CU for no speed gain.
- f32 on any device: it fails the pair gates.
- H100: unavailable.
