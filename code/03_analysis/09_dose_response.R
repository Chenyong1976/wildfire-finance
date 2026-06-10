##
## Dose-response DiD extension — wildfire finance project.
##
## Dose variable: log(max_acres_cohort) = log of the largest qualifying MTBS
## fire experienced by a county within its treatment cohort window:
##   g_any=2017 counties: max fire (>=1,000 ac) in 2013-2016
##   g_any=2022 counties: max fire (>=1,000 ac) in 2017-2021
##
## Estimators:
##   (A) TWFE dose-response (primary):
##       feols(outcome ~ dose_post | fips + year_cog, cluster = ~fips)
##       where dose_post = log(max_acres_cohort) x I(year_cog >= g_any_i)
##       Coefficient: change in outcome per 1-unit increase in log(max acres),
##       post-treatment vs. pre-treatment, relative to never-treated.
##       Pre-trend check: add dose_pre interaction.
##
##   (B) C&S DR dose-bin (robustness):
##       att_gt() for low-dose counties (<=median log acres) vs. never-treated
##       att_gt() for high-dose counties (>median log acres) vs. never-treated
##       Tests whether null ATT holds across fire size distribution.
##
## Output:
##   output/tables/dose_response_twfe.csv
##   output/tables/dose_response_csbin.csv
##

suppressPackageStartupMessages({
  library(here)
  library(dplyr)
  library(fixest)
  library(did)
})
set.seed(42)

ROOT <- here::here()
DATA <- file.path(ROOT, "data", "processed")
TOUT <- file.path(ROOT, "output", "tables")
dir.create(TOUT, showWarnings = FALSE, recursive = TRUE)

## ── Load panel ────────────────────────────────────────────────────────────────

panel <- read.csv(file.path(DATA, "panel_final.csv"), stringsAsFactors = FALSE)
panel$fips <- sprintf("%05d", as.integer(panel$fips))

if (!"max_acres_cohort" %in% names(panel))
  stop("max_acres_cohort missing — run 08_dose_response_prep.py first")

if (!"rev_intergovt_pc" %in% names(panel))
  panel$rev_intergovt_pc <- panel$rev_igt_federal_pc + panel$rev_igt_state_pc

## Impute uninsurance_rate and pop_density (29 UT counties have NaN; no group median)
for (col in c("uninsurance_rate", "pop_density")) {
  if (any(is.na(panel[[col]]))) {
    overall_med <- median(panel[[col]], na.rm = TRUE)
    panel[[col]] <- ifelse(is.na(panel[[col]]), overall_med, panel[[col]])
  }
}

panel <- panel |>
  mutate(
    fips_int        = as.integer(fips),
    g_any           = ifelse(g_any == 0, Inf, g_any),
    uninsurance_imp = uninsurance_rate,
    log_pop_dens    = log(pmax(pop_density, 1)),
    log_hhinc       = log(pmax(median_hhinc, 1)),
    log_hhinc       = log(pmax(median_hhinc, 1)),
    log_max_acres   = ifelse(!is.infinite(g_any) & !is.na(max_acres_cohort),
                             log(max_acres_cohort), 0),
    ## post_treat: 1 for treated counties in post-treatment CoG years
    post_treat = as.integer(!is.infinite(g_any) & year_cog >= g_any),
    ## pre_treat: 1 for treated counties in pre-treatment CoG years
    pre_treat  = as.integer(!is.infinite(g_any) & year_cog < g_any),
    dose_post  = log_max_acres * post_treat,
    dose_pre   = log_max_acres * pre_treat
  )

outcomes <- c(
  "fiscal_balance_pc",
  "exp_capital_pc",
  "rev_total_pc",
  "rev_proptax_pc",
  "rev_intergovt_pc",
  "exp_total_pc",
  "debt_lt_pc"
)

