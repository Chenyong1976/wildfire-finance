##
## Robustness analysis for rev_intergovt_pc — the one outcome with a
## marginal pre-trend violation (joint pre-trend p = 0.042).
##
## Two complementary methods:
##
##  1. Honest DiD (Rambachan & Roth 2023, AER)
##     Relative-magnitudes restriction (Delta_RM): the post-treatment
##     violation of parallel trends is bounded by Mbar × max(|pre-ATT|).
##     Mbar = 0  →  standard DiD CI
##     Mbar = 1  →  post-trend violation can equal the largest pre-trend
##     Reports sensitivity CIs for Mbar ∈ {0, 0.5, 1.0, 1.5, 2.0}.
##     Also applies the smoothness restriction (Delta_SD, second differences)
##     for completeness.
##
##  2. Synthetic DiD (Arkhangelsky et al. 2021, AER)
##     Reweights control units and time periods to match pre-treatment
##     outcome trajectories, attenuating pre-trend differences by
##     construction.  Run separately for each C&S cohort:
##       - g=2017: never-treated controls; T0=3 pre-periods
##       - g=2022: never-treated controls; T0=4 pre-periods
##     Cohort ATTs combined via equal weighting (n_2017/n_total).
##
## Outputs:
##   output/tables/intergovt_honest_did.csv    sensitivity table
##   output/figures/intergovt_honest_did.pdf   sensitivity plot
##   output/tables/intergovt_synthdid.csv      synthdid table
##   output/rds/synthdid_intergovt_g2017.rds
##   output/rds/synthdid_intergovt_g2022.rds
##

suppressPackageStartupMessages({
  library(here)
  library(did)
  library(HonestDiD)
  library(synthdid)
  library(ggplot2)
  library(dplyr)
})
set.seed(42)

ROOT <- here::here()
DATA <- file.path(ROOT, "data", "processed")
TOUT <- file.path(ROOT, "output", "tables")
FOUT <- file.path(ROOT, "output", "figures")
ROUT <- file.path(ROOT, "output", "rds")
dir.create(TOUT, showWarnings = FALSE, recursive = TRUE)
dir.create(FOUT, showWarnings = FALSE, recursive = TRUE)
dir.create(ROUT, showWarnings = FALSE, recursive = TRUE)

OUTCOME <- "rev_intergovt_pc"
ALPHA   <- 0.05

## ─────────────────────────────────────────────────────────────────────────────
## 1.  Load C&S dynamic aggregation for rev_intergovt_pc
## ─────────────────────────────────────────────────────────────────────────────

fit <- readRDS(file.path(ROUT, sprintf("cs_att_gt_%s.rds", OUTCOME)))

## Dynamic aggregation: event times e = -10, -5, 0, +5
ag <- aggte(fit, type = "dynamic")

betahat <- ag$att.egt   # length-4 vector
se_vec  <- ag$se.egt
e_vals  <- ag$egt

cat("=== C&S Dynamic aggregation — rev_intergovt_pc ===\n")
cat(sprintf("  e = %4d  ATT = %7.1f  SE = %6.1f\n",
            e_vals, betahat, se_vec) |> paste(collapse = ""))
cat("\n")

numPrePeriods  <- sum(e_vals < 0)   # 2
numPostPeriods <- sum(e_vals >= 0)  # 2

## Covariance matrix via influence function (n × numPeriods matrix)
## sigma = IF' IF / n^2   (sandwich estimator, exactly what did uses for SE)
IF    <- ag$inf.function$dynamic.inf.func.e   # 2968 × 4
n_obs <- nrow(IF)
sigma <- (t(IF) %*% IF) / (n_obs^2)

## Sanity-check: diagonal of sigma should equal se_vec^2
cat("SE check (max abs diff):", max(abs(sqrt(diag(sigma)) - se_vec)), "\n\n")

## ─────────────────────────────────────────────────────────────────────────────
## 2.  Honest DiD — relative-magnitudes restriction (Delta_RM)
## ─────────────────────────────────────────────────────────────────────────────
## Delta_RM: the deviation of the post-treatment trend from parallel is bounded
## by Mbar × max_{l<0}|delta_l|, where delta_l are the pre-trend violations.
## This directly calibrates the sensitivity to the magnitude of the pre-trend.

cat("=== Honest DiD: relative-magnitudes restriction (Delta_RM) ===\n")

