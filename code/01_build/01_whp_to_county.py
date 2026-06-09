"""
WFP/WHP raster -> county-level area-weighted mean hazard score.

PRIMARY: WFP 2012 (USFS Wildfire Potential 2012, RDS-2015-0045).
  - Predetermined for all fires from 2013 onward (finalized before 2013 fire season)
  - ESRI Grid format, already EPSG:5070, nodata = -2147483647
  - Path: data/raw/WHP/Data/wfp_2012_continuous/wfp2012_cnt

ROBUSTNESS: WHP 2014 (shared from wildfire-health project).
  - Predetermined for fires from 2015 onward
  - Same format, same nodata value

Output: data/processed/whp_county.parquet
  Columns: fips, whp_2012, whp_2014, whp_q (quintile of whp_2012)
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

PROJECT_ROOT   = Path(__file__).resolve().parents[2]
DATA_RAW       = PROJECT_ROOT / "data" / "raw"
DATA_PROCESSED = PROJECT_ROOT / "data" / "processed"
HEALTH_RAW     = PROJECT_ROOT.parent / "wildfire-health" / "data" / "raw"

np.random.seed(42)

WEST_STATES = {"06", "08", "16", "30", "41", "49", "53", "56"}
TARGET_CRS  = "EPSG:5070"
TIGER_URL   = "https://www2.census.gov/geo/tiger/TIGER2020/COUNTY/tl_2020_us_county.zip"

RASTER_CANDIDATES: dict[int, list[Path]] = {
    2012: [
        DATA_RAW  / "WHP" / "Data" / "wfp_2012_continuous" / "wfp2012_cnt",
    ],
    2014: [
        DATA_RAW  / "WHP" / "Data" / "whp_2014_continuous" / "whp2014_cnt",
        HEALTH_RAW / "WHP" / "Data" / "whp_2014_continuous" / "whp2014_cnt",
        HEALTH_RAW / "WHP" / "Data" / "whp2014_GeoTIF" / "whp2014_cls_conus.tif",
        HEALTH_RAW / "whp_2014.tif",
    ],
}


def load_county_boundaries() -> gpd.GeoDataFrame:
    tiger_path = HEALTH_RAW / "tl_2020_us_county.zip"
    if not tiger_path.exists():
        raise FileNotFoundError(f"County shapefile not found: {tiger_path}. Download from: {TIGER_URL}")
    counties = gpd.read_file(f"zip://{tiger_path}")
    counties = counties[counties["STATEFP"].isin(WEST_STATES)].copy()
    counties = counties.to_crs(TARGET_CRS)
    counties["fips"] = counties["STATEFP"] + counties["COUNTYFP"]
    return counties[["fips", "geometry"]].reset_index(drop=True)


def raster_path(vintage: int) -> Path:
    for p in RASTER_CANDIDATES[vintage]:
        if p.exists():
            return p
    raise FileNotFoundError(f"Raster for vintage {vintage} not found. Checked: {RASTER_CANDIDATES[vintage]}")


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


def compute_zonal(raw_path: Path, counties: gpd.GeoDataFrame, label: str) -> pd.Series:
    """Area-weighted mean raster value per county. Reads nodata from raster metadata."""
    reproj_path = DATA_RAW / f"{label}_5070.tif"

    if not reproj_path.exists():
        with rasterio.open(raw_path) as src:
            if src.crs and src.crs.to_epsg() == 5070:
                reproj_path = raw_path   # already projected; use directly
            else:
                print(f"  Reprojecting {label} to EPSG:5070...")
                reproject_raster(raw_path, reproj_path)

    with rasterio.open(reproj_path) as src:
        nodata = src.nodata

    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        stats = zonal_stats(
            counties, str(reproj_path),
            stats=["mean"], nodata=nodata, all_touched=False,
        )
    means = [s["mean"] if s["mean"] is not None else np.nan for s in stats]
    return pd.Series(means, index=counties["fips"].values, name=label)


def main() -> None:
    DATA_PROCESSED.mkdir(parents=True, exist_ok=True)
    counties = load_county_boundaries()
    print(f"Counties: {len(counties)}")

    series = {}
    for vintage, label in [(2012, "whp_2012"), (2014, "whp_2014")]:
        raw = raster_path(vintage)
        print(f"Computing {label} from: {raw}")
        series[label] = compute_zonal(raw, counties, label)

    df = pd.DataFrame({"fips": counties["fips"].values})
    for label, s in series.items():
        df[label] = s.values

    # Primary quintile from WFP 2012 (matching variable for 2013-2021 treatment cohorts)
    df["whp_q"] = pd.qcut(df["whp_2012"], q=5, labels=False, duplicates="drop") + 1

    out = DATA_PROCESSED / "whp_county.parquet"
    df.to_parquet(out, index=False)
    print(f"Output: {len(df)} rows -> {out}")
    print(df[["whp_2012", "whp_2014", "whp_q"]].describe().round(1).to_string())


if __name__ == "__main__":
    main()
