# SCA 2.0 Tier-2 Evaluation Surfaces — Dataset Guide

**Lab:** EconLLM Lab (SCA2_PofW)  
**Purpose:** Out-of-sample evaluation of **frozen** USA / MEX DPO adapters  
**Status:** Evaluation data only — not training data, not a panel econometric product  
**GPS role:** Identification / in-sample cultural state for synthetic generation — **not** included here  

This folder contains four country × survey parquet files plus this guide. Share the folder (or the four parquets + docs) via Google Drive; colleagues load files locally. Do **not** retrain adapters on these surveys.

---

## 1. Files

| File | Survey | Country | Years | Rows | Columns (approx.) |
|------|--------|---------|-------|------|-------------------|
| `USA_WVS_wave7.parquet` | World Values Survey Wave 7 | USA | 2017 | 2,596 | 44 |
| `MEX_WVS_wave7.parquet` | World Values Survey Wave 7 | MEX | 2018 | 1,741 | 44 |
| `USA_Barometer_2012_2019.parquet` | AmericasBarometer (LAPOP) | USA | 2012, 2014, 2017, 2019 | 6,000 | 35 |
| `MEX_Barometer_2012_2019.parquet` | AmericasBarometer (LAPOP) | MEX | 2012, 2014, 2017, 2019 | 6,238 | 35 |

Supporting artifacts:

| File | Role |
|------|------|
| `DATASET_GUIDE.md` | This document (selection, wording, limitations, usage) |
| `CONSTRUCT_MAP.md` | Compact GPS → survey construct map |
| `_manifest.json` | Machine-readable per-wave coverage and weight notes |
| `01_merge_quality_and_usage.ipynb` | Merge QA + colleague load / benchmark recipe |
| `_build_merge.py` | Reproducible builder (lab machines with raw `.dta` only) |
| `README.md` | Short entry point |

**Do not** row-stack WVS with AmericasBarometer. Join only at **country-level moments** when comparing surveys.

---

## 2. Intended use for DPO adapter evaluation

### Research claim under test

Adapters were trained on **synthetic GPS-conditioned preference pairs** (six dimensions: trust, risk taking, patience, altruism, positive reciprocity, negative reciprocity). Tier-1 evidence is own-country recovery of synthetic labels. Tier-2 asks:

> Do the **same frozen adapters**, without retraining, recover the **direction** of independent human survey moments that are *theoretically related* to those dimensions?

Retraining on WVS or AB would collapse the claim into “fit the survey you hand us.” That is **out of scope**.

### What each surface is for

| Surface | Primary role | Dimensional coverage |
|---------|--------------|----------------------|
| **WVS Wave 7** | Main multi-dimension OOS test | Pre-registered map for all 6 GPS dims (quality varies: trust = clean; others = bridge) |
| **AmericasBarometer 2012–2019** | Secondary OOS stress test | **Trust / system support / institutional confidence / corruption** only. Patience and risk: **no coverage**. Reciprocity/altruism: stretch — not primary claims. |
| **GPS** | Not in this folder | In-sample identification instrument for generation |

### Recommended evaluation workflow

1. Load human microdata (these parquets).  
2. Compute country moments (means / shares), **unweighted first**; optional weights only after audit.  
3. Pre-register **sign of USA − MEX** per item (or small item set per dim).  
4. Prompt both adapters with the **same official item wording / option set** (ranking or forced choice consistent with DPO log-ratio).  
5. Compare adapter specialization to human signs; report by dimension with tags: `clean | bridge | stretch | no-coverage`.  
6. Never claim magnitude recovery of GPS prefs or that AB “is” the six GPS dimensions.

See notebook section “Colleague recipe” for load helpers and a human-benchmark skeleton.

---

## 3. Selection criteria

### 3.1 World Values Survey Wave 7

