# C8 — country-named persona arm on the strict battery

Produced by `paper_b/persona_strict.py` from `persona_strict.json`; design `planning/sprint_2026-10-11/paper-b-tier1/C8_PERSONA_DESIGN.md`.
Run `persona-strict-v1-20261019`. 42 countries, 26 sign profiles; 2000 draws, seed 20261011 (profile-block) / 20260905 (country), percentile 95%.

## Inputs

- cohort1_strict: `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/cohort1_strict.csv` sha256 `047cd0e45959…`
- adapter_strict_v1: `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/adapter_strict_v1.csv` sha256 `3683d2211767…`
- signprompt_strict_64: `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/signprompt_strict_64.csv` sha256 `bf05e0773973…`
- persona_strict: `/Users/bonorinoa/Hermes/Projects/SCA2/paper_b_inputs/persona_strict.csv` sha256 `efd663a50af3…`
- gps_z: `/Users/bonorinoa/Desktop/Github_Repositories/SCA2_PofW/synthetic_generation/outputs/gps_sign_relabel_all/gps_z_vectors.json` sha256 `02972f0ec4a8…`

Replay checks (design section 4): {"C1": true, "B2": true, "inputs": true, "SP": true, "all_pass": true}

## E2 — the one test: trust, cohort-1 adapters minus persona (paired profile-block bootstrap)

D = 0.716 [0.191, 1.154]; reading: **adapters closer** (cohort-1 0.744 [0.500, 0.865], persona 0.028 [-0.339, 0.381]). Country bootstrap (E4): 0.716 [0.325, 1.075], adapters closer.

## E1 / E3 — every route against the GPS, and each route minus persona (descriptive)

| Surface | C1 | B2 | SP | Persona (block) | Persona (country) | C1 − P | B2 − P | SP − P |
|---|---|---|---|---|---|---|---|---|
| trust | 0.744 [0.500, 0.865] | 0.803 [0.615, 0.876] | 0.773 [0.584, 0.844] | 0.028 [-0.339, 0.381] | 0.028 [-0.273, 0.330] | 0.716 [0.191, 1.154] | 0.775 [0.347, 1.144] | 0.745 [0.327, 1.086] |
| risktaking | 0.435 [0.085, 0.686] | 0.210 [-0.199, 0.584] | -0.448 [-0.722, -0.049] | 0.195 [-0.201, 0.545] | 0.195 [-0.151, 0.506] | 0.240 [-0.156, 0.617] | 0.015 [-0.436, 0.493] | -0.643 [-1.060, -0.118] |
| posrecip | 0.488 [0.120, 0.695] | 0.366 [-0.068, 0.652] | 0.490 [0.150, 0.709] | 0.033 [-0.342, 0.315] | 0.033 [-0.245, 0.320] | 0.454 [-0.036, 0.907] | 0.332 [-0.196, 0.816] | 0.457 [0.052, 0.884] |
| altruism | 0.406 [0.020, 0.676] | 0.364 [-0.057, 0.653] | 0.540 [0.199, 0.747] | -0.136 [-0.485, 0.214] | -0.136 [-0.427, 0.197] | 0.543 [0.042, 0.990] | 0.500 [-0.026, 0.965] | 0.677 [0.198, 1.083] |
| negrecip | -0.028 [-0.418, 0.406] | 0.239 [-0.237, 0.604] | 0.005 [-0.440, 0.447] | 0.157 [-0.140, 0.449] | 0.157 [-0.153, 0.458] | -0.185 [-0.612, 0.297] | 0.082 [-0.441, 0.561] | -0.152 [-0.640, 0.374] |
| patience:Q43 | -0.019 [-0.414, 0.452] | 0.005 [-0.403, 0.470] | -0.195 [-0.546, 0.218] | -0.491 [-0.771, -0.124] | -0.491 [-0.721, -0.214] | 0.472 [0.019, 0.986] | 0.496 [0.031, 1.013] | 0.295 [-0.134, 0.720] |
| patience:Q50 | 0.177 [-0.313, 0.580] | 0.161 [-0.343, 0.557] | 0.184 [-0.299, 0.573] | 0.509 [0.157, 0.730] | 0.509 [0.243, 0.714] | -0.333 [-0.840, 0.085] | -0.349 [-0.875, 0.084] | -0.326 [-0.802, 0.083] |

## E5 — the 16 development countries (country bootstrap, descriptive)

Cohort-1 trust 0.818 [0.554, 0.926]; persona trust -0.038 [-0.565, 0.480]. Paper B stack; not comparable to the preprint's own numbers, which come from another stack.

Route columns C1/B2/SP use the banked C3 resampling (B2 and SP cluster on the factorial unit); the differences use one profile-block resampling for both columns.
