##
## Home rule / Dillon's Rule heterogeneity analysis.
##
## Research question: do counties in home rule states respond differently to
## high-severity wildfire fiscal shocks than counties in Dillon's Rule states?
##
## Approach: subgroup C&S doubly-robust ATT, estimated separately for:
##   (A) Dillon's Rule states  (dillons_rule_state == 1)
##   (B) Home rule / statutory home rule states  (dillons_rule_state == 0)
##
## Uses intensive-margin treatment (g variable; high-severity fire) only.
##
## Outputs:
##   output/tables/home_rule_heterogeneity.csv
##   output/tables/home_rule_heterogeneity.txt
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
dir.create(TOUT, showWarnings = FALSE, recursive = TRUE)

## ── Load panel ─────────────────────────────────────────────────────────────────

panel <- read.csv(file.path(DATA, "panel_final.csv"), stringsAsFactors = FALSE)
panel$fips <- sprintf("%05d", as.integer(panel$fips))

## Check home rule variables are present
if (!"dillons_rule_state" %in% names(panel)) {
  stop("dillons_rule_state not found in panel — re-run 07_panel_assemble.py first.")
}

cat("Home rule variable coverage (year_cog = 2012):\n")
base12 <- panel[panel$year_cog == 2012, ]
cat(sprintf("  dillons_rule_state = 1 (Dillon's Rule): %d counties\n",
            sum(base12$dillons_rule_state == 1, na.rm = TRUE)))
cat(sprintf("  dillons_rule_state = 0 (Home rule):     %d counties\n",
            sum(base12$dillons_rule_state == 0, na.rm = TRUE)))
cat(sprintf("  home_rule_county   = 1 (charter):       %d counties\n",
            if ("home_rule_county" %in% names(panel))
              sum(base12$home_rule_county == 1, na.rm = TRUE) else NA))
cat("\n")

## ── Pre-compute covariates ─────────────────────────────────────────────────────

panel <- panel |>
  group_by(state, year_cog) |>
  mutate(
    state_share65 = median(share_65plus, na.rm = TRUE),
    state_popdns  = median(pop_density,  na.rm = TRUE)
  ) |>
  ungroup() |>
  mutate(
    share_65plus_imp = case_when(
      !is.na(share_65plus)   ~ share_65plus,
      !is.na(state_share65)  ~ state_share65,
      TRUE                   ~ median(share_65plus, na.rm = TRUE)
    ),
    log_pop_dens = log(case_when(
      !is.na(pop_density)  ~ pop_density,
      !is.na(state_popdns) ~ state_popdns,
      TRUE                 ~ median(pop_density, na.rm = TRUE)
    ) + 1),
    log_hhinc    = log(pmax(median_hhinc, 1)),
    fips_int     = as.integer(fips)
  )

## did v2.x: never-treated = Inf
panel <- panel |>
  mutate(g = ifelse(g == 0, Inf, g))

## ── Covariate formula (same as main spec) ─────────────────────────────────────

xf <- ~ whp_2012 + pre2013_fire + pre2013_log_acres + rucc_2013 +
         log_hhinc + poverty_rate + share_65plus_imp + log_pop_dens

## ── Outcomes ──────────────────────────────────────────────────────────────────

outcomes <- c("fiscal_balance_pc", "rev_total_pc", "exp_capital_pc", "rev_proptax_pc")

outcome_labels <- c(
  fiscal_balance_pc = "Fiscal balance p.c.",
  rev_total_pc      = "Total revenue p.c.",
  exp_capital_pc    = "Capital outlays p.c.",
  rev_proptax_pc    = "Property tax rev. p.c."
)

## ── Subgroup analysis function ────────────────────────────────────────────────

run_subgroup <- function(data, subgroup_label, y) {
  n_treated <- sum(data$g[data$year_cog == 2012] < Inf & data$g[data$year_cog == 2012] > 0,
                   na.rm = TRUE)
  n_ctrl    <- sum(is.infinite(data$g[data$year_cog == 2012]), na.rm = TRUE)
  cat(sprintf("    %s: treated=%d, ctrl=%d\n", subgroup_label, n_treated, n_ctrl))

  if (n_treated < 5 || n_ctrl < 5) {
    cat("    Skipped (insufficient sample)\n")
    return(NULL)
  }

  tryCatch({
    fit <- att_gt(
      yname          = y,
      tname          = "year_cog",
      idname         = "fips_int",
      gname          = "g",
      xformla        = xf,
      data           = as.data.frame(data),
      control_group  = "nevertreated",
      est_method     = "dr",
      base_period    = "varying",
      clustervars    = "fips_int",
      print_details  = FALSE
    )
    agg <- aggte(fit, type = "simple", na.rm = TRUE)
    list(
      att      = round(agg$overall.att, 1),
      se       = round(agg$overall.se,  1),
      pv       = 2 * pnorm(-abs(agg$overall.att / agg$overall.se)),
      n_trt    = n_treated,
      n_ctl    = n_ctrl
    )
  }, error = function(e) {
    cat(sprintf("    ERROR: %s\n", conditionMessage(e)))
    NULL
  })
}

