##
## Heterogeneity analysis: disaggregate by actual first-fire year.
##
## Main analysis uses g = CoG census year (2017 or 2022), which pools
## all 2013-2016 fires and all 2017-2021 fires. Here we set
## g = actual first-fire year (2013, 2014, ..., 2021) from MTBS.
##
## National sample: ~2,634 never-treated controls; cohort sizes vary.
##   - Reliable: 2013 (n=90), 2015 (n=43), 2014 (n=38), 2016 (n=37)
##   - Thin:     2017 (n=31), 2018 (n=29)
##   - Drop:     2019 (n=5), 2021 (n=6), 2020 (n=14) — too small for DR
##
## Outcomes: headline fiscal outcomes only (fiscal_balance_pc, rev_total_pc,
##           rev_proptax_pc, exp_capital_pc).
##
## Time variable: year_cog (2002, 2007, 2012, 2017, 2022).
## Post-treatment cells (g, t) where t >= g and t is the CoG census year
## that follows each fire year:
##   g=2013: post at t=2017 (+4yr), t=2022 (+9yr)
##   g=2015: post at t=2017 (+2yr), t=2022 (+7yr)
##   g=2018: post at t=2022 (+4yr)
##

suppressPackageStartupMessages({
  library(here)
  library(did)
  library(dplyr)
  library(ggplot2)
})
set.seed(42)

ROOT <- here::here()
DATA <- file.path(ROOT, "data", "processed")
TOUT <- file.path(ROOT, "output", "tables")
FOUT <- file.path(ROOT, "output", "figures")
ROUT <- file.path(ROOT, "output", "rds")
dir.create(TOUT, showWarnings = FALSE, recursive = TRUE)
dir.create(FOUT, showWarnings = FALSE, recursive = TRUE)

## ── Build first-fire-year panel ───────────────────────────────────────────────

## Load main panel (fiscal + covariate data)
panel <- read.csv(file.path(DATA, "panel_final.csv"), stringsAsFactors = FALSE)
panel$fips <- sprintf("%05d", as.integer(panel$fips))

## Load MTBS county parquet via CSV workaround
## (mtbs_county.parquet has annual fire data with fire_in_year and g variables)
mtbs_file <- file.path(DATA, "mtbs_county_ffy.csv")

if (!file.exists(mtbs_file)) {
  ## Extract first fire year from parquet using Python — write intermediate CSV
  py_cmd <- paste0(
    "import pandas as pd; ",
    "m = pd.read_parquet('", file.path(DATA, "mtbs_county.parquet"), "'); ",
    "ffy = m[(m['g']>0)&(m['fire_in_year']==1)&(m['year']>=2013)]",
    "  .groupby('fips')['year'].min().reset_index(); ",
    "ffy.columns=['fips','first_fire_year']; ",
    "ffy['fips'] = ffy['fips'].astype(str).str.zfill(5); ",
    "ffy.to_csv('", mtbs_file, "', index=False)"
  )
  system2("python", args = c("-c", shQuote(py_cmd)))
}

ffy <- read.csv(mtbs_file, stringsAsFactors = FALSE)
ffy$fips <- sprintf("%05d", as.integer(ffy$fips))

## Merge actual fire year into panel; never-treated counties get g_ffy = Inf
panel_ffy <- panel |>
  left_join(ffy, by = "fips") |>
  mutate(
    g_ffy = case_when(
      is.na(first_fire_year) ~ Inf,   # never-treated
      TRUE                   ~ as.numeric(first_fire_year)
    )
  )

## ── Covariate prep (same as main analysis) ────────────────────────────────────

overall_share65 <- median(panel_ffy$share_65plus, na.rm = TRUE)
overall_popdns  <- median(panel_ffy$pop_density,  na.rm = TRUE)

panel_ffy <- panel_ffy |>
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
    log_pop_dens = log(case_when(
      !is.na(pop_density)  ~ pop_density,
      !is.na(state_popdns) ~ state_popdns,
      TRUE                 ~ overall_popdns
    ) + 1),
    log_hhinc    = log(pmax(median_hhinc, 1)),
    fips_int     = as.integer(fips)
  )

if (!"rev_intergovt_pc" %in% names(panel_ffy))
  panel_ffy$rev_intergovt_pc <- panel_ffy$rev_igt_federal_pc + panel_ffy$rev_igt_state_pc

## Print cohort sizes
cohorts <- panel_ffy |>
  filter(year_cog == 2012, is.finite(g_ffy)) |>
  count(g_ffy) |>
  arrange(g_ffy)
