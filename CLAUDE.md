# CLAUDE.md — Wildfire Finance Project

Inherits all rules from `~/.claude/CLAUDE.md`. Project-specific additions below.

---

## Project Context

**Research question**: Causal effect of wildfire incidence on local government revenues,
expenditures, and fiscal balance in western US counties.
**Design**: Callaway & Sant'Anna (2021) staggered DiD with PS-IPW matching on USFS WHP.
**Estimand**: ATT.
**Sample**: Quinquennial CoG census panel, 1992–2022. States: CA, OR, WA, ID, MT, WY,
CO, UT. 344 counties × 7 census years (1992, 1997, 2002, 2007, 2012, 2017, 2022)
= 2,408 observations. Complete coverage by design — quinquennial census, no sampling restriction.
**Treatment**: First qualifying MTBS fire (≥1,000 acres) in 2013–2021.
  - g=2017 cohort: first fire 2013–2016 (208 counties)
  - g=2022 cohort: first fire 2017–2021 (85 counties)
  - g=0 (never treated): 56 counties
**WFP/WHP**: WFP 2012 primary (predetermined for fires from 2013 onward; finalized before
2013 fire season). WHP 2014 is robustness only (not predetermined for 2013–2014 fires).
**Status**: CoG panel, WHP county, MTBS county built. Next: PS-IPW matching, C&S estimation.

---

## Project-Specific Coding Rules

- **Primary analysis language**: R for DiD estimation (`did`, `fixest`); Python for data
  assembly and spatial operations. Mirrors wildfire-health stack exactly.
- **DiD estimation**: R `did::att_gt()` for C&S; `fixest::sunab()` for Sun-Abraham;
  `did2s` for two-stage DiD; `synthdid` for synthetic DiD.
- **Public finance data**: Census of Governments (CoG) **quinquennial census years only**
  (1992, 1997, 2002, 2007, 2012, 2017, 2022). Annual Survey years are NOT used — sampling
  gaps create endogenous attrition risk incompatible with the staggered DiD design.
  - Complete coverage by design: all county governments in the 8-state sample appear in all
    7 census years (344 counties, 2,408 obs). No coverage restriction needed.
  - Historical archive (1992–2012): `_IndFin_1967-2012.zip`. FIPS recovered via name-based
    crosswalk to Census `national_county.txt`. State filtering uses `FIPS Code-State` column
    (NOT `State Code`, which is alphabetical not FIPS).
  - 2017, 2022: Individual Unit Files (32-char fixed-width). FIPS embedded in gov ID.
  - Fiscal year alignment: **assign to the calendar year in which the fiscal year BEGINS**
    (FY July 2016–June 2017 → year 2016). All 8 states have non-December FY ends;
    always subtract 1 from the CoG-labeled year. FY-begin years: 1991, 1996, 2001, 2006,
    2011, 2016, 2021.
  - Montana consolidated city-counties (Deer Lodge 30023, Silver Bow 30093) are absent from
    CoG county government (type=1) records. Treat as unobservable; do not impute.
  - `WEST_STATES <- c("06","08","16","30","41","49","53","56")`
    (CA, CO, ID, MT, OR, UT, WA, WY). Use this vector in all R analysis scripts.
- **Unit of analysis**: county government only (type code 1 in CoG), not all local
  governments in the county. This matches the FIPS-level treatment assignment.
  Flag if county government fiscal data is unavailable and special district or
  municipality-level aggregation is used as a substitute.
- **FEMA declarations**: download Presidential Disaster Declarations from FEMA OpenData.
  Flag fire-related declarations (incident type = "Fire") as a potential mechanism
  control. Do NOT include FEMA aid as a covariate by default — it is post-treatment
  and endogenous. Use it only in mechanism decomposition analysis.
- **Smoke exclusion**: same 100 km baseline buffer as wildfire-health
  (`smoke_exclusion.parquet` will be symlinked from wildfire-health processed data
  or rebuilt from MTBS using the same `05_smoke_buffer.py` logic).
- **Three estimators**: Staggered DiD (C&S), Synthetic DiD, Two-Stage DiD — same
  scripts as wildfire-health, adapted for fiscal outcomes.
