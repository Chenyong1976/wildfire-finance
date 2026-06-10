##
## PS-IPW matching for wildfire-finance project.
##
## Design: logistic propensity score (ever_treated vs never_treated) on
## pre-treatment cross-section (year_cog = 2012, FY-begin = 2011).
##
## Covariates:
##   whp_q            WFP 2012 quintile (factor)
##   pre2013_fire     binary pre-treatment fire indicator
##   pre2013_log_acres log acres of pre-2013 fires
##   rucc_2013        RUCC 2013 (continuous 1–9)
##   log_hhinc        log median HH income (ACS 2011)
##   poverty_rate     ACS 2011
##   uninsurance_rate ACS 2011 (29 UT NaN → state-median imputed)
##   log_pop_density  log pop density (29 UT NaN → state-median imputed)
##   log_rev_total_pc log real GR per capita (2012 baseline)
##   log_proptax_pc   log property tax per capita (2012 baseline)
##   log_debt_lt_pc   log(debt_lt_pc + 1) (2012 baseline; includes zeros)
##
## Outputs:
##   data/processed/ps_weights.csv     county-level PS + ATT weights
##   data/processed/ps_model_summary.txt
##
## ATT weighting convention (for use as panel weightsname in att_gt):
##   treated (g > 0): weight = 1
##   control (g = 0): weight = p̂(X) / (1 − p̂(X)),  normalised to sum to n_treated
##
## ESS of reweighted control = [sum(w_c)]^2 / sum(w_c^2).
##

suppressPackageStartupMessages({
  library(here)
  library(dplyr)
  library(tidyr)
})

ROOT <- here::here()
DATA <- file.path(ROOT, "data", "processed")

panel <- read.csv(file.path(DATA, "panel_final.csv"), stringsAsFactors = FALSE)
panel$fips <- sprintf("%05d", as.integer(panel$fips))

## ── Cross-section: year_cog = 2012 (pre-treatment baseline) ─────────────────

base <- panel |>
  filter(year_cog == 2012) |>
  select(fips, state, g, whp_2012, whp_q,
         pre2013_fire, pre2013_fire_count, pre2013_log_acres,
         rucc_2013, median_hhinc, poverty_rate, uninsurance_rate,
         pop_density, pop,
         rev_total_pc, rev_proptax_pc, debt_lt_pc) |>
  mutate(
    ever_treated = as.integer(g > 0),
    cohort       = case_when(g == 0    ~ "control",
                             g == 2017 ~ "g2017",
                             TRUE      ~ "g2022"),
    whp_q = factor(whp_q, levels = 1:5)
  )

stopifnot(nrow(base) == 344)

## ── Impute uninsurance_rate and pop_density for UT (state == "49") ───────────
## 29 UT counties have NaN because UT ACS pull only retrieved pop/income/poverty.
## Impute with within-state (UT) median of available observations.  Since all UT
## counties are NaN for these two variables, fall back to overall sample median.

impute_median <- function(x, group = NULL) {
  if (is.null(group)) {
    x[is.na(x)] <- median(x, na.rm = TRUE)
    return(x)
  }
  for (g in unique(group)) {
    idx <- group == g
    med <- median(x[idx], na.rm = TRUE)
    if (is.na(med)) med <- median(x, na.rm = TRUE)  # fallback to overall
    x[idx & is.na(x)] <- med
  }
  x
}

base <- base |>
  mutate(
    uninsurance_imp = impute_median(uninsurance_rate, state),
    log_pop_density = log(impute_median(pop_density, state) + 1),
    uninsurance_imputed = as.integer(is.na(uninsurance_rate)),
    pop_density_imputed = as.integer(is.na(pop_density))
  )

n_imp <- sum(base$uninsurance_imputed)
cat(sprintf("Imputed %d counties for uninsurance_rate / pop_density (all UT)\n\n", n_imp))

## ── Log-transform skewed fiscal covariates ────────────────────────────────────

base <- base |>
  mutate(
    log_hhinc        = log(median_hhinc),
    log_rev_total_pc = log(pmax(rev_total_pc, 1)),
    log_proptax_pc   = log(pmax(rev_proptax_pc, 1)),
    log_debt_lt_pc   = log(debt_lt_pc + 1)    # includes zeros
  )

## ── Propensity score models ───────────────────────────────────────────────────

ps_formula <- ever_treated ~ whp_q + pre2013_fire + pre2013_log_acres +
  rucc_2013 + log_hhinc + poverty_rate + uninsurance_imp + log_pop_density +
  log_rev_total_pc + log_proptax_pc + log_debt_lt_pc

## Model 1: ever_treated (g > 0) vs never_treated (g = 0)
ps_fit_all <- glm(ps_formula, data = base, family = binomial(link = "logit"))

## Model 2: g=2017 vs never_treated only
base_17 <- filter(base, cohort %in% c("g2017", "control"))
ps_fit_17 <- glm(ps_formula, data = base_17, family = binomial(link = "logit"))

