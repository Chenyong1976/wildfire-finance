# Research Plan: Wildfire Incidence and Local Public Finance

**Version**: 0.4 (redesigned: quinquennial-only, 1992–2022, WHP 2012)
**Last updated**: 2026-06-09

---

## 1. Research Question

What is the causal effect of large wildfire incidence on local government revenues,
expenditures, and fiscal balance in western US counties, and does the effect differ
by counties' institutional fiscal authority (home rule vs. Dillon's Rule)?

### Sub-questions

1. **Revenue**: Does wildfire incidence reduce property tax revenues through property
   damage and assessed-value depreciation? How large is the effect relative to baseline
   revenue, and how quickly does it materialise given state-specific assessment cycles?
2. **Expenditures**: Does wildfire incidence raise emergency and infrastructure
   expenditures? Is there a capital outlays spike followed by reversion, or do
   expenditures remain persistently elevated?
3. **Fiscal balance**: What is the net fiscal effect? Do federal and state
   intergovernmental transfers (FEMA aid, state fire funds) offset revenue losses,
   or do counties experience net fiscal deterioration?
4. **Debt**: Do affected counties issue additional long-term debt to finance
   post-fire recovery spending?
5. **Institutional heterogeneity**: Do home rule counties absorb wildfire fiscal
   shocks differently than Dillon's Rule counties, reflecting greater flexibility
   to raise emergency revenues, reallocate budgets, or issue debt?

---

## 2. Motivation and Contribution

Wildfires impose direct costs on households and businesses, but their fiscal consequences
for local governments are poorly understood. Counties bear first-responder costs,
infrastructure repair obligations, and revenue losses from property damage —
simultaneously. Yet the causal literature is thin: most existing evidence is
case-study-based (e.g., post-Paradise, CA analyses) or relies on self-reported
county estimates that confound fire severity with political incentives for federal aid.

This paper contributes to four literatures.

First, the natural disaster and public finance literature (Deryugina 2017; Groen et al.
2020; Jerch et al. 2023). Deryugina (2017) shows that hurricanes raise intergovernmental
transfers but finds no persistent net fiscal effect; we ask whether this holds for
wildfire, where the primary damage mechanism — land and vegetation rather than structures
— and the federal aid architecture differ substantially from floods and hurricanes.

Second, the wildfire economics literature (Wibbenmeyer & Ma 2021; Boomhower 2019;
Borgschulte et al. 2024). Existing work focuses on property values, insurance, and
health outcomes. Local fiscal consequences are a first-order policy concern that has
not been causally identified.

Third, the local public finance and fiscal resilience literature (Lutz et al. 2011;
Alm & Sjoquist 2020). Property tax revenue responses to assessed value shocks are
well-documented for housing market downturns; wildfire-driven shocks differ because
they affect land value, trigger insurance claims, and generate simultaneous expenditure
pressure on the same government facing revenue decline.

Fourth, the fiscal federalism and local government autonomy literature (Fischel 2001;
Briffault 1990). Home rule grants counties inherent fiscal authority not explicitly
prohibited by state law, while Dillon's Rule confines counties to powers explicitly
granted by the state legislature. This pre-determined institutional variation creates
testable predictions about heterogeneous fiscal responses: home rule counties should
have more tools to respond (emergency levies, special assessment districts, discretionary
debt issuance), leading to faster recovery or larger upfront fiscal adjustment.

---

## 3. Identification Strategy

### 3.1 Design

Treatment is a county's first qualifying wildfire (≥1,000 acres, MTBS-defined) in
**2013–2021** across 8 western states. The treatment window aligns with both WFP
predetermination and quinquennial CoG census years: fires 2013–2016 form the g=2017
cohort (first post-treatment census year is 2017); fires 2017–2021 form the g=2022
cohort.

The **2012 USFS Wildfire Potential (WFP) raster** is the primary matching variable.
WFP 2012 is predetermined for all fires from 2013 onward — it was finalized before the
2013 fire season (RDS-2015-0045, ESRI Grid, EPSG:5070, continuous values 0–100+).
WHP 2014 (the first vintage in the Wildfire Hazard Potential series) is used as a
robustness check only; it is NOT predetermined for 2013–2014 fires because its FSim
and LANDFIRE 2010 inputs extended into the 2014 calibration period.

We construct propensity-score inverse-probability weights (PS-IPW) using WHP quintile,
pre-2012 fire history, pre-2012 fiscal baselines (from the 2012 CoG census), RUCC,
median household income, poverty rate, population density, and home rule status.
Home rule is pre-determined and time-invariant, making it a valid matching covariate.

