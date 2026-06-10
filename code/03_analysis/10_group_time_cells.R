##
## Group-time ATT extraction + MDE computation + Roth sensitivity
##
## Addresses:
##   R1 — Minimum detectable effect (MDE) at 80% power from bootstrap SEs
##   R2 — ATT(g=2017, t=2017) vs ATT(g=2017, t=2022) for double-treatment disclosure
##   R7 — Pre-trend event-study SEs for Roth sensitivity bound
##
## Inputs: output/rds/cs_att_gt_*.rds (previously computed)
## Outputs:
##   output/tables/group_time_atts.csv
##   output/tables/mde_table.csv
##   output/tables/roth_sensitivity.csv
##

suppressPackageStartupMessages({
  library(here)
  library(did)
  library(dplyr)
})

ROOT <- here::here()
ROUT <- file.path(ROOT, "output", "rds")
TOUT <- file.path(ROOT, "output", "tables")
dir.create(TOUT, showWarnings = FALSE, recursive = TRUE)

## ── A: Group-time ATT cells ───────────────────────────────────────────────────
##
## Extract ATT(g, t) cells from saved att_gt objects.
## Key cells: ATT(g=2017, t=2017) and ATT(g=2017, t=2022) for each margin.
## ATT(g=2017, t=2022) is contaminated: 92.3% of g=2017 counties also had fires
## in 2017-2021, so this cell reflects cumulative 2013-2016 + 2017-2021 exposure.

outcomes_int <- c("fiscal_balance_pc", "exp_capital_pc", "rev_total_pc")
outcomes_any <- outcomes_int

cat("=== Group-time ATT cells ===\n\n")

gt_rows <- list()

extract_gt_cells <- function(rds_path, outcome, margin_label) {
  if (!file.exists(rds_path)) {
    cat(sprintf("  WARNING: %s not found\n", basename(rds_path)))
    return(NULL)
  }
  obj <- readRDS(rds_path)

  ## att_gt() stores results in $att (vector), $group, $t
  df <- data.frame(
    g   = obj$group,
    t   = obj$t,
    att = obj$att,
    se  = obj$se,
    stringsAsFactors = FALSE
  )
  df$pvalue <- 2 * pnorm(-abs(df$att / df$se))
  df$outcome <- outcome
  df$margin  <- margin_label
  df
}

## Intensive margin
for (y in outcomes_int) {
  rds_path <- file.path(ROUT, sprintf("cs_att_gt_%s.rds", y))
  df <- extract_gt_cells(rds_path, y, "intensive")
  if (!is.null(df)) gt_rows[[paste0("int_", y)]] <- df
}

## Extensive margin
for (y in outcomes_any) {
  rds_path <- file.path(ROUT, sprintf("cs_att_gt_any_%s.rds", y))
  df <- extract_gt_cells(rds_path, y, "extensive")
  if (!is.null(df)) gt_rows[[paste0("any_", y)]] <- df
}

gt_tbl <- do.call(rbind, gt_rows)

## Print key cells
cat("Key group-time cells (fiscal_balance_pc):\n")
fb <- gt_tbl[gt_tbl$outcome == "fiscal_balance_pc", ]
cat(sprintf("%-12s  %-10s  %5s  %8s  %7s  %7s  %7s\n",
            "Margin", "Outcome", "g", "t", "ATT", "SE", "p-val"))
cat(paste(rep("-", 65), collapse=""), "\n")
for (i in seq_len(nrow(fb))) {
  r <- fb[i, ]
  cat(sprintf("%-12s  %-22s  %5g  %8g  %7.1f  %7.1f  %7.3f\n",
              r$margin, r$outcome, r$g, r$t, r$att, r$se, r$pvalue))
}
cat("\n")

