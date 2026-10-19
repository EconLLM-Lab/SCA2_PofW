### Per-unit table (seconds; load = process start + imports + input fetch; cap = 4 streamed passes; ref+exp+write = 2 float32 HF reference forwards + manifests + file writes)

| device | dtype | unit | wall s | load s | capture s | ref+exp+write s | peak RSS GB | peak VRAM MiB | gates | max parity ulp (arms) |
|---|---|---|---:|---:|---:|---:|---:|---:|---|---|
| Mac (12 CPU, 24 GB, CPU codes) | 64 | ARG x Q57 | 60.9 | 4.3 | 35.6 | 20.9 | 7.81 |  | PASS | 2.99 (2.99, 2.59) |
| Mac (12 CPU, 24 GB, CPU codes) | 64 | base x Q57 | 29.7 | 4.7 | 16.3 | 8.6 | 7.75 |  | PASS | 2.99 (2.99) |
| Mac (12 CPU, 24 GB, CPU codes) | 64 | ARG x Q81 | 57.0 | 4.7 | 34.1 | 18.1 | 7.05 |  | PASS | 3.22 (2.77, 3.22) |
| Mac (12 CPU, 24 GB, CPU codes) | 64 | base x Q81 | 32.1 | 4.4 | 19.6 | 8.1 | 7.76 |  | PASS | 2.77 (2.77) |
| Mac (12 CPU, 24 GB, CPU codes) | 64 | ARG x Q107 | 78.2 | 4.4 | 42.9 | 30.8 | 7.08 |  | PASS | 5.07 (4.93, 5.07) |
| Mac (12 CPU, 24 GB, CPU codes) | 64 | base x Q107 | 35.7 | 4.5 | 22.7 | 8.5 | 7.10 |  | PASS | 4.93 (4.93) |
| Mac (12 CPU, 24 GB, CPU codes) | 32 | ARG x Q57 | 28.8 | 4.3 | 12.7 | 11.7 | 6.82 |  | FAIL: d_attr_gap, d_attr_gap_clamped, d_attr_gap_float32, d_attr_gap_float32_clamped | 2.99 (2.99, 2.60) |
| Mac (12 CPU, 24 GB, CPU codes) | 32 | ARG x Q107 | 32.4 | 3.8 | 15.3 | 13.3 | 7.23 |  | FAIL: d_attr_gap, d_attr_gap_float32 | 5.08 (4.93, 5.08) |
| A100-SXM4-80GB high-mem | 64 | ARG x Q57 | 80.3 | 13.7 | 25.0 | 41.3 | 6.22 | 5714 | PASS | 2.08 (1.94, 2.08) |
| A100-SXM4-80GB high-mem | 64 | base x Q57 | 59.0 | 13.2 | 20.2 | 25.3 | 5.98 | 4666 | PASS | 1.94 (1.94) |
| A100-SXM4-80GB high-mem | 64 | ARG x Q81 | 79.9 | 13.6 | 24.8 | 41.1 | 6.24 | 5878 | PASS | 2.38 (1.58, 2.38) |
| A100-SXM4-80GB high-mem | 64 | base x Q81 | 59.2 | 13.4 | 20.2 | 25.3 | 5.99 | 4708 | PASS | 1.58 (1.58) |
| A100-SXM4-80GB high-mem | 64 | ARG x Q107 | 81.0 | 13.7 | 25.4 | 41.5 | 6.31 | 6646 | PASS | 4.66 (3.88, 4.66) |
| A100-SXM4-80GB high-mem | 64 | base x Q107 | 59.4 | 13.4 | 20.4 | 25.3 | 6.02 | 4938 | PASS | 3.88 (3.88) |
| A100-SXM4-80GB high-mem | 32 | ARG x Q57 | 76.9 | 13.7 | 21.6 | 41.2 | 6.11 | 4444 | PASS | 2.08 (1.95, 2.08) |
| A100-SXM4-80GB high-mem | 32 | ARG x Q107 | 77.6 | 13.7 | 22.2 | 41.5 | 6.18 | 4906 | FAIL: d_attr_gap, d_attr_gap_float32 | 4.66 (3.88, 4.66) |
| L4 | 64 | ARG x Q57 | 107.4 | 15.5 | 50.4 | 41.2 | 6.15 | 5434 | PASS | 2.08 (1.94, 2.08) |
| L4 | 64 | base x Q57 | 70.8 | 12.9 | 32.6 | 25.0 | 5.91 | 4386 | PASS | 1.94 (1.94) |
| L4 | 64 | ARG x Q81 | 106.3 | 13.1 | 52.0 | 40.9 | 6.18 | 5598 | PASS | 2.38 (1.58, 2.38) |
| L4 | 64 | base x Q81 | 71.6 | 12.8 | 33.5 | 25.0 | 5.92 | 4428 | PASS | 1.58 (1.58) |
| L4 | 64 | ARG x Q107 | 119.0 | 13.2 | 64.5 | 41.0 | 6.24 | 6364 | PASS | 4.66 (3.88, 4.66) |
| L4 | 64 | base x Q107 | 77.8 | 12.7 | 39.6 | 25.1 | 5.95 | 4658 | PASS | 3.88 (3.88) |
| L4 | 32 | ARG x Q57 | 75.9 | 13.1 | 21.7 | 40.8 | 6.04 | 3940 | PASS | 2.08 (1.94, 2.08) |
| L4 | 32 | ARG x Q107 | 76.7 | 13.2 | 22.3 | 40.9 | 6.12 | 4626 | FAIL: d_attr_gap, d_attr_gap_float32 | 4.66 (3.88, 4.66) |
| T4 | 64 | ARG x Q57 | 212.7 | 22.4 | 104.0 | 85.9 | 5.93 | 5331 | PASS | 2.12 (1.97, 2.12) |
| T4 | 64 | base x Q57 | skipped (f64 > 3x Mac on first unit) | | | | | | | |
| T4 | 64 | ARG x Q81 | skipped (f64 > 3x Mac on first unit) | | | | | | | |
| T4 | 64 | base x Q81 | skipped (f64 > 3x Mac on first unit) | | | | | | | |
| T4 | 64 | ARG x Q107 | skipped (f64 > 3x Mac on first unit) | | | | | | | |
| T4 | 64 | base x Q107 | skipped (f64 > 3x Mac on first unit) | | | | | | | |
| T4 | 32 | ARG x Q57 | 139.2 | 20.5 | 35.8 | 82.4 | 5.92 | 4061 | FAIL: d_attr_gap_clamped, d_attr_gap_float32_clamped | 2.11 (1.96, 2.11) |
| T4 | 32 | ARG x Q107 | 128.0 | 16.4 | 33.3 | 78.0 | 6.04 | 4299 | PASS | 4.67 (3.90, 4.67) |
| G4 RTX PRO 6000 Blackwell | 64 | ARG x Q57 | 28.5 | 6.3 | 12.9 | 9.2 | 6.54 | 5861 | PASS | 2.08 (1.94, 2.08) |
| G4 RTX PRO 6000 Blackwell | 64 | base x Q57 | 20.2 | 6.3 | 8.5 | 5.3 | 6.30 | 4813 | PASS | 1.94 (1.94) |
| G4 RTX PRO 6000 Blackwell | 64 | ARG x Q81 | 29.0 | 6.4 | 13.3 | 9.1 | 6.57 | 6025 | PASS | 2.38 (1.58, 2.38) |
| G4 RTX PRO 6000 Blackwell | 64 | base x Q81 | 20.3 | 6.2 | 8.7 | 5.3 | 6.31 | 4855 | PASS | 1.58 (1.58) |
| G4 RTX PRO 6000 Blackwell | 64 | ARG x Q107 | 34.0 | 6.4 | 18.2 | 9.2 | 6.63 | 6791 | PASS | 4.66 (3.88, 4.66) |
| G4 RTX PRO 6000 Blackwell | 64 | base x Q107 | 22.8 | 6.2 | 11.1 | 5.3 | 6.35 | 5085 | PASS | 3.88 (3.88) |
| G4 RTX PRO 6000 Blackwell | 32 | ARG x Q57 | 21.4 | 6.3 | 5.9 | 9.1 | 6.32 | 4367 | FAIL: d_attr_gap, d_attr_gap_float32 | 2.08 (1.94, 2.08) |
| G4 RTX PRO 6000 Blackwell | 32 | ARG x Q107 | 21.6 | 6.4 | 6.0 | 9.1 | 6.39 | 5053 | FAIL: d_attr_gap, d_attr_gap_clamped, d_attr_gap_float32, d_attr_gap_float32_clamped | 4.66 (3.88, 4.66) |

