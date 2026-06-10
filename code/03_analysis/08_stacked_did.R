##
## Two-stage DiD (Gardner 2021) via did2s package — wildfire finance project.
##
## Stage 1: Estimate unit and time FEs from pre-treatment ("clean") observations.
##           For each unit i, "pre-treatment" means t < g_i (never-treated: all periods).
## Stage 2: Regress estimated residuals on treatment indicator.
##
## Reference: Gardner (2021), "Two-Stage Differences in Differences"
## Package: did2s v1.0.2 (Butts 2021)
##
## Outputs:
##   output/tables/stacked_did_table.csv
##   output/tables/stacked_did_table.txt
##   output/figures/stacked_did_event_study.pdf
##

suppressPackageStartupMessages({
  library(here)
  library(did2s)
  library(fixest)
  library(dplyr)
  library(ggplot2)
})
set.seed(42)

ROOT <- here::here()
DATA <- file.path(ROOT, "data", "processed")
TOUT <- file.path(ROOT, "output", "tables")
FOUT <- file.path(ROOT, "output", "figures")
dir.create(TOUT, showWarnings = FALSE, recursive = TRUE)
dir.create(FOUT, showWarnings = FALSE, recursive = TRUE)

## ── Load and prepare panel ────────────────────────────────────────────────────

panel <- read.csv(file.path(DATA, "panel_final.csv"), stringsAsFactors = FALSE)
panel$fips <- sprintf("%05d", as.integer(panel$fips))

if (!"rev_intergovt_pc" %in% names(panel))
  panel$rev_intergovt_pc <- panel$rev_igt_federal_pc + panel$rev_igt_state_pc

## did2s requires:
##   - fips_int: integer unit id
##   - year_cog: integer time variable
##   - g_d2s: first treatment period (0 for never-treated; did2s uses 0, not Inf)
##   - treatment indicator (0/1) per unit-period
## g in panel_final.csv: 0=never, 2017=fires 2013-2016, 2022=fires 2017-2021
panel <- panel |>
  mutate(
    fips_int = as.integer(fips),
    g_d2s    = as.integer(g),   # 0=never, 2017, 2022
    ## absorb = 1 in post-treatment periods
    treated  = as.integer(g_d2s > 0 & year_cog >= g_d2s)
  )

cat("Treatment indicator check:\n")
print(table(panel$treated, panel$g_d2s, useNA="ifany"))
cat("\n")

outcomes <- c("fiscal_balance_pc", "rev_total_pc", "rev_proptax_pc", "exp_capital_pc")

## ── Run did2s for each outcome ────────────────────────────────────────────────

d2s_results <- list()

for (y in outcomes) {
  cat(sprintf("--- %s ---\n", y))
  tryCatch({
    fit <- did2s(
      data         = panel,
      yname        = y,
      first_stage  = ~ 0 | fips_int + year_cog,  # unit + year FE only
      second_stage = ~ i(treated, ref = 0L),
      treatment    = "treated",
      cluster_var  = "fips_int"
    )
    ct  <- coeftable(fit)
    att <- ct["treated::1", "Estimate"]
    se  <- ct["treated::1", "Std. Error"]
    pv  <- ct["treated::1", "Pr(>|t|)"]
    d2s_results[[y]] <- list(att=att, se=se, pv=pv, fit=fit)
    sig <- ifelse(pv<0.01,"***",ifelse(pv<0.05,"**",ifelse(pv<0.10,"*","")))
    cat(sprintf("  ATT = %.2f  SE = %.2f  p = %.3f %s\n", att, se, pv, sig))
  }, error = function(e) {
    cat(sprintf("  ERROR: %s\n", conditionMessage(e)))
  })
}

## ── Event study via did2s ─────────────────────────────────────────────────────
##
## Replace `treated` indicator with event-time dummies.
## Event time l = year_cog - g_d2s for treated; exclude never-treated in second stage.

