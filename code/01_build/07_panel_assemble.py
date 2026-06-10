"""
Final panel assembly for wildfire-finance project.

Study period: CoG census years 2002, 2007, 2012 (pre-treatment) and 2017, 2022
(post-treatment). Treatment window: MTBS fires 2013-2021.

Merges:
  - CoG quinquennial fiscal panel (344 counties; filtered to 2002-2022)
  - MTBS treatment indicators, C&S group variable, pre-fire history
  - WFP/WHP county hazard scores
  - Population denominators (2000 Census + ACS)
  - ACS socioeconomic covariates
  - RUCC urban-rural classification
  - Smoke buffer exclusion flags

Applies CPI-U deflation (2019 base) and computes per-capita fiscal outcomes.

Population strategy by CoG FY-begin year:
  2001: 2000 decennial Census (Census API SF1; 1-year gap, effectively exact)
  2006: ACS 5-yr 2006 from health-project file; UT uses 2009 as proxy
  2011, 2016: ACS 5-yr from health-project file + UT from API
  2021: ACS 5-yr 2020 (1-year lag; flagged with pop_year_2021_lag)

ACS covariates (median_hhinc, poverty_rate, uninsurance_rate, pop_density):
  Health-project ACS covers states 04,06,08,16,30,32,35,41,53,56 (not UT=49).
  UT is pulled from Census API within this script.

Output: data/processed/panel_final.parquet
"""

from __future__ import annotations

import os
import time
from pathlib import Path

import numpy as np
import pandas as pd
import requests

PROJECT_ROOT   = Path(__file__).resolve().parents[2]
DATA_RAW       = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
HEALTH_RAW     = PROJECT_ROOT.parent / "wildfire-health" / "data" / "raw"
HEALTH_PROC    = PROJECT_ROOT.parent / "wildfire-health" / "data" / "processed"

np.random.seed(42)

WEST_STATES    = {"06", "08", "16", "30", "41", "49", "53", "56"}
CENSUS_API_KEY = os.environ.get("CENSUS_API_KEY", "5e9b8c7b6f13e5d5f10b100ebf88eba8c778a442")
CENSUS_BASE    = "https://api.census.gov/data"

# Study period: CoG census years 2002-2022 only (FY-begin years below).
# 1992 and 1997 are dropped: 1990 Census not in REST API → unreliable pop proxies.
COG_FY_YEARS = [2001, 2006, 2011, 2016, 2021]   # FY-begin years (census year - 1)
COG_CENSUS_YEARS = [2002, 2007, 2012, 2017, 2022]  # labels used in CoG data

# CPI-U annual average (BLS series CUSR0000SA0). Base year 2019.
CPI_U: dict[int, float] = {
    1991: 136.2, 1996: 156.9,
    2000: 172.2, 2001: 177.1, 2002: 179.9, 2003: 184.0, 2004: 188.9,
    2005: 195.3, 2006: 201.6, 2007: 207.3, 2008: 215.3, 2009: 214.5,
    2010: 218.1, 2011: 224.9, 2012: 229.6, 2013: 233.0, 2014: 236.7,
    2015: 237.0, 2016: 240.0, 2017: 245.1, 2018: 251.1, 2019: 255.7,
    2020: 258.8, 2021: 270.9,
}
CPI_2019 = CPI_U[2019]

FISCAL_COLS = [
    "rev_proptax", "rev_tax_total", "rev_igt_federal", "rev_igt_state",
    "rev_intergovt", "rev_own_sources", "rev_total",
    "exp_total", "exp_capital", "exp_current",
    "debt_lt", "fiscal_balance",
]


# ---------------------------------------------------------------------------
# Census API helpers
# ---------------------------------------------------------------------------

def _api_get(url: str, params: dict) -> list[list] | None:
    if CENSUS_API_KEY:
        params["key"] = CENSUS_API_KEY
    try:
        r = requests.get(url, params=params, timeout=60)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        print(f"  API error: {e} — url={url} params={params}")
        return None


