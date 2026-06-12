suppressPackageStartupMessages({library(did2s); library(dplyr)})
panel <- read.csv("data/processed/panel_final.csv", stringsAsFactors=FALSE)
panel$fips <- sprintf("%05d", as.integer(panel$fips))
panel <- panel |> mutate(
  fips_int=as.integer(fips), g_d2s=as.integer(g),
  treated=as.integer(g_d2s > 0 & year_cog >= g_d2s)
)
fit <- did2s(data=panel, yname="fiscal_balance_pc",
             first_stage=~0|fips_int+year_cog,
             second_stage=~i(treated, ref=0L),
             treatment="treated", cluster_var="fips_int")
cat("coeftable rownames:\n")
print(rownames(coeftable(fit)))
