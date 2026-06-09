# Research Plan: Wildfire Incidence and Local Public Finance

**Version**: 0.3 (design decisions locked, Q9 pending)
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

The design is identical to the companion wildfire-health paper. Treatment is a county's
first qualifying wildfire (≥1,000 acres, MTBS-defined) in 2015–2019 across all 11
contiguous western states. The 2015 starting year is motivated by the 2014 USFS
Wildfire Hazard Potential (WHP) raster, which is predetermined with respect to all
fires from 2015 onward.

We construct propensity-score inverse-probability weights (PS-IPW) using WHP quintile,
pre-2014 fire history, pre-2014 fiscal baselines, RUCC, median household income,
poverty rate, population density, and home rule status. Home rule is pre-determined
and time-invariant, making it a valid matching covariate.

We apply three heterogeneity-robust estimators:
1. Callaway & Sant'Anna (2021) group-time ATT framework
2. Synthetic DiD (Arkhangelsky et al. 2021)
3. Two-stage DiD (Gardner 2022)

### 3.2 Identifying Assumption

Conditional on WHP quintile, pre-2014 fire history, pre-2014 fiscal baselines, and
home rule status, the timing of a county's first qualifying fire in 2015–2019 is
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
pre-date the 2015–2019 treatment window for all counties in our sample. If any county
adopted a charter after 2014, we exclude them from the home rule heterogeneity analysis.

### 3.6 Threat: COVID-19 in 2020

Same exclusion as wildfire-health: 2020 retained in the outcome panel but counties
with first qualifying fire in 2020 excluded from the treatment group.

---

## 4. Sample

- **States**: CA, OR, WA, ID, MT, WY, CO, UT (8 Pacific-Coast/Rockies states;
  desert Southwest excluded for ecological homogeneity — AZ, NV, NM excluded)
- **Period**: 2000–2020 (fiscal year panel)
- **Treatment cohorts**: 2015, 2016, 2017, 2018 (first qualifying fire year)
- **Control counties**: no qualifying MTBS fire ≥1,000 acres in 2015–2019; smoke
  buffer exclusion at 100 km (baseline)
- **Population restriction**: counties with population ≥ 1,000 in every year
- **CoG coverage restriction**: counties with Annual Survey coverage in ≥ 85% of
  sample years (≥ 18 of 21 years, 2000–2020). Document excluded counties' WHP
  distribution and treatment rate. Robustness check at ≥ 70% (≥ 15 of 21 years).
- **Unit of analysis**: county government only (CoG type code 1)
- **Fiscal year alignment**: assign CoG fiscal year data to the calendar year in
  which the fiscal year begins (FY July 2015–June 2016 → year 2015)
- **Deflator**: national CPI-U; all outcomes expressed in 2019 dollars

Expected sample size to be confirmed after CoG coverage audit; 8-state sample smaller
than full western US but broader than wildfire-health (250 counties, 6 NW states).

---

## 5. Data Sources

### 5.1 Census of Governments (CoG)

- **Annual Survey of State and Local Government Finances** (1992–2021): downloaded
  from Census Bureau bulk files. Provides total revenues, tax revenues, property tax,
  intergovernmental revenues, expenditures, capital outlays, and debt by government
  unit and FIPS code.
  - **Coverage rule**: retain counties with Annual Survey data in ≥ 85% of sample
    years (≥ 18 of 21 years). Impute isolated gaps (≤ 3 years) by county-level
    linear interpolation; document imputation rate. Robustness check at ≥ 70%.
    Endogenous attrition risk: verify that missingness does not cluster in
    post-fire years before proceeding with imputation.
  - Data URL: https://www.census.gov/programs-surveys/gov-finances/data/datasets.html
- **Quinquennial Census** (2002, 2007, 2012, 2017): complete coverage; use for
  pre-treatment baseline matching variables (prefer 2012 Census over Annual Survey
  interpolation for pre-2014 baselines).

### 5.2 Fire and Hazard Data (Reused from Wildfire-Health)

- **USFS WHP 2014**: `data/raw/WHP/` — copy or symlink from wildfire-health.
- **MTBS fire perimeters**: `data/raw/mtbs_perims/` — same source; extend county
  intersection to all 11 western states.
- Treatment assignment and smoke buffer parquets rebuilt from MTBS using the same
  `05_smoke_buffer.py` logic, applied to the full western US sample.

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

Logistic propensity score on: WHP quintile, pre-2014 fire indicator, pre-2014 log
acres burned, pre-2014 revenue per capita quintile, pre-2014 property tax per capita
quintile, pre-2014 long-term debt per capita, RUCC, median HH income, poverty rate,
population density, and county home rule charter status (binary).

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

All questions resolved 2026-06-09 except Q9.