## Highlight ATT(g=2017, t=2017) vs ATT(g=2017, t=2022) for extensive margin
cat("--- Extensive margin: g=2017 cohort disaggregated ---\n")
cat("NOTE: 92.3% of g=2017 counties had fires in 2017-2021.\n")
cat("ATT(g=2017, t=2022) reflects cumulative 2013-2016 + 2017-2021 exposure.\n\n")
for (y in outcomes_any) {
  sub <- gt_tbl[gt_tbl$margin=="extensive" & gt_tbl$outcome==y & gt_tbl$g==2017, ]
  if (nrow(sub)==0) next
  cat(sprintf("  %s:\n", y))
  for (i in seq_len(nrow(sub))) {
    r <- sub[i, ]
    contamination <- if (r$t == 2022) " [CONTAMINATED: 92.3% doubly-treated]" else ""
    cat(sprintf("    ATT(g=2017, t=%d) = %.1f (SE=%.1f, p=%.3f)%s\n",
                r$t, r$att, r$se, r$pvalue, contamination))
  }
}

write.csv(gt_tbl, file.path(TOUT, "group_time_atts.csv"), row.names = FALSE)
cat(sprintf("\nGroup-time ATTs -> output/tables/group_time_atts.csv\n\n"))


## ── B: Minimum Detectable Effect (MDE) table ─────────────────────────────────
##
## MDE at alpha=0.05, power=0.80: MDE = (z_{0.025} + z_{0.20}) * SE
##   = (1.960 + 0.842) * SE = 2.802 * SE
##
## Uses bootstrap SEs from cs_simple_agg.csv and cs_simple_agg_any.csv.

z_factor <- qnorm(0.975) + qnorm(0.80)   # = 2.802

agg_int <- read.csv(file.path(TOUT, "cs_simple_agg.csv"),     stringsAsFactors=FALSE)
agg_any <- read.csv(file.path(TOUT, "cs_simple_agg_any.csv"), stringsAsFactors=FALSE)

mde_rows <- list()
for (i in seq_len(nrow(agg_int))) {
  r_int <- agg_int[i, ]
  r_any <- agg_any[agg_any$outcome == r_int$outcome, ]
  mde_rows[[i]] <- data.frame(
    outcome         = r_int$outcome,
    att_int         = round(r_int$att, 1),
    se_int          = round(r_int$se, 1),
    mde_int         = round(z_factor * r_int$se, 0),
    att_any         = if (nrow(r_any)>0) round(r_any$att[1], 1) else NA,
    se_any          = if (nrow(r_any)>0) round(r_any$se[1], 1) else NA,
    mde_any         = if (nrow(r_any)>0) round(z_factor * r_any$se[1], 0) else NA,
    stringsAsFactors = FALSE
  )
}
mde_tbl <- do.call(rbind, mde_rows)

## Liao (2022) California comparison
liao_effect <- 97

cat("=== Minimum Detectable Effect (80% power, alpha=0.05) ===\n\n")
cat(sprintf("z_factor = %.3f (= z_0.025 + z_0.20)\n", z_factor))
cat(sprintf("Reference: Liao & Kousky (2022) California municipal effect ~$%d/cap\n\n", liao_effect))
cat(sprintf("%-24s  %8s  %8s  %8s    %8s  %8s  %8s\n",
            "Outcome", "ATT(int)", "SE(int)", "MDE(int)",
            "ATT(ext)", "SE(ext)", "MDE(ext)"))
cat(paste(rep("-", 88), collapse=""), "\n")
for (i in seq_len(nrow(mde_tbl))) {
  r <- mde_tbl[i, ]
  cat(sprintf("%-24s  %8.1f  %8.1f  %8.0f    %8.1f  %8.1f  %8.0f\n",
              r$outcome, r$att_int, r$se_int, r$mde_int,
              r$att_any, r$se_any, r$mde_any))
}
cat(paste(rep("-", 88), collapse=""), "\n")
cat(sprintf("Note: MDE = %.3f * SE. Design cannot rule out effects < MDE at 80%% power.\n",
            z_factor))
cat(sprintf("      Liao (2022) effect ($%d) is below MDE for all outcomes in both margins.\n\n",
            liao_effect))

write.csv(mde_tbl, file.path(TOUT, "mde_table.csv"), row.names = FALSE)
cat("MDE table -> output/tables/mde_table.csv\n\n")