## ── Run for each outcome and subgroup ─────────────────────────────────────────

results <- list()

for (y in outcomes) {
  cat(sprintf("\n=== %s ===\n", y))

  dr  <- run_subgroup(panel[panel$dillons_rule_state == 1, ], "Dillon's Rule", y)
  hr  <- run_subgroup(panel[panel$dillons_rule_state == 0, ], "Home rule",     y)

  for (nm in c("dillons_rule", "home_rule")) {
    r <- if (nm == "dillons_rule") dr else hr
    if (!is.null(r)) {
      sig <- ifelse(r$pv < 0.01, "***",
               ifelse(r$pv < 0.05, "**",
                 ifelse(r$pv < 0.10, "*", "")))
      cat(sprintf("  %s: ATT=%.1f  SE=%.1f  p=%.3f %s\n",
                  nm, r$att, r$se, r$pv, sig))
      results[[paste(y, nm, sep = "_")]] <- data.frame(
        outcome  = y,
        subgroup = nm,
        att      = r$att,
        se       = r$se,
        ci_lo    = round(r$att - qnorm(0.975) * r$se, 1),
        ci_hi    = round(r$att + qnorm(0.975) * r$se, 1),
        p_value  = round(r$pv, 3),
        signif   = sig,
        n_trt    = r$n_trt,
        n_ctl    = r$n_ctl,
        stringsAsFactors = FALSE
      )
    }
  }
}

if (length(results) == 0) {
  stop("No results produced — check subgroup sizes and data merge.")
}

out_tbl <- do.call(rbind, results)
write.csv(out_tbl, file.path(TOUT, "home_rule_heterogeneity.csv"), row.names = FALSE)

## ── Summary table ─────────────────────────────────────────────────────────────

cat("\n\n=== Home Rule Heterogeneity Results ===\n\n")
cat(sprintf("%-26s  %-14s  %8s  %7s  %14s  %7s  %5s\n",
            "Outcome", "Subgroup", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
cat(paste(rep("-", 95), collapse = ""), "\n")
for (i in seq_len(nrow(out_tbl))) {
  r <- out_tbl[i, ]
  cat(sprintf("%-26s  %-14s  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
              r$outcome, r$subgroup, r$att, r$se, r$ci_lo, r$ci_hi,
              r$p_value, r$signif))
}
cat(paste(rep("-", 95), collapse = ""), "\n")

## ── Wide-format table for paper ───────────────────────────────────────────────

wide <- out_tbl |>
  tidyr::pivot_wider(
    id_cols     = outcome,
    names_from  = subgroup,
    values_from = c(att, se, p_value, signif, n_trt, n_ctl)
  )
write.csv(wide, file.path(TOUT, "home_rule_heterogeneity_wide.csv"), row.names = FALSE)

writeLines(capture.output({
  cat("Home Rule / Dillon's Rule Heterogeneity\n")
  cat("Subgroup C&S doubly-robust ATT (intensive margin: high-severity fire)\n\n")
  cat(sprintf("%-26s  %-14s  %8s  %7s  %14s  %7s  %5s\n",
              "Outcome", "Subgroup", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
  cat(paste(rep("-", 95), collapse = ""), "\n")
  for (i in seq_len(nrow(out_tbl))) {
    r <- out_tbl[i, ]
    cat(sprintf("%-26s  %-14s  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
                r$outcome, r$subgroup, r$att, r$se, r$ci_lo, r$ci_hi,
                r$p_value, r$signif))
  }
  cat(paste(rep("-", 95), collapse = ""), "\n")
  cat("Note: *** p<0.01, ** p<0.05, * p<0.10. 999 bootstrap replications (block by county).\n")
  cat("      Subgroups defined by state-level Dillon's Rule doctrine (dillons_rule_state).\n")
  cat("      Never-treated control group; same covariate formula as Table 3 (main spec).\n")
}), file.path(TOUT, "home_rule_heterogeneity.txt"))

cat("\nOutput -> output/tables/home_rule_heterogeneity.csv / .txt\n")
cat("Done.\n")