We apply three heterogeneity-robust estimators:
1. Callaway & Sant'Anna (2021) group-time ATT framework
2. Synthetic DiD (Arkhangelsky et al. 2021)
3. Two-stage DiD (Gardner 2022)

### 3.2 Identifying Assumption

Conditional on WHP quintile, pre-2012 fire history, pre-2012 fiscal baselines, and
home rule status, the timing of a county's first qualifying fire in 2013–2021 is
plausibly orthogonal to trends in fiscal outcomes. Fire timing within a structural
hazard and institutional class depends on weather shocks (drought, lightning, wind)
unrelated to pre-existing fiscal trends.

### 3.3 Threat: Property Assessment Lag

Property tax revenues respond to assessed value changes, and assessment cycles vary
across states — from annual reassessment (CA, OR) to biennial or triennial cycles
(AZ, CO, ID, MT, NM, NV, UT, WY). This creates a mechanical lag of 1–3 years between
fire occurrence and any property tax revenue response. We will:
- Document assessment cycle lengths for all 11 western states.
- Report event-study estimates through k = +4 to capture delayed effects.
- Report separate estimates for annual-assessment states (CA, OR, WA) vs.
  longer-cycle states as a robustness check.

### 3.4 Threat: FEMA Endogeneity

FEMA Hazard Mitigation Grants and Individual Assistance are triggered by presidential
disaster declarations, which depend on damage scale — creating mechanical correlation
between fire severity and intergovernmental revenue. FEMA aid appears in two roles:
(a) as a **secondary outcome** in the mechanism table (does wildfire incidence raise
intergovernmental transfers?), and (b) as a **control variable in one robustness
specification** to isolate the non-FEMA fiscal effect and ask how much of the
revenue/expenditure response runs through FEMA channels. FEMA aid is never included
in main specifications. Declaration rates by cohort are reported as sample characterisation.

### 3.5 Threat: Home Rule Endogeneity

Home rule charter adoption is a historical political decision, not a response to
recent wildfire risk. We verify this by checking that home rule charter adoption dates
pre-date the 2013 treatment start for all counties in our sample. If any county
adopted a charter after 2012, we exclude them from the home rule heterogeneity analysis.

### 3.6 Threat: COVID-19 in 2020–2021

The CoG 2022 census captures FY data ending in 2022 (FY-begin year 2021). Counties
with first qualifying fire in 2020 and 2021 are included in the g=2022 cohort but
the COVID period may confound fiscal outcomes. We check robustness by restricting the
g=2022 cohort to fires 2017–2019 and treating 2020–2021 fire counties as excluded.

---

## 4. Sample

- **States**: CA, OR, WA, ID, MT, WY, CO, UT (8 Pacific-Coast/Rockies states;
  desert Southwest excluded for ecological homogeneity — AZ, NV, NM excluded)
- **Period**: 1992–2022 (**quinquennial CoG census years only**: 1992, 1997, 2002,
  2007, 2012, 2017, 2022). Annual Survey years ignored. FY-begin recoded years:
  1991, 1996, 2001, 2006, 2011, 2016, 2021.
- **Treatment cohorts**:
  - g=2017: first qualifying fire in 2013–2016 (treated in CoG 2017 census year)
  - g=2022: first qualifying fire in 2017–2021 (treated in CoG 2022 census year)
- **Control counties**: never treated (no qualifying MTBS fire ≥1,000 acres in
  2015–2021); smoke buffer exclusion at 100 km (baseline). **Current sample: 55
  never-treated counties** (16% of the 344-county CoG panel). Thin common support
  is expected and must be documented; ESS of reweighted control group is a key
  diagnostic (see §7).
- **Population restriction**: counties with population ≥ 1,000 in every year
- **CoG coverage**: complete by design — quinquennial census covers all government
  units. No coverage restriction required. Current panel: **344 counties × 7 years
  = 2,408 observations** (all counties in all 7 census years).
- **Unit of analysis**: county government only (CoG type code 1)
- **Fiscal year alignment**: assign CoG fiscal year data to the calendar year in
  which the fiscal year begins (FY July 2016–June 2017 → year 2016)
- **Deflator**: national CPI-U; all outcomes expressed in 2019 dollars

Sample note: Montana consolidated city-counties (Deer Lodge FIPS 30023, Silver Bow
FIPS 30093) are absent from the CoG county government file — they are not coded as
county governments (type=1) and cannot be included in the fiscal analysis.

---

## 5. Data Sources

