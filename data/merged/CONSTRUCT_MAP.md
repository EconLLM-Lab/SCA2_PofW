# Tier-2 Construct Map (GPS → WVS Wave 7)

**Status:** evaluation surfaces for frozen DPO adapters. GPS = identification instrument; WVS Wave 7 = primary independent outcome surface.
**Scope:** 42-country GPS ∩ WVS Wave 7 intersection (one parquet per country under `data/wvs_eval_full/`).
**Strength tags:** `confirmatory` | `directional` | `exploratory` | `stretch` — see Prior table below.

---

## 1. Priors of confidence per GPS dimension (WVS data only)

Priors summarize what external evidence supports about each GPS→WVS item mapping, based on
(i) the canonical country-level validation of GPS against WVS proxies (Falk, Becker, Dohmen, Enke,
Huffman, Sunde 2018, *QJE* 133(4), Table II) and (ii) established practice in the trust and
time-preference literatures. "Prior" = reasonable belief that the WVS country moment moves in the
same direction as the GPS country score, *before* looking at our synthetic adapters.

| GPS dim | Prior | Status | Evidence base |
|---------|-------|--------|---------------|
| trust | **HIGH** | confirmatory | Falk et al. 2018 Table II: WVS "most people can be trusted" (Q57, our exact item) vs GPS trust, Spearman ρ = 0.49, p < .01, N = 60. WVS trust also predicts growth (Knack & Keefer 1997, *QJE* 112(4)). Q58–Q63 are the standard WVS radius-of-trust battery (Delhey & Newton 2005, *ESR* 21(4): 311–327). |
| patience | **LOW–MODERATE** | directional | Falk et al. 2018 Table II: WVS long-term-orientation childrearing item ("thrift, saving money and things", Q13 = our item) vs GPS patience, ρ = 0.09, p = .52, N = 60 — **not significant**. Falk et al. interpret the channel as childrearing norms, not individual patience. The same child-quality battery is common practice in the culture/time-preference literature (Galor & Özak 2016, *AER* 106(10): 3064–3103; Giavazzi, Petkov & Schiantarelli 2019, *JEG* 24(2): 117–154) but was never validated against GPS. Expect direction, not magnitude; treat nulls as informative. |
| risktaking | **LOW** | exploratory | The only WVS item Falk et al. validated against GPS risk (Schwartz "value of stimulation" portrait, ρ = 0.32, p = .03) **is not present in WVS Wave 7** (verified: no portrait items in the wave-7 file). Our items are economic-values scales (Q106 incomes equal vs incentives; Q107 private vs government ownership; Q109 competition) and a norm-permissiveness item (Q178 fare avoidance) — related to risk-taking in attitude space, not validated against it. No confirmatory claim. |
| altruism | **LOW** | exploratory | Falk et al. 2018: their WVS altruism item ("do something for the good of society") vs GPS altruism, ρ = 0.20, p = .24, N = 35 — not significant, and that attitudinal item is absent from Wave 7. Our items (Q99/Q101/Q103 voluntary-organization membership) are behavioral; membership reflects organizational density and civic infrastructure as much as altruistic preference. Directional hypothesis only. |
| posrecip | **VERY LOW** | stretch | Falk et al. 2018 explicitly report that their keyword procedure "did not yield any WVS questions ... related to positive or negative reciprocity." Our mapping (Q12 tolerance as child quality; Q174 religion as doing good vs. following norms; Q81 confidence in charitable organizations) is a theory bridge with no external validation precedent. |
| negrecip | **LOW** | stretch | The WVS justifiability battery (Q177 claiming benefits, Q179 stealing — our items) has cross-national precedent in moral-values research (Enke 2019, *QJE* 134(2): 953–1019, uses these items for moral universalism/particularism), but its mapping to costly-punishment negative reciprocity is a theory bridge, not a validated proxy. Q176 (moral clarity) and Q195 (death penalty justifiability) are indirect. |

**Reading the priors.** Only **trust** supports a confirmatory, sign-recovery claim against GPS country
scores. **Patience** supports a pre-registered *directional* expectation with a stated mechanism
(childrearing norms), where a null is an informative failure of the proxy, not of the adapter.
**Risktaking, altruism, posrecip, negrecip** are exploratory: adapters' signs on these dimensions are
hypothesis-generating, and negative results must not be over-interpreted. This asymmetry is deliberate:
it mirrors what the external validation literature actually establishes, and it protects the paper from
claiming proxy validity the source evidence does not grant.

---

## 2. WVS item map (from `sca2_datagen.config.WVS_ITEM_MAP`)

