##
## Synthetic DiD estimator — wildfire finance project.
##
## Staggered adoption handled by running synthdid separately per cohort:
##   g=2017 (fires 2013-2016): pre={2002,2007,2012}, post={2017,2022}
##            donor pool = never-treated + g=2022 (not-yet-treated in 2017)
##   g=2022 (fires 2017-2021): pre={2002,2007,2012,2017}, post={2022}
##            donor pool = never-treated only
##
## Cohort-level estimates are pooled with cohort-size weights (n_g / n_total).
##
## Reference: Arkhangelsky et al. (2021), AER 111(12): 4088-4118.
##
## Outputs:
##   output/tables/synthdid_table.csv
##   output/tables/synthdid_table.txt
##   output/figures/synthdid_placebo_*.pdf   (placebo/event-study plots)
##

suppressPackageStartupMessages({
  library(here)
  library(synthdid)
  library(dplyr)
})
set.seed(42)

ROOT <- here::here()
DATA <- file.path(ROOT, "data", "processed")
TOUT <- file.path(ROOT, "output", "tables")
FOUT <- file.path(ROOT, "output", "figures")
dir.create(TOUT, showWarnings = FALSE, recursive = TRUE)
dir.create(FOUT, showWarnings = FALSE, recursive = TRUE)

## ── Load panel ────────────────────────────────────────────────────────────────

panel <- read.csv(file.path(DATA, "panel_final.csv"), stringsAsFactors = FALSE)
panel$fips <- sprintf("%05d", as.integer(panel$fips))

if (!"rev_intergovt_pc" %in% names(panel))
  panel$rev_intergovt_pc <- panel$rev_igt_federal_pc + panel$rev_igt_state_pc

## g == 0 → never-treated; keep as 0 (synthdid doesn't need Inf)
cat(sprintf("Panel dims: %d obs, %d units, %d time periods\n",
            nrow(panel), length(unique(panel$fips)), length(unique(panel$year_cog))))
cat("Cohort sizes:\n")
print(table(panel$g[panel$year_cog == 2012]))
cat("\n")

## ── Helper: build synthdid matrices for one cohort ───────────────────────────

build_setup <- function(data, treated_g, y_var, gvar = "g") {
  ## For cohort treated_g, subset to treated units + valid donor pool.
  ## gvar: name of the group variable column ("g" for intensity, "g_any" for extensive).
  g_col <- data[[gvar]]
  if (treated_g == 2017) {
    sub <- data[g_col %in% c(0, 2017, 2022), ]
  } else if (treated_g == 2022) {
    sub <- data[g_col %in% c(0, 2022), ]
  } else {
    stop(sprintf("Unsupported cohort: %d", treated_g))
  }

  ## Treatment indicator: 1 iff unit is in treated cohort AND t >= treated_g
  sub$treat_ind <- as.integer(sub[[gvar]] == treated_g & sub$year_cog >= treated_g)

  ## panel.matrices() needs balanced panel; verify
  panel_counts <- table(sub$fips)
  n_periods    <- length(unique(sub$year_cog))
  unbalanced   <- sum(panel_counts != n_periods)
  if (unbalanced > 0)
    warning(sprintf("Cohort %d: %d units with unequal periods (dropping)", treated_g, unbalanced))

  sub <- sub[sub$fips %in% names(panel_counts[panel_counts == n_periods]), ]

  df_setup <- sub[, c("fips", "year_cog", y_var, "treat_ind")]
  names(df_setup)[3] <- "outcome"

  tryCatch(
    panel.matrices(as.data.frame(df_setup),
                   unit      = "fips",
                   time      = "year_cog",
                   outcome   = "outcome",
                   treatment = "treat_ind"),
    error = function(e) {
      cat(sprintf("  panel.matrices error (g=%d): %s\n", treated_g, conditionMessage(e)))
      NULL
    }
  )
}

## ── Run synthdid for each cohort and outcome ─────────────────────────────────

outcomes <- c("fiscal_balance_pc", "rev_total_pc", "rev_proptax_pc", "exp_capital_pc")
cohorts  <- c(2017, 2022)
n_g      <- c("2017" = 208, "2022" = 85)   # cohort sizes from panel

synthdid_results <- list()

