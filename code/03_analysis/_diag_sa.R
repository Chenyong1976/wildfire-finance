suppressPackageStartupMessages({ library(fixest); library(dplyr) })
panel <- read.csv("data/processed/panel_final.csv", stringsAsFactors=FALSE)
panel$fips <- sprintf("%05d", as.integer(panel$fips))
ffy <- read.csv("data/processed/mtbs_county_ffy.csv", stringsAsFactors=FALSE)
ffy$fips <- sprintf("%05d", as.integer(ffy$fips))
panel_sa <- left_join(panel, ffy, by="fips") |>
  mutate(G_ffy=ifelse(is.na(first_fire_year),0L,as.integer(first_fire_year)), fips_int=as.integer(fips))
panel_sa <- filter(panel_sa, !G_ffy %in% c(2019,2020,2021))

fit <- feols(fiscal_balance_pc ~ sunab(G_ffy, year_cog, ref.p=-1) | fips_int + year_cog,
             data=panel_sa, cluster=~fips_int)
cat("Coef names (first 10):\n")
print(head(names(coef(fit)), 10))
cat("\ncoeftable rownames (first 10):\n")
print(head(rownames(coeftable(fit)), 10))