Mbarvec <- c(0, 0.5, 1.0, 1.5, 2.0)

## HonestDiD v0.2.x API: createSensitivityResults_relativeMagnitudes
## l_vec selects which post-period effect to report; default = first post-period (e=0)
rm_results <- createSensitivityResults_relativeMagnitudes(
  betahat        = betahat,
  sigma          = sigma,
  numPrePeriods  = numPrePeriods,
  numPostPeriods = numPostPeriods,
  Mbarvec        = Mbarvec,
  alpha          = ALPHA
)

cat("Relative-magnitudes sensitivity (first post-period, e=0):\n")
print(rm_results)

## Also for the second post-period (e=+5)
rm_results_2 <- createSensitivityResults_relativeMagnitudes(
  betahat        = betahat,
  sigma          = sigma,
  numPrePeriods  = numPrePeriods,
  numPostPeriods = numPostPeriods,
  Mbarvec        = Mbarvec,
  l_vec          = basisVector(index = 2, size = numPostPeriods),
  alpha          = ALPHA
)
cat("\nRelative-magnitudes sensitivity (second post-period, e=+5):\n")
print(rm_results_2)

## Combine and save
rm_tbl <- rbind(
  cbind(period = "e=0",  rm_results),
  cbind(period = "e=+5", rm_results_2)
)
write.csv(rm_tbl, file.path(TOUT, "intergovt_honest_did_rm.csv"), row.names = FALSE)

## ─────────────────────────────────────────────────────────────────────────────
## 3.  Honest DiD — smoothness restriction (Delta_SD)
## ─────────────────────────────────────────────────────────────────────────────
## Delta_SD: the second difference of the path (acceleration) is bounded by M.
## FLCI computation requires Matrix >= 1.7 (CVXR/OSQP); if unavailable, the
## C-LF conditional method is used as a fallback.

cat("\n=== Honest DiD: smoothness restriction (Delta_SD) ===\n")

Mvec_sd <- c(0, 25, 50, 100, 150, 200)

sd_results <- tryCatch({
  createSensitivityResults(
    betahat        = betahat,
    sigma          = sigma,
    numPrePeriods  = numPrePeriods,
    numPostPeriods = numPostPeriods,
    Mvec           = Mvec_sd,
    alpha          = ALPHA
  )
}, error = function(e) {
  cat("  FLCI failed (Matrix version conflict) — using C-LF conditional method\n")
  ## C-LF only via the conditional CS function
  do.call(rbind, lapply(Mvec_sd, function(M) {
    res <- tryCatch(
      computeConditionalCS_DeltaSD(
        betahat        = betahat,
        sigma          = sigma,
        numPrePeriods  = numPrePeriods,
        numPostPeriods = numPostPeriods,
        M              = M,
        alpha          = ALPHA,
        l_vec          = basisVector(1, numPostPeriods)
      ),
      error = function(e2) list(lb = NA_real_, ub = NA_real_)
    )
    data.frame(lb = res$lb, ub = res$ub, method = "C-LF", Delta = "DeltaSD", M = M)
  }))
})

cat("Smoothness sensitivity (first post-period, e=0):\n")
print(sd_results)

write.csv(sd_results, file.path(TOUT, "intergovt_honest_did_sd.csv"), row.names = FALSE)

## ─────────────────────────────────────────────────────────────────────────────
## 4.  Sensitivity plot — relative magnitudes
## ─────────────────────────────────────────────────────────────────────────────

## Original CS CI (for reference line)
cs_ci_lo <- betahat[numPrePeriods + 1] - qnorm(1 - ALPHA / 2) * se_vec[numPrePeriods + 1]
cs_ci_hi <- betahat[numPrePeriods + 1] + qnorm(1 - ALPHA / 2) * se_vec[numPrePeriods + 1]

## Build plot data.frame
plot_df <- rm_results |>
  mutate(
    method_label = "Relative-magnitudes",
    Mbar_label   = as.character(round(Mbar, 2))
  )

