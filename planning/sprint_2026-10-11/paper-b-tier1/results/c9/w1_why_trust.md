# W1 why trust works: own-bit vs cross-talk decomposition

DESCRIPTIVE / NOT PREREGISTERED; synthetic model quantities + GPS z only.
Intervals: adapter-side Spearman intervals: profile-block bootstrap, 2000 draws, seed 20261011.

Countries: 42 (cohort 1). Prediction = sum_k beta[k,s]*(bit_k-0.5); own = own-bit term; cross = the other five bits. Own-bit betas equal the NUMBERS_TABLE FX_*_own_beta rows (14 pins asserted).

## adapter

### (a) 6 bits x 7 surfaces main effects (composite units)

```
            trust  risktaking  patience:Q43  patience:Q50  altruism  posrecip  negrecip
trust       0.364      -0.003        -0.047         0.495     0.281     0.418    -0.374
risktaking  0.117       0.140        -0.109         0.245     0.983     0.253    -0.668
patience    0.030       0.072         0.049         0.133     0.178     0.132    -0.128
altruism    0.057      -0.209        -0.009         0.025     0.242     0.123     0.071
posrecip    0.079      -0.023        -0.044        -0.055     0.371     0.124    -0.299
negrecip    0.013      -0.380        -0.069        -0.145     0.377     0.051     0.625
```

### (b/c) observed = the route's own 64-cell composite at each country's sign cell

surface | own_beta | top cross bit (beta) | rho(full,obs) | rho(obs,GPS) [CI] | rho(full,GPS) | rho(own,GPS) | rho(cross,GPS) | cross var share | main-eff share (64 cells)
trust | 0.364 | risktaking (0.117) | 0.920 | 0.803 [0.615,0.876] | 0.834 | 0.862 | 0.574 | 0.147 | 0.806
risktaking | 0.140 | negrecip (-0.380) | 0.748 | 0.210 [-0.199,0.584] | 0.104 | 0.862 | -0.097 | 0.999 | 0.609
patience:Q43 | 0.049 | risktaking (-0.109) | 0.871 | 0.005 [-0.403,0.470] | -0.020 | 0.817 | -0.195 | 1.049 | 0.483
patience:Q50 | 0.133 | trust (0.495) | 0.948 | 0.161 [-0.343,0.557] | 0.176 | 0.817 | 0.009 | 0.914 | 0.891
altruism | 0.242 | risktaking (0.983) | 0.957 | 0.364 [-0.057,0.653] | 0.422 | 0.857 | 0.285 | 0.850 | 0.925
posrecip | 0.124 | trust (0.418) | 0.935 | 0.366 [-0.068,0.652] | 0.378 | 0.866 | 0.262 | 0.854 | 0.711
negrecip | 0.625 | risktaking (-0.668) | 0.835 | 0.239 [-0.237,0.604] | 0.386 | 0.866 | -0.128 | 0.830 | 0.666

Interactions are reported only where main effects explain < 80% of the 64-cell variance: risktaking (share 0.609, main+2way rho vs obs 0.920, vs GPS 0.331); patience:Q43 (share 0.483, main+2way rho vs obs 0.903, vs GPS -0.066); posrecip (share 0.711, main+2way rho vs obs 0.919, vs GPS 0.287); negrecip (share 0.666, main+2way rho vs obs 0.928, vs GPS 0.210)

Cross-talk share vs failure to order like GPS, n=7 (descriptive): Spearman 0.821
surface | cross var share | rho(observed, GPS) | failure (1 - rho)
trust | 0.147 | 0.803 | 0.197
risktaking | 0.999 | 0.210 | 0.790
patience:Q43 | 1.049 | 0.005 | 0.995
patience:Q50 | 0.914 | 0.161 | 0.839
altruism | 0.850 | 0.364 | 0.636
posrecip | 0.854 | 0.366 | 0.634
negrecip | 0.830 | 0.239 | 0.761

### (b/c) observed = cohort-1 country composite (model = this route's betas)

surface | own_beta | top cross bit (beta) | rho(full,obs) | rho(obs,GPS) [CI] | rho(full,GPS) | rho(own,GPS) | rho(cross,GPS) | cross var share | main-eff share (64 cells)
trust | 0.364 | risktaking (0.117) | 0.915 | 0.744 [0.500,0.865] | 0.834 | 0.862 | 0.574 | 0.147 | -
risktaking | 0.140 | negrecip (-0.380) | 0.399 | 0.435 [0.085,0.686] | 0.104 | 0.862 | -0.097 | 0.999 | -
patience:Q43 | 0.049 | risktaking (-0.109) | 0.826 | -0.019 [-0.414,0.452] | -0.020 | 0.817 | -0.195 | 1.049 | -
patience:Q50 | 0.133 | trust (0.495) | 0.946 | 0.177 [-0.313,0.580] | 0.176 | 0.817 | 0.009 | 0.914 | -
altruism | 0.242 | risktaking (0.983) | 0.975 | 0.406 [0.020,0.676] | 0.422 | 0.857 | 0.285 | 0.850 | -
posrecip | 0.124 | trust (0.418) | 0.934 | 0.488 [0.120,0.695] | 0.378 | 0.866 | 0.262 | 0.854 | -
negrecip | 0.625 | risktaking (-0.668) | 0.477 | -0.028 [-0.418,0.406] | 0.386 | 0.866 | -0.128 | 0.830 | -

