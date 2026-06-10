"""
Patch panel_final with max_acres_cohort (dose variable for dose-response extension).

max_acres_cohort: largest qualifying MTBS fire (acres) within each county's
treatment cohort window:
  g_any=2017 counties: max fire acres across 2013-2016
  g_any=2022 counties: max fire acres across 2017-2021
  g_any=0 (never-treated): NaN

Patching in-place avoids re-running the full panel assembly (Census API calls).
"""
from pathlib import Path

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
PROC = ROOT / "data" / "processed"


def main() -> None:
    mtbs = pd.read_parquet(PROC / "mtbs_county.parquet")
    mtbs["acres"] = np.exp(mtbs["log_acres"])

    c1 = (
        mtbs[
            (mtbs["g_any"] == 2017)
            & mtbs["year"].between(2013, 2016)
            & (mtbs["fire_in_year"] == 1)
        ]
        .groupby("fips")["acres"]
        .max()
        .rename("max_acres_cohort")
        .reset_index()
    )

    c2 = (
        mtbs[
            (mtbs["g_any"] == 2022)
            & mtbs["year"].between(2017, 2021)
            & (mtbs["fire_in_year"] == 1)
        ]
        .groupby("fips")["acres"]
        .max()
        .rename("max_acres_cohort")
        .reset_index()
    )

    dose = pd.concat([c1, c2], ignore_index=True)

    panel = pd.read_parquet(PROC / "panel_final.parquet")
    panel = panel.drop(columns=["max_acres_cohort"], errors="ignore")
    panel = panel.merge(dose, on="fips", how="left")

    panel.to_parquet(PROC / "panel_final.parquet", index=False)
    panel.to_csv(PROC / "panel_final.csv", index=False)

    n_treated = (panel["g_any"] > 0)
    n_with_dose = panel.loc[n_treated, "fips"].nunique()
    n_missing = panel.loc[n_treated & panel["max_acres_cohort"].isna(), "fips"].nunique()

    print(f"Treated counties with dose:   {n_with_dose}")
    print(f"Treated counties missing dose: {n_missing} (should be 0)")

    log_acres = np.log(
        panel.loc[panel["max_acres_cohort"].notna(), "max_acres_cohort"].drop_duplicates()
    )
    print("\nlog(max_acres_cohort) across treated counties:")
    print(log_acres.describe().round(2).to_string())
    print(f"\nMedian split at log = {log_acres.median():.2f}  "
          f"(exp = {np.exp(log_acres.median()):.0f} acres)")
    print("Done. panel_final.parquet and .csv updated.")


if __name__ == "__main__":
    main()