cat("Panel dims:", nrow(panel), "obs,", length(unique(panel$fips)), "counties\n")
cat("g_any distribution (2012 cross-section):\n")
sub12 <- panel[panel$year_cog == 2012, ]
cat("  g_any=2017:", sum(sub12$g_any == 2017), "\n")
cat("  g_any=2022:", sum(sub12$g_any == 2022), "\n")
cat("  g_any=Inf :", sum(is.infinite(sub12$g_any)), "\n")
cat("Counties with max_acres_cohort:",
    sum(!is.na(panel$max_acres_cohort[panel$year_cog == 2012])), "\n\n")


## ── A: TWFE dose-response ─────────────────────────────────────────────────────

cat(sprintf("%-60s\n", paste(rep("=", 60), collapse="")))
cat("PART A: TWFE dose-response\n")
cat(sprintf("%-60s\n", paste(rep("=", 60), collapse="")))
cat(sprintf("  Sample: treated (n=%d) + never-treated (n=%d) counties\n",
            sum(!is.infinite(sub12$g_any)),
            sum(is.infinite(sub12$g_any))))
cat(sprintf("  Dose: log(max_acres_cohort); median = %.2f (%.0f acres)\n",
            median(panel$log_max_acres[panel$log_max_acres > 0]),
            exp(median(panel$log_max_acres[panel$log_max_acres > 0]))))

cat(sprintf("\n%-22s  %8s  %6s  %7s    %8s  %7s\n",
            "Outcome", "Coef", "SE", "p-val", "Pre-coef", "Pre-p"))
cat(paste(rep("-", 70), collapse=""), "\n")

twfe_rows <- list()
for (y in outcomes) {
  if (!y %in% names(panel)) next

  ## Primary specification
  f_main <- as.formula(paste0(y, " ~ dose_post | fips_int + year_cog"))
  ## Pre-trend test: year x dose event-study interactions, ref=2012.
  ## dose_pre + dose_post are collinear with unit FE (log_max_acres is
  ## time-invariant), so joint pre-trend test uses year-specific interactions.
  f_es <- as.formula(paste0(y, " ~ i(year_cog, log_max_acres, ref=2012) | fips_int + year_cog"))

  fit_main <- tryCatch(
    feols(f_main, data = panel, cluster = ~fips_int),
    error = function(e) { cat("  ERROR main", y, ":", conditionMessage(e), "\n"); NULL }
  )
  fit_es <- tryCatch(
    feols(f_es, data = panel, cluster = ~fips_int),
    error = function(e) NULL
  )
  if (is.null(fit_main)) next

  b   <- coef(fit_main)["dose_post"]
  se_ <- se(fit_main)["dose_post"]
  pv  <- pvalue(fit_main)["dose_post"]

  ## Joint Wald test on pre-treatment year x dose coefficients (2002, 2007)
  pre_names <- grep("year_cog::(2002|2007):log_max_acres", names(coef(fit_es)), value = TRUE)
  if (!is.null(fit_es) && length(pre_names) == 2) {
    wt_pre <- wald(fit_es, keep = pre_names)
    pv_pre <- wt_pre$p
  } else {
    pv_pre <- NA_real_
  }
  b_pre  <- NA_real_
  se_pre <- NA_real_

  twfe_rows[[y]] <- data.frame(
    outcome         = y,
    estimator       = "TWFE",
    coef            = round(b, 2),
    se              = round(se_, 2),
    pvalue          = round(pv, 3),
    pretrend_waldp  = round(pv_pre, 3),
    stringsAsFactors = FALSE
  )

  sig <- ifelse(pv < 0.01, "***", ifelse(pv < 0.05, "**", ifelse(pv < 0.10, "*", "")))
  pre_str <- if (!is.na(pv_pre)) sprintf("Wald p=%5.3f", pv_pre) else "Wald p=  —  "
  cat(sprintf("%-22s  %8.2f  %6.2f  %7.3f%s   %s\n",
              y, b, se_, pv, sig, pre_str))
}
cat(paste(rep("-", 70), collapse=""), "\n")
cat("Note: coef = change per 1 log-unit (2.7x) increase in max fire size.\n")
cat(sprintf("      Interquartile effect (p25->p75 log acres): %.1f x coef\n",
            diff(quantile(panel$log_max_acres[panel$log_max_acres > 0], c(0.25, 0.75)))))

