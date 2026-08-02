# Tier-2 Construct Map (GPS → WVS / AmericasBarometer)

**Status:** evaluation surfaces only. Frozen DPO adapters; no retraining.
**GPS:** identification / in-sample instrument — **not** merged here.
**Years:** WVS USA 2017 / MEX 2018; AB 2012–2019 pooled within country.

Strength tags: `clean` | `bridge` | `stretch` | `no-coverage`.

## Summary table

| GPS dim | WVS (pre-registered) | Strength | AB (trust-core focus) | Strength |
|---------|----------------------|----------|-----------------------|----------|
| trust | Q57, Q59, Q61–63, Q64, Q69–71 (t2); Q58, Q60, Q73 (t3) | clean | IT1; B1–B6; B10A/B12/B13/B21…; EXC6/7 | clean |
| patience | Q13 thrift, Q14 perseverance, Q43 (t2); Q50 (t3) | bridge | — | no-coverage |
| risktaking | Q106, Q107, Q109 (t2); Q178 (t3) | bridge | — | no-coverage |
| posrecip | Q12, Q174 (t2); Q81 (t3) | bridge | CP* not in core extract | stretch / omitted |
| negrecip | Q176, Q177, Q179 (t2); Q195 (t3) | bridge | EXC/JC partial only in core EXC | stretch |
| altruism | Q101, Q99 (t2); Q103 (t3) | bridge | CP community help not in core | thin / omitted |

## WVS item map (from `sca2_datagen.config.WVS_ITEM_MAP`)

| Item | Dim | Tier | Label |
|------|-----|------|-------|
| Q57 | trust | 2 | Most people can be trusted (binary) |
| Q59 | trust | 2 | Trust: Your neighborhood (1-4 inv) |
| Q61 | trust | 2 | Trust: People met first time (1-4 inv) |
| Q62 | trust | 2 | Trust: Other religion (1-4 inv) |
| Q63 | trust | 2 | Trust: Other nationality (1-4 inv) |
| Q64 | trust | 2 | Confidence: Churches (1-4 inv) |
| Q69 | trust | 2 | Confidence: Police (1-4 inv) |
| Q70 | trust | 2 | Confidence: Courts (1-4 inv) |
| Q71 | trust | 2 | Confidence: Government (1-4 inv) |
| Q58 | trust | 3 | Trust: Family (1-4 inv, in-group) |
| Q60 | trust | 3 | Trust: Personal acquaintances (1-4 inv) |
| Q73 | trust | 3 | Confidence: Parliament (1-4 inv) |
| Q13 | patience | 2 | Child quality: Thrift (binary) |
| Q14 | patience | 2 | Child quality: Perseverance (binary) |
| Q43 | patience | 2 | Less importance on work: good/bad (1-3) |
| Q50 | patience | 3 | Financial satisfaction (1-10) |
| Q106 | risktaking | 2 | Incomes equal (1) vs different (10) |
| Q107 | risktaking | 2 | Private ownership (1) vs govt (10) |
| Q109 | risktaking | 2 | Competition good (1) vs harmful (10) |
| Q178 | risktaking | 3 | Justifiable: fare avoidance (1-10) |
| Q12 | posrecip | 2 | Child quality: Tolerance/respect (binary) |
| Q174 | posrecip | 2 | Religion: follow norms vs do good (binary) |
| Q81 | posrecip | 3 | Confidence: Charitable orgs (1-4 inv) |
| Q176 | negrecip | 2 | Moral clarity (1-10) |
| Q177 | negrecip | 2 | Justifiable: Claiming benefits (1-10 inv) |
| Q179 | negrecip | 2 | Justifiable: Stealing (1-10 inv) |
| Q195 | negrecip | 3 | Justifiable: Death penalty (1-10) |
| Q101 | altruism | 2 | Member: Charitable org (0-2) |
| Q99 | altruism | 2 | Member: Environmental org (0-2) |
| Q103 | altruism | 3 | Member: Self-help group (0-2) |

## AB trust-core items retained

Canonical lowercase names in merged files:

- Interpersonal: `it1`
- System support: `b1` `b2` `b3` `b4` `b6`
- Institutional trust (subset): `b10a` `b12` `b13` `b18` `b21` `b31` `b32` `b37` `b47a`
- Corruption: `exc6` `exc7`
- Democracy / system eval: `ing4` `pn4` `dem2`
- Demographics: `q1` `q2` `ed` `q10`
- Design/weights: `wt` `weight1500` `upm` `strata`/`estratopri`… + derived `weight`

Per-wave presence is recorded in `_manifest.json` → `*.waves[].trust_core_missing`.

## Files

| File | Role |
|------|------|
| `USA_WVS_wave7.parquet` | USA WVS7 evaluation surface |
| `MEX_WVS_wave7.parquet` | MEX WVS7 evaluation surface |
| `USA_Barometer_2012_2019.parquet` | USA AB 2012–2019 evaluation surface |
| `MEX_Barometer_2012_2019.parquet` | MEX AB 2012–2019 evaluation surface |
| `_manifest.json` | row counts, weight notes, coverage |

## Non-claims

- Item wording is **not** identical across GPS training scenarios and these surveys.
- AB does **not** cover all six GPS dimensions; score trust-core only for primary AB claims.
- Values are **raw** (no reverse-coding in merge). Recodes belong in the scoring step.
- Do **not** row-merge these four files across surveys.
