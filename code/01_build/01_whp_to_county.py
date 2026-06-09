"""
WHP raster -> county-level area-weighted mean WHP.

DESIGN NOTE — WHP 2012 does not exist as a standalone raster product.
The USFS WHP series begins with the 2014 vintage (the 2012 predecessor
was called WFP — Wildfire Potential — and used a different methodology).
WHP 2014 is predetermined for fires from 2015 onward; see 02_mtbs_to_county.py.
WHP 2014 is used here as both the primary and the robustness matching variable.
The WHP 2018 vintage is retained for reference but not used in main analysis.

Shared raw data: reads from the wildfire-health project (same rasters, no duplication).
Output: data/processed/whp_county.parquet  (one row per county, columns: fips, whp_2014)
"""

from __future__ import annotations

import warnings
from pathlib import Path

import geopandas as gpd
import numpy as np
import pandas as pd
import rasterio
from rasterio.enums import Resampling
from rasterio.warp import calculate_default_transform, reproject
from rasterstats import zonal_stats

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_RAW      = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"

# Raw spatial data shared with the companion wildfire-health project.
# Set HEALTH_RAW to the wildfire-health data/raw directory.
HEALTH_RAW = PROJECT_ROOT.parent / "wildfire-health" / "data" / "raw"

np.random.seed(42)

# 8-state finance sample: CA, CO, ID, MT, OR, UT, WA, WY
WEST_STATES = {"06", "08", "16", "30", "41", "49", "53", "56"}

TARGET_CRS = "EPSG:5070"
TIGER_URL  = "https://www2.census.gov/geo/tiger/TIGER2020/COUNTY/tl_2020_us_county.zip"


def load_county_boundaries() -> gpd.GeoDataFrame:
    tiger_path = HEALTH_RAW / "tl_2020_us_county.zip"
    if not tiger_path.exists():
        raise FileNotFoundError(
            f"County shapefile not found at {tiger_path}. "
            f"Download from: {TIGER_URL}"
        )
    counties = gpd.read_file(f"zip://{tiger_path}")
    counties = counties[counties["STATEFP"].isin(WEST_STATES)].copy()
    counties = counties.to_crs(TARGET_CRS)
    counties["fips"] = counties["STATEFP"] + counties["COUNTYFP"]
    return counties[["fips", "geometry"]].reset_index(drop=True)


def whp_raster_path(vintage: int) -> Path:
    candidates = [
        DATA_RAW / f"whp_{vintage}.tif",
        HEALTH_RAW / f"whp_{vintage}.tif",
        HEALTH_RAW / "WHP" / "Data" / f"whp_{vintage}_continuous" / f"whp{vintage}_cnt",
        HEALTH_RAW / "WHP" / "Data" / f"whp{vintage}_GeoTIF" / f"whp{vintage}_cls_conus.tif",
    ]
    for p in candidates:
        if p.exists():
            return p
    raise FileNotFoundError(
        f"WHP raster for vintage {vintage} not found. "
        f"Expected one of: {[str(c) for c in candidates]}"
    )


def reproject_raster(src_path: Path, dst_path: Path) -> None:
    with rasterio.open(src_path) as src:
        transform, width, height = calculate_default_transform(
            src.crs, TARGET_CRS, src.width, src.height, *src.bounds
        )
        kwargs = src.meta.copy()
        kwargs.update({"driver": "GTiff", "crs": TARGET_CRS,
                       "transform": transform, "width": width, "height": height})
        with rasterio.open(dst_path, "w", **kwargs) as dst:
            for i in range(1, src.count + 1):
                reproject(
                    source=rasterio.band(src, i),
                    destination=rasterio.band(dst, i),
                    src_transform=src.transform,
                    src_crs=src.crs,
                    dst_transform=transform,
                    dst_crs=TARGET_CRS,
                    resampling=Resampling.bilinear,
                )


def compute_zonal_whp(
    raster_path: Path, counties: gpd.GeoDataFrame, reproj_path: Path
) -> pd.Series:
    if not reproj_path.exists():
        with rasterio.open(raster_path) as src:
            if src.crs and src.crs.to_epsg() == 5070:
                reproj_path = raster_path
            else:
                reproject_raster(raster_path, reproj_path)

    # Read nodata from raster metadata (ESRI Grid uses -2147483647, not -9999)
    with rasterio.open(reproj_path) as src:
        raster_nodata = src.nodata

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        stats = zonal_stats(
            counties, str(reproj_path),
            stats=["mean"], nodata=raster_nodata, all_touched=False,
        )
    means = [s["mean"] if s["mean"] is not None else np.nan for s in stats]
    return pd.Series(means, index=counties["fips"].values)


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)

    counties = load_county_boundaries()
    print(f"Counties loaded: {len(counties)} ({len(WEST_STATES)} states)")

    raw_2014 = whp_raster_path(2014)
    reproj_2014 = DATA_RAW / "whp_2014_5070.tif"
    if not reproj_2014.exists():
        reproj_2014 = HEALTH_RAW / "whp_2014_5070.tif"

    print(f"Computing zonal WHP 2014 from: {raw_2014}")
    whp_2014 = compute_zonal_whp(raw_2014, counties, reproj_2014)

    df = pd.DataFrame({
        "fips":     counties["fips"].values,
        "whp_2014": whp_2014.values,
    })

    # WHP quintile for matching (quintile 1 = lowest hazard, 5 = highest)
    df["whp_q"] = pd.qcut(df["whp_2014"], q=5, labels=False, duplicates="drop") + 1

    out = DATA_PROCESSED / "whp_county.parquet"
    df.to_parquet(out, index=False)
    print(f"WHP county file: {len(df)} rows -> {out}")
    print(df[["whp_2014", "whp_q"]].describe().to_string())


if __name__ == "__main__":
    main()