| # | Question | Decision |
|---|---|---|
| Q1 | Study area | **8 states**: CA, OR, WA, ID, MT, WY, CO, UT. Desert SW (AZ, NV, NM) excluded for ecological homogeneity. |
| Q2 | CoG coverage threshold | **≥ 85%** (≥ 18 of 21 years) as primary; ≥ 70% as robustness check. Verify missingness not clustered in post-fire years before imputing gaps. |
| Q3 | Unit of analysis | **County government only** (CoG type code 1). Consistent with FIPS-level treatment assignment. |
| Q4 | Fiscal year alignment | **Assign to year FY begins** (FY July 2015–June 2016 → year 2015). Aligns fiscal label with treatment cohort year; clean k = −1 pre-trend window. |
| Q5 | Inflation deflator | **National CPI-U**. Consistent with public finance literature and companion health paper. |
| Q6 | Home rule coding | **Both levels**: state-level doctrine (background) + county-level charter status (primary variable for propensity score and heterogeneity). |
| Q7 | Home rule role | **Both**: county charter status in propensity score and regression adjustment (control) AND as heterogeneity variable in a dedicated table. |
| Q8 | FEMA aid | **Secondary outcome + robustness control**: (a) in the mechanism table as an outcome, (b) as a control in one robustness specification to isolate non-FEMA fiscal effects. |
| Q9 | Headline estimand | **`fiscal_balance_pc`** (revenues minus expenditures per capita). Positions against Liao & Kousky (2022) — the only existing causal paper (California municipalities only). Leads with the policy-relevant net burden; `rev_proptax_pc` is the primary mechanism column. See `literature_review.md` §3. |

---

## 10. Pending Tasks (Ordered)

- [x] Answer design questions Q1–Q8 (done 2026-06-09)
- [x] Literature review (`/deep-research`) — done 2026-06-09; see `literature_review.md`
- [x] **Q9**: Headline estimand = `fiscal_balance_pc`. See `literature_review.md` §3.
- [x] Collect home rule / Dillon's Rule data: state doctrine + county charter status
      for CA, OR, WA, ID, MT, WY, CO, UT; done 2026-06-09 via `code/01_build/00_home_rule_compile.py`
      Findings: 34–36 valid pre-2015 charter counties (CA:14, CO:2, MT:3*, OR:9, WA:6).
      Clark County WA (charter 2015) excluded. Montana charter dates unconfirmed — verify
      via MT Secretary of State before using in analysis. WY home rule is municipal only
      (counties follow Dillon's Rule). UT home rule statewide by statute (no individual charters).
      Primary heterogeneity: cross-state (home rule states vs. Dillon's Rule states: ID, WY).
- [x] Document fiscal year end months for 8 western states; implement FY-begin recoding
      in `code/01_build/03_cog_finance_pull.py` — done 2026-06-09.
      All 8 states: June 30 FY end (month=6), except ID (September 30) and WA (verify per county).
      FY-begin recoding: CoG year → year-1 when FY end month < 12.
- [x] **CoG data download and coverage audit**: done 2026-06-09. See `data/raw/cog/cog_coverage_audit.csv`.
      **Findings (critical — review before proceeding)**:
      - Raw panel: 3,991 obs, 485 unique counties, FY-begin years 1999–2011 and 2016–2020.
      - FY-begin years MISSING: 2012–2015 (CoG survey years 2013–2016 not publicly available).
      - ≥85% primary threshold: **33 counties** pass (594 obs). Sample too small for credible C&S inference.
      - ≥70% robustness threshold: 63 counties pass.
      - Attrition risk: 87 counties show >50% of their missing years falling in the post-fire window
        (2016–2020). This reflects sparse survey sampling of small counties, not endogenous dropout.
      - FY end months: 81.8% at June (month 6), 18.2% at September (Idaho; month 9). Correct.
      - **Root cause of thin coverage**: the ≥85% threshold requires 18/21 years. With only 18 years
        structurally available (1999–2011 + 2016–2020), the maximum achievable coverage is 18/21 = 85.7%.
        Counties must appear in every available survey year to pass. Most small counties are sampled only
        in quinquennial years and some Annual Survey years.
      - **Critical gap implication**: FY-begin years 2012–2015 are missing, cutting across the pre-treatment
        transition period. For g=2015 cohort: treatment year (FY-begin 2015) is unobservable; only k=+1
        through k=+4 are available post-treatment. For g=2016+: contemporaneous year IS available.
        Last observable pre-treatment data point is FY-begin 2011 for all cohorts.
- [ ] **BLOCKER: Fill CoG 2013–2016 gap via Census API** (required for credible inference).
      Without this, the ≥85% sample has 33 counties and the treatment year itself is missing for
      the 2015 cohort. Steps:
      1. Register for Census API key: https://api.census.gov/data/key_signup.html (free, instant)
      2. Query: `https://api.census.gov/data/2013/govs/govsannual?get=GOVID,AMTNUM,AMOUNT&for=county:*&in=state:06,08,16,30,41,49,53,56&key=<KEY>`
      3. Extend `03_cog_finance_pull.py` with `fill_gap_via_api(key, years=[2013,2014,2015,2016])` function.
      4. Re-run coverage audit; expected improvement to ~80–100+ counties at ≥85% threshold.
      Until this is done, analysis should use the ≥70% sample (63 counties) as interim,
      with the understanding that results are preliminary.
- [ ] Extend WHP and MTBS county intersection to 8-state sample
- [ ] Panel assembly: CPI-U deflation, outlier flagging, suppression audit
- [ ] PS-IPW matching and balance table (include county charter status)
- [ ] C&S main estimation (primary and secondary outcomes)
- [ ] Event study (dynamic aggregation)
- [ ] Cohort-specific ATTs (group aggregation)
- [ ] Home rule heterogeneity table (county charter × treatment interaction)
- [ ] SDiD and Two-Stage DiD
- [ ] Robustness checks (incl. ≥ 70% CoG coverage, FEMA control spec)
- [x] Literature review (`/deep-research`) — done 2026-06-09; see `literature_review.md`
- [ ] Paper draft (`/academic-paper`)