| Criterion | Decision |
|-----------|----------|
| Wave | Wave 7 only (local file `WVS_wave7.dta`) |
| Countries | USA (`B_COUNTRY_ALPHA == "USA"`), MEX |
| Fieldwork years | USA **2017** (n=2,596); MEX **2018** (n=1,741) |
| Items | Lab pre-registered `WVS_ITEM_MAP` in `synthetic_generation/sca2_datagen/config.py` (tier 2 + tier 3) |
| Demographics | `Q260` sex, `Q261` birth year, `Q262` age, `Q275` education, `Q288` income scale |
| Weights | `W_WEIGHT` retained as `W_WEIGHT` and copied to `weight` |
| Recodes | **None** in merge — raw codes only |

### 3.2 AmericasBarometer (LAPOP)

| Criterion | Decision |
|-----------|----------|
| Years | **2012, 2014, 2017, 2019** only |
| Excluded | Pre-2012 (schema/weight chaos); **2020–2023** (user decision); USA pretest file (`usa final dataset.dta`) |
| Rationale for ≥2012 | Post-2012 sampling / design more stable; usable `wt` on all retained waves |
| Columns | **Eval subset only**: trust-core + demog + design/weights + provenance (not full outer-union of all LAPOP vars) |
| Year labeling | Explicit map year (not LAPOP `wave`). **2019 files have `wave=2018`** → stored as `year=2019`, raw in `wave_raw` |
| Recodes | **None** |

### 3.3 Why years need not match across surveys

Adapters encode a **country cultural state** \(z_c\), not “Mexico in calendar year \(t\).” For OOS generalization, **country-level moments** are the target. Year matching would matter only for a historical coincidence claim (same moment in time). Pooling AB 2012–2019 within country increases power for stable political-culture items; WVS remains a single-year anchor per country.

---

## 4. Known limitations

1. **Construct ≠ instrument.** GPS preference tasks ≠ WVS attitude items ≠ AB political-culture items. Mapping is theory-guided and pre-registered; it is not item equivalence.  
2. **AB does not cover all six GPS dimensions.** Primary AB claims should stay in the trust / system-support cluster.  
3. **Wave-specific missingness (AB).** USA 2017 (WVS-adjacent year) is thin on core: missing e.g. `b10a`, `b31`, `exc6`, `exc7`, `dem2` in that wave. See `_manifest.json`.  
4. **`exc7` sparse.** Roughly ~60% non-null overall (wave-dependent).  
5. **Weights.**  
   - AB: `wt` non-null on all retained waves; `weight1500` mainly 2012. Unified column `weight` = `wt` when present.  
   - WVS: `W_WEIGHT` non-null with mean ≈ 1.0 — treat weighted analyses carefully; **unweighted is the safe default** until design is re-checked.  
6. **Missing codes not cleaned.** LAPOP often uses 88/98 (or longer missing codes in later waves); WVS uses negative codes in the master questionnaire for DK/NA. Scoring must mask missings.  
7. **No reverse-coding in merge.** Config notes like “1-4 inv” mean *scoring* should invert for polarity alignment — not that values were inverted here.  
8. **DEM2 coverage.** Present mainly in earlier waves; missing in USA 2017/2019 and MEX 2017/2019 per manifest. Wording below follows standard LAPOP democracy-preference item (2012 master questionnaire lineage).  
9. **Replication / sharing.** LAPOP terms of use typically prohibit redistributing raw third-party data dumps to journals; for external publication follow Vanderbilt CGD citation and replication rules. Internal Drive share for lab collaborators is the intended use of this folder.

---

## 5. Provenance columns (all files)

| Column | Meaning |
|--------|---------|
| `survey` | `WVS_wave7` or `AmericasBarometer` |
| `country` | `USA` or `MEX` |
| `year` | Evaluation year label (see selection criteria) |
| `source_file` | Original `.dta` filename |
| `weight` | Convenience copy of primary weight when available |
| `wave_raw` / `year_lapop_raw` | AB only — original LAPOP wave/year fields when present |

---

## 6. Exact item wording — World Values Survey Wave 7