### 5.1 Census of Governments (CoG) — Quinquennial Census Only

**Source**: Census of Governments quinquennial census (years ending in 2 and 7).
Complete coverage of all government units — no sampling. No coverage restriction required.

**Years used**: 1992, 1997, 2002, 2007, 2012, 2017, 2022.

**Archive sources**:
- 1992–2012: `_IndFin_1967-2012.zip` (wide CSV format)
- 2017, 2022: Individual Unit Files (32-char fixed-width, `tables/{year}/`)

**FIPS crosswalk**: historical archive (1992–2012) uses sequential county numbering
and alphabetical state codes. County FIPS codes are recovered by matching normalized
county names to the Census national county reference file (`national_county.txt`).

**Current panel**: 344 counties × 7 census years = 2,408 county-year observations.
All 344 counties present in all 7 years. Montana consolidated city-counties excluded
(not coded as county governments in CoG type=1 records).

**Item codes used**: T01 (property tax), T09 (total taxes), B01 (fed IGR), B20 (state IGR),
B80 (total IGR), C89 (own-source general revenue), A15 (total general revenue),
E61 (total general expenditure), E04 (capital outlays), F01 (long-term debt outstanding).

### 5.2 Fire and Hazard Data

- **USFS WFP 2012**: `wildfire-finance/data/raw/WHP/Data/wfp_2012_continuous/wfp2012_cnt`
  — primary matching variable. Predetermined for fires from 2013 onward. ESRI Grid
  format, EPSG:5070 native, nodata = -2147483647, dtype int32. Continuous values.
- **USFS WHP 2014**: `wildfire-health/data/raw/WHP/Data/whp_2014_continuous/whp2014_cnt`
  — robustness matching variable only. Not predetermined for 2013–2014 fires.
- **MTBS fire perimeters**: shared from `wildfire-health/data/raw/mtbs_perims/`.
  County intersection built for 8-state sample. Treatment window: 2013–2021.
  MTBS minimum threshold: ≥1,000 acres.
- Treatment assignment: first qualifying fire per county in 2013–2021. Groups:
  g=2017 for fires 2013–2016; g=2022 for fires 2017–2021; g=0 for never treated.
- **Cohort counts**: updated after re-run with 2013–2021 treatment window.
- Smoke buffer parquets: `data/processed/fire_perimeters_100km_buffer.parquet`.

### 5.3 FEMA Disaster Declarations

- Source: FEMA OpenData API (`https://www.fema.gov/api/open/v2/disasterDeclarationsSummaries`)
- Filter: `incidentType = "Fire"`, `stateCode` in 8-state sample, `incidentBeginDate`
  in 2000–2020.
- Use as secondary outcome (mechanism) and sample characterisation only.

### 5.4 Home Rule / Dillon's Rule

- **State-level doctrine**: National League of Cities (NLC) classifications and state
  constitutional provisions. Western state classification: MT, OR, WA, CA, CO, NM
  grant counties home rule authority (to varying degrees); AZ, ID, NV, UT, WY follow
  Dillon's Rule for counties.
- **County-level charter status**: ICMA Form of Government Survey and state archives
  for county charter adoption dates. Relevant for CA (14 charter counties), CO, MT,
  WA, OR where within-state variation exists.
- Coding level to be confirmed (open question 6).

### 5.5 Covariates (Reused)

- ACS 5-year estimates: median HH income, poverty rate, uninsurance rate, population,
  share 65+, population density. Extended to all 11 western states.
- USDA RUCC: 2003 and 2013 vintages.

---

## 6. Outcome Variables

All fiscal outcomes are expressed per capita (ACS population denominators) and
deflated to 2019 dollars using the national CPI-U.

### Primary outcomes

| Variable | Description |
|---|---|
| `rev_total_pc` | Total general revenues per capita |
| `rev_proptax_pc` | Property tax revenues per capita |
| `exp_total_pc` | Total general expenditures per capita |
| `fiscal_balance_pc` | Total revenues minus total expenditures per capita |

### Secondary / mechanism outcomes

| Variable | Description |
|---|---|
| `rev_intergovt_pc` | Intergovernmental revenues per capita (FEMA channel) |
| `exp_capital_pc` | Capital outlays per capita (infrastructure repair) |
| `exp_current_pc` | Current operations expenditures per capita |
| `debt_lt_pc` | Long-term debt outstanding per capita |

### Headline estimand