for (y in outcomes) {
  cat(sprintf("\n=== %s ===\n", y))
  cohort_ests <- list()

  for (g in cohorts) {
    cat(sprintf("  g=%d ... ", g))
    setup <- build_setup(panel, g, y)
    if (is.null(setup)) { cat("skipped (setup failed)\n"); next }

    n_treated  <- sum(rowSums(setup$W) > 0)
    n_donors   <- setup$N0
    n_pre      <- setup$T0
    cat(sprintf("treated=%d, donors=%d, T_pre=%d\n", n_treated, n_donors, n_pre))

    tryCatch({
      ## v0.0.9 API: synthdid_estimate(Y, N0, T0) — no W argument.
      ## panel.matrices already orders Y so rows 1:N0 are controls, cols 1:T0 pre-treatment.
      est <- synthdid_estimate(setup$Y, setup$N0, setup$T0)
      ## Bootstrap SE (n=500, unit-level)
      se_val  <- sqrt(vcov(est, method = "bootstrap", replications = 500))
      att_val <- as.numeric(est)
      pv      <- 2 * pnorm(-abs(att_val / se_val))
      cohort_ests[[as.character(g)]] <- list(
        att = att_val, se = se_val, pv = pv,
        est_obj = est, n_treated = n_treated
      )
      sig <- ifelse(pv < 0.01, "***", ifelse(pv < 0.05, "**", ifelse(pv < 0.10, "*", "")))
      cat(sprintf("    ATT = %.2f  SE = %.2f  p = %.3f %s\n", att_val, se_val, pv, sig))
    }, error = function(e) {
      cat(sprintf("    ERROR: %s\n", conditionMessage(e)))
    })
  }

  ## Pool cohort estimates with cohort-size weights
  valid_g <- intersect(names(cohort_ests), names(n_g))
  if (length(valid_g) >= 1) {
    ws    <- n_g[valid_g] / sum(n_g[valid_g])
    atts  <- sapply(valid_g, function(g) cohort_ests[[g]]$att)
    ses   <- sapply(valid_g, function(g) cohort_ests[[g]]$se)
    ## Pooled ATT = weighted average; pooled SE = sqrt(sum(w^2 * se^2))
    att_p <- sum(ws * atts)
    se_p  <- sqrt(sum(ws^2 * ses^2))
    pv_p  <- 2 * pnorm(-abs(att_p / se_p))
    synthdid_results[[y]] <- list(
      att = att_p, se = se_p, pv = pv_p,
      cohort_ests = cohort_ests
    )
    sig <- ifelse(pv_p < 0.01, "***", ifelse(pv_p < 0.05, "**", ifelse(pv_p < 0.10, "*", "")))
    cat(sprintf("  Pooled ATT: %.2f  SE: %.2f  p: %.3f %s\n", att_p, se_p, pv_p, sig))
  }
}

## ── Summary table ─────────────────────────────────────────────────────────────

rows <- lapply(names(synthdid_results), function(y) {
  r   <- synthdid_results[[y]]
  att <- r$att; se_ <- r$se; pv <- r$pv
  data.frame(
    outcome  = y,
    att      = round(att, 1),
    se       = round(se_, 1),
    ci_lo    = round(att - qnorm(0.975) * se_, 1),
    ci_hi    = round(att + qnorm(0.975) * se_, 1),
    p_value  = round(pv, 3),
    signif   = ifelse(pv < 0.01, "***", ifelse(pv < 0.05, "**", ifelse(pv < 0.10, "*", ""))),
    stringsAsFactors = FALSE
  )
})
sdid_tbl <- do.call(rbind, rows)
write.csv(sdid_tbl, file.path(TOUT, "synthdid_table.csv"), row.names = FALSE)

cat("\n=== Synthetic DiD ATT ===\n")
cat(sprintf("%-22s  %8s  %7s  %14s  %7s  %5s\n",
            "Outcome", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
cat(paste(rep("-", 78), collapse = ""), "\n")
for (i in seq_len(nrow(sdid_tbl))) {
  r <- sdid_tbl[i, ]
  cat(sprintf("%-22s  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
              r$outcome, r$att, r$se, r$ci_lo, r$ci_hi, r$p_value, r$signif))
}
cat(paste(rep("-", 78), collapse = ""), "\n")
cat("Note: synthdid (Arkhangelsky et al. 2021); bootstrap SE (n=500).\n")
cat("      Pooled across cohorts g=2017, g=2022 with cohort-size weights.\n\n")

writeLines(capture.output({
  cat("Synthetic DiD ATT — Wildfire Finance\n")
  cat("Estimator: Arkhangelsky et al. (2021); bootstrap SE replications=500\n")
  cat("Staggered: cohort-specific estimates pooled with cohort-size weights\n\n")
  cat(sprintf("%-22s  %8s  %7s  %14s  %7s  %5s\n",
              "Outcome", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
  cat(paste(rep("-", 78), collapse = ""), "\n")
  for (i in seq_len(nrow(sdid_tbl))) {
    r <- sdid_tbl[i, ]
    cat(sprintf("%-22s  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
                r$outcome, r$att, r$se, r$ci_lo, r$ci_hi, r$p_value, r$signif))
  }
  cat(paste(rep("-", 78), collapse = ""), "\n")
  cat("Note: *** p<0.01 ** p<0.05 * p<0.10\n")
}), file.path(TOUT, "synthdid_table.txt"))

## ── Placebo/diagnostic plots ──────────────────────────────────────────────────

for (y in names(synthdid_results)) {
  res <- synthdid_results[[y]]
  for (g in names(res$cohort_ests)) {
    tryCatch({
      est_obj <- res$cohort_ests[[g]]$est_obj
      pdf(file.path(FOUT, sprintf("synthdid_%s_g%s.pdf", y, g)), width = 7, height = 4)
      plot(est_obj, main = sprintf("%s — g=%s cohort", gsub("_", " ", y), g))
      dev.off()
    }, error = function(e) NULL)
  }
}

cat("Output -> output/tables/synthdid_table.csv / .txt\n")
cat("Plots  -> output/figures/synthdid_*.pdf\n")
cat("Done.\n")