**Source:** Local `data/WVS/MasterQuestionnaire.pdf` (WVS 2017–2021 Wave 7 master questionnaire).  
**Codes:** As in questionnaire; data file may store the same integers. Mask official missing codes before analysis.

### 6.1 Trust (GPS dim: trust) — clean bridge

**Q57 — Generalized trust**  
> Generally speaking, would you say that most people can be trusted or that you need to be very careful in dealing with people?  
> (1) Most people can be trusted (2) Need to be very careful  

**Stem for Q58–Q63**  
> I’d like to ask you how much you trust people from various groups. Could you tell me for each whether you trust people from this group completely, somewhat, not very much or not at all?  

| Item | Object | Scale |
|------|--------|-------|
| Q58 | Your family | 1 Completely … 4 Not at all (tier 3 / in-group) |
| Q59 | Your neighborhood | same |
| Q60 | People you know personally | same (tier 3) |
| Q61 | People you meet for the first time | same |
| Q62 | People of another religion | same |
| Q63 | People of another nationality | same |

**Stem for Q64, Q69–Q71, Q73, Q81 (confidence in organizations)**  
> I am going to name a number of organizations. For each one, could you tell me how much confidence you have in them: is it a great deal of confidence, quite a lot of confidence, not very much confidence or none at all?  

| Item | Object | Scale |
|------|--------|-------|
| Q64 | The churches | 1 A great deal … 4 None at all |
| Q69 | The police | same |
| Q70 | The courts | same |
| Q71 | The government | same |
| Q73 | Parliament | same (tier 3) |
| Q81 | Charitable or humanitarian organizations | same (mapped under posrecip tier 3) |

### 6.2 Patience (bridge)

**Stem for child qualities Q12–Q14**  
> Here is a list of qualities that children can be encouraged to learn at home. Which, if any, do you consider to be especially important? Please choose up to five!  

Coded as mentioned / not mentioned (binary in map):

| Item | Quality | GPS map |
|------|---------|---------|
| Q12 | Tolerance and respect for other people | posrecip (tier 2) |
| Q13 | Thrift, saving money and things | patience (tier 2) |
| Q14 | Determination, perseverance | patience (tier 2) |

**Q43**  
> Less importance placed on work in our lives — Good (1) / Don’t mind (2) / Bad (3)  

**Q50**  
> How satisfied are you with the financial situation of your household?  
> 1 Completely dissatisfied … 10 Completely satisfied (tier 3)

### 6.3 Risk / economic values (bridge — not lottery risk)

**Stem for Q106–Q109**  
> Now I'd like you to tell me your views on various issues. How would you place your views on this scale? 1 means you agree completely with the statement on the left; 10 means you agree completely with the statement on the right…

| Item | Left (1) | Right (10) |
|------|----------|------------|
| Q106 | Incomes should be made more equal | There should be greater incentives for individual effort |
| Q107 | Private ownership of business and industry should be increased | Government ownership of business and industry should be increased |
| Q109 | Competition is good | Competition is harmful |

### 6.4 Positive reciprocity (thin bridge)

| Item | Wording summary |
|------|-----------------|
| Q12 | Child quality: tolerance and respect (see above) |
| Q174 | With which statement do you agree most? The basic meaning of religion is: (1) To follow religious norms and ceremonies (2) To do good to other people |
| Q81 | Confidence in charitable/humanitarian organizations (see confidence stem) |

### 6.5 Negative reciprocity / norm enforcement (bridge)

**Q176**  
> How much do you agree or disagree with the statement that nowadays one often has trouble deciding which moral rules are the right ones to follow?  
> 1 Completely agree … 10 Completely disagree  

**Justifiability stem (Q177–Q179, Q178, Q195)**  
> Please tell me for each of the following actions whether you think it can always be justified, never be justified, or something in between…  
> 1 Never justifiable … 10 Always justifiable  

| Item | Action |
|------|--------|
| Q177 | Claiming government benefits to which you are not entitled |
| Q178 | Avoiding a fare on public transport (mapped risktaking tier 3) |
| Q179 | Stealing property |
| Q195 | Death penalty (tier 3) |

