# Bank-2 transport on the strict battery (checkpoint C3)

Produced by `paper_b/bank2_transport.py`; every number below is read from
`bank2_transport_strict.json`. Seeds: bootstrap 20261011, 2000 draws, percentile interval.
Cohort: 42 countries in 26 factorial cells (26 GPS-sign profiles).

## Inputs

- cohort1_strict: `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/cohort1_strict.csv` sha256 `047cd0e45959…`
- adapter_strict_v1: `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/adapter_strict_v1.csv` sha256 `3683d2211767…`
- gps_z: `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json` sha256 `02972f0ec4a8…`

## Method

Step 1 reproduces the banked cohort-1 adapter-GPS Spearman per surface
(profile-block bootstrap, clusters = GPS-sign profile). Step 2 gives each of
the 42 cohort countries the composite of its sign-profile unit on bank 2
(`factorial.unit_of_z` on the GPS z vector) and correlates it with the
surface's own GPS dimension, profile-block bootstrap. Step 3 correlates
bank-1 cell means with bank-2 profile composites over the shared cells, with
a 2,000-draw bootstrap over cells.

## Table 1 — seven surfaces

| Surface | Imprint | Cohort-1 rho [95% CI] | Bank-2 rho [95% CI] | C3 reading |
|---|---|---|---|---|
| trust | yes | 0.744 [0.500, 0.865] | 0.803 [0.615, 0.876] | transport holds |
| risktaking | yes | 0.435 [0.085, 0.686] | 0.210 [-0.199, 0.584] | transport dropped: interval includes 0 |
| posrecip | yes | 0.488 [0.120, 0.695] | 0.366 [-0.068, 0.652] | transport dropped: interval includes 0 |
| altruism | yes | 0.406 [0.020, 0.676] | 0.364 [-0.057, 0.653] | transport dropped: interval includes 0 |
| negrecip | no | -0.028 [-0.418, 0.406] | 0.239 [-0.237, 0.604] | reported (not an imprint dimension) |
| patience:Q43 | no | -0.019 [-0.414, 0.452] | 0.005 [-0.403, 0.470] | reported (not an imprint dimension) |
| patience:Q50 | no | 0.177 [-0.313, 0.580] | 0.161 [-0.343, 0.557] | reported (not an imprint dimension) |

## Table 2 — bank-to-bank agreement (26 shared cells)

| Bank-to-bank | Surface | Pearson [95% CI] | Spearman [95% CI] |
|---|---|---|---|
| Bank-to-bank | trust | 0.909 [0.797, 0.965] | 0.907 [0.774, 0.957] |
| Bank-to-bank | risktaking | 0.598 [0.229, 0.819] | 0.544 [0.187, 0.772] |
| Bank-to-bank | posrecip | 0.898 [0.775, 0.960] | 0.937 [0.818, 0.983] |
| Bank-to-bank | altruism | 0.949 [0.859, 0.989] | 0.944 [0.832, 0.985] |
| Bank-to-bank | negrecip | 0.708 [0.488, 0.861] | 0.600 [0.230, 0.838] |
| Bank-to-bank | patience:Q43 | 0.812 [0.699, 0.945] | 0.889 [0.682, 0.971] |
| Bank-to-bank | patience:Q50 | 0.940 [0.890, 0.975] | 0.953 [0.856, 0.982] |

## C3 reading

Imprint dimensions whose bank-2 interval still excludes 0: trust. Dropped (interval includes 0): risktaking, posrecip, altruism.

Not every imprint interval excludes 0 on bank 2. The write-up names the dropped dimension(s) above and drops their transport sentence; the remaining imprint dimensions keep theirs. Patience and negative reciprocity are reported only.

