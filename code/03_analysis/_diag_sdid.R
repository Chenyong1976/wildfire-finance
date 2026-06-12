library(synthdid)
panel <- read.csv("data/processed/panel_final.csv", stringsAsFactors=FALSE)
sub   <- panel[panel$g %in% c(0,2017,2022), ]
sub$treat_ind <- as.integer(sub$g == 2017 & sub$year_cog >= 2017)
df <- data.frame(fips=sub$fips, year=sub$year_cog, y=sub$fiscal_balance_pc, w=sub$treat_ind)
setup <- panel.matrices(df, unit='fips', time='year', outcome='y', treatment='w')
cat("dim Y:", paste(dim(setup$Y), collapse="x"), "\n")
cat("N0:", setup$N0, "T0:", setup$T0, "\n")
cat("ncol(Y):", ncol(setup$Y), "T0:", setup$T0, "ncol>T0:", ncol(setup$Y) > setup$T0, "\n")

## Try do.call
cat("Calling do.call(synthdid_estimate, setup)...\n")
est <- tryCatch(do.call(synthdid_estimate, setup), error=function(e) { cat("  Error:", conditionMessage(e), "\n"); NULL })

## Try explicit args
cat("Calling synthdid_estimate(setup$Y, setup$W, setup$N0, setup$T0)...\n")
est2 <- tryCatch(synthdid_estimate(setup$Y, setup$W, setup$N0, setup$T0),
                 error=function(e) { cat("  Error:", conditionMessage(e), "\n"); NULL })

if (!is.null(est2)) cat("ATT:", as.numeric(est2), "\n")