Cross-talk share vs failure to order like GPS, n=7 (descriptive): Spearman 0.286
surface | cross var share | rho(observed, GPS) | failure (1 - rho)
trust | 0.147 | 0.744 | 0.256
risktaking | 0.999 | 0.435 | 0.565
patience:Q43 | 1.049 | -0.019 | 1.019
patience:Q50 | 0.914 | 0.177 | 0.823
altruism | 0.850 | 0.406 | 0.594
posrecip | 0.854 | 0.488 | 0.512
negrecip | 0.830 | -0.028 | 1.028

## signprompt

### (a) 6 bits x 7 surfaces main effects (composite units)

```
            trust  risktaking  patience:Q43  patience:Q50  altruism  posrecip  negrecip
trust       1.780      -0.858        -0.120         1.774     0.809     0.530     0.230
risktaking  0.143      -0.457        -0.102         0.571     0.578     0.255     0.069
patience    0.025       0.019        -0.069         0.421     0.279     0.154     0.099
altruism    0.019      -0.077        -0.018        -0.028     0.364     0.411     0.020
posrecip    0.042      -0.136        -0.065         0.416     0.167     0.103     0.000
negrecip    0.013       0.002        -0.018         0.097     0.054     0.023    -0.023
```

### (b/c) observed = the route's own 64-cell composite at each country's sign cell

surface | own_beta | top cross bit (beta) | rho(full,obs) | rho(obs,GPS) [CI] | rho(full,GPS) | rho(own,GPS) | rho(cross,GPS) | cross var share | main-eff share (64 cells)
trust | 1.780 | risktaking (0.143) | 0.946 | 0.773 [0.584,0.844] | 0.811 | 0.862 | 0.472 | 0.008 | 0.997
risktaking | -0.457 | trust (-0.858) | 0.929 | -0.448 [-0.722,-0.049] | -0.577 | -0.862 | -0.207 | 0.694 | 0.898
patience:Q43 | -0.069 | trust (-0.120) | 0.972 | -0.195 [-0.546,0.218] | -0.222 | -0.817 | -0.067 | 0.837 | 0.862
patience:Q50 | 0.421 | trust (1.774) | 0.987 | 0.184 [-0.299,0.573] | 0.223 | 0.817 | 0.055 | 0.912 | 0.953
altruism | 0.364 | trust (0.809) | 0.981 | 0.540 [0.199,0.747] | 0.516 | 0.857 | 0.391 | 0.731 | 0.943
posrecip | 0.103 | trust (0.530) | 0.914 | 0.490 [0.150,0.709] | 0.479 | 0.866 | 0.423 | 0.893 | 0.902
negrecip | -0.023 | trust (0.230) | 0.866 | 0.005 [-0.440,0.447] | 0.094 | -0.866 | 0.171 | 1.047 | 0.855

Interactions are reported only where main effects explain < 80% of the 64-cell variance: none

Cross-talk share vs failure to order like GPS, n=7 (descriptive): Spearman 0.250
surface | cross var share | rho(observed, GPS) | failure (1 - rho)
trust | 0.008 | 0.773 | 0.227
risktaking | 0.694 | -0.448 | 1.448
patience:Q43 | 0.837 | -0.195 | 1.195
patience:Q50 | 0.912 | 0.184 | 0.816
altruism | 0.731 | 0.540 | 0.460
posrecip | 0.893 | 0.490 | 0.510
negrecip | 1.047 | 0.005 | 0.995

### (b/c) observed = cohort-1 country composite (model = this route's betas)

surface | own_beta | top cross bit (beta) | rho(full,obs) | rho(obs,GPS) [CI] | rho(full,GPS) | rho(own,GPS) | rho(cross,GPS) | cross var share | main-eff share (64 cells)
trust | 1.780 | risktaking (0.143) | 0.928 | 0.744 [0.500,0.865] | 0.811 | 0.862 | 0.472 | 0.008 | -
risktaking | -0.457 | trust (-0.858) | -0.253 | 0.435 [0.085,0.686] | -0.577 | -0.862 | -0.207 | 0.694 | -
patience:Q43 | -0.069 | trust (-0.120) | 0.636 | -0.019 [-0.414,0.452] | -0.222 | -0.817 | -0.067 | 0.837 | -
patience:Q50 | 0.421 | trust (1.774) | 0.909 | 0.177 [-0.313,0.580] | 0.223 | 0.817 | 0.055 | 0.912 | -
altruism | 0.364 | trust (0.809) | 0.885 | 0.406 [0.020,0.676] | 0.516 | 0.857 | 0.391 | 0.731 | -
posrecip | 0.103 | trust (0.530) | 0.925 | 0.488 [0.120,0.695] | 0.479 | 0.866 | 0.423 | 0.893 | -
negrecip | -0.023 | trust (0.230) | -0.264 | -0.028 [-0.418,0.406] | 0.094 | -0.866 | 0.171 | 1.047 | -

