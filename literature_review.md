# Literature Review: Wildfire Incidence and Local Public Finance

**Version:** 1.0  
**Date:** 2026-06-09  
**Status:** Complete — Q9 decided  

---

## 1. Contribution Positioning

### Strand 1: Natural Disasters and Local Public Finance

The disaster-finance literature established that natural disasters impose persistent fiscal costs on local governments, but the evidence base rests almost entirely on hurricanes and floods in the eastern US. Jerch, Kahn, and Lin (2023) provided the most credible estimates: major hurricanes reduced local tax revenues and raised debt costs for over a decade, with distributional effects concentrated in minority-majority municipalities. Deryugina (2017) showed that the net fiscal burden on local governments is roughly neutral only because federal social insurance programs absorb a large share — a mechanism that may operate differently in wildfire-affected western counties, where FEMA disaster declarations are less automatic and federal transfers are structured differently. The proposed paper fills a first-order geographic and hazard-type gap: no causal evidence exists on fiscal impacts of wildfires for county governments outside California, a setting in which property tax rules, land use patterns, and insurance markets differ substantially from hurricane-exposed Atlantic and Gulf Coast municipalities.

### Strand 2: Wildfire Economics

Causal research on the economic consequences of wildfires has concentrated on labor market outcomes (Borgschulte, Molitor, and Zou 2024), housing market and development incentives (Baylis and Boomhower 2023), and health outcomes. The fiscal side of wildfire exposure is almost entirely unstudied at the causal level. Liao and Kousky (2022) is the sole exception: they found that California municipalities experienced a 25 percentage-point increase in the probability of running a budget deficit post-fire, with expenditure growth (17.3%) outstripping revenue growth (10.5%) despite rising property transfer tax receipts. Their identifying variation relies on quasi-random fire perimeter exposure within California, but their estimand is the municipality-level fiscal balance, their institutional setting is governed by Proposition 13's unique reassessment rules, and they study municipalities rather than county governments. The proposed paper extends this work to county governments across eight western states with varying property tax institutions, uses a formally staggered DiD estimator with pre-treatment hazard matching, and generates estimates that are more directly generalizable to the broader western US policy context.

### Strand 3: Property Tax Assessment Dynamics

The property tax literature established that assessed values lag market values by three to four years on average, and that assessors and legislatures actively smooth revenues by adjusting rates when values fall (Lutz, Molloy, and Shan 2011; Chen and Cohen 2025). This institutional behavior is central to the wildfire fiscal transmission mechanism. Wildfire does not simply destroy assessed value and reduce property tax revenue mechanically; the revenue response depends on how quickly assessors reassess fire-damaged properties, whether homeowners appeal, how state law constrains rate adjustments, and whether post-fire rebuilding triggers reassessment events. Chen and Cohen (2025) documented that a 1% change in market values translates to less than 0.30% change in assessed values within three years, with large cross-jurisdiction variance driven by institutional and political factors rather than market fundamentals. This lag structure implies that property tax revenues will respond to wildfire exposure on a delayed schedule — likely years 2 through 5 post-fire — which has direct implications for the event study window the paper should report, and for interpreting near-zero effects in years 0 and 1 as consistent with the underlying mechanism rather than as evidence of no effect.

### Strand 4: Home Rule and Fiscal Institutions