cat("Cohort sizes by actual first-fire year:\n")
print(cohorts)
cat(sprintf("Never-treated: %d\n\n",
            sum(panel_ffy$year_cog == 2012 & !is.finite(panel_ffy$g_ffy))))

## Drop cohorts too small for reliable DR estimation (< 20 counties)
small_cohorts <- cohorts$g_ffy[cohorts$n < 20]
if (length(small_cohorts) > 0) {
  cat(sprintf("Dropping cohorts with n < 20: %s\n\n",
              paste(small_cohorts, collapse = ", ")))
  panel_ffy <- panel_ffy |>
    filter(!g_ffy %in% small_cohorts)
}

## ── att_gt with actual fire year as g ────────────────────────────────────────

xf <- ~ whp_2012 + pre2013_fire + pre2013_log_acres + rucc_2013 +
         log_hhinc + poverty_rate + share_65plus_imp + log_pop_dens

outcomes <- c("fiscal_balance_pc", "rev_total_pc",
              "rev_proptax_pc", "exp_capital_pc")

ffy_results <- list()

for (y in outcomes) {
  cat(sprintf("--- %s ---\n", y))
  tryCatch({
    fit <- att_gt(
      yname         = y,
      tname         = "year_cog",
      idname        = "fips_int",
      gname         = "g_ffy",
      xformla       = xf,
      data          = panel_ffy,
      control_group = "nevertreated",
      est_method    = "dr",
      base_period   = "varying",
      anticipation  = 0,
      bstrap        = TRUE,
      biters        = 999,
      clustervars   = "fips_int",
      print_details = FALSE
    )
    ffy_results[[y]] <- fit
    saveRDS(fit, file.path(ROUT, sprintf("cs_ffy_att_gt_%s.rds", y)))

    ag_g <- aggte(fit, type = "group")
    cat("  Group effects:\n")
    gdf <- data.frame(
      g       = ag_g$egt,
      att     = round(ag_g$att.egt, 1),
      se      = round(ag_g$se.egt, 1),
      p_value = round(2 * pnorm(-abs(ag_g$att.egt / ag_g$se.egt)), 3)
    ) |> mutate(signif = ifelse(p_value < 0.01, "***",
                                ifelse(p_value < 0.05, "**",
                                       ifelse(p_value < 0.10, "*", ""))))
    print(gdf)
    cat("\n")
  }, error = function(e) {
    cat(sprintf("  ERROR: %s\n\n", conditionMessage(e)))
  })
}

## ── Summary table ─────────────────────────────────────────────────────────────

group_rows <- lapply(names(ffy_results), function(y) {
  ag_g <- aggte(ffy_results[[y]], type = "group")
  data.frame(
    outcome  = y,
    cohort   = ag_g$egt,
    att      = round(ag_g$att.egt, 1),
    se       = round(ag_g$se.egt, 1),
    ci_lo    = round(ag_g$att.egt - qnorm(0.975) * ag_g$se.egt, 1),
    ci_hi    = round(ag_g$att.egt + qnorm(0.975) * ag_g$se.egt, 1),
    p_value  = round(2 * pnorm(-abs(ag_g$att.egt / ag_g$se.egt)), 3),
    signif   = ifelse(
      2*pnorm(-abs(ag_g$att.egt/ag_g$se.egt)) < 0.01, "***",
      ifelse(2*pnorm(-abs(ag_g$att.egt/ag_g$se.egt)) < 0.05, "**",
             ifelse(2*pnorm(-abs(ag_g$att.egt/ag_g$se.egt)) < 0.10, "*", ""))),
    stringsAsFactors = FALSE
  )
})
ffy_tbl <- do.call(rbind, group_rows)
write.csv(ffy_tbl, file.path(TOUT, "cs_ffy_group_agg.csv"), row.names = FALSE)

cat("\n=== Group ATT by Actual Fire Year ===\n")
cat(sprintf("%-22s  %6s  %8s  %7s  %14s  %7s  %5s\n",
            "Outcome", "Cohort", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
cat(paste(rep("-", 88), collapse=""), "\n")
for (i in seq_len(nrow(ffy_tbl))) {
  r <- ffy_tbl[i, ]
  cat(sprintf("%-22s  %6d  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
              r$outcome, r$cohort, r$att, r$se, r$ci_lo, r$ci_hi,
              r$p_value, r$signif))
}
cat(paste(rep("-", 88), collapse=""), "\n")
cat("Note: per capita, nominal 2019$. DR estimator. Never-treated controls.\n")
cat("      *** p<0.01 ** p<0.05 * p<0.10\n\n")

cat("Results -> output/tables/cs_ffy_group_agg.csv\n")
cat("Done.\n")
