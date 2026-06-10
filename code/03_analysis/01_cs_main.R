##
## Callaway & Sant'Anna (2021) staggered DiD — wildfire finance project.
##
## Design:
##   id:      fips (county)
##   time:    year_cog  (2002, 2007, 2012, 2017, 2022)
##   group:   g         (2017 = fires 2013-2016; 2022 = fires 2017-2021; 0 = never)
##   control: never-treated only (g = 0, n = 51)
##   method:  doubly-robust (est_method = "dr", C&S default)
##   base:    universal (2012 = last pre-treatment period for all cohorts)
##
## Outcomes (all per-capita, nominal 2019 $):
##   rev_total_pc       total general revenues
##   rev_proptax_pc     property tax revenues
##   rev_intergovt_pc   intergovernmental revenues (federal + state)   ← renamed
##   exp_total_pc       total general expenditures
##   exp_capital_pc     capital outlays
##   fiscal_balance_pc  revenues minus expenditures
##   debt_lt_pc         long-term debt outstanding
##
## Covariates (xformla): pre-treatment, time-invariant (measured 2012 or earlier)
##   whp_2012, pre2013_fire, pre2013_log_acres, rucc_2013,
##   I(log(median_hhinc)), poverty_rate, uninsurance_imp, log_pop_dens
##   (last two imputed for 29 UT counties using state-year median)
##
## Outputs:
##   data/processed/cs_att_gt_<outcome>.rds   raw att_gt objects
##   output/tables/cs_simple_agg.txt          simple aggregation table
##   output/tables/cs_group_agg.txt           group-average ATTs
##

suppressPackageStartupMessages({
  library(here)
  library(did)
  library(dplyr)
})
set.seed(42)

ROOT <- here::here()
DATA <- file.path(ROOT, "data", "processed")
TOUT <- file.path(ROOT, "output", "tables")
ROUT <- file.path(ROOT, "output", "rds")
dir.create(TOUT, showWarnings = FALSE, recursive = TRUE)
dir.create(ROUT, showWarnings = FALSE, recursive = TRUE)

## ── Load and prepare panel ───────────────────────────────────────────────────

panel <- read.csv(file.path(DATA, "panel_final.csv"), stringsAsFactors = FALSE)
panel$fips <- sprintf("%05d", as.integer(panel$fips))

## Rename rev_igt_state_pc + rev_igt_federal_pc → rev_intergovt_pc if needed
if (!"rev_intergovt_pc" %in% names(panel) &&
    all(c("rev_igt_federal_pc", "rev_igt_state_pc") %in% names(panel))) {
  panel$rev_intergovt_pc <- panel$rev_igt_federal_pc + panel$rev_igt_state_pc
}

## Impute uninsurance and pop_density for UT (29 counties, all NaN).
## State-year median is undefined for UT (all NaN) → fall back to overall sample median.
overall_uninsurance <- median(panel$uninsurance_rate, na.rm = TRUE)
overall_pop_density <- median(panel$pop_density,      na.rm = TRUE)
panel <- panel |>
  group_by(state, year_cog) |>
  mutate(
    state_unins  = median(uninsurance_rate, na.rm = TRUE),
    state_popdns = median(pop_density,      na.rm = TRUE)
  ) |>
  ungroup() |>
  mutate(
    uninsurance_imp = case_when(
      !is.na(uninsurance_rate) ~ uninsurance_rate,
      !is.na(state_unins)      ~ state_unins,
      TRUE                     ~ overall_uninsurance
    ),
    log_pop_dens = log(case_when(
      !is.na(pop_density) ~ pop_density,
      !is.na(state_popdns) ~ state_popdns,
      TRUE                 ~ overall_pop_density
    ) + 1)
  )

## Pre-compute log-transformed covariates for xformla (att_gt doesn't evaluate I())
panel <- panel |>
  mutate(
    log_hhinc        = log(pmax(median_hhinc, 1)),
    log_rev_total_pc = log(pmax(rev_total_pc, 1)),
    log_proptax_pc   = log(pmax(rev_proptax_pc, 1)),
    log_debt_lt_pc   = log(debt_lt_pc + 1)
  )

## did v2.x requires g=Inf for never-treated (g=0 is not recognised)
panel <- panel |>
  mutate(
    g     = ifelse(g     == 0, Inf, g),
    g_any = ifelse(g_any == 0, Inf, g_any)
  )

## Numeric id for did (att_gt requires integer or numeric idname)
panel <- panel |>
  mutate(fips_int = as.integer(fips))

## ── Outcomes to estimate ─────────────────────────────────────────────────────

outcomes <- c(
  "rev_total_pc",
  "rev_proptax_pc",
  "rev_intergovt_pc",
  "exp_total_pc",
  "exp_capital_pc",
  "fiscal_balance_pc",
  "debt_lt_pc"
)