sens_plot <- ggplot(plot_df, aes(x = Mbar, ymin = lb, ymax = ub)) +
  annotate("rect", xmin = -Inf, xmax = Inf, ymin = cs_ci_lo, ymax = cs_ci_hi,
           fill = "#adb5bd", alpha = 0.35) +
  annotate("segment", x = -Inf, xend = Inf,
           y = betahat[numPrePeriods + 1], yend = betahat[numPrePeriods + 1],
           linetype = "dashed", colour = "#495057", linewidth = 0.5) +
  geom_hline(yintercept = 0, colour = "grey50", linewidth = 0.4) +
  geom_errorbar(width = 0.06, linewidth = 0.8, colour = "#c0392b") +
  scale_x_continuous(breaks = Mbarvec,
                     labels = sprintf("M̅=%.1f", Mbarvec)) +
  labs(
    x     = "Mbar (post-period violation relative to max pre-period deviation)",
    y     = "ATT, first post-period (e=0)",
    title = "Figure: Honest DiD Sensitivity — Intergovernmental Revenue p.c.",
    subtitle = paste0(
      "Grey band = standard C&S 95% CI (Mbar=0). Red bars = honest 95% CI.\n",
      "Dashed line = point estimate (",
      round(betahat[numPrePeriods + 1], 1), " $/capita). ",
      "Outcome: rev_intergovt_pc."
    )
  ) +
  theme_bw(base_size = 10) +
  theme(panel.grid.minor = element_blank(),
        plot.subtitle = element_text(size = 7.5, colour = "grey40"))

ggsave(file.path(FOUT, "intergovt_honest_did.pdf"),
       plot = sens_plot, width = 7, height = 4.5, dpi = 300)
cat(sprintf("\nSensitivity plot saved -> output/figures/intergovt_honest_did.pdf\n\n"))

## ─────────────────────────────────────────────────────────────────────────────
## 5.  Synthetic DiD — run separately for g=2017 and g=2022
## ─────────────────────────────────────────────────────────────────────────────

cat("=== Synthetic DiD — rev_intergovt_pc ===\n\n")

panel_csv <- read.csv(file.path(DATA, "panel_final.csv"), stringsAsFactors = FALSE)
panel_csv$fips <- sprintf("%05d", as.integer(panel_csv$fips))

## Add rev_intergovt_pc if not present
if (!"rev_intergovt_pc" %in% names(panel_csv))
  panel_csv$rev_intergovt_pc <- panel_csv$rev_igt_federal_pc + panel_csv$rev_igt_state_pc

## synthdid requires a balanced panel; keep only counties present in all periods
keep_fips <- panel_csv |>
  group_by(fips) |>
  summarise(n_periods = n(), .groups = "drop") |>
  filter(n_periods == 5) |>
  pull(fips)
panel_bal <- panel_csv |> filter(fips %in% keep_fips)
cat(sprintf("Balanced panel: %d counties × 5 periods\n\n", length(keep_fips)))

## Helper: run synthdid for one cohort against never-treated controls
run_sdid <- function(g_cohort, panel) {
  ## Cohort rows + never-treated; exclude other cohorts to avoid contamination
  sub <- panel |>
    filter(g == g_cohort | g == 0)

  ## Treatment indicator: 1 iff in cohort AND year_cog >= g_cohort
  sub$w <- as.integer(sub$g == g_cohort & sub$year_cog >= g_cohort)

  df <- data.frame(
    unit    = sub$fips,
    time    = sub$year_cog,
    outcome = sub[[OUTCOME]],
    treat   = sub$w
  )

  mat <- tryCatch(
    panel.matrices(df, unit = "unit", time = "time",
                   outcome = "outcome", treatment = "treat"),
    error = function(e) { cat("  panel.matrices error:", conditionMessage(e), "\n"); NULL }
  )
  if (is.null(mat)) return(NULL)

  cat(sprintf("  g=%d: N0=%d treated=%d T0=%d T1=%d\n",
              g_cohort, mat$N0,
              nrow(mat$Y) - mat$N0,
              mat$T0, ncol(mat$Y) - mat$T0))

  est <- tryCatch(
    synthdid_estimate(mat$Y, mat$N0, mat$T0),
    error = function(e) { cat("  synthdid_estimate error:", conditionMessage(e), "\n"); NULL }
  )
  if (is.null(est)) return(NULL)

  ## Placebo-based SE (jackknife over control units)
  se_jk <- tryCatch(
    sqrt(vcov(est, method = "jackknife")),
    error = function(e) {
      cat("  jackknife SE error:", conditionMessage(e),
          "— falling back to placebo SE\n")
      tryCatch(sqrt(vcov(est, method = "placebo")),
               error = function(e2) NA_real_)
    }
  )

  list(
    g        = g_cohort,
    n_treat  = nrow(mat$Y) - mat$N0,
    att      = as.numeric(est),
    se       = as.numeric(se_jk),
    est_obj  = est,
    mat      = mat
  )
}

