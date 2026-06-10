##
## Robustness checks — wildfire finance project.
## All specs use C&S DR estimator, bstrap=999, clustered by county.
## Headline outcomes: fiscal_balance_pc, rev_total_pc, exp_capital_pc.
##
## Specs:
##   (0) Baseline   — never-treated controls, WFP 2012 xformla         [main result]
##   (1) NYT        — not-yet-treated controls (adds g=2022 as controls for g=2017)
##   (2) No outliers — drop flag_rev_total_pc == 1
##   (3) 6-state    — drop CO ('08') and UT ('49'); removes NaN imputation noise
##   (4) WHP2014    — WHP 2014 in xformla (note: NOT predetermined for 2013-2014 fires)
##
## Smoke buffer note: 40/51 never-treated counties are within 100 km of a fire
## perimeter in post-treatment years (2017 or 2022). Restricting to 11 clean
## controls is infeasible given the sample size. For fiscal outcomes, 100 km
## smoke does not directly affect property tax rolls or government expenditures;
## the relevant spillover channel (property damage) is geographically localised.
## Documented here as a limitation; not implemented as a sample restriction.
##
## Outputs:
##   output/tables/robustness_table.csv
##   output/tables/robustness_table.txt
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

## ── Load and prepare panel ────────────────────────────────────────────────────

panel <- read.csv(file.path(DATA, "panel_final.csv"), stringsAsFactors = FALSE)
panel$fips <- sprintf("%05d", as.integer(panel$fips))

if (!"rev_intergovt_pc" %in% names(panel))
  panel$rev_intergovt_pc <- panel$rev_igt_federal_pc + panel$rev_igt_state_pc

## Standard covariate prep
overall_unins  <- median(panel$uninsurance_rate, na.rm = TRUE)
overall_popdns <- median(panel$pop_density,      na.rm = TRUE)

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
      TRUE                     ~ overall_unins
    ),
    log_pop_dens     = log(case_when(
      !is.na(pop_density)  ~ pop_density,
      !is.na(state_popdns) ~ state_popdns,
      TRUE                 ~ overall_popdns
    ) + 1),
    log_hhinc        = log(pmax(median_hhinc, 1)),
    fips_int         = as.integer(fips),
    g                = ifelse(g == 0, Inf, g)   # did v2.x: 0 → Inf for never-treated
  )

## ── Specification list ────────────────────────────────────────────────────────

## xformla variants
xf_base <- ~ whp_2012 + pre2013_fire + pre2013_log_acres + rucc_2013 +
               log_hhinc + poverty_rate + uninsurance_imp + log_pop_dens

xf_whp14 <- ~ whp_2014 + pre2013_fire + pre2013_log_acres + rucc_2013 +
               log_hhinc + poverty_rate + uninsurance_imp + log_pop_dens

specs <- list(
  list(label = "(0) Baseline",
       data_filter   = function(d) d,
       control_group = "nevertreated",
       xformla       = xf_base),
  list(label = "(1) Not-yet-treated",
       data_filter   = function(d) d,
       control_group = "notyettreated",
       xformla       = xf_base),
  list(label = "(2) Drop outliers",
       data_filter   = function(d) {
         ## Drop entire counties with any outlier year (keeps panel balanced)
         bad <- unique(d$fips[d$flag_rev_total_pc == 1])
         filter(d, !fips %in% bad)
       },
       control_group = "nevertreated",
       xformla       = xf_base),
  list(label = "(3) 6-state (no CO/UT)",
       data_filter   = function(d) filter(d, !state %in% c("08", "49")),
       control_group = "nevertreated",
       xformla       = xf_base),
  list(label = "(4) WHP 2014 xformla",
       data_filter   = function(d) d,
       control_group = "nevertreated",
       xformla       = xf_whp14)
)

outcomes <- c("fiscal_balance_pc", "rev_total_pc", "exp_capital_pc")

## ── Run all specs × outcomes ──────────────────────────────────────────────────

run_spec <- function(spec, y, data) {
  tryCatch({
    dat <- spec$data_filter(data)

    fit <- att_gt(
      yname         = y,
      tname         = "year_cog",
      idname        = "fips_int",
      gname         = "g",
      xformla       = spec$xformla,
      data          = dat,
      control_group = spec$control_group,
      est_method    = "dr",
      base_period   = "varying",
      anticipation  = 0,
      bstrap        = TRUE,
      biters        = 999,
      clustervars   = "fips_int",
      print_details = FALSE
    )
    ag <- aggte(fit, type = "simple")
    att <- ag$overall.att
    se  <- ag$overall.se
    pv  <- 2 * pnorm(-abs(att / se))
    list(att = att, se = se, pv = pv,
         ci_lo = att - qnorm(0.975) * se,
         ci_hi = att + qnorm(0.975) * se,
         n_units = length(unique(dat$fips_int[is.finite(dat$g)])),
         n_ctrl  = length(unique(dat$fips_int[!is.finite(dat$g)])))
  }, error = function(e) {
    list(att = NA, se = NA, pv = NA, ci_lo = NA, ci_hi = NA,
         n_units = NA, n_ctrl = NA, err = conditionMessage(e))
  })
}