## ── Covariate formula ─────────────────────────────────────────────────────────

xf <- ~ whp_2012 + pre2013_fire + pre2013_log_acres + rucc_2013 +
         log_hhinc + poverty_rate + uninsurance_imp + log_pop_dens

## ── Run att_gt for each outcome ──────────────────────────────────────────────

results <- list()

for (y in outcomes) {
  cat(sprintf("\n--- %s ---\n", y))
  tryCatch({
    fit <- att_gt(
      yname          = y,
      tname          = "year_cog",
      idname         = "fips_int",
      gname          = "g",
      xformla        = xf,
      data           = panel,
      control_group  = "nevertreated",
      est_method     = "dr",
      base_period    = "varying",
      anticipation   = 0,
      bstrap         = TRUE,
      biters         = 999,
      clustervars    = "fips_int",
      print_details  = FALSE
    )
    results[[y]] <- fit
    saveRDS(fit, file.path(ROUT, sprintf("cs_att_gt_%s.rds", y)))

    ## Simple aggregation
    agg_s <- aggte(fit, type = "simple")
    cat(sprintf("  Simple ATT: %.2f  SE: %.2f  p: %.3f\n",
                agg_s$overall.att, agg_s$overall.se,
                2 * pnorm(-abs(agg_s$overall.att / agg_s$overall.se))))
  }, error = function(e) {
    cat(sprintf("  ERROR: %s\n", conditionMessage(e)))
  })
}

## ── Summary table: simple aggregation ────────────────────────────────────────

simple_rows <- lapply(names(results), function(y) {
  ag  <- aggte(results[[y]], type = "simple")
  att <- ag$overall.att
  se  <- ag$overall.se
  ci  <- ag$overall.att + c(-1, 1) * qnorm(0.975) * ag$overall.se
  pv  <- 2 * pnorm(-abs(att / se))
  data.frame(
    outcome  = y,
    att      = round(att, 1),
    se       = round(se, 1),
    ci_lo    = round(ci[1], 1),
    ci_hi    = round(ci[2], 1),
    p_value  = round(pv, 3),
    signif   = ifelse(pv < 0.01, "***",
                      ifelse(pv < 0.05, "**",
                             ifelse(pv < 0.10, "*", ""))),
    stringsAsFactors = FALSE
  )
})
simple_tbl <- do.call(rbind, simple_rows)
write.csv(simple_tbl, file.path(TOUT, "cs_simple_agg.csv"), row.names = FALSE)