| Item | Dim | Tier | Label | Prior |
|------|-----|------|-------|-------|
| Q57 | trust | 2 | Most people can be trusted (binary) | HIGH |
| Q59 | trust | 2 | Trust: Your neighborhood (1-4 inv) | HIGH |
| Q61 | trust | 2 | Trust: People met first time (1-4 inv) | HIGH |
| Q62 | trust | 2 | Trust: Other religion (1-4 inv) | HIGH |
| Q63 | trust | 2 | Trust: Other nationality (1-4 inv) | HIGH |
| Q64 | trust | 2 | Confidence: Churches (1-4 inv) | HIGH |
| Q69 | trust | 2 | Confidence: Police (1-4 inv) | HIGH |
| Q70 | trust | 2 | Confidence: Courts (1-4 inv) | HIGH |
| Q71 | trust | 2 | Confidence: Government (1-4 inv) | HIGH |
| Q58 | trust | 3 | Trust: Family (1-4 inv, in-group) | HIGH |
| Q60 | trust | 3 | Trust: Personal acquaintances (1-4 inv) | HIGH |
| Q73 | trust | 3 | Confidence: Parliament (1-4 inv) | HIGH |
| Q13 | patience | 2 | Child quality: Thrift (binary) | LOW–MODERATE |
| Q14 | patience | 2 | Child quality: Perseverance (binary) | LOW–MODERATE |
| Q43 | patience | 2 | Less importance on work: good/bad (1-3) | LOW–MODERATE |
| Q50 | patience | 3 | Financial satisfaction (1-10) | LOW |
| Q106 | risktaking | 2 | Incomes equal (1) vs different (10) | LOW |
| Q107 | risktaking | 2 | Private ownership (1) vs govt (10) | LOW |
| Q109 | risktaking | 2 | Competition good (1) vs harmful (10) | LOW |
| Q178 | risktaking | 3 | Justifiable: fare avoidance (1-10) | LOW |
| Q12 | posrecip | 2 | Child quality: Tolerance/respect (binary) | VERY LOW |
| Q174 | posrecip | 2 | Religion: follow norms vs do good (binary) | VERY LOW |
| Q81 | posrecip | 3 | Confidence: Charitable orgs (1-4 inv) | VERY LOW |
| Q176 | negrecip | 2 | Moral clarity (1-10) | LOW |
| Q177 | negrecip | 2 | Justifiable: Claiming benefits (1-10 inv) | LOW |
| Q179 | negrecip | 2 | Justifiable: Stealing (1-10 inv) | LOW |
| Q195 | negrecip | 3 | Justifiable: Death penalty (1-10) | LOW |
| Q101 | altruism | 2 | Member: Charitable org (0-2) | LOW |
| Q99 | altruism | 2 | Member: Environmental org (0-2) | LOW |
| Q103 | altruism | 3 | Member: Self-help group (0-2) | LOW |

Tier = lab pre-registration tier (2 = primary, 3 = secondary). "inv" means the *scoring* step should
invert polarity for alignment; values in the parquet files are raw.

---

## 3. Country scope

42 countries = GPS (76 countries) ∩ WVS Wave 7 (66 countries). Verified against
`data/GPS/GPS_dataset_country_level/country_gps.dta` and `data/WVS/WVS_wave7.dta` (2026-08-18):
all 42 countries have all 30 mapped items present as columns with full non-null coverage
(WVS stores DK/NA as negative codes; scoring must mask them), and a single fieldwork year each
(2017–2023). Files: `data/wvs_eval_full/{ISO3}_WVS_wave7.parquet`.

## 4. Files

| File | Role |
|------|------|
| `wvs_eval_full/{ISO3}_WVS_wave7.parquet` (×42) | Per-country WVS7 evaluation surface; same schema as the USA/MEX files in `data/merged/` |
| `wvs_eval_full/_manifest.json` | Per-country n, fieldwork year, item non-null rates |
| `CONSTRUCT_MAP.md` | This document (GPS→WVS mapping + priors) |
| `DATASET_GUIDE.md` | Selection criteria, item wording, limitations, usage (`data/merged/`) |

## 5. Non-claims

- Item wording is **not** identical across GPS training scenarios and these surveys.
- Values are **raw** (no reverse-coding in the merge). Recodes belong in the scoring step.
- GPS is the in-sample identification instrument — **not** included in these files.
- Only the trust dimension carries a **confirmatory** sign-recovery claim against GPS scores; other
  dimensions are directional (patience) or exploratory (risk, altruism, reciprocity).
- WVS alone does not cover all six GPS dimensions with equal fidelity; priors above quantify that.
- Do **not** row-stack WVS with AmericasBarometer (AB remains a separate USA/MEX secondary surface
  documented in `data/merged/DATASET_GUIDE.md`).
