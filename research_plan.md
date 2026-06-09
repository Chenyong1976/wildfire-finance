# Research Plan: Wildfire Incidence and Local Public Finance

**Version**: 0.1 (planning phase)
**Last updated**: 2026-06-09

---

## 1. Research Question

What is the causal effect of large wildfire incidence on local government revenues,
expenditures, and fiscal balance in western US counties?

### Sub-questions

1. **Revenue**: Does wildfire incidence reduce property tax revenues through property
   damage and assessed-value depreciation? How large is the effect relative to baseline
   revenue, and how quickly does it materialise given typical assessment cycles?
2. **Expenditures**: Does wildfire incidence raise emergency and infrastructure
   expenditures? Is there a capital outlays spike followed by a reversion, or do
   expenditures remain persistently elevated?
3. **Fiscal balance**: What is the net fiscal effect? Do federal and state
   intergovernmental transfers (FEMA aid, state fire funds) offset revenue losses,
   or do counties experience net fiscal deterioration?
4. **Debt**: Do affected counties issue additional long-term debt to finance
   post-fire recovery spending?

---

## 2. Motivation and Contribution

Wildfires impose direct costs on households and businesses, but their fiscal consequences
for local governments are poorly understood. Counties bear first-responder costs,
infrastructure repair obligations, and revenue losses from property damage —
simultaneously. Yet the causal literature is thin: most existing evidence is
case-study-based (e.g., post-Paradise, CA analyses) or relies on self-reported
county estimates that confound fire severity with political incentives for federal aid.

This paper contributes to three literatures.

First, the natural disaster and public finance literature (Deryugina 2017; Groen et al.
2020; Jerch et al. 2023). Deryugina (2017) shows that hurricanes raise intergovernmental
transfers but finds no persistent net fiscal effect; we ask whether this holds for a
different disaster type (wildfire) where the primary mechanism — property damage to
land rather than structures — operates differently and where FEMA coverage is less
generous than for floods/hurricanes.

Second, the wildfire economics literature (Wibbenmeyer & Ma 2021; Boomhower 2019;
Borgschulte et al. 2024). Existing work focuses on property values, insurance, and
health. Local fiscal consequences are a first-order policy concern that has not been
causally identified.

Third, the local public finance and fiscal resilience literature (Lutz et al. 2011;
Alm & Sjoquist 2020). Property tax revenue responses to assessed value shocks are
well-documented for housing market downturns; wildfire-driven shocks differ because
they affect land value, trigger insurance claims, and generate expenditure pressure
simultaneously.

---

## 3. Identification Strategy

### 3.1 Design

The design is identical to the companion wildfire-health paper. Treatment is defined as
a county's first qualifying wildfire (≥1,000 acres, MTBS-defined) in 2015–2019.
The 2015 starting year is motivated by the 2014 USFS Wildfire Hazard Potential (WHP)
raster, which is predetermined with respect to all fires from 2015 onward.

We construct propensity-score inverse-probability weights (PS-IPW) using WHP quintile,
pre-2014 fire history, pre-2014 fiscal baselines (total revenue per capita, property
tax per capita, long-term debt per capita), RUCC, median household income, poverty rate,
and population density.

We apply three heterogeneity-robust estimators:
1. Callaway & Sant'Anna (2021) group-time ATT framework
2. Synthetic DiD (Arkhangelsky et al. 2021)
3. Two-stage DiD (Gardner 2022)

### 3.2 Identifying Assumption

Conditional on WHP quintile, pre-2014 fire history, and pre-2014 fiscal baselines, the
timing of a county's first qualifying fire in 2015–2019 is plausibly orthogonal to
trends in fiscal outcomes. Fire timing within a structural hazard class depends on
weather shocks (drought, lightning, wind) that are unrelated to pre-existing revenue
or expenditure trends.

### 3.3 Threat: Property Assessment Lag

Property tax revenues respond to assessed value changes, and assessment cycles vary
from annual (CA, OR) to biennial or triennial (ID, MT, WY). This creates a
mechanical lag of 1–3 years between fire occurrence and any property tax revenue
response. We will:
- Document state-specific assessment cycles and code expected lag lengths.
- Report event-study estimates with a long post-period (k = 0 through k = 4) to
  capture delayed effects.
- Estimate separately for states with annual assessment (CA, OR, WA) vs. longer
  cycles (ID, MT, WY).

### 3.4 Threat: FEMA Endogeneity

FEMA Hazard Mitigation Grants and Individual Assistance are triggered by presidential
disaster declarations, which themselves depend on the scale of damage — creating a
mechanical correlation between fire severity and intergovernmental revenue. We treat
FEMA aid as a downstream outcome (part of the intergovernmental revenue channel),
not as a control. We will report FEMA fire declaration rates by cohort as a
characterisation of the sample.

### 3.5 Threat: COVID-19 in 2020

Same exclusion as wildfire-health: 2020 is retained in the outcome panel but counties
with first qualifying fire in 2020 are excluded from the treatment group.

---

## 4. Sample

- **States**: CA, OR, WA, ID, MT, WY (same NW states as wildfire-health)
- **Period**: 2000–2020 (fiscal year panel)
- **Treatment cohorts**: 2015, 2016, 2017, 2018 (first qualifying fire year)
- **Control counties**: no qualifying MTBS fire ≥1,000 acres in 2015–2019; smoke
  buffer exclusion at 100 km (baseline)
- **Population restriction**: counties with population ≥ 1,000 in every year
- **CoG coverage restriction**: counties with CoG Annual Survey coverage in ≥ 15 of
  21 sample years; document exclusion rate