sdid_17 <- run_sdid(2017, panel_bal)
sdid_22 <- run_sdid(2022, panel_bal)

## Save estimate objects
if (!is.null(sdid_17))
  saveRDS(sdid_17$est_obj, file.path(ROUT, "synthdid_intergovt_g2017.rds"))
if (!is.null(sdid_22))
  saveRDS(sdid_22$est_obj, file.path(ROUT, "synthdid_intergovt_g2022.rds"))

## Print and combine
sdid_list <- Filter(Negate(is.null), list(sdid_17, sdid_22))

sdid_tbl <- do.call(rbind, lapply(sdid_list, function(x) {
  pval <- if (!is.na(x$se) && x$se > 0)
    2 * pnorm(-abs(x$att / x$se)) else NA_real_
  data.frame(
    method    = "SynthDiD",
    cohort    = x$g,
    n_treated = x$n_treat,
    att       = round(x$att, 1),
    se        = round(x$se, 1),
    ci_lo     = round(x$att - qnorm(0.975) * x$se, 1),
    ci_hi     = round(x$att + qnorm(0.975) * x$se, 1),
    p_value   = round(pval, 3),
    signif    = ifelse(is.na(pval), "",
                ifelse(pval < 0.01, "***",
                ifelse(pval < 0.05, "**",
                ifelse(pval < 0.10, "*", "")))),
    stringsAsFactors = FALSE
  )
}))

## Weighted average ATT across cohorts
if (nrow(sdid_tbl) == 2) {
  w1 <- sdid_tbl$n_treated[1]; w2 <- sdid_tbl$n_treated[2]
  wt_att <- (w1 * sdid_tbl$att[1] + w2 * sdid_tbl$att[2]) / (w1 + w2)
  cat(sprintf("SynthDiD weighted ATT: %.1f  (n_2017=%d, n_2022=%d)\n\n",
              wt_att, w1, w2))
}

write.csv(sdid_tbl, file.path(TOUT, "intergovt_synthdid.csv"), row.names = FALSE)

cat("\n=== Synthetic DiD Results — rev_intergovt_pc ===\n")
cat(sprintf("%-9s  %8s  %8s  %7s  %14s  %7s  %5s\n",
            "Cohort", "N treat", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
cat(paste(rep("-", 72), collapse = ""), "\n")
for (i in seq_len(nrow(sdid_tbl))) {
  r <- sdid_tbl[i, ]
  cat(sprintf("g=%-7d  %8d  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
              r$cohort, r$n_treated, r$att, r$se,
              r$ci_lo, r$ci_hi, r$p_value, r$signif))
}
cat(paste(rep("-", 72), collapse = ""), "\n")
cat("Note: jackknife SE. Never-treated controls only. 95% CI. *** p<0.01\n\n")

## ─────────────────────────────────────────────────────────────────────────────
## 6.  Summary interpretation
## ─────────────────────────────────────────────────────────────────────────────

cat("=== Summary: Causal interpretation of rev_intergovt_pc ===\n\n")
cat(sprintf(
  "C&S dynamic ATTs (e=0, e=+5): %.1f (SE %.1f), %.1f (SE %.1f)\n",
  betahat[3], se_vec[3], betahat[4], se_vec[4]
))
cat(sprintf(
  "Pre-trend (e=-10, e=-5):       %.1f (SE %.1f), %.1f (SE %.1f)\n",
  betahat[1], se_vec[1], betahat[2], se_vec[2]
))
cat("\nHonest DiD (Delta_RM) — first post-period (e=0):\n")
for (i in seq_len(nrow(rm_results))) {
  covers_zero <- (rm_results$lb[i] <= 0 & rm_results$ub[i] >= 0)
  cat(sprintf("  Mbar=%.1f:  [%7.1f, %7.1f]  covers 0: %s\n",
              rm_results$Mbar[i], rm_results$lb[i], rm_results$ub[i],
              ifelse(covers_zero, "YES", "NO")))
}
cat("\n")

cat("Done. Outputs:\n")
cat("  output/tables/intergovt_honest_did_rm.csv\n")
cat("  output/tables/intergovt_honest_did_sd.csv\n")
cat("  output/tables/intergovt_synthdid.csv\n")
cat("  output/figures/intergovt_honest_did.pdf\n")
