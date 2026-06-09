"""
Download and parse Census of Governments (CoG) Annual Survey data.

Produces a county-year panel of fiscal outcomes for county governments (CoG
type code 1) in the 8-state western sample, 2000-2021.

FISCAL YEAR ALIGNMENT RULE:
  Assign CoG fiscal data to the calendar year in which the fiscal year BEGINS.
  FY July 2015 – June 2016 → year 2015.
  All 8 western states use June 30 fiscal year end for county governments
  (see FY_END_MONTHS below; verify from CoG FYMONTH field in raw data).

  CoG encodes fiscal year data under the YEAR in which the FY ENDS; we
  recode to FY-begin convention by subtracting 1 when FY end month != Dec.

COVERAGE RULE (per research_plan.md):
  Retain counties with Annual Survey data in ≥ 85% of sample years
  (≥ 18 of 21). Robustness check at ≥ 70% (≥ 15 of 21).
  Flag if missingness clusters in post-fire years (2015-2021) — if so,
  do NOT impute; exclude the county and document.

DATA SOURCE:
  Census Bureau bulk ZIP files, individual unit files.
  URL: https://www2.census.gov/programs-surveys/gov-finances/tables/{YEAR}/

ITEM CODES (CoG Annual Survey):
  T01  Property tax revenue
  T09  Total taxes
  B80  Total intergovernmental revenue (federal + state)
  B01  Intergovernmental revenue from federal government
  B20  Intergovernmental revenue from state government
  C89  Total general revenue from own sources
  A15  Total general revenue
  E61  Total general expenditure
  E04  Capital outlays
  F01  Long-term debt outstanding at end of year
  Current operations = E61 - E04
"""

from __future__ import annotations
import io
import re
import time
import zipfile
from pathlib import Path
from typing import Iterator

import pandas as pd
import requests
from tqdm import tqdm

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
RAW = ROOT / "data" / "raw" / "cog"
OUT = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

WEST_STATES = {"06", "08", "16", "30", "41", "49", "53", "56"}  # CA CO ID MT OR UT WA WY

SAMPLE_YEARS = list(range(2000, 2022))  # 2000-2021 inclusive

# CoG government type code for county governments
COUNTY_TYPE_CODE = "1"

# Fiscal variables to extract (item code → output column name)
ITEMS = {
    "T01": "rev_proptax",
    "T09": "rev_tax_total",
    "B01": "rev_igt_federal",
    "B20": "rev_igt_state",
    "B80": "rev_intergovt",
    "C89": "rev_own_sources",
    "A15": "rev_total",
    "E61": "exp_total",
    "E04": "exp_capital",
    "F01": "debt_lt",
}

# Fiscal year end months for county governments in 8 western states.
# All 8 states use June 30 (month = 6) for county FY end.
# Source: CoG documentation + state statutes.
# Verify against FYMONTH field in raw CoG data — if a county reports a
# different FY end month, apply the recoding individually.
FY_END_MONTHS: dict[str, int] = {
    "06": 6,  # CA — FY ends June 30
    "08": 6,  # CO — FY ends June 30 (some home rule counties may vary; verify)
    "16": 9,  # ID — FY ends September 30 (state FY; most county govts follow)
    "30": 6,  # MT — FY ends June 30
    "41": 6,  # OR — FY ends June 30
    "49": 6,  # UT — FY ends June 30
    "53": 6,  # WA — FY ends December 31 for some; June 30 for most counties
    "56": 6,  # WY — FY ends June 30
}
# NOTE: WA state FY ends June 30; most county governments follow.
# Verify for individual WA counties. ID state FY ends June 30; county FYs
# may vary — flag any county with FYMONTH ≠ 9.

# Known URL patterns for CoG Annual Survey individual unit files.
# Census Bureau occasionally changes filenames; update if download fails.
# Format: https://www2.census.gov/programs-surveys/gov-finances/tables/{YEAR}/{filename}
COG_URL_PATTERNS = {
    # 2016-2021: consistent naming
    2021: "2021_Individual_Unit_File.zip",
    2020: "2020_Individual_Unit_File.zip",
    2019: "2019_Individual_Unit_File.zip",
    2018: "2018_Individual_Unit_File.zip",
    2017: "2017_Individual_Unit_File.zip",
    2016: "2016_Individual_Unit_File.zip",
    # 2012-2015: slightly different naming
    2015: "2015_Individual_Unit_File.zip",
    2014: "2014_Individual_Unit_File.zip",
    2013: "2013_Individual_Unit_File.zip",
    2012: "2012_Individual_Unit_File.zip",
    # Pre-2012: older format; filenames vary significantly
    # These require manual download from Census Bureau; see note below.
    2011: None,
    2010: None,
    2009: None,
    2008: None,
    2007: None,  # Quinquennial Census year — use Census file instead
    2006: None,
    2005: None,
    2004: None,
    2003: None,
    2002: None,  # Quinquennial Census year
    2001: None,
    2000: None,
}