rows <- list()
for (y in outcomes) {
  cat(sprintf("\n=== %s ===\n", y))
  for (s in specs) {
    cat(sprintf("  %s ... ", s$label))
    res <- run_spec(s, y, panel)
    if (!is.na(res$att)) {
      sig <- ifelse(res$pv < 0.01, "***",
                    ifelse(res$pv < 0.05, "**",
                           ifelse(res$pv < 0.10, "*", "")))
      cat(sprintf("ATT: %.1f (SE %.1f, p=%.3f) %s  [n_treat=%s, n_ctrl=%s]\n",
                  res$att, res$se, res$pv, sig, res$n_units, res$n_ctrl))
    } else {
      cat(sprintf("ERROR: %s\n", res$err))
    }
    rows[[length(rows) + 1]] <- data.frame(
      outcome = y,
      spec    = s$label,
      att     = round(res$att, 1),
      se      = round(res$se, 1),
      ci_lo   = round(res$ci_lo, 1),
      ci_hi   = round(res$ci_hi, 1),
      p_value = round(res$pv, 3),
      signif  = ifelse(is.na(res$pv), "",
                       ifelse(res$pv < 0.01, "***",
                              ifelse(res$pv < 0.05, "**",
                                     ifelse(res$pv < 0.10, "*", "")))),
      n_treated = res$n_units,
      n_ctrl    = res$n_ctrl,
      stringsAsFactors = FALSE
    )
  }
}

rob_tbl <- do.call(rbind, rows)
write.csv(rob_tbl, file.path(TOUT, "robustness_table.csv"), row.names = FALSE)

## ── Formatted robustness table ────────────────────────────────────────────────

cat("\n\n")
for (y in outcomes) {
  yt <- rob_tbl[rob_tbl$outcome == y, ]
  cat(sprintf("Panel: %s\n", y))
  cat(sprintf("%-28s  %8s  %7s  %14s  %6s  %5s\n",
              "Specification", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
  cat(paste(rep("-", 78), collapse = ""), "\n")
  for (i in seq_len(nrow(yt))) {
    r <- yt[i, ]
    if (!is.na(r$att)) {
      cat(sprintf("%-28s  %8.1f  %7.1f  [%6.1f, %6.1f]  %6.3f  %5s\n",
                  r$spec, r$att, r$se, r$ci_lo, r$ci_hi, r$p_value, r$signif))
    } else {
      cat(sprintf("%-28s  %s\n", r$spec, "failed"))
    }
  }
  cat(paste(rep("-", 78), collapse = ""), "\n\n")
}

## Save formatted table
txt_lines <- capture.output({
  cat("Robustness Table: C&S Simple ATT across specifications\n")
  cat("Outcomes: fiscal_balance_pc, rev_total_pc, exp_capital_pc\n\n")
  for (y in outcomes) {
    yt <- rob_tbl[rob_tbl$outcome == y, ]
    cat(sprintf("Panel: %s\n", y))
    cat(sprintf("%-28s  %8s  %7s  %14s  %6s  %5s\n",
                "Specification", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
    cat(paste(rep("-", 78), collapse = ""), "\n")
    for (i in seq_len(nrow(yt))) {
      r <- yt[i, ]
      if (!is.na(r$att)) {
        cat(sprintf("%-28s  %8.1f  %7.1f  [%6.1f, %6.1f]  %6.3f  %5s\n",
                    r$spec, r$att, r$se, r$ci_lo, r$ci_hi, r$p_value, r$signif))
      }
    }
    cat(paste(rep("-", 78), collapse = ""), "\n\n")
  }
  cat("Note: DR estimator, bootstrap SE (n=999). *** p<0.01 ** p<0.05 * p<0.10\n")
  cat("Smoke buffer (100 km) not applied as sample restriction: 40/51\n")
  cat("never-treated counties are within 100 km of a fire perimeter in\n")
  cat("post-treatment years. For fiscal outcomes, 100 km smoke contamination\n")
  cat("does not operate through the fiscal mechanism (property damage is\n")
  cat("geographically localised). Documented as a limitation.\n")
})
writeLines(txt_lines, file.path(TOUT, "robustness_table.txt"))

cat(sprintf("\nRobustness table -> output/tables/robustness_table.txt\n"))
cat(sprintf("Machine-readable -> output/tables/robustness_table.csv\n"))
cat("\nDone. Next: 05_sun_abraham.R\n")