### Per-device table

| device | setup min (provision to NF4 frozen) | measured CU/h (median; min-max; polls) | ARG f64 mean s/unit | base f64 mean s/unit | ARG f32 mean s/unit | f64 gates | f32 gates | max VRAM MiB |
|---|---:|---|---:|---:|---:|---|---|---:|
| Mac (12 CPU, 24 GB, CPU codes) | 0 (local codes pre-built) | 0 (Mac) | 65.3 (n=3) | 32.5 (n=3) | 30.6 (n=2) | 6/6 pass | 0/2 pass |  |
| A100-SXM4-80GB high-mem | 2.62 | 6.77; 6.77-6.77; 13 | 80.4 (n=3) | 59.2 (n=3) | 77.3 (n=2) | 6/6 pass | 1/2 pass | 6646 |
| L4 | 2.69 | 1.54; 1.07-1.54; 15 | 110.9 (n=3) | 73.4 (n=3) | 76.3 (n=2) | 6/6 pass | 1/2 pass | 6364 |
| T4 | 9.83 | 1.07; 1.07-1.07; 18 | 212.7 (n=1) | n/a | 133.6 (n=2) | 1/1 pass | 1/2 pass | 5331 |
| G4 RTX PRO 6000 Blackwell | 2.01 | 8.90; 8.90-8.90; 5 | 30.5 (n=3) | 21.1 (n=3) | 21.5 (n=2) | 6/6 pass | 0/2 pass | 6791 |