twfe_tbl <- do.call(rbind, twfe_rows)
write.csv(twfe_tbl, file.path(TOUT, "dose_response_twfe.csv"), row.names = FALSE)
cat("TWFE table -> output/tables/dose_response_twfe.csv\n\n")


## ── B: C&S dose-bin ───────────────────────────────────────────────────────────

cat(sprintf("%-60s\n", paste(rep("=", 60), collapse="")))
cat("PART B: C&S dose-bin (low vs. high, median split)\n")
cat(sprintf("%-60s\n", paste(rep("=", 60), collapse="")))

xf <- ~ whp_2012 + pre2013_fire + pre2013_log_acres + rucc_2013 +
         log_hhinc + poverty_rate + uninsurance_imp + log_pop_dens

treated_sub <- panel[panel$year_cog == 2012 & !is.infinite(panel$g_any), ]
med_log <- median(log(treated_sub$max_acres_cohort), na.rm = TRUE)
cat(sprintf("Median log(max_acres): %.2f (%.0f acres)\n", med_log, exp(med_log)))

low_fips  <- treated_sub$fips[log(treated_sub$max_acres_cohort) <= med_log]
high_fips <- treated_sub$fips[log(treated_sub$max_acres_cohort) >  med_log]
never_fips <- panel$fips[is.infinite(panel$g_any)]
cat(sprintf("Low-dose counties  (<=median): %d\n", length(low_fips)))
cat(sprintf("High-dose counties (>median):  %d\n", length(high_fips)))
cat(sprintf("Never-treated controls:        %d\n\n", length(unique(never_fips))))

panel_low  <- panel[panel$fips %in% c(low_fips,  unique(never_fips)), ]
panel_high <- panel[panel$fips %in% c(high_fips, unique(never_fips)), ]

cat(sprintf("%-22s  %-10s  %8s  %7s  %7s\n",
            "Outcome", "Dose bin", "ATT ($)", "SE", "p-val"))
cat(paste(rep("-", 60), collapse=""), "\n")

cs_bin_rows <- list()
for (y in c("fiscal_balance_pc", "exp_capital_pc")) {
  if (!y %in% names(panel)) next
  for (tag in c("low", "high")) {
    sub <- if (tag == "low") panel_low else panel_high
    n_tr <- length(if (tag == "low") low_fips else high_fips)
    tryCatch({
      fit <- att_gt(
        yname          = y,
        tname          = "year_cog",
        idname         = "fips_int",
        gname          = "g_any",
        xformla        = xf,
        data           = sub,
        control_group  = "nevertreated",
        base_period    = "varying",
        est_method     = "dr",
        print_details  = FALSE
      )
      agg <- aggte(fit, type = "simple")
      att <- agg$overall.att
      se_ <- agg$overall.se
      pv  <- 2 * pnorm(-abs(att / se_))

      cs_bin_rows[[paste0(y, "_", tag)]] <- data.frame(
        outcome        = y,
        estimator      = paste0("CS_", tag, "_dose"),
        coef           = round(att, 1),
        se             = round(se_, 1),
        pvalue         = round(pv, 3),
        pretrend_waldp = NA_real_,
        stringsAsFactors = FALSE
      )
      sig <- ifelse(pv < 0.01, "***", ifelse(pv < 0.05, "**", ifelse(pv < 0.10, "*", "")))
      cat(sprintf("%-22s  %-10s  %8.1f  %7.1f  %7.3f%s  (n_treated=%d)\n",
                  y, tag, att, se_, pv, sig, n_tr))
    }, error = function(e) {
      cat(sprintf("  ERROR %s %s: %s\n", tag, y, conditionMessage(e)))
    })
  }
}
cat(paste(rep("-", 60), collapse=""), "\n")

cs_bin_tbl <- if (length(cs_bin_rows) > 0) do.call(rbind, cs_bin_rows) else NULL
if (!is.null(cs_bin_tbl))
  write.csv(cs_bin_tbl, file.path(TOUT, "dose_response_csbin.csv"), row.names = FALSE)

cat("C&S dose-bin table -> output/tables/dose_response_csbin.csv\n")
cat("Done.\n")