cat("\n\n=== C&S Simple ATT (doubly robust, never-treated controls) ===\n")
cat(sprintf("%-22s  %8s  %7s  %14s  %7s  %5s\n",
            "Outcome", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
cat(paste(rep("-", 78), collapse = ""), "\n")
for (i in seq_len(nrow(simple_tbl))) {
  r <- simple_tbl[i, ]
  cat(sprintf("%-22s  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
              r$outcome, r$att, r$se, r$ci_lo, r$ci_hi, r$p_value, r$signif))
}
cat(paste(rep("-", 78), collapse = ""), "\n")
cat("Note: per capita, nominal 2019$. Clustered SE by county. *** p<0.01 ** p<0.05 * p<0.10\n\n")

writeLines(
  capture.output({
    cat("=== C&S Simple ATT (doubly robust, never-treated controls) ===\n")
    cat(sprintf("%-22s  %8s  %7s  %14s  %7s  %5s\n",
                "Outcome", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
    cat(paste(rep("-", 78), collapse = ""), "\n")
    for (i in seq_len(nrow(simple_tbl))) {
      r <- simple_tbl[i, ]
      cat(sprintf("%-22s  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
                  r$outcome, r$att, r$se, r$ci_lo, r$ci_hi, r$p_value, r$signif))
    }
    cat(paste(rep("-", 78), collapse = ""), "\n")
    cat("Note: per capita, nominal 2019$. Clustered SE by county. *** p<0.01 ** p<0.05 * p<0.10\n")
  }),
  file.path(TOUT, "cs_simple_agg.txt")
)

## ── Group-level aggregation ───────────────────────────────────────────────────

cat("=== C&S Group ATT ===\n")
for (y in names(results)) {
  ag_g <- aggte(results[[y]], type = "group")
  cat(sprintf("\n%s:\n", y))
  print(summary(ag_g))
}

group_rows <- lapply(names(results), function(y) {
  ag_g  <- aggte(results[[y]], type = "group")
  n_grp <- length(ag_g$egt)
  data.frame(
    outcome = y,
    group   = ag_g$egt,
    att     = round(ag_g$att.egt, 1),
    se      = round(ag_g$se.egt, 1),
    p_value = round(2 * pnorm(-abs(ag_g$att.egt / ag_g$se.egt)), 3),
    stringsAsFactors = FALSE
  )
})
group_tbl <- do.call(rbind, group_rows)
write.csv(group_tbl, file.path(TOUT, "cs_group_agg.csv"), row.names = FALSE)
cat("\nGroup ATT table -> output/tables/cs_group_agg.csv\n")
cat("Simple ATT table -> output/tables/cs_simple_agg.csv\n")
cat("ATT_gt objects   -> output/rds/cs_att_gt_*.rds\n")

## ═══════════════════════════════════════════════════════════════════════════
## EXTENSIVE MARGIN: any qualifying fire (≥1,000 acres)
## Control = never-fired counties (g_any = Inf); n ≈ 51
## ═══════════════════════════════════════════════════════════════════════════

cat("\n\n══════════════════════════════════════════════════\n")
cat("EXTENSIVE MARGIN: any qualifying fire\n")
cat("Control = never-fired counties (g_any = Inf)\n")
cat("══════════════════════════════════════════════════\n\n")

cat(sprintf("Cohort sizes (g_any):\n"))
print(table(panel$g_any[!duplicated(panel$fips_int)]))

results_any <- list()

for (y in outcomes) {
  cat(sprintf("\n--- %s ---\n", y))
  tryCatch({
    fit <- att_gt(
      yname          = y,
      tname          = "year_cog",
      idname         = "fips_int",
      gname          = "g_any",
      xformla        = xf,
      data           = panel,
      control_group  = "nevertreated",
      est_method     = "dr",
      base_period    = "varying",
      anticipation   = 0,
      bstrap         = TRUE,
      biters         = 999,
      clustervars    = "fips_int",
      print_details  = FALSE
    )
    results_any[[y]] <- fit
    saveRDS(fit, file.path(ROUT, sprintf("cs_att_gt_any_%s.rds", y)))

    agg_s <- aggte(fit, type = "simple")
    cat(sprintf("  Simple ATT: %.2f  SE: %.2f  p: %.3f\n",
                agg_s$overall.att, agg_s$overall.se,
                2 * pnorm(-abs(agg_s$overall.att / agg_s$overall.se))))
  }, error = function(e) {
    cat(sprintf("  ERROR: %s\n", conditionMessage(e)))
  })
}

## Simple aggregation table — extensive margin
simple_rows_any <- lapply(names(results_any), function(y) {
  ag  <- aggte(results_any[[y]], type = "simple")
  att <- ag$overall.att
  se  <- ag$overall.se
  ci  <- ag$overall.att + c(-1, 1) * qnorm(0.975) * ag$overall.se
  pv  <- 2 * pnorm(-abs(att / se))
  data.frame(
    outcome  = y,
    att      = round(att, 1),
    se       = round(se, 1),
    ci_lo    = round(ci[1], 1),
    ci_hi    = round(ci[2], 1),
    p_value  = round(pv, 3),
    signif   = ifelse(pv < 0.01, "***",
                      ifelse(pv < 0.05, "**",
                             ifelse(pv < 0.10, "*", ""))),
    stringsAsFactors = FALSE
  )
})
simple_tbl_any <- do.call(rbind, simple_rows_any)
write.csv(simple_tbl_any, file.path(TOUT, "cs_simple_agg_any.csv"), row.names = FALSE)

cat("\n\n=== C&S Simple ATT — EXTENSIVE MARGIN (any fire, doubly robust) ===\n")
cat(sprintf("%-22s  %8s  %7s  %14s  %7s  %5s\n",
            "Outcome", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
cat(paste(rep("-", 78), collapse = ""), "\n")
for (i in seq_len(nrow(simple_tbl_any))) {
  r <- simple_tbl_any[i, ]
  cat(sprintf("%-22s  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
              r$outcome, r$att, r$se, r$ci_lo, r$ci_hi, r$p_value, r$signif))
}
cat(paste(rep("-", 78), collapse = ""), "\n")
cat("Note: per capita, nominal 2019$. Clustered SE by county. *** p<0.01 ** p<0.05 * p<0.10\n\n")

## Group-level aggregation — extensive margin
group_rows_any <- lapply(names(results_any), function(y) {
  ag_g  <- aggte(results_any[[y]], type = "group")
  data.frame(
    outcome = y,
    group   = ag_g$egt,
    att     = round(ag_g$att.egt, 1),
    se      = round(ag_g$se.egt, 1),
    p_value = round(2 * pnorm(-abs(ag_g$att.egt / ag_g$se.egt)), 3),
    stringsAsFactors = FALSE
  )
})
group_tbl_any <- do.call(rbind, group_rows_any)
write.csv(group_tbl_any, file.path(TOUT, "cs_group_agg_any.csv"), row.names = FALSE)

cat("Group ATT table (any) -> output/tables/cs_group_agg_any.csv\n")
cat("Simple ATT table (any) -> output/tables/cs_simple_agg_any.csv\n")
cat("\nDone. Next: 02_event_study.R\n")