def fetch_decennial_pop(year: int, state_fips: str) -> pd.DataFrame | None:
    """County-level total population from decennial Census SF1 (2000 only via API).
    Note: 1990 Census is not available via the Census REST API. Use 2000 as proxy.
    """
    if year != 2000:
        return None   # 1990 API returns 404; caller uses 2000 as proxy
    var  = "P001001"
    url  = f"{CENSUS_BASE}/{year}/dec/sf1"
    data = _api_get(url, {"get": var, "for": "county:*", "in": f"state:{state_fips}"})
    if not data or len(data) < 2:
        return None
    df = pd.DataFrame(data[1:], columns=data[0])
    df["fips"] = df["state"].str.zfill(2) + df["county"].str.zfill(3)
    df["pop"]  = pd.to_numeric(df[var], errors="coerce")
    return df[["fips", "pop"]]


def fetch_acs5_pop_covars(year: int, state_fips: str) -> pd.DataFrame | None:
    """ACS 5-yr county: population + median HH income + poverty + uninsurance."""
    vars_needed = [
        "B01003_001E",   # total population
        "B19013_001E",   # median household income
        "B17001_002E",   # poverty count (numerator)
        "B17001_001E",   # poverty universe (denominator)
    ]
    url  = f"{CENSUS_BASE}/{year}/acs/acs5"
    data = _api_get(url, {"get": ",".join(["NAME"] + vars_needed),
                          "for": "county:*", "in": f"state:{state_fips}"})
    if not data or len(data) < 2:
        return None
    df = pd.DataFrame(data[1:], columns=data[0])
    df["fips"]         = df["state"].str.zfill(2) + df["county"].str.zfill(3)
    df["pop"]          = pd.to_numeric(df["B01003_001E"], errors="coerce")
    df["median_hhinc"] = pd.to_numeric(df["B19013_001E"], errors="coerce") * (CPI_2019 / CPI_U.get(year, CPI_2019))
    pov_n = pd.to_numeric(df["B17001_002E"], errors="coerce")
    pov_d = pd.to_numeric(df["B17001_001E"], errors="coerce")
    df["poverty_rate"] = pov_n / pov_d.replace(0, np.nan)
    return df[["fips", "pop", "median_hhinc", "poverty_rate"]]


# ---------------------------------------------------------------------------
# Population panel construction
# ---------------------------------------------------------------------------