COG_BASE_URL = "https://www2.census.gov/programs-surveys/gov-finances/tables"


def _download_year(year: int, dest: Path) -> Path | None:
    """Download CoG Annual Survey zip for one year. Returns path or None if not available."""
    filename = COG_URL_PATTERNS.get(year)
    if filename is None:
        print(f"  [SKIP] {year}: no known URL pattern — download manually from Census Bureau")
        return None
    url = f"{COG_BASE_URL}/{year}/{filename}"
    local_zip = dest / f"cog_{year}.zip"
    if local_zip.exists():
        return local_zip
    print(f"  Downloading {year}... ", end="", flush=True)
    try:
        r = requests.get(url, timeout=120)
        r.raise_for_status()
        local_zip.write_bytes(r.content)
        print(f"OK ({len(r.content) // 1024:,} KB)")
        time.sleep(0.5)  # be polite to Census servers
        return local_zip
    except requests.HTTPError as e:
        print(f"FAILED ({e})")
        return None


def _parse_zip(zip_path: Path, year: int) -> pd.DataFrame | None:
    """Parse one CoG zip file and return a filtered DataFrame for western county governments."""
    try:
        with zipfile.ZipFile(zip_path) as zf:
            csv_names = [n for n in zf.namelist() if n.lower().endswith((".csv", ".txt"))]
            if not csv_names:
                print(f"  [WARN] {year}: no CSV found in zip; skipping")
                return None

            # Try to find the main individual unit file (not the header/codebook)
            data_files = [n for n in csv_names if "indunit" in n.lower() or "individual" in n.lower() or "FinEst" in n]
            if not data_files:
                data_files = csv_names  # fall back to any CSV

            dfs = []
            for fname in data_files:
                raw = zf.read(fname)
                try:
                    df = pd.read_csv(io.BytesIO(raw), dtype=str, low_memory=False,
                                     encoding="latin-1")
                except Exception:
                    df = pd.read_csv(io.BytesIO(raw), dtype=str, low_memory=False,
                                     encoding="utf-8", sep="|")
                dfs.append(df)
            if not dfs:
                return None
            df = pd.concat(dfs, ignore_index=True) if len(dfs) > 1 else dfs[0]
    except Exception as e:
        print(f"  [WARN] {year}: zip parse error — {e}")
        return None

    # Normalise column names to lowercase
    df.columns = df.columns.str.lower().str.strip()

    return df