Cross-talk share vs failure to order like GPS, n=7 (descriptive): Spearman 0.714
surface | cross var share | rho(observed, GPS) | failure (1 - rho)
trust | 0.008 | 0.744 | 0.256
risktaking | 0.694 | 0.435 | 0.565
patience:Q43 | 0.837 | -0.019 | 1.019
patience:Q50 | 0.912 | 0.177 | 0.823
altruism | 0.731 | 0.406 | 0.594
posrecip | 0.893 | 0.488 | 0.512
negrecip | 1.047 | -0.028 | 1.028

## (d) Bank composition (aggregates)

### bank1: 658 pairs

dimension | pairs | prompt words | resp A words | resp B words | A minus B words
trust | 110 | 100.9 | 46.8 | 45.7 | 1.2
risktaking | 109 | 83.3 | 47.3 | 42.8 | 4.5
patience | 110 | 88.4 | 52.7 | 49.2 | 3.6
altruism | 110 | 91.1 | 50.1 | 47.9 | 2.2
posrecip | 109 | 93.3 | 48.6 | 45.4 | 3.1
negrecip | 110 | 89.2 | 49.3 | 46.4 | 2.9

Label dependence: 27636 country-pair rows over 42 countries; 0 disagree with the sign of the pair's own dimension (0 = every label depends on exactly one dimension's sign).

Keyword-family share (rows = pair dimension, cols = family):
```
            trust  risktaking  patience  altruism  posrecip  negrecip
trust        0.98        0.85      0.76      0.56      0.16      0.15
risktaking   0.32        1.00      0.61      0.28      0.05      0.07
patience     0.15        0.55      0.99      0.70      0.05      0.04
altruism     0.10        0.26      0.70      0.96      0.07      0.08
posrecip     0.15        0.11      0.75      0.96      0.99      0.06
negrecip     0.14        0.57      0.60      0.40      0.05      0.59
```

Mean marker gap (A minus B) by pair dimension (rows) on each dimension's marker (cols):
```
            trust  risktaking  patience  altruism  posrecip  negrecip
trust        0.88        0.41     -0.09      0.26      0.47     -0.34
risktaking  -0.05        0.78     -0.24      0.04      0.03     -0.04
patience     0.07       -0.17      0.84      0.10      0.04     -0.03
altruism     0.24        0.01      0.05      0.88      0.41     -0.08
posrecip     0.26        0.08      0.16      0.53      0.82     -0.03
negrecip    -0.36        0.34     -0.32     -0.18     -0.31      0.89
```

### bank2: 658 pairs

dimension | pairs | prompt words | resp A words | resp B words | A minus B words
trust | 110 | 100.8 | 47.2 | 45.7 | 1.5
risktaking | 110 | 84.0 | 48.4 | 43.7 | 4.7
patience | 110 | 67.5 | 53.2 | 49.4 | 3.9
altruism | 110 | 99.7 | 48.8 | 46.5 | 2.3
posrecip | 109 | 93.6 | 46.7 | 42.9 | 3.8
negrecip | 109 | 87.9 | 47.6 | 43.7 | 3.9

Label dependence: 27636 country-pair rows over 42 countries; 0 disagree with the sign of the pair's own dimension (0 = every label depends on exactly one dimension's sign).

Keyword-family share (rows = pair dimension, cols = family):
```
            trust  risktaking  patience  altruism  posrecip  negrecip
trust        0.97        0.89      0.75      0.65      0.15      0.13
risktaking   0.33        0.99      0.65      0.44      0.04      0.04
patience     0.15        0.46      1.00      0.48      0.02      0.03
altruism     0.13        0.25      0.67      0.96      0.05      0.05
posrecip     0.08        0.15      0.72      0.99      1.00      0.16
negrecip     0.14        0.55      0.69      0.37      0.06      0.53
```

(this bank stores no per-response marker scores)

## (e) Mechanistic follow-up candidates

Leak score by bit (sum over non-own surfaces of |beta| / surface SD over 64 cells): trust 4.345, risktaking 5.693, patience 1.269, altruism 1.607, posrecip 2.062, negrecip 3.176
Leakiest bit: risktaking. 27 cohort pairs differ in only that bit. Rule: countries differing in exactly this sign bit; ranked by the smallest |z| over all six dimensions of either country (clean signs, rule fixed before any outcome).

