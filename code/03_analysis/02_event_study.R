##
## Event study plot — dynamic aggregation of C&S ATT_gt objects.
## Shows pre-trends and post-treatment paths for each outcome.
##
## Relative time: e = t − g  (years since first-fire CoG census)
##   e = -10, -5, 0, 5 for g=2017 (5-year CoG gaps)
##   e = -20, -15, -10, -5, 0 for g=2022
##
## Outputs:
##   output/figures/event_study_<outcome>.pdf   (one plot per outcome)
##   output/figures/event_study_main.pdf        (6-panel combined)
##

suppressPackageStartupMessages({
  library(here)
  library(did)
  library(ggplot2)
  library(dplyr)
})

ROOT  <- here::here()
ROUT  <- file.path(ROOT, "output", "rds")
FOUT  <- file.path(ROOT, "output", "figures")
dir.create(FOUT, showWarnings = FALSE, recursive = TRUE)

## ── Outcomes and display labels ──────────────────────────────────────────────

outcomes <- c(
  "rev_total_pc",
  "rev_proptax_pc",
  "rev_intergovt_pc",
  "exp_total_pc",
  "exp_capital_pc",
  "fiscal_balance_pc",
  "debt_lt_pc"
)

labels <- c(
  rev_total_pc      = "Total Revenue p.c. (2019$)",
  rev_proptax_pc    = "Property Tax Revenue p.c. (2019$)",
  rev_intergovt_pc  = "Intergovernmental Revenue p.c. (2019$)",
  exp_total_pc      = "Total Expenditure p.c. (2019$)",
  exp_capital_pc    = "Capital Outlays p.c. (2019$)",
  fiscal_balance_pc = "Fiscal Balance p.c. (2019$)",
  debt_lt_pc        = "Long-term Debt p.c. (2019$)"
)

## ── Extract dynamic aggregation for one outcome ───────────────────────────────

plot_event_study <- function(y, save = TRUE) {
  rds_path <- file.path(ROUT, sprintf("cs_att_gt_%s.rds", y))
  if (!file.exists(rds_path)) {
    warning(sprintf("Missing RDS: %s", rds_path))
    return(invisible(NULL))
  }
  fit <- readRDS(rds_path)

  ## Dynamic aggregation (event study)
  ag_dyn <- tryCatch(
    aggte(fit, type = "dynamic", min_e = -15, max_e = 5),
    error = function(e) aggte(fit, type = "dynamic")
  )

  ## Build data.frame
  df <- data.frame(
    e      = ag_dyn$egt,
    att    = ag_dyn$att.egt,
    se     = ag_dyn$se.egt,
    ci_lo  = ag_dyn$att.egt - qnorm(0.975) * ag_dyn$se.egt,
    ci_hi  = ag_dyn$att.egt + qnorm(0.975) * ag_dyn$se.egt
  )

  ## Identify pre-treatment and post-treatment periods
  df$post <- df$e >= 0
  df$colour <- ifelse(df$post, "#c0392b", "#2c3e50")

  ylab   <- labels[y]
  ttl    <- sprintf("Event Study: %s", ylab)
  sub    <- "Doubly-robust C&S estimator. Never-treated controls. 95% CI."

  p <- ggplot(df, aes(x = e, y = att, colour = post)) +
    geom_hline(yintercept = 0, colour = "grey50", linewidth = 0.4) +
    geom_vline(xintercept = -0.5, linetype = "dashed", colour = "grey60", linewidth = 0.4) +
    geom_errorbar(aes(ymin = ci_lo, ymax = ci_hi), width = 0.4, linewidth = 0.5) +
    geom_point(size = 2.2) +
    scale_colour_manual(values = c("FALSE" = "#2c3e50", "TRUE" = "#c0392b"),
                        guide = "none") +
    scale_x_continuous(breaks = df$e,
                       labels = paste0(ifelse(df$e >= 0, "+", ""), df$e)) +
    labs(x = "Years relative to first-fire CoG census", y = ylab,
         title = ttl, subtitle = sub) +
    theme_bw(base_size = 10) +
    theme(
      panel.grid.minor = element_blank(),
      plot.title    = element_text(size = 9, face = "bold"),
      plot.subtitle = element_text(size = 7, colour = "grey40"),
      axis.title    = element_text(size = 8)
    )

  if (save) {
    ggsave(file.path(FOUT, sprintf("event_study_%s.pdf", y)),
           plot = p, width = 7, height = 4, dpi = 300)
  }
  list(plot = p, data = df)
}

## ── Generate all event study plots ───────────────────────────────────────────

plots <- list()
for (y in outcomes) {
  res <- plot_event_study(y)
  if (!is.null(res)) {
    plots[[y]] <- res$plot
    cat(sprintf("Event study: %s  -->  output/figures/event_study_%s.pdf\n", y, y))
  }
}

## ── 6-panel combined figure (exclude debt_lt_pc for cleaner layout) ───────────

main_outcomes <- c("rev_total_pc", "rev_proptax_pc", "rev_intergovt_pc",
                   "exp_total_pc", "exp_capital_pc", "fiscal_balance_pc")

main_plots <- plots[main_outcomes]

if (requireNamespace("patchwork", quietly = TRUE)) {
  library(patchwork)
  combined <- (main_plots[[1]] | main_plots[[2]] | main_plots[[3]]) /
              (main_plots[[4]] | main_plots[[5]] | main_plots[[6]]) +
    plot_annotation(
      title    = "Figure 2: Event Study — Effect of Wildfire Incidence on County Government Finance",
      subtitle = "Callaway-Sant'Anna (2021) doubly-robust estimates. Never-treated controls. 95% pointwise CI.",
      theme    = theme(plot.title    = element_text(size = 10, face = "bold"),
                       plot.subtitle = element_text(size = 8, colour = "grey40"))
    )
  ggsave(file.path(FOUT, "event_study_main.pdf"),
         plot = combined, width = 14, height = 8, dpi = 300)
  cat("\nCombined 6-panel -> output/figures/event_study_main.pdf\n")
} else {
  cat("\npatchwork not available — individual plots saved to output/figures/\n")
}

## ── Print pre-trend test results ─────────────────────────────────────────────

cat("\n=== Pre-trend Test Summary (e < 0 ATTs) ===\n")
for (y in outcomes) {
  rds_path <- file.path(ROUT, sprintf("cs_att_gt_%s.rds", y))
  if (!file.exists(rds_path)) next
  fit    <- readRDS(rds_path)
  ag_dyn <- tryCatch(
    aggte(fit, type = "dynamic", min_e = -15, max_e = 5),
    error = function(e) aggte(fit, type = "dynamic")
  )
  pre    <- data.frame(e = ag_dyn$egt, att = ag_dyn$att.egt, se = ag_dyn$se.egt) |>
    filter(e < 0)
  if (nrow(pre) == 0) {
    cat(sprintf("  %-22s  No pre-treatment periods\n", y))
    next
  }
  ## Simple joint Wald test: sum(att^2/se^2) ~ chi2(k) under H0: all pre-ATTs = 0
  chi2 <- sum((pre$att / pre$se)^2, na.rm = TRUE)
  pv   <- pchisq(chi2, df = nrow(pre), lower.tail = FALSE)
  cat(sprintf("  %-22s  max|pre-ATT|: %6.1f   joint p: %.3f\n",
              y, max(abs(pre$att), na.rm = TRUE), pv))
}

cat("\nDone.\n")
