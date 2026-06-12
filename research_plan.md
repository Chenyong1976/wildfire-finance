# Research Plan: Wildfire Incidence and Local Public Finance

**Version**: 0.7 (all analyses complete; paper draft with 8 tables + home rule; June 2026)
**Last updated**: 2026-06-10

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

- **States**: All lower-48 states (~3,000 counties). Expanded from the original 8-state
  western sample (CA, OR, WA, ID, MT, WY, CO, UT) in June 2026. AK, HI, DC excluded.
  Western 8-state subsample retained as a robustness check for ecological homogeneity.
- **Period**: 2002–2022 (**quinquennial CoG census years only**: 2002, 2007, 2012,
  2017, 2022). Annual Survey years ignored. FY-begin recoded years vary by state
  FY end month (June, September, or December/calendar year). 1992 and 1997 dropped:
  1990 Census not in Census REST API.
  Pre-treatment periods: 2002, 2007, 2012. Post-treatment periods: 2017, 2022.
- **FY alignment note**: December FY-end states (IN, KY, MN, MO, NH, NJ, ND, NY, OH,
  PA, SD, WV, WI) assign CoG year directly as FY-begin year (no recoding). All other
  states subtract 1 (June or September FY ends). See `FY_END_MONTHS` in `03_cog_finance_pull.py`.
- **Treatment cohorts**:
  - g=2017: first qualifying fire in 2013–2016 (treated in CoG 2017 census year);
    post-treatment observations at 2017 and 2022
  - g=2022: first qualifying fire in 2017–2021 (treated in CoG 2022 census year);
    post-treatment observation at 2022 only
- **Control counties**: never treated (no qualifying MTBS fire ≥1,000 acres in
  2013–2021); smoke buffer exclusion at 100 km (baseline). National expansion greatly
  expands never-treated pool (many eastern counties have no large wildfire history).
  ESS of reweighted control group remains a key diagnostic (see §7).
- **Population restriction**: counties with population ≥ 1,000 in every year
- **CoG coverage**: complete by design — quinquennial census covers all government
  units. No coverage restriction required. National panel: **~3,000 counties × 5 years
  ≈ 15,000 observations** (all lower-48 county governments in all 5 census years).
  Note: CT county governments abolished 1960 (no type=1 rows); RI counties largely
  administrative. Virginia independent cities excluded (not county governments).
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

**Years used**: 2002, 2007, 2012, 2017, 2022 (analysis panel). CoG raw data spans
1992–2022; 1992 and 1997 are parsed but excluded from analysis panel.

**Archive sources**:
- 1992–2012: `_IndFin_1967-2012.zip` (wide CSV; parts a/b/c are horizontal splits
  merged on ID, not concatenated vertically)
- 2017, 2022: Individual Unit Files (32-char fixed-width, `tables/{year}/`)

**FIPS crosswalk**: historical archive uses name-based matching to `national_county.txt`.

**Current panel**: ~2,975 counties × 5 census years ≈ 14,875 county-year observations
(all lower-48 county governments). Montana consolidated city-counties excluded.

**2017/2022 item code aggregation** (summary codes absent in IUF format):
- rev_total = sum(A + B + C + T + U prefix codes)  [B=federal IGR, C=state IGR]
- exp_total = sum(E01–E89, F01–F89, G01–G89, I89, J19/J67/J68/J85)
- debt_lt   = 44T + 49U
- rev_proptax = T01; exp_capital = sum(F01–F89, G01–G89)

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
- **Cohort counts** (national lower-48, intensive margin):
  g=2017 (fires 2013–2016): 267 counties; g=2022 (fires 2017–2021): 117 counties;
  never-treated: 2,591 counties. Extensive margin: 629 / 255 / 2,091.
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
| **Western-8 subsample** | Restrict to original CA/CO/ID/MT/OR/UT/WA/WY sample — tests sensitivity to national expansion and ecological heterogeneity |
| Regional heterogeneity | Census division FEs or region-interacted estimates to test whether eastern/western fire regimes produce different fiscal effects |

---

## 9. Design Decisions Log

All questions resolved 2026-06-09.

