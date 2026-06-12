##
## Assessment-cycle subgroup robustness.
##
## Addresses the property tax lag threat (§3.3): property tax revenues
## respond to assessed value changes, but assessment cycles vary — annual
## in CA, OR, WA vs. biennial or longer elsewhere. If the wildfire-property
## tax channel operates through assessed values, the effect should appear
## earlier (or be better captured within the 5-year CoG gap) in annual-
## reassessment states.
##
## Subgroups:
##   (A) Annual reassessment states:  CA (06), OR (41), WA (53)
##   (B) Multi-year cycle states: all others in lower-48
##
## Intensive-margin treatment only. Focus outcomes: property tax revenue
## (primary mechanism) plus fiscal balance and capital outlays.
##
## Outputs:
##   output/tables/assessment_cycle.csv / .txt
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

## Annual reassessment state FIPS
ANNUAL_STATES <- c("06", "41", "53")  # CA, OR, WA

## ── Load panel ─────────────────────────────────────────────────────────────────

panel <- read.csv(file.path(DATA, "panel_final.csv"), stringsAsFactors = FALSE)
panel$fips      <- sprintf("%05d", as.integer(panel$fips))
panel$state_fips <- substr(panel$fips, 1, 2)

## Annual reassessment indicator
panel$annual_assess <- as.integer(panel$state_fips %in% ANNUAL_STATES)

cat("Assessment cycle coverage (year_cog = 2012):\n")
base12 <- panel[panel$year_cog == 2012, ]
cat(sprintf("  Annual reassessment (CA/OR/WA): %d counties\n",
            sum(base12$annual_assess == 1, na.rm = TRUE)))
cat(sprintf("  Multi-year cycle:               %d counties\n",
            sum(base12$annual_assess == 0, na.rm = TRUE)))
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
      !is.na(share_65plus)  ~ share_65plus,
      !is.na(state_share65) ~ state_share65,
      TRUE                  ~ median(share_65plus, na.rm = TRUE)
    ),
    log_pop_dens = log(case_when(
      !is.na(pop_density)  ~ pop_density,
      !is.na(state_popdns) ~ state_popdns,
      TRUE                 ~ median(pop_density, na.rm = TRUE)
    ) + 1),
    log_hhinc = log(pmax(median_hhinc, 1)),
    fips_int  = as.integer(fips)
  )

## did v2.x: never-treated = Inf
panel <- panel |>
  mutate(g     = ifelse(g     == 0, Inf, g),
         g_any = ifelse(g_any == 0, Inf, g_any))

## ── Covariate formula ─────────────────────────────────────────────────────────

xf <- ~ whp_2012 + pre2013_fire + pre2013_log_acres + rucc_2013 +
         log_hhinc + poverty_rate + share_65plus_imp + log_pop_dens

## ── Outcomes ──────────────────────────────────────────────────────────────────

outcomes <- c("fiscal_balance_pc", "rev_total_pc", "rev_proptax_pc", "exp_capital_pc")

outcome_labels <- c(
  fiscal_balance_pc = "Fiscal balance p.c.",
  rev_total_pc      = "Total revenue p.c.",
  rev_proptax_pc    = "Property tax rev. p.c.",
  exp_capital_pc    = "Capital outlays p.c."
)

## ── Subgroup function ─────────────────────────────────────────────────────────

run_subgroup <- function(data, label, y, gname = "g") {
  g_vec <- data[[gname]][data$year_cog == 2012]
  n_trt <- sum(is.finite(g_vec) & g_vec > 0, na.rm = TRUE)
  n_ctl <- sum(is.infinite(g_vec), na.rm = TRUE)
  cat(sprintf("    %s [%s]: treated=%d, ctrl=%d\n", label, gname, n_trt, n_ctl))
  if (n_trt < 5 || n_ctl < 5) {
    cat("    Skipped (insufficient sample)\n"); return(NULL)
  }
  tryCatch({
    fit <- att_gt(
      yname         = y,
      tname         = "year_cog",
      idname        = "fips_int",
      gname         = gname,
      xformla       = xf,
      data          = as.data.frame(data),
      control_group = "nevertreated",
      est_method    = "dr",
      base_period   = "varying",
      clustervars   = "fips_int",
      print_details = FALSE
    )
    agg <- aggte(fit, type = "simple", na.rm = TRUE)
    list(att   = round(agg$overall.att, 1),
         se    = round(agg$overall.se,  1),
         pv    = 2 * pnorm(-abs(agg$overall.att / agg$overall.se)),
         n_trt = n_trt, n_ctl = n_ctl)
  }, error = function(e) {
    cat(sprintf("    ERROR: %s\n", conditionMessage(e))); NULL
  })
}

