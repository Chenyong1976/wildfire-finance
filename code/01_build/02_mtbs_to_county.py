"""
MTBS fire perimeters -> county-year treatment indicators for the wildfire-finance project.

KEY DESIGN DIFFERENCES FROM WILDFIRE-HEALTH COMPANION:
  - 8-state sample: CA, CO, ID, MT, OR, UT, WA, WY (adds CO, UT; drops AZ, NV, NM)
  - Treatment window: 2013-2021. WFP 2012 is predetermined for all fires from 2013
    onward (finalized before the 2013 fire season). WHP 2014 is NOT predetermined for
    2013-2014 fires and is used only as a robustness check.
  - TWO C&S cohorts, keyed to quinquennial CoG census years:
      g=2017: first qualifying fire in 2013-2016 (post-treatment census year = 2017)
      g=2022: first qualifying fire in 2017-2021 (post-treatment census year = 2022)
  - TREAT_YEAR_MAX extended to 2021 (vs 2019 in health paper). COVID affects mortality
    outcomes but is less directly confounding for fiscal outcomes. Robustness: restrict
    g=2022 to fires 2017-2019 only (implemented in 04_robustness.R).
  - Pre-fire history window: 2000-2012 (predetermined relative to WFP 2012 vintage)

WFP/WHP VINTAGE NOTE:
  Primary: WFP 2012 (USFS Wildfire Potential 2012, RDS-2015-0045). Predetermined for
  all fires from 2013 onward — finalized before the 2013 fire season.
  Robustness: WHP 2014, which is predetermined only from 2015 onward.

Outputs:
  data/processed/mtbs_county.parquet             (annual county-year panel)
  data/processed/fire_perimeters_100km_buffer.parquet
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import geopandas as gpd
import numpy as np
import pandas as pd
from shapely.ops import unary_union

PROJECT_ROOT   = Path(__file__).resolve().parents[2]
DATA_RAW       = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

# Shared raw data from the companion wildfire-health project
HEALTH_RAW = PROJECT_ROOT.parent / "wildfire-health" / "data" / "raw"

np.random.seed(42)

# 8-state finance sample: CA CO ID MT OR UT WA WY
WEST_STATES = {"06", "08", "16", "30", "41", "49", "53", "56"}

TARGET_CRS      = "EPSG:5070"
SMOKE_BUFFER_M  = 100_000   # 100 km baseline
FIRE_ACRES_MIN  = 1_000

YEAR_MIN        = 2000
YEAR_MAX        = 2021

# Treatment window aligned to WFP 2012 predetermination (predetermined from 2013).
# 2020-2021 retained for fiscal analysis (COVID robustness in 04_robustness.R).
TREAT_YEAR_MIN = 2013
TREAT_YEAR_MAX = 2021

# C&S cohort boundaries (first post-treatment quinquennial CoG census year)
COG_COHORT_2017_MAX = 2016   # fires 2013-2016 -> g=2017
COG_COHORT_2022_MAX = 2021   # fires 2017-2021 -> g=2022

MTBS_URL  = "https://www.mtbs.gov/direct-download"
TIGER_URL = "https://www2.census.gov/geo/tiger/TIGER2020/COUNTY/tl_2020_us_county.zip"


def load_counties() -> gpd.GeoDataFrame:
    tiger_path = HEALTH_RAW / "tl_2020_us_county.zip"
    if not tiger_path.exists():
        raise FileNotFoundError(
            f"County shapefile not found at {tiger_path}. Download from: {TIGER_URL}"
        )
    counties = gpd.read_file(f"zip://{tiger_path}")
    counties = counties[counties["STATEFP"].isin(WEST_STATES)].copy()
    counties = counties.to_crs(TARGET_CRS)
    counties["fips"] = counties["STATEFP"] + counties["COUNTYFP"]
    counties["county_area"] = counties.geometry.area
    counties["centroid"]    = counties.geometry.centroid
    return counties[["fips", "geometry", "county_area", "centroid"]].reset_index(drop=True)


def load_mtbs_perimeters() -> gpd.GeoDataFrame:
    """
    Load MTBS perimeters, normalise columns, filter to analysis window/size,
    then reproject to TARGET_CRS. Filtering before reprojection avoids OOM
    errors when handling the full national dataset (~33M vertices).
    """
    candidates = [
        HEALTH_RAW / "mtbs_perims" / "S_USA.MTBS_BURN_AREA_BOUNDARY.shp",
        DATA_RAW   / "mtbs_perims" / "S_USA.MTBS_BURN_AREA_BOUNDARY.shp",
        HEALTH_RAW / "mtbs_perims_DD" / "mtbs_perims_DD.shp",
    ]
    fires: Optional[gpd.GeoDataFrame] = None
    for path in candidates:
        if path.exists():
            fires = gpd.read_file(str(path))
            break
    if fires is None:
        raise FileNotFoundError(
            f"MTBS perimeter shapefile not found. Download from: {MTBS_URL}"
        )

    year_col = next((c for c in fires.columns if c.lower() in ("fire_year", "year")), None)
    if year_col is None:
        raise KeyError("Cannot identify year column in MTBS data.")
    fires = fires.rename(columns={year_col: "fire_year"})
    fires["fire_year"] = fires["fire_year"].astype(int)

    acre_col = next(
        (c for c in fires.columns if c.lower() in ("burnbndac", "acres", "gis_acres")), None
    )
    if acre_col is None:
        raise KeyError("Cannot identify acreage column in MTBS data.")
    fires = fires.rename(columns={acre_col: "fire_acres"})
    fires["fire_acres"] = pd.to_numeric(fires["fire_acres"], errors="coerce")

    sev_col = next((c for c in fires.columns if c.lower() in ("dnbrcat", "severity")), None)
    fires["severity_raw"] = (
        pd.to_numeric(fires[sev_col], errors="coerce") if sev_col else np.nan
    )

    # HIGH_THRES: per-fire dNBR threshold for the High-severity class.
    # Values 100–5000 are valid thresholds set by MTBS analysts (indicating detectable
    # high-severity burning). Sentinel values 9999 / -9999 mean no high-severity class
    # was identified (typically low-moderate severity fires, e.g. sage brush burns).
    high_col = next((c for c in fires.columns if c.lower() == "high_thres"), None)
    if high_col:
        fires["high_thres_raw"] = pd.to_numeric(fires[high_col], errors="coerce")
    else:
        fires["high_thres_raw"] = np.nan
    fires["high_sev_flag"] = fires["high_thres_raw"].between(100, 5000).astype(int)

    # Filter to analysis window BEFORE reprojection to avoid OOM on full dataset
    fires = fires[
        (fires["fire_year"] >= YEAR_MIN)
        & (fires["fire_year"] <= YEAR_MAX)
        & (fires["fire_acres"] >= FIRE_ACRES_MIN)
    ].copy()

    fires = fires.to_crs(TARGET_CRS)
    return fires


def filter_fires(fires: gpd.GeoDataFrame) -> gpd.GeoDataFrame:
    # Data is already filtered in load_mtbs_perimeters(); this is a no-op passthrough.
    return fires.copy()


def assign_fires_to_counties(
    fires: gpd.GeoDataFrame, counties: gpd.GeoDataFrame
) -> gpd.GeoDataFrame:
    """
    Spatial join using intersection area.
    County is treated if intersection >= 1% of county area OR >= 10% of fire area.
    """
    fires_v    = fires[fires.geometry.is_valid].copy()
    # Strip non-geometry attribute columns before overlay to avoid column conflicts;
    # 'centroid' is a geometry-type column and can confuse geopandas overlay.
    counties_v = counties[counties.geometry.is_valid][["fips", "geometry"]].copy()
    county_areas = counties[["fips", "county_area"]].copy()

    joined = gpd.overlay(counties_v, fires_v, how="intersection", keep_geom_type=False)
    joined["intersection_area"] = joined.geometry.area
    joined = joined.merge(county_areas, on="fips", how="left")

    fire_areas = fires_v.copy()
    fire_areas["fire_geom_area"] = fire_areas.geometry.area

    id_col = next(
        (c for c in fires_v.columns if c.lower() in ("event_id", "fire_id", "objectid")), None
    )
    if id_col:
        joined = joined.merge(fire_areas[[id_col, "fire_geom_area"]], on=id_col, how="left")
    else:
        fire_areas["_key"] = (
            fire_areas["fire_year"].astype(str) + "_" + fire_areas["fire_acres"].round(1).astype(str)
        )
        joined["_key"] = (
            joined["fire_year"].astype(str) + "_" + joined["fire_acres"].round(1).astype(str)
        )
        joined = joined.merge(fire_areas[["_key", "fire_geom_area"]], on="_key", how="left")

    pct_county = joined["intersection_area"] / joined["county_area"].replace(0, np.nan)
    pct_fire   = joined["intersection_area"] / joined["fire_geom_area"].replace(0, np.nan)
    joined["overlap_flag"] = (pct_county >= 0.01) | (pct_fire >= 0.10)
    return joined[joined["overlap_flag"]].copy()


def build_county_year_panel(
    joined: gpd.GeoDataFrame, counties: gpd.GeoDataFrame
) -> pd.DataFrame:
    agg = (
        joined.groupby(["fips", "fire_year"])
        .agg(
            fire_count=("fire_acres", "count"),
            total_acres=("fire_acres", "sum"),
            mean_severity=("severity_raw", "mean"),
            has_high_sev_fire=("high_sev_flag", "max"),   # 1 if any intersecting fire
        )                                                  # had a valid HIGH_THRES class
        .reset_index()
        .rename(columns={"fire_year": "year"})
    )
    agg["fire_in_year"] = 1
    agg["log_acres"]    = np.log1p(agg["total_acres"])
    agg["mtbs_severity"] = agg["mean_severity"].fillna(0)

    all_fips  = counties["fips"].unique()
    full_panel = pd.DataFrame(
        [(f, y) for f in all_fips for y in range(YEAR_MIN, YEAR_MAX + 1)],
        columns=["fips", "year"],
    )
    panel = full_panel.merge(
        agg[["fips", "year", "fire_in_year", "log_acres", "mtbs_severity",
             "has_high_sev_fire"]],
        on=["fips", "year"], how="left",
    )
    panel["fire_in_year"]     = panel["fire_in_year"].fillna(0).astype(int)
    panel["log_acres"]        = panel["log_acres"].fillna(0)
    panel["mtbs_severity"]    = panel["mtbs_severity"].fillna(0)
    panel["has_high_sev_fire"] = panel["has_high_sev_fire"].fillna(0).astype(int)

    # --- Intensive margin treatment: high-severity fires only ---
    # HIGH_THRES in (100, 5000) = MTBS identified a distinct high-severity dNBR class.
    # HIGH_THRES=9999 is a sentinel meaning no high-severity class was detected.
    panel["treated"] = (
        (panel["has_high_sev_fire"] == 1)
        & (panel["year"] >= TREAT_YEAR_MIN)
        & (panel["year"] <= TREAT_YEAR_MAX)
    ).astype(int)

    # g: intensive-margin cohort — first CoG census year after first high-severity fire.
    first_treated = (
        panel[panel["treated"] == 1]
        .groupby("fips")["year"]
        .min()
        .rename("first_fire_year")
        .reset_index()
    )
    first_treated["g"] = np.where(
        first_treated["first_fire_year"] <= COG_COHORT_2017_MAX, 2017, 2022
    )
    panel = panel.merge(first_treated[["fips", "g"]], on="fips", how="left")
    panel["g"] = panel["g"].fillna(0).astype(int)

    # --- Extensive margin treatment: any qualifying fire (≥1,000 acres) ---
    panel["treated_any"] = (
        (panel["fire_in_year"] == 1)
        & (panel["year"] >= TREAT_YEAR_MIN)
        & (panel["year"] <= TREAT_YEAR_MAX)
    ).astype(int)

    # g_any: extensive-margin cohort — first CoG census year after first qualifying fire.
    first_any = (
        panel[panel["treated_any"] == 1]
        .groupby("fips")["year"]
        .min()
        .rename("first_any_year")
        .reset_index()
    )
    first_any["g_any"] = np.where(
        first_any["first_any_year"] <= COG_COHORT_2017_MAX, 2017, 2022
    )
    panel = panel.merge(first_any[["fips", "g_any"]], on="fips", how="left")
    panel["g_any"] = panel["g_any"].fillna(0).astype(int)

    # Pre-2013 fire history (2000-2012): matching covariate.
    # Consistent with WFP 2012 predetermination (history through end of 2012).
    pre_fire = (
        panel[(panel["fire_in_year"] == 1) & (panel["year"] <= 2012)]
        .groupby("fips")
        .agg(
            pre2013_fire_count=("fire_in_year", "sum"),
            pre2013_log_acres=("log_acres", "sum"),
        )
        .reset_index()
    )
    pre_fire["pre2013_fire"] = 1
    panel = panel.merge(pre_fire, on="fips", how="left")
    panel["pre2013_fire"]       = panel["pre2013_fire"].fillna(0).astype(int)
    panel["pre2013_fire_count"] = panel["pre2013_fire_count"].fillna(0).astype(int)
    panel["pre2013_log_acres"]  = panel["pre2013_log_acres"].fillna(0)

    return panel


def compute_smoke_buffer(
    fires: gpd.GeoDataFrame, counties: gpd.GeoDataFrame, buffer_m: float = SMOKE_BUFFER_M
) -> pd.DataFrame:
    centroid_gdf = gpd.GeoDataFrame(
        counties[["fips"]].copy(), geometry=counties["centroid"].values, crs=TARGET_CRS
    )
    rows = []
    for year in range(YEAR_MIN, YEAR_MAX + 1):
        year_fires = fires[fires["fire_year"] == year]
        if len(year_fires) == 0:
            rows.append(pd.DataFrame({"fips": counties["fips"], "year": year, "excl_flag": 0}))
            continue
        dissolved = unary_union(year_fires.geometry.buffer(buffer_m))
        within = centroid_gdf.geometry.within(dissolved)
        rows.append(pd.DataFrame({
            "fips": counties["fips"].values,
            "year": year,
            "excl_flag": within.astype(int).values,
        }))
    return pd.concat(rows, ignore_index=True)


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    counties = load_counties()
    print(f"Counties: {len(counties)} ({len(WEST_STATES)} states)")

    fires_raw = load_mtbs_perimeters()
    fires     = filter_fires(fires_raw)
    print(f"MTBS fires (>={FIRE_ACRES_MIN} ac, {YEAR_MIN}-{YEAR_MAX}): {len(fires):,}")

    joined = assign_fires_to_counties(fires, counties)
    panel  = build_county_year_panel(joined, counties)

    smoke_excl = compute_smoke_buffer(fires, counties, SMOKE_BUFFER_M)
    smoke_excl = smoke_excl.rename(columns={"excl_flag": "smoke_buffer_excl"})
    panel = panel.merge(smoke_excl, on=["fips", "year"], how="left")
    panel["smoke_buffer_excl"] = panel["smoke_buffer_excl"].fillna(0).astype(int)

    panel.to_parquet(DATA_PROCESSED / "mtbs_county.parquet", index=False)
    smoke_excl.rename(columns={"smoke_buffer_excl": "excl_flag"}).to_parquet(
        DATA_PROCESSED / "fire_perimeters_100km_buffer.parquet", index=False
    )

    n_g2017  = panel[panel["g"] == 2017]["fips"].nunique()
    n_g2022  = panel[panel["g"] == 2022]["fips"].nunique()
    n_never  = panel[panel["g"] == 0]["fips"].nunique()
    n_any_fire = panel[panel["g"].isin([2017, 2022])]["fips"].nunique()
    print(
        f"\nMTBS county panel (SEVERITY-BASED TREATMENT): {len(panel):,} county-years\n"
        f"  Treatment = fires with detectable High-severity class (HIGH_THRES in 100-5000)\n"
        f"  g=2017 (sev. fires 2013-2016): {n_g2017} counties\n"
        f"  g=2022 (sev. fires 2017-2021): {n_g2022} counties\n"
        f"  Never treated (g=0):           {n_never} counties\n"
        f"  Total treated:                 {n_any_fire} counties\n"
        f"  Smoke-excluded (any year):     {panel['smoke_buffer_excl'].sum():,} county-years"
    )


if __name__ == "__main__":
    main()