| # | Question | Decision |
|---|---|---|
| Q1 | Study area | **All lower-48 states** (expanded June 2026). Original 8-state western sample (CA, OR, WA, ID, MT, WY, CO, UT) retained as robustness subsample for ecological homogeneity check. |
| Q2 | CoG data source | **Quinquennial census years only** (2002, 2007, 2012, 2017, 2022 in analysis panel). 1992/1997 parsed but excluded — 1990 Census not in REST API, making pop denominators unreliable. Annual Survey dropped — sampling gaps create endogenous attrition. |
| Q3 | Unit of analysis | **County government only** (CoG type code 1). Consistent with FIPS-level treatment assignment. |
| Q4 | Fiscal year alignment | **Assign to year FY begins** (FY July 2016–June 2017 → year 2016). Aligns fiscal label with treatment cohort year; clean k = −1 pre-trend window. |
| Q5 | Inflation deflator | **National CPI-U**. Consistent with public finance literature and companion health paper. |
| Q6 | Home rule coding | **Both levels**: state-level doctrine (background) + county-level charter status (primary variable for propensity score and heterogeneity). |
| Q7 | Home rule role | **Both**: county charter status in propensity score and regression adjustment (control) AND as heterogeneity variable in a dedicated table. |
| Q8 | FEMA aid | **Secondary outcome + robustness control**: (a) in the mechanism table as an outcome, (b) as a control in one robustness specification to isolate non-FEMA fiscal effects. |
| Q9 | Headline estimand | **`fiscal_balance_pc`** (revenues minus expenditures per capita). Positions against Liao & Kousky (2022) — the only existing causal paper (California municipalities only). Leads with the policy-relevant net burden; `rev_proptax_pc` is the primary mechanism column. See `literature_review.md` §3. |
| Q10 | Treatment window & WFP/WHP vintage | **Treatment window 2013–2021**. C&S groups: g=2017 (fires 2013–2016), g=2022 (fires 2017–2021). Primary matching variable: **WFP 2012** (USFS Wildfire Potential 2012; predetermined for fires from 2013 onward; finalized before 2013 fire season). WHP 2014 is robustness only — not predetermined for 2013–2014 fires. |
| Q11 | Study period | **2002–2022** (quinquennial census years: 5 years of data). Pre-treatment periods: 2002, 2007, 2012 (3 pre-treatment observations). Post-treatment: 2017 and 2022 for g=2017 cohort; 2022 only for g=2022 cohort. 1992/1997 excluded — 1990 Census unavailable via API. |

---

## 10. Task Log

### Completed

- [x] Answer design questions Q1–Q11 (2026-06-09)
- [x] Literature review — see `literature_review.md`
- [x] Home rule / Dillon's Rule data collection — national lower-48 state doctrine
      (`home_rule_states.csv`) + confirmed pre-2015 charter counties (`home_rule_counties.csv`).
      State counts: Dillon's Rule 2,177 counties, home rule 798 counties. Charter counties: 90.
- [x] CoG data download — **national lower-48** quinquennial census panel (June 2026 expansion).
      `data/processed/panel_final.parquet`: ~2,975 counties × 5 census years ≈ 14,875 obs.
      FY-begin recoding applied for all 48 states (see `FY_END_MONTHS` in `03_cog_finance_pull.py`).
- [x] WFP 2012 / WHP 2014 county intersection — `data/processed/whp_county.parquet`.
- [x] MTBS county intersection — national treatment assignment (g=2017: 629 ext / 267 int;
      g=2022: 255 ext / 117 int; never-treated: 2,091 ext / 2,591 int).
- [x] Panel assembly with home rule columns — `code/01_build/07b_add_home_rule.py`.
- [x] PS-IPW matching — `code/02_matching/01_ps_matching.R`. ESS = 122.1 (intensive).
- [x] Balance table — `output/tables/balance_table.txt`; `code/02_matching/02_balance_table.R`.
- [x] C&S main estimation (intensive + extensive) — `code/03_analysis/01_cs_main.R`;
      output in `output/rds/cs_att_gt_*.rds` and `output/tables/cs_simple_agg*.csv`.
- [x] Event study — `code/03_analysis/02_event_study.R`; `output/figures/event_study_*.pdf`.
- [x] Cohort ATTs (g=2017 / g=2022) — `output/tables/group_time_atts.csv`.
- [x] Robustness checks (8 specs incl. assessment-cycle subsamples) — `code/03_analysis/04_robustness.R`
      + `07_assessment_cycle.R`; `output/tables/robustness_table.csv`, `assessment_cycle.csv`.
- [x] Sun-Abraham estimator — `code/03_analysis/05_sun_abraham.R`; `output/tables/sun_abraham_table.csv`.
- [x] Synthetic DiD — `output/tables/intergovt_synthdid.csv`; `output/rds/synthdid_*.rds`.
- [x] Two-Stage DiD — `output/tables/stacked_did_table.csv`.
- [x] Dose-response analysis — `output/tables/dose_response_*.csv`.
- [x] Home rule / Dillon's Rule institutional heterogeneity — `code/03_analysis/06_home_rule_heterogeneity.R`;
      `output/tables/home_rule_heterogeneity.csv`. Key result: property tax decline concentrated
      in Dillon's Rule states (−$410, p=0.011); home rule states null (−$26, p=0.915).
- [x] Assessment-cycle subgroup robustness — `code/03_analysis/07_assessment_cycle.R`;
      `output/tables/assessment_cycle.csv`. Both subgroups null; confirms main finding not
      driven by assessment timing. Annual subgroup power-constrained (n_ctl=30).
- [x] Paper draft — `paper/wildfire_finance.tex`. 8 tables (+ Table A1 MDE):
      Table 1 Balance, Table 2 Extensive main, Table 3 Intensive main,
      Table 4 Cohort ATTs, Table 5 Robustness (8 specs), Table 6 Estimators,
      Table 7 Dose-response, Table 8 Home rule heterogeneity, Table A1 MDE.
      Four contributions; national sample (2,975 counties).

### Not implemented (deferred)

- [ ] COVID robustness: restrict g=2022 to fires 2017–2019 (deferred by user 2026-06-10)
- [ ] Bacon decomposition (`code/03_analysis/06_cohort_bacon.R`)
- [ ] Montana charter county date verification via MT Secretary of State (low priority;
      MT counties excluded by `pre2015_valid == True` filter in current analysis)
- [ ] HCUP hospitalization outcomes (separate health paper)