The home rule literature establishes that local governments' fiscal capacity and revenue flexibility depend on state-granted legal authority, not just on underlying economic conditions. Zhang, Nguyen-Hoang, and Chen (2022, 2023) provided the most credible evidence: home rule cities in Texas expanded their fiscal capacity primarily through property tax flexibility, though the effect took roughly 20 years to materialize in expenditure differences. The proposed paper exploits cross-state variation in fiscal institutions — CA, CO, MT, OR, WA classify as home rule states; ID and WY are Dillon's Rule states — as a source of treatment effect heterogeneity. However, county-level home rule adoption is rare even in home rule states: Washington has 7 home rule counties out of 39, Colorado has 2. Within-state variation in county home rule status is limited. This means the home rule heterogeneity analysis is more credibly executed as a cross-state comparison (home rule states vs. Dillon's Rule states) than as a within-state county charter analysis. That framing — how state institutional structure mediates wildfire fiscal impacts — is a genuine contribution relative to Liao and Kousky (2022), which operated within a single institutional environment.

---

## 2. Key Papers to Cite

The following constitute the core citation cluster for Section 2. Listed in argument order:

| Paper | Citation point |
|---|---|
| Liao & Kousky (2022), JAERE 9(3) | The only existing causal estimate of wildfire fiscal impacts; this paper directly extends their analysis to county governments outside California and to states without Proposition 13. |
| Jerch, Kahn & Lin (2023), JUE 134 | Establishes the credible causal framework for disaster → local public finance; the proposed paper applies equivalent logic to wildfire in the western US. |
| Deryugina (2017), AEJ:Policy 9(3) | Shows that net fiscal neutrality of disasters for local governments depends on federal social insurance absorption; motivates examining whether the same mechanism operates for wildfires. |
| Baylis & Boomhower (2023), AEJ:Applied 15(1) | Wildfire suppression subsidies create moral hazard in residential development, generating the stock of at-risk housing that determines the fiscal exposure the proposed paper estimates. |
| Borgschulte, Molitor & Zou (2024), RESTAT 106(6) | Wildfire smoke reduces labor market earnings, creating downstream fiscal pressure on income-related tax bases beyond direct fire damage. |
| Lutz, Molloy & Shan (2011), RSUE 41(4) | Assessment lag dynamics imply a predictable multi-year delay between fire-induced market value destruction and property tax revenue response; motivates the event study window design (k = 0 to +4). |
| Chen & Cohen (2025), NBER W33238 | Quantifies the market-to-assessed-value elasticity at below 0.30 within three years; provides the mechanism underpinning the delayed property tax revenue results. |
| Zhang, Nguyen-Hoang & Chen (2022, 2023), JRS / PBF | Most credible causal evidence that home rule increases fiscal capacity through property tax flexibility; supports the paper's cross-state institutional heterogeneity analysis. |
| Miao et al. (2023), EDCC 7(1) | Flood and hurricane evidence that lower-income counties borrow more after disasters; motivates rural-urban heterogeneity analysis. |
| Auh, Choi, Deryugina & Park (2022), NBER W30280 | Natural disasters raise municipal bond yields; relevant if the paper examines debt costs as a secondary outcome. |

---

## 3. Q9 Decision: Lead with `fiscal_balance_pc`

**Recommendation: `fiscal_balance_pc` (revenues minus expenditures per capita) as the headline estimand.**

### Argument

**Contribution differentiation from Liao and Kousky (2022).** Liao and Kousky's headline result is already expressed as a fiscal balance effect: a 25 percentage-point increase in the probability of running a budget deficit, corresponding to a $97 per capita decline in excess revenues. Leading with `rev_proptax_pc` measures a component Liao and Kousky already analyzed — and whether property taxes rise (the Prop 13 transfer tax mechanism) or fall (direct damage mechanism) is an ambiguous and harder-to-generalize result compared to the net fiscal position. Leading with fiscal balance makes the comparison direct and the extension clear: this paper answers the same question Liao and Kousky answered, but for county governments across eight states with different institutional rules.

**Economic significance and policy relevance.** County fiscal balance determines whether counties can continue providing services, whether they must issue debt, and whether they face state receivership risk. Property tax revenues alone do not determine service capacity because expenditure pressures (emergency response, debris removal, infrastructure repair) rise simultaneously. A paper that shows `rev_proptax_pc` rises modestly post-fire but `fiscal_balance_pc` deteriorates sharply is a stronger and more policy-relevant result than a paper showing only the revenue side. The fiscal balance framing also maps cleanly onto Jerch, Kahn, and Lin (2023) — persistent revenue decline plus rising debt costs — and positions the paper as establishing whether wildfire imposes analogous long-run fiscal burdens to hurricanes.

**Target journal alignment.** JUE and AEJ:Applied favor papers that establish a new stylized fact with broad policy implications over papers that estimate a component mechanism. A fiscal balance result is immediately interpretable: counties in the western US lose $X per capita in fiscal capacity over Y years following a qualifying wildfire. A property tax result requires institutional interpretation — does it reflect assessment revaluations, reassessment events triggered by sales, or rate adjustments? — and the answer varies with state law in ways that make the headline coefficient hard to interpret without extensive caveats.

### How to feature `rev_proptax_pc`

Property tax revenues should be the primary mechanism analysis, not the headline. The contribution to the property tax literature is most credibly presented as: fiscal balance deteriorates because expenditures rise faster than revenues, and the property tax revenue response is delayed and partial due to assessment lag dynamics. `rev_proptax_pc` explains the fiscal balance result; it is not a competing headline.

**Recommended table structure for main results:**
- Column (1): `fiscal_balance_pc` — headline
- Column (2): `rev_total_pc` — revenue decomposition
- Column (3): `exp_total_pc` — expenditure decomposition
- Column (4): `rev_proptax_pc` — mechanism (with note on assessment lag)

This structure mirrors Liao and Kousky and will make the comparison transparent to referees.

---

## 4. Critical Identification Concern

**The paper must directly address the Liao and Kousky generalizability claim before a referee does.**

Liao and Kousky explicitly stated that their California results likely understate fiscal damage in states without Proposition 13, because Prop 13's reassessment-at-sale mechanism generates transfer tax revenues that partially offset fire damage. If this paper finds smaller negative fiscal balance effects than Liao and Kousky in non-California western states — plausible because rural western counties have lower property tax bases and fewer high-value homes to generate reassessment events — the result risks being read as a null finding rather than as evidence that the California mechanism does not generalize.

The paper needs either a direct comparison of estimated effects against the Liao and Kousky benchmark with explicit attention to why the samples and institutions differ, or a heterogeneity analysis by state that shows California counties in the sample producing estimates consistent with Liao and Kousky while other states diverge in predictable directions. The recommended approach: include a California subsample estimate as an internal replication check, then show state-by-state or home-rule-by-Dillon's-Rule heterogeneity to establish where and why effects diverge.

---

## 5. Gap Summary

| Gap | How this paper fills it |
|---|---|
| No causal evidence on wildfire → county fiscal outcomes outside California | 8-state staggered DiD with WHP-matched controls |
| Liao & Kousky (2022) uses municipal data, California only, Prop 13 rules | County government data, 8 states, varying property tax institutions |
| No disaster-finance paper for wildfire hazard type in western US | Explicit wildfire treatment; MTBS fire perimeters; WHP pre-treatment matching |
| No causal paper on home rule × disaster fiscal heterogeneity | Cross-state institutional heterogeneity (home rule states vs. Dillon's Rule states) |
| Property tax assessment lag dynamics undocumented for wildfire | Event study k = 0 to +4; assessment cycle subsample splits |

---

## 6. Annotated Bibliography (Key Papers)

**Liao, Y. & Kousky, C. (2022).** "The Fiscal Impacts of Wildfires on California Municipalities." *Journal of the Association of Environmental and Resource Economists* 9(3). — (1) Causal effect of wildfire on municipal fiscal outcomes. (2) Historical fire perimeters + quasi-experimental spatial exposure in California. (3) Budget deficit probability +25 pp; expenditures +17.3%, revenues +10.5%; net fiscal loss $97/capita. (4) California-specific: Prop 13 reassessment-at-sale mechanism may not generalize; municipality-level, not county-level.

**Jerch, R., Kahn, M.E., & Lin, G.C. (2023).** "Local Public Finance Dynamics and Hurricane Shocks." *Journal of Urban Economics* 134. NBER W28050. — (1) Causal effect of hurricanes on local government revenues, expenditures, and debt costs. (2) Hurricane wind speeds at county level; 2,000+ local governments in Atlantic/Gulf states since 1980. (3) Major hurricanes reduce tax revenues and raise debt costs persistently for a decade; distributional effects on minority-majority municipalities. (4) Hurricane geography may correlate with pre-existing economic conditions.

**Deryugina, T. (2017).** "The Fiscal Cost of Hurricanes: Disaster Aid versus Social Insurance." *AEJ:Economic Policy* 9(3). — (1) How hurricanes affect local fiscal outcomes through disaster aid and social insurance. (2) County-level hurricane wind speed exposure, 1980s–2000s. (3) Post-hurricane government transfers exceed direct disaster aid in present value; net local fiscal effect approximately neutral due to federal absorption. (4) Hurricane landfall geography may correlate with pre-existing conditions.

**Baylis, P. & Boomhower, J. (2023).** "The Economic Incidence of Wildfire Suppression in the United States." *AEJ:Applied Economics* 15(1). — (1) Does federal wildfire suppression subsidize high-risk residential development? (2) Administrative suppression spending matched to home locations; spatial variation in fire hazard and development density. (3) Suppression subsidy exceeds 20% of home value in high-risk areas; ~84,000 excess homes built due to subsidy. (4) Unobserved amenities correlated with fire risk.

**Borgschulte, M., Molitor, D. & Zou, E. (2024).** "Air Pollution and the Labor Market: Evidence from Wildfire Smoke." *Review of Economics and Statistics* 106(6). — (1) Causal earnings and employment effects of wildfire smoke exposure. (2) Satellite-detected smoke plumes; county-level labor data 2007–2019. (3) One additional smoke day reduces quarterly earnings by ~0.1%; employment reduction explains 13% of earnings losses. (4) Seasonal labor demand confounders.

**Lutz, B., Molloy, R. & Shan, H. (2011).** "The Housing Crisis and State and Local Government Tax Revenue: Five Channels." *Regional Science and Urban Economics* 41(4). — (1) How housing market contractions affect state and local government tax revenues. (2) Time-series analysis of revenue channels 2005–2009. (3) Property tax proved resilient, growing ~5% in 2008 and 2009 despite falling market values; 4-year lag between price peak and revenue trough. (4) Aggregate state-level; cannot isolate assessment cycle effects from policy responses.

**Chen, H. & Cohen, L. (2025).** "Assessing Assessors." NBER Working Paper W33238. — (1) How do property tax assessments respond to market value changes, and do assessor incentives distort assessment patterns? (2) Comprehensive longitudinal dataset of US assessments and transactions 2000–2020. (3) 1% market value change → <0.30% assessed value change within 3 years; market value explains only ~8% of assessment variation. (4) Correlational evidence on assessor incentives.

**Zhang, P., Nguyen-Hoang, P. & Chen, N. (2022).** "The Impact of Home Rule on Municipal Boundary and Fiscal Expansion." *Journal of Regional Science* 62(5). **(2023).** "Home Rule and Municipal Revenue Stability." *Public Budgeting & Finance* 43(1). — (1) Does home rule adoption causally affect municipal fiscal expansion and revenue stability? (2) Fuzzy RD exploiting Texas population thresholds. (3) Home rule increases boundary expansion and reduces probability of revenue decline; improvements stem primarily from property tax flexibility; ~20-year lag for per capita expenditure effects. (4) Texas-specific; threshold RD may not generalize.

**Miao, Q. et al. (2023).** "Extreme Weather Events and Local Fiscal Responses." *Economics of Disasters and Climate Change* 7(1). — (1) How do floods and hurricanes affect county tax revenues, spending, IGTs, and borrowing? (2) Presidential Disaster Declarations for floods/hurricanes. (3) Disasters lower tax revenue, increase spending and IGT; lower-income counties engage in more borrowing. (4) PDD endogeneity.

**Auh, J.K., Choi, J., Deryugina, T. & Park, T. (2022).** NBER Working Paper W30280. — (1) How do natural disasters affect municipal bond returns? (2) Disaster event study; bond characteristics heterogeneity. (3) Uninsured bond returns fall 0.31% post-disaster; high-debt counties face 55 bp decline. (4) Event study with controls for pre-existing bond characteristics.