## Model 3: g=2022 vs never_treated only
base_22 <- filter(base, cohort %in% c("g2022", "control"))
ps_fit_22 <- glm(ps_formula, data = base_22, family = binomial(link = "logit"))

## Attach predicted scores
base$pscore_all <- predict(ps_fit_all, type = "response")
base_17$pscore_17 <- predict(ps_fit_17, type = "response")
base_22$pscore_22 <- predict(ps_fit_22, type = "response")

base <- base |>
  left_join(select(base_17, fips, pscore_17), by = "fips") |>
  left_join(select(base_22, fips, pscore_22), by = "fips")

## ── Common support check ─────────────────────────────────────────────────────

ps_range_treated <- range(base$pscore_all[base$ever_treated == 1])
ps_range_control <- range(base$pscore_all[base$ever_treated == 0])

cat("PS distribution (ever_treated model):\n")
cat(sprintf("  Treated  [%.3f, %.3f]  n=%d\n",
            ps_range_treated[1], ps_range_treated[2],
            sum(base$ever_treated == 1)))
cat(sprintf("  Controls [%.3f, %.3f]  n=%d\n",
            ps_range_control[1], ps_range_control[2],
            sum(base$ever_treated == 0)))

## Trim: drop controls outside treated PS range (common support)
in_support <- base$ever_treated == 1 |
  (base$ever_treated == 0 &
     base$pscore_all >= ps_range_treated[1] &
     base$pscore_all <= ps_range_treated[2])
n_trimmed <- sum(base$ever_treated == 0 & !in_support)
cat(sprintf("  Controls outside treated PS range (trimmed): %d\n\n", n_trimmed))

## ── ATT IPW weights ──────────────────────────────────────────────────────────
## Treated: w = 1.  Control: w = p̂/(1-p̂).
## Normalise controls so sum(w_control) = n_control (sum-to-n convention).

n_treated <- sum(base$ever_treated == 1)
n_control <- sum(base$ever_treated == 0)

base <- base |>
  mutate(
    ## Odds-ratio weight (un-normalised)
    w_raw = ifelse(ever_treated == 1, 1.0,
                   pscore_all / (1 - pscore_all)),
    ## Normalise control weights so mean = 1 among controls
    w_ipw = ifelse(ever_treated == 1, 1.0,
                   w_raw / mean(w_raw[ever_treated == 0]))
  )

## ESS of reweighted control group
w_c    <- base$w_ipw[base$ever_treated == 0]
ess_c  <- sum(w_c)^2 / sum(w_c^2)
cat(sprintf("ESS of reweighted control group: %.1f (raw n = %d)\n", ess_c, n_control))
cat(sprintf("ESS / n_treated: %.3f\n\n", ess_c / n_treated))

## ── PS summary table ─────────────────────────────────────────────────────────

ps_summary_lines <- capture.output({
  cat("\n=== PS Model Summary (ever_treated) ===\n")
  print(summary(ps_fit_all))
  cat("\n=== PS Distribution by Cohort ===\n")
  base |>
    group_by(cohort) |>
    summarise(n = n(),
              ps_mean = round(mean(pscore_all), 3),
              ps_sd   = round(sd(pscore_all), 3),
              ps_min  = round(min(pscore_all), 3),
              ps_max  = round(max(pscore_all), 3)) |>
    print()
  cat(sprintf("\nESS reweighted controls: %.1f / %d\n", ess_c, n_control))
  cat(sprintf("Controls trimmed (off common support): %d\n", n_trimmed))
})
writeLines(ps_summary_lines,
           file.path(DATA, "ps_model_summary.txt"))
cat("PS model summary -> data/processed/ps_model_summary.txt\n")

## ── Output county-level weight file ─────────────────────────────────────────
## Columns: fips, g, ever_treated, pscore_all, pscore_17, pscore_22, w_ipw

ps_out <- base |>
  select(fips, state, g, cohort, ever_treated,
         pscore_all, pscore_17, pscore_22, w_ipw,
         uninsurance_imputed, pop_density_imputed) |>
  arrange(fips)

write.csv(ps_out, file.path(DATA, "ps_weights.csv"), row.names = FALSE)
cat(sprintf("PS weights -> data/processed/ps_weights.csv  (%d rows)\n\n", nrow(ps_out)))

## ── Merge weights into full panel for att_gt use ─────────────────────────────
## In the long panel, w_ipw is the county-level sampling weight (constant over time).

panel_w <- panel |>
  left_join(select(ps_out, fips, w_ipw), by = "fips")

write.csv(panel_w, file.path(DATA, "panel_with_weights.csv"), row.names = FALSE)
cat(sprintf("Panel with weights -> data/processed/panel_with_weights.csv  (%d rows)\n",
            nrow(panel_w)))

cat("\nDone. Next: 02_balance_table.R  then  ../03_analysis/01_cs_main.R\n")