### Projection (989 units = 23 base + 966 adapter); CU available = 186.66 - benchmark spend = 183.50

| device | dtype | adapter s / base s (central) | wall h central (upper) | CU central (upper) | CU with +1.37 h Hub sync, central (upper) | fits (upper, with sync) |
|---|---|---|---:|---:|---:|---|
| mac | 64 | 65.3 / 32.5 | 17.74 (21.20) | 0 | 0 | n/a (0 CU) |
| mac | 32 | 30.6 / 30.6 * | 8.40 (8.90) | 0 | 0 | n/a (0 CU) |
| a100 | 64 | 80.4 / 59.2 | 21.94 (22.11) | 157.0 (158.2) | 166.8 (168.0) | yes |
| a100 | 32 | 77.3 / 77.3 * | 21.22 (21.33) | 151.8 (152.6) | 161.6 (162.4) | yes |
| l4 | 64 | 110.9 / 73.4 | 30.23 (32.43) | 49.2 (52.8) | 51.5 (55.1) | yes |
| l4 | 32 | 76.3 / 76.3 * | 20.97 (21.07) | 34.1 (34.3) | 36.4 (36.5) | yes |
| t4 | 64 | 212.7 / 212.7 * | 58.43 (58.43) | 66.4 (66.4) | 68.0 (68.0) | yes |
| t4 | 32 | 133.6 / 133.6 * | 36.70 (38.24) | 41.7 (43.4) | 43.2 (45.0) | yes |
| g4 | 64 | 30.5 / 21.1 | 8.32 (9.27) | 78.3 (87.2) | 91.1 (100.1) | yes |
| g4 | 32 | 21.5 / 21.5 * | 5.90 (5.93) | 55.6 (55.9) | 68.5 (68.7) | yes |
