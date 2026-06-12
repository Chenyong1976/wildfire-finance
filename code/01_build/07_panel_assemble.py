"""
Final panel assembly for wildfire-finance project.

Study period: CoG census years 2002, 2007, 2012 (pre-treatment) and 2017, 2022
(post-treatment). Treatment window: MTBS fires 2013-2021.

Merges:
  - CoG quinquennial fiscal panel (all lower-48 counties; filtered to 2002-2022)
  - MTBS treatment indicators, C&S group variable, pre-fire history
  - WFP/WHP county hazard scores
  - Population denominators (2000 Census + ACS) — pulled from Census API for all states
  - ACS socioeconomic covariates (median_hhinc, poverty_rate, uninsurance_rate,
    share_65plus, pop_density) — all states via Census API
  - RUCC urban-rural classification
  - Smoke buffer exclusion flags

Applies CPI-U deflation (2019 base) and computes per-capita fiscal outcomes.

Population strategy by CoG census year (year_cog):
  2002: 2000 decennial Census (Census API SF1)
  2007: ACS 5-yr 2009 proxy (ACS 5-yr not available before 2009)
  2012: ACS 5-yr 2011
  2017: ACS 5-yr 2016
  2022: ACS 5-yr 2020 (1-year lag; flagged with pop_year_lag)

  Pop panel merges by ["fips","year_cog"] to handle December FY-end states
  (IN,KY,MN,MO,NH,NJ,NY,ND,OH,PA,SD,WV,WI) whose FY-begin year == year_cog.

Output: data/processed/panel_final.parquet
"""

from __future__ import annotations

import os
import time
import zipfile
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

# All lower-48 state FIPS codes (excludes AK=02, HI=15, DC=11, territories)
LOWER_48 = {
    "01","04","05","06","08","09","10","12","13",
    "16","17","18","19","20","21","22","23","24","25","26","27","28","29",
    "30","31","32","33","34","35","36","37","38","39","40","41","42","44",
    "45","46","47","48","49","50","51","53","54","55","56",
}

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
    """ACS 5-yr county: population, median HH income, poverty, uninsurance, share 65+.

    B27001 (health insurance) is not available in the current format before 2011.
    For years < 2011, falls back to core demographic variables only; uninsurance_rate=NaN.
    """
    _MALE65   = ["B01001_020E","B01001_021E","B01001_022E","B01001_023E","B01001_024E","B01001_025E"]
    _FEM65    = ["B01001_044E","B01001_045E","B01001_046E","B01001_047E","B01001_048E","B01001_049E"]
    _MALE_UNI = ["B27001_005E","B27001_008E","B27001_011E","B27001_014E","B27001_017E",
                 "B27001_020E","B27001_023E","B27001_026E","B27001_029E"]
    _FEM_UNI  = ["B27001_033E","B27001_036E","B27001_039E","B27001_042E","B27001_045E",
                 "B27001_048E","B27001_051E","B27001_054E","B27001_057E"]

    core_vars = (
        ["B01003_001E","B19013_001E","B17001_002E","B17001_001E"]
        + _MALE65 + _FEM65
    )
    ins_vars = ["B27001_001E"] + _MALE_UNI + _FEM_UNI

    # Try full variable list first; fall back to core only if insurance vars fail
    for var_list in [core_vars + ins_vars, core_vars]:
        url  = f"{CENSUS_BASE}/{year}/acs/acs5"
        data = _api_get(url, {"get": ",".join(["NAME"] + var_list),
                              "for": "county:*", "in": f"state:{state_fips}"})
        if data and len(data) >= 2:
            has_insurance = "B27001_001E" in var_list
            break
    else:
        return None

    df = pd.DataFrame(data[1:], columns=data[0])
    df["fips"]         = df["state"].str.zfill(2) + df["county"].str.zfill(3)
    df["pop"]          = pd.to_numeric(df["B01003_001E"], errors="coerce")
    df["median_hhinc"] = (pd.to_numeric(df["B19013_001E"], errors="coerce")
                          * (CPI_2019 / CPI_U.get(year, CPI_2019)))
    pov_n = pd.to_numeric(df["B17001_002E"], errors="coerce")
    pov_d = pd.to_numeric(df["B17001_001E"], errors="coerce")
    df["poverty_rate"] = pov_n / pov_d.replace(0, np.nan)

    age65_n = sum(pd.to_numeric(df[c], errors="coerce").fillna(0) for c in _MALE65 + _FEM65)
    df["share_65plus"] = age65_n / df["pop"].replace(0, np.nan)

    if has_insurance:
        unins_n = sum(pd.to_numeric(df[c], errors="coerce").fillna(0) for c in _MALE_UNI + _FEM_UNI)
        unins_d = pd.to_numeric(df["B27001_001E"], errors="coerce")
        df["uninsurance_rate"] = unins_n / unins_d.replace(0, np.nan)
    else:
        df["uninsurance_rate"] = np.nan   # B27001 not available for this year

    return df[["fips", "pop", "median_hhinc", "poverty_rate", "uninsurance_rate", "share_65plus"]]