def build_population_panel() -> pd.DataFrame:
    """
    Construct population for the 5 CoG FY-begin years (2001-2021) and all 8 finance states.

    Sources:
      2001:   2000 decennial Census (Census API SF1; 1-year gap)
      2006:   ACS 5-yr 2006 from health-project file; UT uses 2009 proxy
      2011:   ACS 5-yr 2011 from health-project file + UT from API
      2016:   ACS 5-yr 2016 from health-project file + UT from API
      2021:   ACS 5-yr 2020 from health-project file + UT from API; 1-yr lag flagged
    """
    # Load existing ACS panel (health project, excludes UT)
    acs_all = pd.read_parquet(HEALTH_PROC / "acs_covariates.parquet")
    acs_all = acs_all[acs_all["fips"].str[:2].isin(WEST_STATES)].copy()

    # Pull ACS for UT for years we need.
    # ACS 5-yr starts in 2009; use 2009 as fallback proxy for 2006 (UT only).
    UT_ACS_YEARS = [2006, 2011, 2016, 2020]
    ut_frames: list[pd.DataFrame] = []
    for yr in UT_ACS_YEARS:
        api_yr = 2009 if yr == 2006 else yr   # ACS 5-yr 2006 not in API; 2009 is proxy
        print(f"  Pulling ACS 5-yr {api_yr} for UT (49)" +
              (" [proxy for 2006]" if yr == 2006 else "") + "...")
        df = fetch_acs5_pop_covars(api_yr, "49")
        if df is not None:
            df["year"] = yr    # label as 2006 so the merge key matches year_cog=2007
            ut_frames.append(df)
        time.sleep(0.3)

    if ut_frames:
        ut_acs = pd.concat(ut_frames, ignore_index=True)
        # Merge into acs_all — only columns that match
        for yr in UT_ACS_YEARS:
            yr_df = ut_acs[ut_acs["year"] == yr][["fips", "pop", "median_hhinc", "poverty_rate"]].copy()
            yr_df["year"] = yr
            # Also fill columns that exist in acs_all but not in yr_df
            for col in ["uninsurance_rate", "share_65plus", "pop_density"]:
                yr_df[col] = np.nan
            acs_all = pd.concat([acs_all, yr_df], ignore_index=True)
    else:
        print("  WARNING: UT ACS pull failed entirely — UT per-capita values will be NaN")

    # Pull 2000 decennial Census for FY-begin year 2001 (1-year gap; effectively exact).
    print("  Pulling 2000 decennial Census population...")
    frames_2000 = []
    for st in sorted(WEST_STATES):
        df = fetch_decennial_pop(2000, st)
        if df is not None:
            frames_2000.append(df)
        time.sleep(0.1)
    pop_2000: dict[str, float] = {}
    if frames_2000:
        dec_df = pd.concat(frames_2000, ignore_index=True)
        pop_2000 = dec_df.set_index("fips")["pop"].to_dict()
    else:
        print("  WARNING: 2000 decennial Census API failed — 2001 pop will be NaN")

    # Get all FIPS in CoG panel (backbone)
    cog = pd.read_parquet(DATA_PROCESSED / "cog_census_panel.parquet")
    all_fips = cog["fips"].unique()

    # ACS covariate source year for each FY-begin year
    acs_map = {2001: 2000, 2006: 2006, 2011: 2011, 2016: 2016, 2021: 2020}

    rows = []
    for fips in all_fips:
        p00 = pop_2000.get(fips, np.nan)

        acs_fips = acs_all[acs_all["fips"] == fips]

        def _acs_val(year: int, col: str) -> float:
            sub = acs_fips[acs_fips["year"] == year]
            return sub[col].values[0] if (len(sub) > 0 and col in sub.columns and not sub[col].isna().all()) else np.nan

        pop_by_year = {
            2001: p00,
            2006: _acs_val(2006, "pop"),
            2011: _acs_val(2011, "pop"),
            2016: _acs_val(2016, "pop"),
            2021: _acs_val(2020, "pop"),
        }

        for cog_yr in COG_FY_YEARS:
            acs_yr = acs_map[cog_yr]
            rows.append({
                "fips":             fips,
                "year":             cog_yr,
                "pop":              pop_by_year.get(cog_yr, np.nan),
                "median_hhinc":     _acs_val(acs_yr, "median_hhinc"),
                "poverty_rate":     _acs_val(acs_yr, "poverty_rate"),
                "uninsurance_rate": _acs_val(acs_yr, "uninsurance_rate"),
                "share_65plus":     _acs_val(acs_yr, "share_65plus"),
                "pop_density":      _acs_val(acs_yr, "pop_density"),
                "pop_year_2021_lag": int(cog_yr == 2021),
            })

    return pd.DataFrame(rows)


# ---------------------------------------------------------------------------
# RUCC merge
# ---------------------------------------------------------------------------

def load_rucc() -> pd.DataFrame:
    path = HEALTH_RAW / "rucc2013.xls"
    rucc = pd.read_excel(path, dtype=str)
    rucc["fips"]      = rucc["FIPS"].str.strip().str.zfill(5)
    rucc["rucc_2013"] = pd.to_numeric(rucc["RUCC_2013"], errors="coerce").astype("Int64")
    return rucc[["fips", "rucc_2013"]]


# ---------------------------------------------------------------------------
# Main assembly
# ---------------------------------------------------------------------------