pair JOR vs KAZ: min |z| over six dims 0.125, z gap on the bit 0.370
pair IDN vs IRN: min |z| over six dims 0.103, z gap on the bit 0.660
pair KEN vs MEX: min |z| over six dims 0.076, z gap on the bit 0.383
pair KEN vs ROU: min |z| over six dims 0.076, z gap on the bit 0.473
pair KEN vs RUS: min |z| over six dims 0.069, z gap on the bit 0.567

Items with the largest leaked effect of that bit (|effect| / cell SD), adapter route:
Q101 (altruism): effect 1.013, ratio 1.597
Q99 (altruism): effect 1.006, ratio 1.523
Q103 (altruism): effect 0.931, ratio 1.516
Q179 (negrecip): effect -2.065, ratio 1.375
Q43 (patience): effect -0.109, ratio 0.994
Q177 (negrecip): effect -1.413, ratio 0.891

## (e) Reading

DESCRIPTIVE / NOT PREREGISTERED. Every number below is read from the tables above (same file).

Cross-talk survives, and it is specific: the adapters order countries like GPS on a surface only when that surface's own bit is the largest mover in its column. The own-bit-only prediction orders the 42 countries like GPS on all seven surfaces (rho 0.82 to 0.87 in absolute value), which restates the sign-copier ceiling the PM found. The full main-effects prediction keeps that ordering on trust (rho(full, GPS) 0.834 against own-only 0.862; cross share of the variance in the full prediction 0.147) and loses it on the other surfaces (rho(full, GPS) 0.104 risktaking, -0.020 patience:Q43, 0.176 patience:Q50, 0.422 altruism, 0.378 posrecip, 0.386 negrecip; cross share 0.83 to 1.05). On trust the own beta is 0.364 and the largest cross beta is 0.117 (risktaking bit). On altruism the own beta is 0.242 and the risktaking bit's is 0.983; on negrecip the own beta is 0.625 and the risktaking bit's is -0.668; on patience:Q50 the trust bit's 0.495 exceeds the own 0.133. Cross-only predictions correlate with GPS at 0.574 on trust and at -0.195 to 0.285 elsewhere. The main-effects model also explains the surfaces (rho(full, bank-2 composite) 0.75 to 0.96; 0.399 and 0.477 on cohort-1 risktaking and negrecip, where bank-2 betas transfer worst), so the failure is a property of what the bits do, not of a poor fit. The same pattern holds on the sign-prompt route, which inverts risk (own beta -0.457, rho(own, GPS) -0.862): trust has the smallest cross share (0.008), every other surface 0.69 to 1.05. Interactions are needed on four adapter surfaces (main effects below 80% of the 64-cell variance: risktaking, patience:Q43, posrecip, negrecip) and they do not rescue the GPS ordering (main+2way rho vs GPS 0.331, -0.066, 0.287, 0.210), though they lift the fit to the observed composite to 0.90 to 0.93. The n=7 rank correlation between cross share and GPS failure is 0.821 against bank-2 composites and 0.286 against cohort-1 composites; the signal is one surface (trust) against six, not a graded relation, so we do not claim a dose-response.

Ruled out: sign balance and item count (PM's run), and any account in which the bank's labels depend on more than one dimension: every one of the 27,636 country-pair rows per bank follows the sign of the pair's own dimension (0 mismatches in both banks). Bank text is not why trust is spared: pair lengths are similar across dimensions, keyword families overlap heavily across dimensions in both banks, and bank 1's marker scores show that the pairs of several dimensions already separate A from B on other dimensions (trust pairs on posrecip 0.47 and risktaking 0.41; altruism pairs on posrecip 0.41; negrecip pairs on trust -0.36). Cross-dimension content is present for every dimension, so text co-loading alone does not distinguish trust. What distinguishes trust is that its own effect outruns the leakage into it. Bank 2 stores no marker scores, so the marker comparison is bank 1 only.

Single most informative workbench follow-up: the risktaking bit is the leakiest (leak score above), so compare the cohort-1 adapters of JOR and KAZ (the one-bit-apart pair differing only in the risktaking sign with the cleanest signs of the 27 candidates) and trace which adapter directions move the altruism items Q101, Q99 and Q103 and the negrecip items Q179 and Q177, the items with the largest leaked effect of that bit. If the activation difference between the two adapters on those items is carried by a direction shared with the altruism-pair training signal, cross-talk lives in a shared direction; if not, it is entangled in the same weights as the risk signal. Caveat: pair choice rests on a fixed a priori rule, and JOR and KAZ have a smallest |z| of 0.125, so a second pair from the list (IDN vs IRN) should replicate the contrast.