### 6.6 Altruism (bridge — membership, not windfall giving)

**Membership stem**  
> Now I am going to read off a list of voluntary organizations… active member (2) / inactive member (1) / don’t belong (0)  

| Item | Organization |
|------|----------------|
| Q99 | Environmental organization |
| Q101 | Humanitarian or charitable organization |
| Q103 | Self-help group, mutual aid group (tier 3) |

### 6.7 Demographics (WVS)

| Item | Wording |
|------|---------|
| Q260 | Respondent’s sex (by observation): (1) Male (2) Female |
| Q261 | Year of birth |
| Q262 | Age in years |
| Q275 | Highest education level completed (ISCED-style codes in questionnaire) |
| Q288 | Household income scale 1 (lowest) … 10 (highest) in country |

---

## 7. Exact item wording — AmericasBarometer (LAPOP)

**Primary source:** LAPOP AmericasBarometer **2012** Master Core Questionnaire (English), Vanderbilt University.  
**Cross-check:** 2017 Master Questionnaire for continuity of IT1 / B / EXC / ING4 / PN4.  
**Scale for B-battery (Card B):** 1 = **Not at all** … 7 = **A lot** (88 DK, 98 DA in many waves; later waves may use longer missing codes).

Country name is filled as “(country)” / “country” in the master; USA and Mexico field instruments substitute national labels (e.g. Congress vs National Legislature).

### 7.1 Interpersonal trust (clean for GPS trust)

**IT1**  
> And speaking of the people from around here, would you say that people in this community are very trustworthy, somewhat trustworthy, not very trustworthy or untrustworthy…?  
> (1) Very trustworthy (2) Somewhat trustworthy (3) Not very trustworthy (4) Untrustworthy  

### 7.2 System support (B1–B6)

Introduced with the 1–7 ladder (television example in interviewer script).

| Item | Wording (2012 master) |
|------|------------------------|
| **B1** | To what extent do you think the courts in (country) guarantee a fair trial? |
| **B2** | To what extent do you respect the political institutions of (country)? |
| **B3** | To what extent do you think that citizens' basic rights are well protected by the political system of (country)? |
| **B4** | To what extent do you feel proud of living under the political system of (country)? |
| **B6** | To what extent do you think that one should support the political system of (country)? |

### 7.3 Institutional trust (selected B items)

| Item | Wording |
|------|---------|
| **B10A** | To what extent do you trust the justice system? |
| **B12** | To what extent do you trust the Armed Forces? |
| **B13** | To what extent do you trust the National Legislature? |
| **B18** | To what extent do you trust the National Police? |
| **B21** | To what extent do you trust the political parties? |
| **B31** | To what extent do you trust the Supreme Court? |
| **B32** | To what extent do you trust the local or municipal government? |
| **B37** | To what extent do you trust the mass media? |
| **B47A** | To what extent do you trust elections in this country? |

### 7.4 Corruption

| Item | Wording |
|------|---------|
| **EXC6** | In the last twelve months, did any government employee ask you for a bribe? (0 No / 1 Yes typical) |
| **EXC7** | Taking into account your own experience or what you have heard, corruption among public officials is… (1) Very common (2) Common (3) Uncommon (4) Very uncommon |

**Note:** Some later waves change corruption batteries (e.g. politician-focused variants). Use `_manifest.json` for presence; confirm coding before scoring.

### 7.5 Democracy / system evaluation

| Item | Wording |
|------|---------|
| **ING4** | Democracy may have problems, but it is better than any other form of government. To what extent do you agree or disagree with this statement? (typically 1–7 agree ladder) |
| **PN4** | In general, would you say that you are very satisfied, satisfied, dissatisfied or very dissatisfied with the way democracy works in (country)? (1) Very satisfied (2) Satisfied (3) Dissatisfied (4) Very dissatisfied |
| **DEM2** | Democracy preference item (standard LAPOP form): which statement do you agree with most — democracy is preferable to any other form of government, or under some circumstances an authoritarian government may be preferable, (plus a common third option that it does not matter / indifferent in many rounds). **Coverage is wave-dependent** (often missing in 2017/2019 USA). Spot-check value labels in the year-specific raw file before strict stem matching. |