Expected sample size will be verified once CoG data are assembled; as a starting
point, the health paper's 250-county analytic sample provides the ceiling.

---

## 5. Data Sources

### 5.1 Census of Governments (CoG)

- **Annual Survey of State and Local Government Finances** (1992–2021): downloaded
  from Census Bureau bulk files. Provides total revenues, tax revenues, property tax,
  intergovernmental revenues, expenditures, capital outlays, and debt by government
  unit and FIPS code.
  - **Critical limitation**: the Annual Survey is a stratified sample. All governments
    above a threshold population are included with certainty; smaller governments are
    sampled. For NW states, verify coverage rates for counties with population < 25,000
    before proceeding. If coverage is < 70% of county-years for the treatment group,
    consider switching to Quinquennial Census years only (2002, 2007, 2012, 2017) as
    a restricted sample.
  - Data URL: https://www.census.gov/programs-surveys/gov-finances/data/datasets.html
- **Quinquennial Census** (2002, 2007, 2012, 2017): complete coverage; use for
  matching variable construction (2012 Census pre-treatment baselines).

### 5.2 Fire and Hazard Data (Reused from Wildfire-Health)

- **USFS WHP 2014**: `data/raw/WHP/` — symlink or copy from wildfire-health if
  re-downloading is not needed.
- **MTBS fire perimeters**: `data/raw/mtbs_perims/` — same source.
- Treatment assignment and smoke buffer parquets can be derived from wildfire-health
  processed outputs or rebuilt from scratch.

### 5.3 FEMA Disaster Declarations

- Source: FEMA OpenData API (`https://www.fema.gov/api/open/v2/disasterDeclarationsSummaries`)
- Filter: `incidentType = "Fire"`, `stateCode` in NW states, `incidentBeginDate`
  in 2000–2020.
- Use to characterise FEMA aid as a mechanism; do NOT use as a control variable
  in main specifications.

### 5.4 Covariates (Reused)

- ACS 5-year estimates: median HH income, poverty rate, uninsurance rate, population,
  share 65+, population density.
- USDA RUCC: 2003 and 2013 vintages.

---

## 6. Outcome Variables

All fiscal outcomes are expressed per capita (using ACS population denominators)
and deflated to 2019 dollars using the CPI-U.

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

### Reporting order

Following the health paper's structure: report primary outcomes in the main table
(Panel A–C by estimator), secondary outcomes in a separate table. The primary
estimand for the abstract is `rev_proptax_pc` (sharpest channel) and
`fiscal_balance_pc` (policy-relevant summary).

---

## 7. Matching and Control Group Construction

Logistic propensity score on: WHP quintile, pre-2014 fire indicator, pre-2014 log
acres burned, pre-2014 revenue per capita quintile, pre-2014 property tax per capita
quintile, pre-2014 long-term debt per capita, RUCC, median HH income, poverty rate,
population density.

ATT inverse-probability weights: treated counties receive w=1; control counties
receive w = ê/(1−ê), trimmed at the 99th percentile.

Check and report the effective sample size (ESS) of the reweighted control group.
Given the structural scarcity of high-WHP, never-fired counties documented in the
health paper (ESS = 8 out of 48), we anticipate similarly thin common support.
Report ESS prominently and consider a robustness check restricted to counties below
the 90th-percentile propensity score.

---

## 8. Robustness Checks

| Check | Rationale |
|---|---|
| 50 km smoke buffer | Widen the control pool; test directional stability |
| Placebo (random treatment year) | Falsification: should yield ATT ≈ 0 |
| Sun-Abraham estimator | Heterogeneity-robust TWFE check |
| Bacon decomposition | Verify proportion of clean comparisons |
| Assessment-cycle subsamples | Separate CA/OR/WA (annual) from ID/MT/WY (lagged) |
| Exclude 2015 cohort | Check whether 2015 fire-season severity drives results |
| Per-capita vs. per-county-dollar | Verify population normalisation does not drive results |
| Trim extreme fiscal outliers | Sensitivity to unusual CoG records |

---

## 9. Open Questions (Resolve Before Data Assembly)

1. **CoG coverage audit**: What fraction of NW county-years in 2000–2020 have Annual
   Survey data? If coverage is sparse for treated counties, the design may need to
   restrict to Quinquennial Census years.
2. **Unit definition**: CoG distinguishes county governments (type 1) from county-
   dependent school districts and special districts. Confirm county government type
   codes for CA (which has charter counties with different reporting structures).
3. **Fiscal year alignment**: Confirm fiscal year end months by state and code the
   calendar-year assignment rule before any analysis.
4. **Inflation deflator**: Confirm CPI-U (all urban) vs. regional CPI is appropriate.
   For rural western counties, PCE deflator may be preferable — flag this in the paper.
5. **FEMA aid timing**: FEMA grants are often disbursed 2–4 years after the disaster
   declaration. The intergovernmental revenue response in the event study may therefore
   be delayed relative to the fire date. Pre-register this expectation.

---

## 10. Pending Tasks (Ordered)

- [ ] CoG data download and coverage audit (script: `code/01_build/03_cog_finance_pull.py`)
- [ ] Fiscal year alignment documentation by state
- [ ] Reuse or rebuild WHP and MTBS county assignments from wildfire-health
- [ ] Panel assembly and suppression/outlier audit
- [ ] PS-IPW matching and balance table
- [ ] C&S main estimation (primary and secondary outcomes)
- [ ] Event study (dynamic aggregation)
- [ ] Cohort-specific ATTs (group aggregation)
- [ ] SDiD and Two-Stage DiD
- [ ] Robustness checks
- [ ] Literature review (`/deep-research`)
- [ ] Paper draft (`/academic-paper`)