def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    print("Loading core processed files...")
    cog   = pd.read_parquet(DATA_PROCESSED / "cog_census_panel.parquet")
    mtbs  = pd.read_parquet(DATA_PROCESSED / "mtbs_county.parquet")
    whp   = pd.read_parquet(DATA_PROCESSED / "whp_county.parquet")
    smoke = pd.read_parquet(DATA_PROCESSED / "fire_perimeters_100km_buffer.parquet")

    # ------------------------------------------------------------------
    # Treatment variables: county-level (time-invariant from MTBS)
    # ------------------------------------------------------------------
    treat_cols = ["fips", "g", "g_any", "pre2013_fire", "pre2013_fire_count", "pre2013_log_acres"]
    treat = mtbs[treat_cols].drop_duplicates("fips")

    # ------------------------------------------------------------------
    # Filter CoG to study period (2002-2022 only)
    # ------------------------------------------------------------------
    cog = cog[cog["year_cog"].isin(COG_CENSUS_YEARS)].copy()

    # ------------------------------------------------------------------
    # Smoke buffer: merge FY-begin year to MTBS year
    # ------------------------------------------------------------------
    # FY-begin year 2001 → CoG year 2002; smoke fire-year 2001 is pre-treatment (no exclusion needed)
    smoke_cog = []
    for cog_yr in COG_FY_YEARS:
        s = smoke[smoke["year"] == cog_yr][["fips", "excl_flag"]].copy()
        s["year"] = cog_yr
        smoke_cog.append(s)
    smoke_panel = pd.concat(smoke_cog, ignore_index=True).rename(
        columns={"excl_flag": "smoke_buffer_excl"}
    )

    # ------------------------------------------------------------------
    # Population and ACS covariates
    # ------------------------------------------------------------------
    print("Building population and ACS covariate panel...")
    pop_panel = build_population_panel()

    # ------------------------------------------------------------------
    # RUCC
    # ------------------------------------------------------------------
    rucc = load_rucc()

    # ------------------------------------------------------------------
    # Assemble final panel
    # ------------------------------------------------------------------
    print("Assembling final panel...")
    panel = cog.copy()

    # Merge treatment (county-level)
    panel = panel.merge(treat, on="fips", how="left")
    panel["g"]     = panel["g"].fillna(0).astype(int)
    panel["g_any"] = panel["g_any"].fillna(0).astype(int)

    # Derive treated_post: =1 if post-treatment CoG census year
    # g=2017 → treated from year_cog=2017 onward; g=2022 → from year_cog=2022 onward
    panel["treated_post"] = (
        (panel["g"] > 0) & (panel["year_cog"] >= panel["g"])
    ).astype(int)

    # Merge WFP/WHP
    panel = panel.merge(whp, on="fips", how="left")

    # Merge smoke buffer
    panel = panel.merge(smoke_panel, on=["fips", "year"], how="left")
    panel["smoke_buffer_excl"] = panel["smoke_buffer_excl"].fillna(0).astype(int)

    # Merge population and ACS covariates
    panel = panel.merge(pop_panel, on=["fips", "year"], how="left")

    # Merge RUCC
    panel = panel.merge(rucc, on="fips", how="left")

    # ------------------------------------------------------------------
    # CPI-U deflation
    # ------------------------------------------------------------------
    def deflator(year: int) -> float:
        return CPI_2019 / CPI_U.get(year, CPI_2019)

    panel["cpi_deflator"] = panel["year"].map(deflator)

    for col in FISCAL_COLS:
        if col in panel.columns:
            panel[f"{col}_real"] = panel[col] * panel["cpi_deflator"]

    # ------------------------------------------------------------------
    # Per-capita fiscal outcomes (real 2019$, per capita)
    # ------------------------------------------------------------------
    # CoG amounts stored in dollars (pull script multiplied $thousands × 1000).
    # _real = nominal_dollars × deflator → 2019 dollars.
    # _pc   = 2019_dollars / pop → dollars per capita in 2019$.
    pop_safe = panel["pop"].replace(0, np.nan)
    for col in FISCAL_COLS:
        real_col = f"{col}_real"
        if real_col in panel.columns:
            panel[f"{col}_pc"] = panel[real_col] / pop_safe

    # ------------------------------------------------------------------
    # Per-capita outlier flags
    # ------------------------------------------------------------------
    # Per-capita outlier flags (supplement the nominal flag_rev_* from CoG pull).
    # Revenue/expenditure: flag < 0 or > 3× state-year median.
    # fiscal_balance_pc can legitimately be negative; use ±5 SD instead.
    for col in ["rev_total_pc", "exp_total_pc", "rev_proptax_pc"]:
        if col in panel.columns:
            med = panel.groupby(["state", "year_cog"])[col].transform("median")
            panel[f"flag_{col}"] = (panel[col] < 0) | (panel[col] > 3 * med)

    if "fiscal_balance_pc" in panel.columns:
        med = panel.groupby(["state", "year_cog"])["fiscal_balance_pc"].transform("median")
        std = panel.groupby(["state", "year_cog"])["fiscal_balance_pc"].transform("std")
        panel["flag_fiscal_balance_pc"] = (panel["fiscal_balance_pc"] - med).abs() > 5 * std

    # ------------------------------------------------------------------
    # Sort and output
    # ------------------------------------------------------------------
    panel = panel.sort_values(["fips", "year_cog"]).reset_index(drop=True)

    out_path = DATA_PROCESSED / "panel_final.parquet"
    panel.to_parquet(out_path, index=False)
    csv_path = DATA_PROCESSED / "panel_final.csv"
    panel.to_csv(csv_path, index=False)

    # ------------------------------------------------------------------
    # Summary
    # ------------------------------------------------------------------
    print(f"\nPanel written: {len(panel):,} rows × {len(panel.columns)} cols -> {out_path}")
    print(f"  Counties: {panel['fips'].nunique()}")
    print(f"  Study period: CoG census years {sorted(panel['year_cog'].unique().tolist())} (2002-2022)")
    print(f"  FY-begin years: {sorted(panel['year'].unique().tolist())}")
    print(f"\nTreatment groups:")
    print(f"  g=2017: {(panel['g']==2017)['fips'].nunique() if False else panel[panel['g']==2017]['fips'].nunique()} counties")
    print(f"  g=2022: {panel[panel['g']==2022]['fips'].nunique()} counties")
    print(f"  g=0:    {panel[panel['g']==0]['fips'].nunique()} counties")
    print(f"\nMissing population (NaN pop): {panel['pop'].isna().sum()} rows")
    print(f"Missing primary fiscal (rev_total): {panel['rev_total'].isna().sum()} rows")

    # Key per-capita stats for the post-treatment year (year_cog=2017)
    pt = panel[panel["year_cog"] == 2017]
    if "rev_total_pc" in pt.columns:
        print(f"\nrev_total_pc (year_cog=2017, non-null):")
        print(pt["rev_total_pc"].describe().round(0).to_string())
    if "fiscal_balance_pc" in pt.columns:
        print(f"\nfiscal_balance_pc (year_cog=2017, non-null):")
        print(pt["fiscal_balance_pc"].describe().round(0).to_string())

    # Write codebook
    codebook_rows = []
    for col in panel.columns:
        codebook_rows.append({
            "variable": col,
            "dtype": str(panel[col].dtype),
            "n_nonmissing": panel[col].notna().sum(),
            "n_missing": panel[col].isna().sum(),
        })
    pd.DataFrame(codebook_rows).to_csv(DATA_PROCESSED / "panel_codebook.csv", index=False)
    print(f"\nCodebook written -> {DATA_PROCESSED / 'panel_codebook.csv'}")


if __name__ == "__main__":
    main()
