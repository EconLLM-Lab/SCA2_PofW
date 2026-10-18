# float32 vs float64 conservation gaps (SmolLM2-135M family)

Card `t_1547e1a8`. Produced by `plans/scripts/f32_gaps.py`; raw records in
`plans/scripts/out/f32_gaps.json`, long-format in `plans/stage1_f32_gaps.csv`.

Same checkpoint, same prompt, two passes: float64 (the reference) and float32. 3 models x 6 items = 18 pairs, T = 136-306. The relative error is
`|error| / scale` with the scales `sca2_workbench.gates` divides by, so it is directly
comparable with the taus below.

## 1. Worst relative error per check

| check | float64 max | where | float32 max | where | float32 scale at that point |
|---|---|---|---|---|---|
| residual closure | 5.45e-15 | smol_base / wvs_Q81 | 6.23e-06 | smol_base / wvs_Q81 | max abs h = 891 (abs error 5.55e-03) |
| head closure | 0 | smol_inst_usa_e3 / wvs_Q81 | 0 | smol_inst_usa_e3 / wvs_Q81 | max abs a = 191 |
| readout (DLA) | 2.13e-14 | smol_base / bank_USA_7232414df567 | 2.28e-05 | smol_inst / wvs_Q43 | |margin| + 1 = 1.04 |
| vs HF reference | 6.14e-15 | smol_base / wvs_Q57 | 4.44e-06 | smol_inst / wvs_Q57 | max abs logits |

Across the 18 pairs, `max|h|` runs from 891 to 4.43e+03: the
stream is dominated by one very large entry, which is why an absolute gate measured in
its units stops being informative. The absolute residual error at the worst point is in
the table above; one float32 ulp of that entry is 1.19e-7 x `max|h|`.

## 2. float32 fidelity to the float64 pass

How far the float32 numbers move from the float64 ones. This is not a conservation
gate (nothing in the pass can fail it); it bounds what a float32 export changes on
screen.

| quantity | max relative error | where |
|---|---|---|
| margin | 3.50e-05 | smol_inst / wvs_Q43 |
| logits | 3.41e-06 | smol_inst / wvs_Q57 |
| probs | 1.94e-05 | smol_inst / wvs_Q43 |

## 3. Per layer (float32, computed in float64 on the stored pieces)

| check | max relative error | where |
|---|---|---|
| residual closure, layer 29 | 2.28e-07 | smol_base / wvs_Q81 |
| head closure, layer 16 | 1.80e-07 | smol_inst_usa_e3 / wvs_Q81 |

Worst residual closure per layer, max over the 18 pairs:

| layer | 0 | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 | 16 | 17 | 18 | 19 | 20 | 21 | 22 | 23 | 24 | 25 | 26 | 27 | 28 | 29 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| rel | 4.7e-08 | 2.9e-08 | 4.3e-08 | 7.1e-08 | 7.4e-08 | 5.0e-08 | 6.4e-08 | 7.4e-08 | 9.0e-08 | 8.2e-08 | 1.4e-07 | 4.0e-08 | 1.2e-08 | 5.2e-08 | 2.0e-08 | 6.3e-08 | 4.8e-08 | 7.7e-08 | 4.0e-08 | 5.4e-08 | 3.9e-08 | 4.8e-08 | 2.1e-08 | 5.7e-08 | 4.3e-08 | 7.3e-08 | 4.0e-08 | 6.2e-08 | 1.9e-07 | 2.3e-07 |

## 4. Tau per gate

`tau = 10 x the largest relative error measured above, rounded up to the
next power of ten. The multiple is a judgement, not a law: 10x sits well above the
measured worst case (so the gate is not flaky) and far below the failure we care about
(a dropped head write, section 5: up to 218x over tau in residual closure and 361x in readout
for float32, and more than 1e11x in float64). The rounding to a
power of ten keeps the number readable and adds headroom rather than taking it away.

| check | measured float32 max | x10, rounded up | measured float64 max | x10, rounded up |
|---|---|---|---|---|
| residual closure | 6.23e-06 | 1e-04 | 5.45e-15 | 1e-13 |
| head closure | 1.80e-07 | 1e-05 | 9.10e-17 | 1e-15 |
| readout (DLA) | 2.28e-05 | 1e-03 | 2.13e-14 | 1e-12 |
| vs HF reference | 4.44e-06 | 1e-04 | 6.14e-15 | 1e-13 |

For `head_closure` the measured column is the float64-checker form of the same identity
(section 3); in the shipped form the error is exactly 0 in both dtypes.

`head_closure` is the exception to the rule: it is **exactly 0.0** in both dtypes, because
the gate compares `a = o.sum(0)` with `o.sum(1)` -- the same sum, computed twice. What a
rewrite of that sum could produce is bounded by the same identity summed in float64:
1.80e-07 in float32 (section 3) and 9.1e-17 in float64, so
`head_closure` tau is 10x that, rounded up (1e-5 / 1e-15).

`pair_attribution` is not measured here: it is the B - A gate and this script exports no
pair. It keeps the value the pair gate already had (1e-6), which covers the looser of its
two forms, the sum of the stored float32 arrays (worst 7.4e-8 over the 16 exported pairs).

## 5. The broken capture: one head's write dropped

The same capture with `drop_head_write=(l, h)` at the (layer, head) with the largest
write, run through `run()`: both *stored* pieces lose that head, the residual stream
keeps it. Ratio = the gate's relative error / its tau; above 1 means the gate fails.

| check | float32 worst ratio | where | float64 worst ratio | where |
|---|---|---|---|---|
| residual_closure | 218 | smol_base / bank_USA_f48d3d37c50e (L23H3) | 2.18e+11 | smol_base / bank_USA_f48d3d37c50e (L23H3) |
| readout | 361 | smol_inst / wvs_Q43 (L29H1) | 3.61e+11 | smol_inst / wvs_Q43 (L29H1) |
| head_closure | 0.00406 | smol_inst_usa_e3 / bank_USA_7232414df567 (L29H1) | 0.0906 | smol_inst / bank_USA_00023ac74dac (L29H1) |

`head_closure` stays under its tau by construction: both stored pieces lost the same
head, so they still agree with each other. The gate that catches this bug is the residual
closure (the pieces no longer add up to the stream) and the readout (the head's
attribution is gone from the DLA sum).

## 6. The taus in `gates.py` are these numbers

- derived from these measurements: `f64 residual_closure = 1e-13`
- derived from these measurements: `f64 readout = 1e-12`
- derived from these measurements: `f64 reference = 1e-13`
- derived from these measurements: `f32 residual_closure = 1e-04`
- derived from these measurements: `f32 readout = 1e-03`
- derived from these measurements: `f32 reference = 1e-04`

Checked against `sca2_workbench.gates`: **all six agree**.