**`fiscal_balance_pc`** (Q9 decided 2026-06-09). Positions directly against Liao & Kousky (2022)
— the only existing causal paper, California municipalities only, finding a 25 pp increase in
budget deficit probability. This paper extends to county governments across 8 western states
with varying property tax institutions. `rev_proptax_pc` is the primary mechanism column,
not the headline. Recommended table structure: col (1) `fiscal_balance_pc`,
col (2) `rev_total_pc`, col (3) `exp_total_pc`, col (4) `rev_proptax_pc`.
See `literature_review.md` §3.

---

## 7. Matching and Control Group Construction

Logistic propensity score on: WHP 2012 quintile, pre-2012 fire indicator, pre-2012 log
acres burned, pre-2012 revenue per capita quintile (from 2012 CoG census), pre-2012
property tax per capita quintile, pre-2012 long-term debt per capita, RUCC, median
HH income, poverty rate, population density, and county home rule charter status (binary).

**Home rule coding**: coded at both levels.
- *State-level*: binary for whether the state follows Dillon's Rule vs. grants
  home rule authority to counties (CA, CO, MT, OR, WA = home rule; ID, WY, UT = Dillon's Rule).
  Serves as background context; collinear with state FEs if included.
- *County-level*: binary for whether the specific county has adopted a home rule
  charter. Captures within-state variation in CA (14 charter counties), CO, MT, WA, OR.
  This is the primary variable used in the propensity score, main specifications, and
  heterogeneity analysis.
- Verify all county charters pre-date 2015; exclude any post-2014 charter adoptions
  from the heterogeneity analysis.

Home rule is included in the propensity score to ensure balance on institutional
structure across treated and control counties.

ATT inverse-probability weights: treated counties w=1; control counties
w = ê/(1−ê), trimmed at 99th percentile. Report ESS of reweighted control group.
The structural scarcity of high-WHP, never-fired counties may again produce thin
common support (ESS = 8/48 in the health paper); with the broader western US sample,
support is expected to improve but should be verified.

---

## 8. Robustness and Heterogeneity Checks

| Check | Rationale |
|---|---|
| 50 km smoke buffer | Widen control pool; test directional stability |
| Placebo (random treatment year) | Falsification: ATT ≈ 0 expected |
| Sun-Abraham estimator | Heterogeneity-robust TWFE check |
| Bacon decomposition | Verify proportion of clean comparisons |
| Assessment-cycle subsamples | Annual (CA, OR, WA) vs. longer-cycle states (others) |
| Exclude 2015 cohort | Check if 2015 NW fire-season severity drives results |
| Per-capita vs. total dollars | Verify population normalisation does not drive results |
| Trim extreme fiscal outliers | Sensitivity to unusual CoG records |
| **Home rule heterogeneity** | Interact treatment with home rule status; test whether fiscal response magnitude or recovery speed differs by institutional authority |
| **Dillon's Rule heterogeneity** | Symmetric check using state-level Dillon's Rule classification |
| Desert Southwest subsample | Exclude AZ, NV, NM to test sensitivity to ecological heterogeneity (if all 11 states used) |

---

## 9. Design Decisions Log

All questions resolved 2026-06-09.

| # | Question | Decision |
|---|---|---|
| Q1 | Study area | **8 states**: CA, OR, WA, ID, MT, WY, CO, UT. Desert SW (AZ, NV, NM) excluded for ecological homogeneity. |
| Q2 | CoG data source | **Quinquennial census years only** (1992, 1997, 2002, 2007, 2012, 2017, 2022). Annual Survey dropped — sampling gaps create endogenous attrition. Complete coverage by design; no coverage restriction required. |
| Q3 | Unit of analysis | **County government only** (CoG type code 1). Consistent with FIPS-level treatment assignment. |
| Q4 | Fiscal year alignment | **Assign to year FY begins** (FY July 2016–June 2017 → year 2016). Aligns fiscal label with treatment cohort year; clean k = −1 pre-trend window. |
| Q5 | Inflation deflator | **National CPI-U**. Consistent with public finance literature and companion health paper. |
| Q6 | Home rule coding | **Both levels**: state-level doctrine (background) + county-level charter status (primary variable for propensity score and heterogeneity). |
| Q7 | Home rule role | **Both**: county charter status in propensity score and regression adjustment (control) AND as heterogeneity variable in a dedicated table. |
| Q8 | FEMA aid | **Secondary outcome + robustness control**: (a) in the mechanism table as an outcome, (b) as a control in one robustness specification to isolate non-FEMA fiscal effects. |
| Q9 | Headline estimand | **`fiscal_balance_pc`** (revenues minus expenditures per capita). Positions against Liao & Kousky (2022) — the only existing causal paper (California municipalities only). Leads with the policy-relevant net burden; `rev_proptax_pc` is the primary mechanism column. See `literature_review.md` §3. |
| Q10 | Treatment window & WFP/WHP vintage | **Treatment window 2013–2021**. C&S groups: g=2017 (fires 2013–2016), g=2022 (fires 2017–2021). Primary matching variable: **WFP 2012** (USFS Wildfire Potential 2012; predetermined for fires from 2013 onward; finalized before 2013 fire season). WHP 2014 is robustness only — not predetermined for 2013–2014 fires. |
| Q11 | Study period | **1992–2022** (quinquennial census years: 7 years of data). Pre-treatment window: 5 census observations (1992–2012). Post-treatment: up to 2 observations (2017, 2022) depending on cohort. |

---

## 10. Pending Tasks (Ordered)

- [x] Answer design questions Q1–Q11 (done 2026-06-09)
- [x] Literature review (`/deep-research`) — done 2026-06-09; see `literature_review.md`
- [x] **Q9**: Headline estimand = `fiscal_balance_pc`. See `literature_review.md` §3.
- [x] Collect home rule / Dillon's Rule data: state doctrine + county charter status
      for CA, OR, WA, ID, MT, WY, CO, UT; done 2026-06-09 via `code/01_build/00_home_rule_compile.py`
      Findings: 34–36 valid pre-2013 charter counties (CA:14, CO:2, MT:3*, OR:9, WA:6).
      Clark County WA (charter 2015) excluded. Montana charter dates unconfirmed — verify
      via MT Secretary of State before using in analysis. WY home rule is municipal only
      (counties follow Dillon's Rule). UT home rule statewide by statute (no individual charters).
      Primary heterogeneity: cross-state (home rule states vs. Dillon's Rule states: ID, WY).
- [x] Document fiscal year end months for 8 western states; implement FY-begin recoding
      in `code/01_build/03_cog_finance_pull.py` — done 2026-06-09.
      All 8 states: June 30 FY end (month=6), except ID (September 30).
      FY-begin recoding: CoG year → year-1 when FY end month < 12.
- [x] **CoG data download — quinquennial census panel**: done 2026-06-09.
      **Final panel**: 344 counties × 7 census years = 2,408 county-year observations.
      All 344 counties present in all 7 census years (complete coverage by design).
      FY-begin years: 1991, 1996, 2001, 2006, 2011, 2016, 2021.
      FIPS crosswalk: name-based matching to Census national county file (national_county.txt).
      Montana consolidated city-counties (30023 Deer Lodge, 30093 Silver Bow) excluded —
      not coded as county governments (CoG type=1). WHP 2012 primary; WHP 2014 robustness.
- [ ] **WHP county intersection** — re-run required. WFP 2012 now primary (RDS-2015-0045,
      `data/raw/WHP/Data/wfp_2012_continuous/wfp2012_cnt`). Script outputs both `whp_2012`
      (primary) and `whp_2014` (robustness). Nodata bug fixed: reads nodata from raster metadata
      (ESRI Grid nodata = -2147483647, not -9999). Health project `01_whp_to_county.py` also
      fixed. Run `code/01_build/01_whp_to_county.py` to produce updated parquet.
- [ ] **MTBS county intersection** — re-run required. Treatment window extended to 2013–2021.
      Pre-fire history variables renamed `pre2013_*` (history 2000–2012). C&S group g=2017
      now captures fires 2013–2016. Run `code/01_build/02_mtbs_to_county.py` to produce
      updated parquet and cohort counts.
- [ ] Panel assembly: CPI-U deflation, outlier flagging (code/01_build/07_panel_assemble.py)
- [ ] PS-IPW matching on WHP 2012 quintile + pre-2012 fiscal baselines + covariates
- [ ] Balance table (code/02_matching/02_balance_table.R)
- [ ] C&S main estimation with g=2017 / g=2022 cohorts (code/03_analysis/01_cs_main.R)
- [ ] Event study: dynamic aggregation relative to quinquennial treatment year
- [ ] Cohort-specific ATTs (g=2017 vs g=2022)
- [ ] Home rule heterogeneity table
- [ ] SDiD and Two-Stage DiD
- [ ] Robustness: WHP 2014 vintage, 50 km smoke buffer, COVID robustness (restrict g=2022 to fires 2017–2019)
- [ ] Verify Montana charter county dates via MT Secretary of State
- [ ] Paper draft (`/academic-paper`)