### 7.6 Demographics & design

| Item | Typical content |
|------|-----------------|
| **Q1** | Sex (often interviewer-noted): (1) Male (2) Female |
| **Q2** | Age in years completed |
| **ED** | Years of education / last year of schooling completed (country card) |
| **Q10** | Household income category (country-specific card; USA present in merged USA file) |
| **wt** | Single-country single-year weight |
| **weight1500** | Multi-year / multi-country style weight when provided |
| **upm**, **estratopri**, **estratosec** | Design / sampling variables when present |

---

## 8. GPS → survey map (audit tags)

| GPS dim | WVS items (tier) | Tag | AB items | Tag |
|---------|------------------|-----|----------|-----|
| trust | Q57, Q59, Q61–63, Q64, Q69–71 (t2); Q58, Q60, Q73 (t3) | **clean** | IT1; B1–B6; B10A…; EXC6/7 | **clean** |
| patience | Q13, Q14, Q43 (t2); Q50 (t3) | bridge | — | **no-coverage** |
| risktaking | Q106, Q107, Q109 (t2); Q178 (t3) | bridge | — | **no-coverage** |
| posrecip | Q12, Q174 (t2); Q81 (t3) | bridge | (not in core extract) | stretch / omit |
| negrecip | Q176, Q177, Q179 (t2); Q195 (t3) | bridge | EXC only (partial) | stretch |
| altruism | Q101, Q99 (t2); Q103 (t3) | bridge | (not in core extract) | thin / omit |

Full compact table: `CONSTRUCT_MAP.md`.

---

## 9. How a colleague should load the data (Drive)

```python
from pathlib import Path
import pandas as pd

# Point this at the folder you downloaded from Drive
DATA = Path("path/to/merged")  # or Path(".") if notebook sits next to parquets

usa_wvs = pd.read_parquet(DATA / "USA_WVS_wave7.parquet")
mex_wvs = pd.read_parquet(DATA / "MEX_WVS_wave7.parquet")
usa_ab  = pd.read_parquet(DATA / "USA_Barometer_2012_2019.parquet")
mex_ab  = pd.read_parquet(DATA / "MEX_Barometer_2012_2019.parquet")
```

Dependencies: `pandas`, `pyarrow` (and `matplotlib`/`seaborn` optional for the notebook plots).

---

## 10. Citations

- **WVS:** Haerpfer et al., World Values Survey Wave 7 (2017–2022). JD Systems Institute & WVSA. Local codebook/questionnaire in `data/WVS/`.  
- **AmericasBarometer:** LAPOP Lab / Center for Global Democracy, Vanderbilt University. Cite country, year(s), version from original filenames, and www.vanderbilt.edu/lapop.  
- **GPS (context only):** Falk et al. (2018), *QJE*.  
- **SCA 2.0 design:** lab position paper / `synthetic_generation` README; item map in `sca2_datagen.config.WVS_ITEM_MAP`.

---

## 11. Rebuild note (lab only)

On a machine that still has the raw country-year `.dta` files under `data/Barometer/` and `data/WVS/`:

```bash
python _build_merge.py
```

Drive recipients normally **do not** rebuild; they use the four parquets.

---

## 12. Non-claims (read before scoring)

- These files do **not** prove cultural fidelity of adapters to real populations by themselves.  
- Matching human **signs** is directional evidence, not calibrated GPS magnitudes.  
- AB political culture is **not** a six-preference GPS battery.  
- Synthetic Tier-1 accuracy and Tier-2 survey alignment answer different questions — keep them labeled separately (H1 synthetic recovery vs H2/H3 external moments).