panel_es <- panel |>
  filter(g_d2s > 0 | TRUE) |>   # keep all (never-treated serve as controls)
  mutate(
    ## event time for treated units; large negative for never-treated (excluded)
    l = ifelse(g_d2s > 0, year_cog - g_d2s, -99L)
  )

cat("\nEvent study for fiscal_balance_pc:\n")
tryCatch({
  fit_es <- did2s(
    data         = panel_es,
    yname        = "fiscal_balance_pc",
    first_stage  = ~ 0 | fips_int + year_cog,
    second_stage = ~ i(l, ref = c(-5, -99)),  # ref = -5 (pre-treatment) and -99 (never)
    treatment    = "treated",
    cluster_var  = "fips_int"
  )
  iplot(fit_es,
        main = "Two-Stage DiD Event Study: Fiscal Balance p.c.",
        xlab = "Event time (CoG census years relative to first fire cohort)",
        ylab = "Fiscal Balance p.c. (2019$)")
  ggsave(file.path(FOUT, "stacked_did_event_study.pdf"), width=8, height=4)
  cat("  Event study -> output/figures/stacked_did_event_study.pdf\n")
}, error = function(e) {
  cat(sprintf("  Event study error: %s\n", conditionMessage(e)))
})

## ── Summary table ─────────────────────────────────────────────────────────────

rows <- lapply(names(d2s_results), function(y) {
  r <- d2s_results[[y]]
  data.frame(
    outcome = y,
    att     = round(r$att, 1),
    se      = round(r$se, 1),
    ci_lo   = round(r$att - qnorm(0.975)*r$se, 1),
    ci_hi   = round(r$att + qnorm(0.975)*r$se, 1),
    p_value = round(r$pv, 3),
    signif  = ifelse(r$pv<0.01,"***",ifelse(r$pv<0.05,"**",ifelse(r$pv<0.10,"*",""))),
    stringsAsFactors = FALSE
  )
})
d2s_tbl <- do.call(rbind, rows)
write.csv(d2s_tbl, file.path(TOUT, "stacked_did_table.csv"), row.names=FALSE)

cat("\n=== Two-Stage DiD ATT (Gardner 2021) ===\n")
cat(sprintf("%-22s  %8s  %7s  %14s  %7s  %5s\n",
            "Outcome", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
cat(paste(rep("-",78),collapse=""), "\n")
for (i in seq_len(nrow(d2s_tbl))) {
  r <- d2s_tbl[i,]
  cat(sprintf("%-22s  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
              r$outcome, r$att, r$se, r$ci_lo, r$ci_hi, r$p_value, r$signif))
}
cat(paste(rep("-",78),collapse=""), "\n")
cat("Note: Stage 1 absorbs unit + time FE from pre-treatment data; clustered SE.\n")
cat("      *** p<0.01 ** p<0.05 * p<0.10\n\n")

writeLines(capture.output({
  cat("Two-Stage DiD ATT — Wildfire Finance (Gardner 2021)\n")
  cat("Package: did2s v1.0.2 (Butts 2021)\n")
  cat("Stage 1: unit + year FE on pre-treatment observations\n")
  cat("Stage 2: treatment indicator on residuals, clustered SE by county\n\n")
  cat(sprintf("%-22s  %8s  %7s  %14s  %7s  %5s\n",
              "Outcome", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
  cat(paste(rep("-",78),collapse=""), "\n")
  for (i in seq_len(nrow(d2s_tbl))) {
    r <- d2s_tbl[i,]
    cat(sprintf("%-22s  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
                r$outcome, r$att, r$se, r$ci_lo, r$ci_hi, r$p_value, r$signif))
  }
  cat(paste(rep("-",78),collapse=""), "\n")
  cat("Note: *** p<0.01 ** p<0.05 * p<0.10\n")
}), file.path(TOUT, "stacked_did_table.txt"))

cat("Output -> output/tables/stacked_did_table.csv / .txt\n")
cat("Done.\n")