# ---------------------------------------------------------------------------
# Population panel construction
# ---------------------------------------------------------------------------

def _pull_acs_all_states(api_year: int) -> pd.DataFrame:
    """Pull ACS 5-yr for all lower-48 states; tags rows with the api_year as 'acs_year'."""
    frames: list[pd.DataFrame] = []
    for st in sorted(LOWER_48):
        df = fetch_acs5_pop_covars(api_year, st)
        if df is not None and not df.empty:
            df["acs_year"] = api_year
            frames.append(df)
        time.sleep(0.15)
    if not frames:
        return pd.DataFrame(columns=["fips", "acs_year", "pop", "median_hhinc",
                                     "poverty_rate", "uninsurance_rate", "share_65plus"])
    return pd.concat(frames, ignore_index=True)


def build_population_panel() -> pd.DataFrame:
    """
    Population and ACS covariate panel indexed by year_cog (CoG census year).
    Merges by ["fips","year_cog"] in main() — avoids the FY-begin year mismatch
    for December fiscal-year-end states (IN,KY,MN,MO,NH,NJ,NY,ND,OH,PA,SD,WV,WI).

    Sources:
      year_cog 2002: 2000 decennial Census
      year_cog 2007: ACS 5-yr 2009 proxy (earliest available)
      year_cog 2012: ACS 5-yr 2011
      year_cog 2017: ACS 5-yr 2016
      year_cog 2022: ACS 5-yr 2020 (1-year lag; flagged with pop_year_lag=1)
    """
    # Maps CoG census year → ACS API year (None = use 2000 decennial Census)
    acs_proxy: dict[int, int | None] = {
        2002: None,
        2007: 2009,
        2012: 2011,
        2017: 2016,
        2022: 2020,
    }

    # --- 2000 decennial Census (for year_cog 2002) ---
    print("  Pulling 2000 decennial Census (all lower-48)...")
    frames_2000 = []
    for st in sorted(LOWER_48):
        df = fetch_decennial_pop(2000, st)
        if df is not None:
            frames_2000.append(df)
        time.sleep(0.1)
    pop_2000: dict[str, float] = {}
    if frames_2000:
        dec_df = pd.concat(frames_2000, ignore_index=True)
        pop_2000 = dec_df.set_index("fips")["pop"].to_dict()
        print(f"    2000 Census: {len(pop_2000):,} counties")
    else:
        print("  WARNING: 2000 decennial Census API failed — year_cog=2002 pop will be NaN")

    # --- ACS 5-yr panels ---
    acs_api_years = [2009, 2011, 2016, 2020]
    acs_frames: list[pd.DataFrame] = []
    for api_yr in acs_api_years:
        print(f"  Pulling ACS 5-yr {api_yr} (all lower-48)...")
        df = _pull_acs_all_states(api_yr)
        print(f"    ACS {api_yr}: {len(df):,} county-rows, "
              f"{df['pop'].notna().sum():,} non-null pop")
        acs_frames.append(df)
    acs_all = pd.concat(acs_frames, ignore_index=True) if acs_frames else pd.DataFrame()

    # --- Pop density from Census Gazetteer (ALAND, sq metres → sq km) ---
    pop_density_lookup: dict[str, float] = {}
    gaz_path = DATA_RAW / "2020_Gaz_counties_national.txt"
    if not gaz_path.exists():
        print("  Downloading 2020 Census Gazetteer for county land area...")
        gaz_url = ("https://www2.census.gov/geo/docs/maps-data/data/gazetteer"
                   "/2020_Gazetteer/2020_Gaz_counties_national.zip")
        gaz_zip = DATA_RAW / "2020_Gaz_counties_national.zip"
        r = requests.get(gaz_url, timeout=60)
        gaz_zip.write_bytes(r.content)
        with zipfile.ZipFile(gaz_zip) as zf:
            zf.extractall(DATA_RAW)
    if gaz_path.exists():
        gaz = pd.read_csv(gaz_path, sep="\t", dtype=str,
                          usecols=["GEOID", "ALAND_SQMI"])
        gaz["fips"]      = gaz["GEOID"].str.strip().str.zfill(5)
        gaz["aland_km2"] = pd.to_numeric(gaz["ALAND_SQMI"], errors="coerce") * 2.58999
        pop_density_lookup = gaz.set_index("fips")["aland_km2"].to_dict()
        print(f"    Gazetteer: {len(pop_density_lookup):,} counties with land area")

    # --- CoG panel backbone ---
    cog = pd.read_parquet(DATA_PROCESSED / "cog_census_panel.parquet")
    all_fips = cog["fips"].unique()

    rows = []
    for fips in all_fips:
        p00   = pop_2000.get(fips, np.nan)
        aland = pop_density_lookup.get(fips, np.nan)
        acs_f = acs_all[acs_all["fips"] == fips] if not acs_all.empty else pd.DataFrame()

        def _acs_val(api_yr: int | None, col: str) -> float:
            if api_yr is None or acs_f.empty:
                return np.nan
            sub = acs_f[acs_f["acs_year"] == api_yr]
            if len(sub) == 0 or col not in sub.columns:
                return np.nan
            v = sub[col].values[0]
            return float(v) if not pd.isna(v) else np.nan

        for cog_yr in COG_CENSUS_YEARS:
            api_yr = acs_proxy[cog_yr]
            pop    = p00 if cog_yr == 2002 else _acs_val(api_yr, "pop")
            rows.append({
                "fips":             fips,
                "year_cog":         cog_yr,
                "pop":              pop,
                "median_hhinc":     _acs_val(api_yr, "median_hhinc"),
                "poverty_rate":     _acs_val(api_yr, "poverty_rate"),
                "uninsurance_rate": _acs_val(api_yr, "uninsurance_rate"),
                "share_65plus":     _acs_val(api_yr, "share_65plus"),
                "pop_density": (
                    (pop / aland)
                    if (not (isinstance(pop, float) and np.isnan(pop))
                        and not (isinstance(aland, float) and np.isnan(aland))
                        and aland > 0)
                    else np.nan
                ),
                "pop_year_lag": int(cog_yr == 2022),   # ACS 2020 used for year_cog 2022
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
    # Smoke buffer: index by year_cog for consistent merging
    # ------------------------------------------------------------------
    smoke_cog = []
    for cog_yr in COG_CENSUS_YEARS:
        s = smoke[smoke["year"] == cog_yr][["fips", "excl_flag"]].copy()
        s["year_cog"] = cog_yr
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

    # Merge smoke buffer (keyed by year_cog)
    panel = panel.merge(smoke_panel, on=["fips", "year_cog"], how="left")
    panel["smoke_buffer_excl"] = panel["smoke_buffer_excl"].fillna(0).astype(int)

    # Merge population and ACS covariates (keyed by year_cog, not FY-begin year)
    panel = panel.merge(pop_panel, on=["fips", "year_cog"], how="left")

    # Merge RUCC
    panel = panel.merge(rucc, on="fips", how="left")

    # ------------------------------------------------------------------
    # Home rule / Dillon's Rule
    # ------------------------------------------------------------------
    hr_states_path   = DATA_RAW / "home_rule" / "home_rule_states.csv"
    hr_counties_path = DATA_RAW / "home_rule" / "home_rule_counties.csv"

    if hr_states_path.exists():
        hr_states = pd.read_csv(hr_states_path, dtype={"state_fips": str})
        hr_states["state_fips"] = hr_states["state_fips"].str.zfill(2)
        panel["state_fips"] = panel["fips"].str[:2]
        panel = panel.merge(
            hr_states[["state_fips", "dillons_rule_state"]],
            on="state_fips", how="left"
        )
        panel["dillons_rule_state"] = panel["dillons_rule_state"].fillna(0).astype(int)
        print(f"  dillons_rule_state: {panel['dillons_rule_state'].sum() // len(panel['year_cog'].unique())} counties in Dillon's Rule states")
    else:
        print("  WARNING: home_rule_states.csv not found — dillons_rule_state omitted")
        panel["dillons_rule_state"] = np.nan

    if hr_counties_path.exists():
        hr_counties = pd.read_csv(hr_counties_path, dtype={"fips": str})
        hr_counties["fips"] = hr_counties["fips"].str.zfill(5)
        # Only use counties with confirmed pre-2015 charter (pre2015_valid == True)
        hr_valid = hr_counties[hr_counties["pre2015_valid"] == True][
            ["fips", "home_rule_county"]
        ].drop_duplicates("fips")
        panel = panel.merge(hr_valid, on="fips", how="left")
        panel["home_rule_county"] = panel["home_rule_county"].fillna(0).astype(int)
        n_hr = panel[panel["year_cog"] == 2012]["home_rule_county"].sum()
        print(f"  home_rule_county: {n_hr} counties with confirmed pre-2015 charter")
    else:
        print("  WARNING: home_rule_counties.csv not found — home_rule_county omitted")
        panel["home_rule_county"] = 0

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
