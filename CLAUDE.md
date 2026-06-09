# CLAUDE.md — Wildfire Finance Project

Inherits all rules from `~/.claude/CLAUDE.md`. Project-specific additions below.

---

## Project Context

**Research question**: Causal effect of wildfire incidence on local government revenues,
expenditures, and fiscal balance in western US counties.
**Design**: Callaway & Sant'Anna (2021) staggered DiD with PS-IPW matching on USFS WHP —
identical identification strategy to the wildfire-health project.
**Estimand**: ATT.
**Sample**: NW US county-year panel, 2000–2020. States: CA, OR, WA, ID, MT, WY.
Treatment: first qualifying MTBS fire (≥1,000 acres) in 2015–2019; WHP 2014 vintage
predetermined for all treated cohorts.
**Status**: Planning phase. See `research_plan.md`.

---

## Project-Specific Coding Rules

- **Primary analysis language**: R for DiD estimation (`did`, `fixest`); Python for data
  assembly and spatial operations. Mirrors wildfire-health stack exactly.
- **DiD estimation**: R `did::att_gt()` for C&S; `fixest::sunab()` for Sun-Abraham;
  `did2s` for two-stage DiD; `synthdid` for synthetic DiD.
- **Public finance data**: Census of Governments (CoG) Annual Survey and Quinquennial Census.
  - Annual Survey (1992–2021): sampled — verify county coverage before using. Small
    counties (population < 25,000) may have gaps; impute only if ≤ 3 missing years
    per county and document the imputation rate.
  - Quinquennial Census (years ending in 2 and 7): complete coverage. For pre-treatment
    baseline matching variables, prefer the 2012 Census over Annual Survey interpolation.
  - Fiscal year alignment: CA, OR use July–June (offset by 6 months from calendar year);
    WA, ID, MT, WY use calendar year or varying fiscal years. Assign CoG fiscal year to
    the calendar year in which the fiscal year ends. Document state-specific conventions
    in `code/01_build/03_cog_finance_pull.py`.
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
- **Matching covariates**: WHP quintile + pre-2014 fire history + pre-2014 fiscal
  baseline (revenue per capita, property tax per capita, debt per capita) + RUCC +
  median HH income + poverty rate + population density.
- **Treatment window**: 2015–2019 only. WHP 2014 predetermined for all cohorts.
- **Suppress / flag**: CoG records with clearly implausible values (per-capita revenues
  > 3× state median or < 0) should be flagged and excluded with documentation.
- **Reproducibility**: all scripts seed random processes. All paths relative to project
  root via `here::here()` in R and `pathlib.Path` in Python.

---

## Data Sources

| Source | Description | Coverage | Key Limitation |
|---|---|---|---|
| Census of Governments Annual Survey | County-level revenues, expenditures, debt | 1992–2021 (annual, sampled) | Incomplete for small counties; verify coverage |
| Census of Governments Quinquennial Census | Same, complete coverage | 1992, 1997, 2002, 2007, 2012, 2017 | 5-year gaps |
| USFS WHP 2014 | Pre-treatment fire hazard raster | 270 m, static | Reuse from wildfire-health |
| MTBS | Fire perimeters and treatment assignment | 1984–2022 | Reuse from wildfire-health |
| FEMA OpenData | Presidential Disaster Declarations | 1953–present | Mechanism control only; post-treatment |
| ACS 5-yr | Socioeconomic covariates | 2009–2020 | Reuse from wildfire-health |
| USDA RUCC | Urban-rural classification | 2003, 2013 | Reuse from wildfire-health |

---

## Key Variables

| Variable | Description | Source |
|---|---|---|
| `fips` | 5-digit county FIPS code | Census |
| `year` | Calendar year (CoG fiscal year end) | — |
| `g` | Year of first qualifying fire; 0 if never treated | MTBS |
| `treated` | =1 if county had ≥1 MTBS fire ≥1,000 ac in year | MTBS |
| `whp_mean` | Area-weighted mean WHP score | USFS WHP 2014 |
| `whp_q` | WHP quintile (1–5) | Derived |
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
