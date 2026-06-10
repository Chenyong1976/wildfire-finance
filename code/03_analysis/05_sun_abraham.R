##
## Sun & Abraham (2021) heterogeneity-robust estimator via fixest::sunab().
##
## sunab() is equivalent to running a TWFE regression with cohort × relative-time
## interactions and the SA aggregation weights. It is robust to heterogeneous
## treatment effects across cohorts and time, unlike naive TWFE.
##
## Specification:
##   y_it = alpha_i + lambda_t + sum_{g,l} delta_{g,l} * 1(G_i=g) * 1(t-G_i=l) + e_it
##
## where G_i is the CoG-census cohort (2017, 2022; 0=never-treated) and l is
## event time in CoG census years. g=2017: l ∈ {-15,-10,-5,0,5} with ref.p=-5.
## g=2022: l ∈ {-20,-15,-10,-5,0}. Both cohorts contribute to shared l values.
##
## Outputs:
##   output/tables/sun_abraham_table.csv
##   output/tables/sun_abraham_table.txt
##   output/figures/sun_abraham_event_study.pdf  (headline: fiscal_balance_pc)
##

suppressPackageStartupMessages({
  library(here)
  library(fixest)
  library(dplyr)
  library(ggplot2)
})

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

## SA uses the same CoG-census-year cohort coding as C&S (g=2017, g=2022, 0=never).
panel_sa <- panel |>
  mutate(
    ## sunab() requires: never-treated G_i = 0 (NOT Inf)
    g_cog     = as.integer(g),      # intensive margin: 0/2017/2022
    g_any_cog = as.integer(g_any),  # extensive margin: 0/2017/2022
    fips_int  = as.integer(fips)
  )

cat("Sun-Abraham cohort table — INTENSIVE (g_cog):\n")
print(table(panel_sa$g_cog[panel_sa$year_cog == 2012]))
cat("\nSun-Abraham cohort table — EXTENSIVE (g_any_cog):\n")
print(table(panel_sa$g_any_cog[panel_sa$year_cog == 2012]))
cat("\n")

## ── Outcomes ──────────────────────────────────────────────────────────────────

outcomes <- c(
  "fiscal_balance_pc",
  "rev_total_pc",
  "rev_proptax_pc",
  "exp_capital_pc"
)

## ── Run sunab() for each outcome ──────────────────────────────────────────────

sa_results <- list()

sa_extract <- function(fit) {
  ## sunab() in fixest returns SA-weighted averages by event time.
  ## Coef names: "year_cog::L" where L = event time (year_cog - G_ffy).
  ct   <- coeftable(fit)
  nms  <- rownames(ct)
  mask <- grepl("^year_cog::", nms)
  if (!any(mask)) return(NULL)
  df <- data.frame(
    name = nms[mask],
    att  = ct[mask, "Estimate"],
    se   = ct[mask, "Std. Error"],
    stringsAsFactors = FALSE
  )
  df$L <- as.numeric(sub("^year_cog::(.+)$", "\\1", df$name))
  df
}

att_simple <- function(fit) {
  ## Weighted average ATT over post-treatment cells (L >= 0).
  ## Weight by cohort size (n_g = number of treated units in cohort g).
  df   <- sa_extract(fit)
  if (is.null(df)) return(c(att=NA, se=NA, pv=NA))
  post <- df[df$L >= 0, ]
  if (nrow(post) == 0) return(c(att=NA, se=NA, pv=NA))
  ## Simple unweighted average (cohort-size weighting requires external data)
  att_bar <- mean(post$att)
  ## Conservative SE: SE of the mean (assuming independence across cells)
  se_bar  <- sqrt(mean(post$se^2))
  pv      <- 2 * pnorm(-abs(att_bar / se_bar))
  c(att = att_bar, se = se_bar, pv = pv)
}

for (y in outcomes) {
  cat(sprintf("--- %s ---\n", y))
  tryCatch({
    fit <- feols(
      as.formula(sprintf(
        "%s ~ sunab(g_cog, year_cog, ref.p = -5) | fips_int + year_cog", y
      )),
      data    = panel_sa,
      cluster = ~fips_int
    )
    sa_results[[y]] <- fit
    res <- att_simple(fit)
    cat(sprintf("  Simple ATT (post avg): %.2f  SE: %.2f  p: %.3f\n",
                res["att"], res["se"], res["pv"]))
  }, error = function(e) {
    cat(sprintf("  ERROR: %s\n", conditionMessage(e)))
  })
}