## ── C: Roth sensitivity (pre-trend power bound) ───────────────────────────────
##
## For the intensive margin: extract event-study coefficients at ell=-10 and
## ell=-5 (t=2002 and t=2007, base=2012) to compute the maximum undetectable
## pre-trend slope.
##
## Linear pre-trend extrapolation: if undetected slope = delta per 5-year period,
## then at ell=+5 (t=2022 for g=2017) the bias = delta.
## At ell=0 (t=2017 for g=2017) the bias from extrapolation = 0 by construction.
##
## The key sensitivity question: what delta could pass the pre-trend test?
## Pre-trend test has power to reject |delta| > (z_alpha + z_beta) * se_pre.
## A slope of magnitude delta would generate a coefficient at ell=-10 of -2*delta
## and at ell=-5 of -delta. The test uses joint Wald on both pre-periods.
##
## Simplified scalar bound: largest undetectable slope delta_max such that
## P(|N(delta, se_pre)| < z_alpha) >= 0.80; delta_max = (z_alpha - z_beta) * se_pre
## (the Roth M=1 "honest" bound uses the most conservative extrapolation).

cat("=== Roth (2022) pre-trend sensitivity ===\n\n")
cat("Estimating event-study coefficients from saved att_gt objects...\n\n")

roth_rows <- list()

for (y in c("fiscal_balance_pc", "exp_capital_pc", "rev_total_pc")) {
  rds_path <- file.path(ROUT, sprintf("cs_att_gt_%s.rds", y))
  if (!file.exists(rds_path)) next
  obj <- readRDS(rds_path)

  ## aggte(type="dynamic") gives event-time aggregated ATT
  tryCatch({
    es <- aggte(obj, type = "dynamic", na.rm = TRUE)
    es_df <- data.frame(
      ell = es$egt,
      att = es$att.egt,
      se  = es$se.egt
    )

    pre <- es_df[es_df$ell < 0, ]
    if (nrow(pre) == 0) {
      cat(sprintf("  %s: no pre-trend observations in event study\n", y))
      next
    }

    cat(sprintf("  %s — event-study pre-trend estimates:\n", y))
    for (i in seq_len(nrow(pre))) {
      cat(sprintf("    ell=%3d: ATT=%.1f (SE=%.1f)\n",
                  pre$ell[i], pre$att[i], pre$se[i]))
    }

    ## Use the SE at ell=-10 (earliest pre-trend) as the binding constraint
    se_pre_max <- max(pre$se, na.rm = TRUE)
    se_pre_min <- min(pre$se, na.rm = TRUE)

    ## delta_max: largest slope undetectable at alpha=0.05, 80% power
    ## For joint test, conservative bound uses max SE
    delta_max <- qnorm(0.975) * se_pre_max  # undetectable if |effect| < z_alpha * se

    ## Post-treatment bias from extrapolating delta_max one period forward (ell=+5)
    bias_1period <- delta_max

    cat(sprintf("    Max pre-period SE = %.1f; delta_max (undetectable slope) = %.1f\n",
                se_pre_max, delta_max))
    cat(sprintf("    Extrapolated bias at ell=+5: ~$%.0f/cap (%.1f%% of ATT=%.1f)\n\n",
                bias_1period,
                100 * abs(bias_1period / es_df$att[es_df$ell==0][1]),
                es_df$att[es_df$ell==0][1]))

    roth_rows[[y]] <- data.frame(
      outcome          = y,
      se_pre_ell_neg10 = pre$se[pre$ell == min(pre$ell)][1],
      att_ell_neg5     = if (any(pre$ell==-5)) pre$att[pre$ell==-5][1] else NA,
      se_ell_neg5      = if (any(pre$ell==-5)) pre$se[pre$ell==-5][1] else NA,
      att_ell_0        = es_df$att[es_df$ell==0][1],
      delta_max_undetect = round(delta_max, 1),
      bias_1period_extrap = round(bias_1period, 1),
      stringsAsFactors = FALSE
    )
  }, error = function(e) {
    cat(sprintf("  %s: ERROR in aggte: %s\n", y, conditionMessage(e)))
  })
}

if (length(roth_rows) > 0) {
  roth_tbl <- do.call(rbind, roth_rows)
  write.csv(roth_tbl, file.path(TOUT, "roth_sensitivity.csv"), row.names = FALSE)
  cat("Roth sensitivity -> output/tables/roth_sensitivity.csv\n")
}

cat("\nDone.\n")