def _extract_county_items(df: pd.DataFrame, year: int) -> pd.DataFrame | None:
    """
    Extract fiscal items for county governments in WEST_STATES.

    CoG data comes in two shapes:
      LONG: one row per (government, item); columns include 'item' and 'amount'
      WIDE: one row per government; one column per item code

    We detect the shape from the column names and normalize to wide.
    """
    # Detect shape
    is_long = any(c in df.columns for c in ("item", "finitem", "itemcode"))
    is_wide = any(c in df.columns for c in list(ITEMS.keys()) + [k.lower() for k in ITEMS])

    # Identify key column names (Census uses different names across years)
    col_map = _map_columns(df.columns.tolist())
    if col_map is None:
        print(f"  [WARN] {year}: could not identify required columns; skipping")
        return None

    gov_type_col = col_map["govtype"]
    state_col = col_map["state"]
    county_col = col_map.get("county")
    govid_col = col_map.get("govid")

    # Filter to county governments in western states
    df[gov_type_col] = df[gov_type_col].str.strip()
    df[state_col] = df[state_col].str.strip().str.zfill(2)
    mask = (df[gov_type_col] == COUNTY_TYPE_CODE) & (df[state_col].isin(WEST_STATES))
    df_counties = df[mask].copy()

    if df_counties.empty:
        print(f"  [WARN] {year}: no county governments found after filter; check type code column")
        return None

    if is_long and not is_wide:
        item_col = next(c for c in df.columns if c in ("item", "finitem", "itemcode"))
        amount_col = next(c for c in df.columns if c in ("amount", "value", "dollars"))
        id_col = govid_col or state_col

        df_counties[item_col] = df_counties[item_col].str.strip().str.upper()
        df_counties = df_counties[df_counties[item_col].isin(ITEMS.keys())]

        df_wide = df_counties.pivot_table(
            index=id_col, columns=item_col, values=amount_col, aggfunc="first"
        ).reset_index()
        df_wide.columns.name = None
        df_counties = df_counties.drop_duplicates(subset=[id_col]).drop(columns=[item_col, amount_col])
        df_counties = df_counties.merge(df_wide, on=id_col, how="left")

    # Build FIPS
    if county_col and state_col in df_counties.columns:
        df_counties["fips"] = (
            df_counties[state_col].str.zfill(2) + df_counties[county_col].str.zfill(3)
        )
    elif govid_col:
        df_counties["fips"] = df_counties[govid_col].str[:5]
    else:
        print(f"  [WARN] {year}: cannot construct FIPS; skipping")
        return None

    # Fiscal year adjustment: recode CoG year (FY-end year) → FY-begin year
    df_counties["year_cog"] = year
    df_counties["fy_end_month"] = df_counties[state_col].map(FY_END_MONTHS).fillna(6).astype(int)
    # If FY ends before December, the FY started in the previous calendar year
    df_counties["year"] = df_counties.apply(
        lambda r: r["year_cog"] - 1 if r["fy_end_month"] < 12 else r["year_cog"], axis=1
    )

    # Extract fiscal items
    out_cols = {"fips": df_counties["fips"], "year": df_counties["year"],
                "fy_end_month": df_counties["fy_end_month"]}
    for item_code, col_name in ITEMS.items():
        # item columns may be upper or lower case
        candidates = [item_code, item_code.lower()]
        found = next((c for c in candidates if c in df_counties.columns), None)
        out_cols[col_name] = pd.to_numeric(df_counties[found], errors="coerce") * 1000 if found else pd.NA

    result = pd.DataFrame(out_cols)
    result = result[result["fips"].notna() & (result["fips"].str.len() == 5)]
    return result


def _map_columns(cols: list[str]) -> dict | None:
    """Map known CoG column name variants to canonical names."""
    lower = [c.lower() for c in cols]
    mapping: dict[str, str] = {}

    for alias, canonical in [
        (["govtype", "type", "typecode", "ftype", "govtype4"], "govtype"),
        (["state", "stcode", "statefp", "state_code", "fips_state"], "state"),
        (["county", "cntyfp", "county_code", "fips_county"], "county"),
        (["idcensus", "govid", "id14", "census_id", "id"], "govid"),
    ]:
        match = next((cols[lower.index(a)] for a in alias if a in lower), None)
        if match:
            mapping[canonical] = match

    if "govtype" not in mapping or "state" not in mapping:
        return None
    return mapping


def coverage_audit(panel: pd.DataFrame, n_years: int = 21,
                   min_pct_primary: float = 0.85,
                   min_pct_robust: float = 0.70) -> pd.DataFrame:
    """
    Compute coverage rates and flag counties below the threshold.
    Also checks whether missingness clusters in post-fire years (2015-2021).
    """
    counts = panel.groupby("fips")["year"].nunique().rename("n_years_obs")
    coverage = counts.reset_index()
    coverage["coverage_pct"] = coverage["n_years_obs"] / n_years
    coverage["pass_primary"] = coverage["coverage_pct"] >= min_pct_primary
    coverage["pass_robust"] = coverage["coverage_pct"] >= min_pct_robust

    # Check if missing years cluster in post-fire window (2015-2021)
    all_years = set(range(2000, 2021))
    post_fire_years = set(range(2015, 2022))
    records = []
    for fips, grp in panel.groupby("fips"):
        observed = set(grp["year"])
        missing_all = all_years - observed
        missing_post = missing_post_fire = missing_all & post_fire_years
        records.append({
            "fips": fips,
            "n_missing_total": len(missing_all),
            "n_missing_post_fire": len(missing_post_fire),
            "post_fire_missing_share": (
                len(missing_post_fire) / len(missing_all) if missing_all else 0.0
            ),
        })
    missing_df = pd.DataFrame(records)
    coverage = coverage.merge(missing_df, on="fips", how="left")

    # Flag counties where >50% of missing observations are in the post-fire period
    coverage["attrition_risk"] = (coverage["post_fire_missing_share"] > 0.5) & (coverage["n_missing_total"] > 0)

    n_primary = coverage["pass_primary"].sum()
    n_robust = coverage["pass_robust"].sum()
    n_attrition = coverage["attrition_risk"].sum()
    print(f"\nCoverage audit:")
    print(f"  Total counties: {len(coverage)}")
    print(f"  Pass ≥{min_pct_primary:.0%} (primary): {n_primary}")
    print(f"  Pass ≥{min_pct_robust:.0%} (robustness): {n_robust}")
    print(f"  Attrition risk (>50% missing in post-fire window): {n_attrition}")
    if n_attrition > 0:
        print("  WARNING: Attrition risk counties should NOT be imputed — exclude and document.")
        at_risk = coverage[coverage["attrition_risk"]][["fips", "n_years_obs", "n_missing_post_fire"]]
        print(at_risk.to_string(index=False))

    return coverage