## ── Run both margins ──────────────────────────────────────────────────────────

margins_ac <- list(
  list(label = "intensive", gname = "g"),
  list(label = "extensive", gname = "g_any")
)

results <- list()

for (m in margins_ac) {
  cat(sprintf("\n\n══ MARGIN: %s (gname=%s) ══\n", toupper(m$label), m$gname))
  for (y in outcomes) {
    cat(sprintf("\n=== %s ===\n", y))
    annual <- run_subgroup(panel[panel$annual_assess == 1, ],
                           "Annual (CA/OR/WA)", y, m$gname)
    multi  <- run_subgroup(panel[panel$annual_assess == 0, ],
                           "Multi-year cycle",  y, m$gname)

    for (nm in c("annual", "multi_year")) {
      r <- if (nm == "annual") annual else multi
      if (!is.null(r)) {
        sig <- ifelse(r$pv < 0.01, "***",
                 ifelse(r$pv < 0.05, "**",
                   ifelse(r$pv < 0.10, "*", "")))
        cat(sprintf("  %s: ATT=%.1f  SE=%.1f  p=%.3f %s\n",
                    nm, r$att, r$se, r$pv, sig))
        results[[paste(m$label, y, nm, sep = "_")]] <- data.frame(
          margin   = m$label,
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
}

if (length(results) == 0) stop("No results produced.")

out_tbl <- do.call(rbind, results)
write.csv(out_tbl, file.path(TOUT, "assessment_cycle.csv"), row.names = FALSE)

## ── Print ─────────────────────────────────────────────────────────────────────

cat("\n\n=== Assessment Cycle Subgroup Results ===\n\n")
cat(sprintf("%-26s  %-12s  %8s  %7s  %14s  %7s  %5s\n",
            "Outcome", "Subgroup", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
cat(paste(rep("-", 90), collapse = ""), "\n")
for (i in seq_len(nrow(out_tbl))) {
  r <- out_tbl[i, ]
  cat(sprintf("%-26s  %-12s  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
              r$outcome, r$subgroup, r$att, r$se, r$ci_lo, r$ci_hi,
              r$p_value, r$signif))
}
cat(paste(rep("-", 90), collapse = ""), "\n")

writeLines(capture.output({
  cat("Assessment-Cycle Subgroup Analysis\n")
  cat("C&S doubly-robust ATT (intensive margin)\n\n")
  cat(sprintf("%-26s  %-12s  %8s  %7s  %14s  %7s  %5s\n",
              "Outcome", "Subgroup", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
  cat(paste(rep("-", 90), collapse = ""), "\n")
  for (i in seq_len(nrow(out_tbl))) {
    r <- out_tbl[i, ]
    cat(sprintf("%-26s  %-12s  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
                r$outcome, r$subgroup, r$att, r$se, r$ci_lo, r$ci_hi,
                r$p_value, r$signif))
  }
  cat(paste(rep("-", 90), collapse = ""), "\n")
  cat("Note: *** p<0.01, ** p<0.05, * p<0.10.\n")
  cat("      Annual = CA (FIPS 06), OR (41), WA (53). Multi-year = all other lower-48 states.\n")
  cat("      Never-treated control group; intensive-margin treatment (high-severity fire).\n")
}), file.path(TOUT, "assessment_cycle.txt"))

cat("\nOutput -> output/tables/assessment_cycle.csv / .txt\n")
cat("Done.\n")