## ── Summary table ─────────────────────────────────────────────────────────────

rows <- lapply(names(sa_results), function(y) {
  fit <- sa_results[[y]]
  res <- att_simple(fit)
  att <- as.numeric(res["att"])
  se_ <- as.numeric(res["se"])
  pv  <- as.numeric(res["pv"])
  data.frame(
    outcome  = y,
    att      = round(att, 1),
    se       = round(se_, 1),
    ci_lo    = round(att - qnorm(0.975) * se_, 1),
    ci_hi    = round(att + qnorm(0.975) * se_, 1),
    p_value  = round(pv, 3),
    signif   = ifelse(pv < 0.01, "***",
                      ifelse(pv < 0.05, "**",
                             ifelse(pv < 0.10, "*", ""))),
    stringsAsFactors = FALSE
  )
})
sa_tbl <- do.call(rbind, rows)
write.csv(sa_tbl, file.path(TOUT, "sun_abraham_table.csv"), row.names = FALSE)

cat("\n=== Sun-Abraham ATT (heterogeneity-robust TWFE) ===\n")
cat(sprintf("%-22s  %8s  %7s  %14s  %7s  %5s\n",
            "Outcome", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
cat(paste(rep("-", 78), collapse = ""), "\n")
for (i in seq_len(nrow(sa_tbl))) {
  r <- sa_tbl[i, ]
  cat(sprintf("%-22s  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
              r$outcome, r$att, r$se, r$ci_lo, r$ci_hi, r$p_value, r$signif))
}
cat(paste(rep("-", 78), collapse = ""), "\n")
cat("Note: sunab() via fixest; county and year FE; clustered SE. *** p<0.01\n\n")

writeLines(capture.output({
  cat("Sun & Abraham (2021) Estimator — Heterogeneity-Robust TWFE\n")
  cat("  Formula: y ~ sunab(g_cog, year_cog) | county FE + year FE\n")
  cat("  g_cog = CoG-census cohort (0=never, 2017, 2022)\n")
  cat("  ref.p = -5 (l=-5 is base period for g=2017 cohort)\n\n")
  cat(sprintf("%-22s  %8s  %7s  %14s  %7s  %5s\n",
              "Outcome", "ATT ($)", "SE", "95% CI", "p-val", "Sig"))
  cat(paste(rep("-", 78), collapse = ""), "\n")
  for (i in seq_len(nrow(sa_tbl))) {
    r <- sa_tbl[i, ]
    cat(sprintf("%-22s  %8.1f  %7.1f  [%6.1f, %6.1f]  %7.3f  %5s\n",
                r$outcome, r$att, r$se, r$ci_lo, r$ci_hi, r$p_value, r$signif))
  }
  cat(paste(rep("-", 78), collapse = ""), "\n")
  cat("Note: clustered SE by county. *** p<0.01 ** p<0.05 * p<0.10\n")
}), file.path(TOUT, "sun_abraham_table.txt"))

## ── Event study plot for headline outcome ─────────────────────────────────────

y_headline <- "fiscal_balance_pc"
if (y_headline %in% names(sa_results)) {
  fit_h  <- sa_results[[y_headline]]
  iplot_data <- tryCatch({
    ## Extract sunab coefficients and CIs (relative-time l = year_cog - G_ffy)
    cf   <- coef(fit_h)
    ci   <- confint(fit_h, level = 0.95)
    nms  <- names(cf)
    ## sunab coefs named as "year_cog::l:cohort" — extract l
    is_sa <- grepl("^year_cog::", nms)
    sa_cf <- cf[is_sa]
    sa_ci <- ci[is_sa, ]
    ## aggregate by event time (average across cohorts, SA-weighted — done by iplot)
    NULL
  }, error = function(e) NULL)

  tryCatch({
    pdf(file.path(FOUT, "sun_abraham_event_study.pdf"), width = 8, height = 4)
    iplot(fit_h,
          main  = "Sun-Abraham Event Study: Fiscal Balance p.c.",
          xlab  = "CoG census year",
          ylab  = "Fiscal Balance p.c. (2019$)",
          ci_level = 0.95)
    abline(v = 2012.5, lty = 2, col = "grey50")
    abline(h = 0, col = "grey50", lwd = 0.5)
    dev.off()
    cat(sprintf("Event study -> output/figures/sun_abraham_event_study.pdf\n"))
  }, error = function(e) {
    cat(sprintf("Event study plot error: %s\n", conditionMessage(e)))
  })
}

cat("\nDone.\n")
