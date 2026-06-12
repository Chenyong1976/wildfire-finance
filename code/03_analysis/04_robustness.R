##
## Robustness checks — wildfire finance project.
## All specs use C&S DR estimator, bstrap=999, clustered by county.
## Headline outcomes: fiscal_balance_pc, rev_total_pc, exp_capital_pc.
##
## Specs:
##   (0) Baseline      — never-treated controls, WFP 2012 xformla      [main result]
##   (1) NYT           — not-yet-treated controls (adds g=2022 as controls for g=2017)
##   (2) No outliers   — drop flag_rev_total_pc == 1
##   (3) Western only  — restrict to 11 western states (AZ,CA,CO,ID,MT,NV,NM,OR,UT,WA,WY)
##   (4) WHP2014       — WHP 2014 in xformla (NOT predetermined for 2013-2014 fires)
##   (5) Excl. CA      — remove all California counties (~22% of treated)
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
overall_share65 <- median(panel$share_65plus, na.rm = TRUE)
overall_popdns  <- median(panel$pop_density,  na.rm = TRUE)

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
      TRUE                   ~ overall_share65
    ),
    log_pop_dens     = log(case_when(
      !is.na(pop_density)  ~ pop_density,
      !is.na(state_popdns) ~ state_popdns,
      TRUE                 ~ overall_popdns
    ) + 1),
    log_hhinc        = log(pmax(median_hhinc, 1)),
    fips_int         = as.integer(fips),
    g                = ifelse(g == 0, Inf, g),      # did v2.x: 0 → Inf for never-treated
    g_any            = ifelse(g_any == 0, Inf, g_any)
  )

## ── Specification list ────────────────────────────────────────────────────────

## xformla variants
xf_base <- ~ whp_2012 + pre2013_fire + pre2013_log_acres + rucc_2013 +
               log_hhinc + poverty_rate + share_65plus_imp + log_pop_dens

xf_whp14 <- ~ whp_2014 + pre2013_fire + pre2013_log_acres + rucc_2013 +
               log_hhinc + poverty_rate + share_65plus_imp + log_pop_dens

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
  list(label = "(3) Western states only",
       data_filter   = function(d) {
         ## Restrict to 11 western states (core wildfire region). Tests whether
         ## including eastern US fires — a different geographic/ecological regime —
         ## changes the results.
         WEST <- c("04","06","08","16","30","32","35","41","49","53","56")
         filter(d, state %in% WEST)
       },
       control_group = "nevertreated",
       xformla       = xf_base),
  list(label = "(4) WHP 2014 xformla",
       data_filter   = function(d) d,
       control_group = "nevertreated",
       xformla       = xf_whp14),
  list(label = "(5) Excl. California",
       data_filter   = function(d) {
         ## Remove all California counties (FIPS 06xxx). Tests whether results
         ## are driven by the large CA high-severity fire share (~21% of treated).
         filter(d, !startsWith(fips, "06"))
       },
       control_group = "nevertreated",
       xformla       = xf_base)
)

outcomes <- c("fiscal_balance_pc", "rev_total_pc", "exp_capital_pc")

## ── Margins to run ────────────────────────────────────────────────────────────
## Intensive: gname = "g"     (first high-severity MTBS fire; n_treated ~ 384)
## Extensive: gname = "g_any" (first any-qualifying MTBS fire; n_treated ~ 884)

margins <- list(
  list(label = "intensive", gname = "g"),
  list(label = "extensive", gname = "g_any")
)

## ── Run all specs × outcomes × margins ───────────────────────────────────────

run_spec <- function(spec, y, data, gname) {
  tryCatch({
    dat <- spec$data_filter(data)

    fit <- att_gt(
      yname         = y,
      tname         = "year_cog",
      idname        = "fips_int",
      gname         = gname,
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
    g_vec <- dat[[gname]]
    list(att = att, se = se, pv = pv,
         ci_lo = att - qnorm(0.975) * se,
         ci_hi = att + qnorm(0.975) * se,
         n_units = length(unique(dat$fips_int[is.finite(g_vec)])),
         n_ctrl  = length(unique(dat$fips_int[!is.finite(g_vec)])))
  }, error = function(e) {
    list(att = NA, se = NA, pv = NA, ci_lo = NA, ci_hi = NA,
         n_units = NA, n_ctrl = NA, err = conditionMessage(e))
  })
}

rows <- list()
for (m in margins) {
  cat(sprintf("\n\n══════════════════════════════════════════════════\n"))
  cat(sprintf("MARGIN: %s (gname = %s)\n", toupper(m$label), m$gname))
  cat(sprintf("══════════════════════════════════════════════════\n"))
  for (y in outcomes) {
    cat(sprintf("\n=== %s ===\n", y))
    for (s in specs) {
      cat(sprintf("  %s ... ", s$label))
      res <- run_spec(s, y, panel, m$gname)
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
        margin  = m$label,
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
}

rob_tbl <- do.call(rbind, rows)
write.csv(rob_tbl, file.path(TOUT, "robustness_table.csv"), row.names = FALSE)

## Split for convenience
rob_int <- rob_tbl[rob_tbl$margin == "intensive", ]
rob_ext <- rob_tbl[rob_tbl$margin == "extensive", ]
write.csv(rob_int, file.path(TOUT, "robustness_intensive.csv"), row.names = FALSE)
write.csv(rob_ext, file.path(TOUT, "robustness_extensive.csv"), row.names = FALSE)

## ── Formatted robustness tables ───────────────────────────────────────────────

print_margin_table <- function(tbl, margin_label) {
  cat(sprintf("\n\n══════ %s ══════\n", toupper(margin_label)))
  cat("Robustness Table: C&S Simple ATT across specifications\n")
  cat("Outcomes: fiscal_balance_pc, rev_total_pc, exp_capital_pc\n\n")
  for (y in outcomes) {
    yt <- tbl[tbl$outcome == y, ]
    cat(sprintf("Outcome: %s\n", y))
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
}

print_margin_table(rob_int, "INTENSIVE MARGIN (high-severity fire, n_treated~384)")
print_margin_table(rob_ext, "EXTENSIVE MARGIN (any qualifying fire, n_treated~884)")

## Save formatted table
txt_lines <- capture.output({
  print_margin_table(rob_int, "INTENSIVE MARGIN (high-severity fire, n_treated~384)")
  print_margin_table(rob_ext, "EXTENSIVE MARGIN (any qualifying fire, n_treated~884)")
  cat("Note: DR estimator, bootstrap SE (n=999). *** p<0.01 ** p<0.05 * p<0.10\n")
  cat("National sample (lower-48). Smoke buffer (100 km) not applied: fiscal\n")
  cat("transmission (property assessment, debt) is geographically localised.\n")
})
writeLines(txt_lines, file.path(TOUT, "robustness_table.txt"))

cat(sprintf("\nRobustness table -> output/tables/robustness_table.txt\n"))
cat(sprintf("Intensive CSV    -> output/tables/robustness_intensive.csv\n"))
cat(sprintf("Extensive CSV    -> output/tables/robustness_extensive.csv\n"))
cat(sprintf("Combined CSV     -> output/tables/robustness_table.csv\n"))
cat("\nDone. Next: 05_sun_abraham.R\n")
