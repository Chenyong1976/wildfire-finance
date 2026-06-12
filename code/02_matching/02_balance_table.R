##
## Covariate balance table — pre- and post-IPW weighting.
##
## SMD = (mean_treated − mean_control) / pooled_SD  (Cohen's d convention).
## |SMD| < 0.1 considered balanced.
##
## Outputs:
##   data/processed/balance_table.csv    machine-readable
##   output/tables/balance_table.txt     formatted for paper
##

suppressPackageStartupMessages({
  library(here)
  library(dplyr)
})

ROOT <- here::here()
DATA <- file.path(ROOT, "data", "processed")
OUT  <- file.path(ROOT, "output", "tables")
dir.create(OUT, showWarnings = FALSE, recursive = TRUE)

panel   <- read.csv(file.path(DATA, "panel_final.csv"),   stringsAsFactors = FALSE)
weights <- read.csv(file.path(DATA, "ps_weights.csv"),    stringsAsFactors = FALSE)
panel$fips   <- sprintf("%05d", as.integer(panel$fips))
weights$fips <- sprintf("%05d", as.integer(weights$fips))

base <- panel |>
  filter(year_cog == 2012) |>
  left_join(select(weights, fips, w_ipw), by = "fips") |>
  mutate(
    ever_treated     = as.integer(g > 0),
    log_pop_density  = log(ifelse(is.na(pop_density),
                                   median(pop_density, na.rm = TRUE),
                                   pop_density) + 1),
    log_hhinc        = log(median_hhinc),
    log_rev_total_pc = log(pmax(rev_total_pc, 1)),
    log_proptax_pc   = log(pmax(rev_proptax_pc, 1)),
    log_debt_lt_pc   = log(pmax(debt_lt_pc, 0) + 1)
  )

## ── SMD function ─────────────────────────────────────────────────────────────

smd <- function(x, trt, w = NULL) {
  if (is.null(w)) w <- rep(1, length(x))
  x_t <- x[trt == 1];  w_t <- w[trt == 1]
  x_c <- x[trt == 0];  w_c <- w[trt == 0]
  mu_t <- weighted.mean(x_t, w_t, na.rm = TRUE)
  mu_c <- weighted.mean(x_c, w_c, na.rm = TRUE)
  v_t  <- sum(w_t * (x_t - mu_t)^2, na.rm = TRUE) / sum(w_t)
  v_c  <- sum(w_c * (x_c - mu_c)^2, na.rm = TRUE) / sum(w_c)
  sd_pool <- sqrt((v_t + v_c) / 2)
  list(mean_t = mu_t, mean_c = mu_c, smd = (mu_t - mu_c) / sd_pool)
}

## ── Covariates and labels ─────────────────────────────────────────────────────

covs <- list(
  list(var = "whp_2012",        label = "WFP 2012 (raw)"),
  list(var = "whp_q",           label = "WFP quintile"),
  list(var = "pre2013_fire",    label = "Pre-2013 fire (0/1)"),
  list(var = "pre2013_log_acres", label = "Pre-2013 log fire acres"),
  list(var = "rucc_2013",       label = "RUCC 2013"),
  list(var = "log_hhinc",       label = "Log median HH income"),
  list(var = "poverty_rate",    label = "Poverty rate (%)"),
  list(var = "share_65plus",    label = "Share population 65+"),
  list(var = "log_pop_density", label = "Log pop density"),
  list(var = "log_rev_total_pc",label = "Log total revenue p.c."),
  list(var = "log_proptax_pc",  label = "Log property tax p.c."),
  list(var = "log_debt_lt_pc",  label = "Log LT debt p.c.")
)

trt <- base$ever_treated
w   <- base$w_ipw

rows <- lapply(covs, function(cv) {
  x  <- as.numeric(base[[cv$var]])
  un <- smd(x, trt)
  wt <- smd(x, trt, w)
  data.frame(
    covariate   = cv$label,
    mean_treated_unweighted = round(un$mean_t, 3),
    mean_control_unweighted = round(un$mean_c, 3),
    smd_unweighted          = round(un$smd, 3),
    mean_treated_weighted   = round(wt$mean_t, 3),
    mean_control_weighted   = round(wt$mean_c, 3),
    smd_weighted            = round(wt$smd, 3),
    stringsAsFactors = FALSE
  )
})

bal <- do.call(rbind, rows)
write.csv(bal, file.path(DATA, "balance_table.csv"), row.names = FALSE)

## ── Formatted table ───────────────────────────────────────────────────────────

hdr <- sprintf("%-42s  %8s  %8s  %7s  |  %8s  %8s  %7s",
               "Covariate", "Trt mean", "Ctl mean", "SMD",
               "Trt mean", "Ctl mean", "SMD")
sep <- paste(rep("-", nchar(hdr)), collapse = "")

lines <- c(
  "Covariate Balance: Treated vs. Never-Treated (year_cog = 2012)",
  "",
  sprintf("%-42s  %26s       |  %26s",
          "", "Unweighted", "IPW-weighted"),
  hdr, sep,
  apply(bal, 1, function(r) {
    sprintf("%-42s  %8s  %8s  %7s  |  %8s  %8s  %7s",
            r["covariate"],
            r["mean_treated_unweighted"], r["mean_control_unweighted"],
            r["smd_unweighted"],
            r["mean_treated_weighted"],  r["mean_control_weighted"],
            r["smd_weighted"])
  }),
  sep,
  sprintf("N treated = %d   N control = %d   ESS (IPW) = %.1f",
          sum(trt == 1), sum(trt == 0),
          sum(w[trt == 0])^2 / sum(w[trt == 0]^2))
)

writeLines(lines, file.path(OUT, "balance_table.txt"))
cat(readLines(file.path(OUT, "balance_table.txt")), sep = "\n")
cat(sprintf("\nBalance table -> output/tables/balance_table.txt\n"))
cat(sprintf("Machine-readable -> data/processed/balance_table.csv\n"))