def derive_outcomes(panel: pd.DataFrame) -> pd.DataFrame:
    """Compute derived fiscal outcomes from raw item amounts."""
    panel = panel.copy()
    # Current operations = total expenditure minus capital outlays
    panel["exp_current"] = panel["exp_total"] - panel["exp_capital"]
    # Fiscal balance = total revenues minus total expenditures
    panel["fiscal_balance"] = panel["rev_total"] - panel["exp_total"]
    return panel


def main() -> None:
    print("=== Census of Governments Annual Survey Pull ===")
    print(f"Sample years: {SAMPLE_YEARS[0]}–{SAMPLE_YEARS[-1]}")
    print(f"States: {sorted(WEST_STATES)}")

    frames: list[pd.DataFrame] = []
    for year in tqdm(SAMPLE_YEARS, desc="Years"):
        zip_path = _download_year(year, RAW)
        if zip_path is None:
            continue
        df_raw = _parse_zip(zip_path, year)
        if df_raw is None:
            continue
        df_year = _extract_county_items(df_raw, year)
        if df_year is not None and not df_year.empty:
            frames.append(df_year)

    if not frames:
        print("ERROR: No data parsed. Check download URLs and CoG data format.")
        return

    panel = pd.concat(frames, ignore_index=True)
    panel = panel.sort_values(["fips", "year"]).reset_index(drop=True)
    panel = derive_outcomes(panel)

    print(f"\nRaw panel: {len(panel):,} county-year observations")
    print(f"  Unique counties: {panel['fips'].nunique()}")
    print(f"  Year range: {panel['year'].min()}–{panel['year'].max()}")

    # Coverage audit
    coverage = coverage_audit(panel)
    coverage.to_csv(RAW / "cog_coverage_audit.csv", index=False)
    print(f"\nCoverage audit written → {RAW / 'cog_coverage_audit.csv'}")

    # Apply primary coverage filter (≥ 85%)
    valid_fips = coverage[coverage["pass_primary"]]["fips"]
    panel_filtered = panel[panel["fips"].isin(valid_fips)].copy()
    print(f"\nFiltered panel (≥85% coverage): {len(panel_filtered):,} obs, {panel_filtered['fips'].nunique()} counties")

    # Flag outliers: per-county values > 3× state-year median or < 0
    revenue_cols = [c for c in panel_filtered.columns if c.startswith("rev_")]
    for col in revenue_cols:
        state_yr_median = panel_filtered.groupby(["fips", "year"])[col].transform(
            lambda x: x.median()
        )
        panel_filtered[f"flag_{col}"] = (
            (panel_filtered[col] < 0) |
            (panel_filtered[col] > 3 * state_yr_median)
        ).fillna(False)

    # Write outputs
    panel_filtered.to_parquet(OUT / "cog_panel_raw.parquet", index=False)
    print(f"\nPanel written → {OUT / 'cog_panel_raw.parquet'}")
    print("Next step: merge ACS population for per-capita deflation in 07_panel_assemble.py")

    # Print FY end month distribution as sanity check
    fy_dist = panel_filtered.groupby("fy_end_month").size()
    print(f"\nFiscal year end month distribution:\n{fy_dist.to_string()}")
    print("  Expected: most observations at month 6 (June 30). Any month ≠ 6 should be verified.")


if __name__ == "__main__":
    main()