- **Matching covariates**: WFP 2012 quintile + pre-2013 fire history + pre-2013 fiscal
  baseline (from 2012 CoG census: revenue per capita, property tax per capita, debt per capita) +
  RUCC + median HH income + poverty rate + population density + home rule status
  (county-level charter indicator or state-level Dillon's Rule binary).
- **Home rule / Dillon's Rule**: Include as a pre-determined control variable in all
  main specifications and as the basis for a dedicated heterogeneity table. Source:
  state constitutional provisions and ICMA/NLC county charter records.
- **Treatment window**: 2013–2021. WFP 2012 primary (predetermined from 2013 onward;
  finalized before 2013 fire season). WHP 2014 is robustness only. C&S groups:
  g=2017 (fires 2013–2016), g=2022 (fires 2017–2021). Pre-treatment fire history:
  2000–2012 (`pre2013_*` variables). Document ESS of PS-IPW reweighted controls.
- **Deflator**: deflate all per-capita fiscal outcomes to 2019 dollars using the
  **national CPI-U**. Apply before any analysis; store deflated variables with
  `_real` suffix.
- **Suppress / flag**: CoG records with clearly implausible values (per-capita revenues
  > 3× state median or < 0) should be flagged and excluded with documentation.
- **Reproducibility**: all scripts seed random processes. All paths relative to project
  root via `here::here()` in R and `pathlib.Path` in Python.

---

## Data Sources

| Source | Description | Coverage | Key Limitation |
|---|---|---|---|
| Census of Governments Quinquennial Census | County-level revenues, expenditures, debt | 1992, 1997, 2002, 2007, 2012, 2017, 2022 | 5-year gaps; Annual Survey NOT used |
| USFS WFP 2012 | Primary matching raster (predetermined for 2013–2021 fires) | 270 m, static | wildfire-finance/data/raw/WHP/Data/wfp_2012_continuous/wfp2012_cnt |
| USFS WHP 2014 | Robustness matching raster (predetermined for 2015–2021 fires only) | 270 m, static | Shared from wildfire-health/data/raw/WHP/ |
| MTBS | Fire perimeters and treatment assignment | 1984–2022 | Reuse from wildfire-health |
| FEMA OpenData | Presidential Disaster Declarations | 1953–present | Mechanism control only; post-treatment |
| ACS 5-yr | Socioeconomic covariates | 2009–2020 | Reuse from wildfire-health |
| USDA RUCC | Urban-rural classification | 2003, 2013 | Reuse from wildfire-health |
| ICMA Form of Government Survey / NLC | County home rule charter status | Various years | Manual verification required for some counties |

---

## Key Variables

| Variable | Description | Source |
|---|---|---|
| `fips` | 5-digit county FIPS code | Census |
| `year` | Calendar year (CoG fiscal year end) | — |
| `g` | Year of first qualifying fire; 0 if never treated | MTBS |
| `treated` | =1 if county had ≥1 MTBS fire ≥1,000 ac in year | MTBS |
| `whp_2012` | Area-weighted mean WFP score | USFS WFP 2012 |
| `whp_2014` | Area-weighted mean WHP score (robustness) | USFS WHP 2014 |
| `whp_q` | WFP quintile (1–5, derived from whp_2012) | Derived from WFP 2012 |
| `rev_total_pc` | Total general revenues per capita | CoG |
| `rev_tax_pc` | Total tax revenues per capita | CoG |
| `rev_proptax_pc` | Property tax revenues per capita | CoG |
| `rev_intergovt_pc` | Intergovernmental revenues per capita | CoG |
| `exp_total_pc` | Total general expenditures per capita | CoG |
| `exp_capital_pc` | Capital outlays per capita | CoG |
| `exp_current_pc` | Current operations expenditures per capita | CoG |
| `debt_lt_pc` | Long-term debt outstanding per capita | CoG |
| `fiscal_balance_pc` | General revenues minus expenditures per capita | Derived |
| `fema_fire_decl` | =1 if county received FEMA fire disaster declaration in year | FEMA |
| `smoke_buffer_excl` | =1 if within 100 km of any fire perimeter in year | Derived |
| `home_rule_county` | =1 if county has adopted a home rule charter | ICMA / state records |
| `dillons_rule_state` | =1 if state follows Dillon's Rule for county powers | NLC / state constitutions |

---

## File Naming Convention

```
code/01_build/
  01_whp_to_county.py        # raster → county WHP (reuse/adapt from wildfire-health)
  02_mtbs_to_county.py       # fire perimeters → county-year treatment (reuse)
  03_cog_finance_pull.py     # Census of Governments download and parse
  04_fema_declarations.py    # FEMA disaster declarations download
  05_acs_merge.py            # ACS covariates (reuse)
  06_smoke_buffer.py         # exclusion zone construction (reuse)
  07_panel_assemble.py       # final panel build

code/02_matching/
  01_ps_matching.R           # PS-IPW matching
  02_balance_table.R         # covariate balance

code/03_analysis/
  01_cs_main.R               # C&S ATT_gt + simple and group aggregation
  02_event_study.R           # event study plot (dynamic aggregation)
  03_heterogeneity.R         # subgroup estimates by outcome and county type
  04_robustness.R            # robustness specs
  05_sun_abraham.R           # Sun-Abraham check
  06_cohort_bacon.R          # Bacon decomposition
  07_synthdid.R              # Synthetic DiD
  08_stacked_did.R           # Two-Stage DiD

code/04_output/
  01_tables.R                # regression tables
  02_figures.py              # matplotlib figures (300 DPI)
```

---

## Skill Configuration

**`/deep-research` prompt prefix**:
> "Economics mode. Target journals: JUE, AEJ:Applied, JPUBE, NTJ, JPublicEcon. Search NBER,
> SSRN, REPEC. Annotate each paper with: (1) research question, (2) identifying variation,
> (3) main result with magnitude, (4) primary identification threat."

**`/academic-paper` configuration**:
- Paper type: empirical journal article
- Template: `empirical_economics_template.md`
- Target journal: Journal of Public Economics or Journal of Urban Economics
- Citation format: Chicago author-date
- Output: LaTeX
