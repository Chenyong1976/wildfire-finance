"""
Download and parse Census of Governments (CoG) Annual Survey data.

Produces a county-year panel of fiscal outcomes for county governments (CoG
type code 1) in the 8-state western sample, 2000-2021.

FISCAL YEAR ALIGNMENT RULE:
  Assign CoG fiscal data to the calendar year in which the fiscal year BEGINS.
  FY July 2015 – June 2016 -> year 2015.
  All 8 western states use June 30 fiscal year end for county governments
  (see FY_END_MONTHS below; verify from CoG FYMONTH field in raw data).

  CoG encodes fiscal year data under the YEAR in which the FY ENDS; we
  recode to FY-begin convention by subtracting 1 when FY end month != Dec.

COVERAGE RULE (per research_plan.md):
  Retain counties with Annual Survey data in >= 85% of sample years
  (>= 18 of 21). Robustness check at >= 70% (>= 15 of 21).
  Flag if missingness clusters in post-fire years (2015-2021); if so,
  do NOT impute -- exclude the county and document.

DATA SOURCE — THREE ERAS:

  2000-2012:  Historical archive (wide format, one row per government per year)
              https://www2.census.gov/programs-surveys/gov-finances/datasets/
              historical/_IndFin_1967-2012.zip (~250 MB, downloaded once)
              Contains IndFin00a/b/c.Txt through IndFin12a/b/c.Txt.
              Key columns: Year4, Type Code, FIPS Code-State, County,
              Property Tax, General Revenue, General Expenditure, etc.

  2013-2016:  Fixed-width long format (34 chars/record, 14-char gov ID)
              https://www2.census.gov/programs-surveys/gov-finances/datasets/
              {YEAR}/public-use-datasets/{YEAR}FinEstDAT_*_pu.txt (inside zip)
              Record layout: [0:14] gov ID, [14:17] item code,
              [17:29] amount ($000s, right-justified), [29:33] year, [33] flag
              Gov ID: [0:2]=state FIPS, [2]=type (1=county), [3:6]=county FIPS,
              [6:14]=local ID (8 chars, vs 6 chars in 2017+ format)

  2017-2021:  Fixed-width long format (32 chars/record, 12-char gov ID)
              https://www2.census.gov/programs-surveys/gov-finances/tables/
              {YEAR}/{YEAR}_Individual_Unit_File.zip
              Record layout: [0:12] gov ID, [12:15] item code,
              [15:27] amount ($000s, right-justified), [27:31] year, [31] flag
              Gov ID: [0:2]=state FIPS, [2]=type (1=county), [3:6]=county FIPS,
              [6:12]=local ID (6 chars)

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
COUNTY_TYPE = "1"  # CoG government type code for county governments

# Fiscal year end months for county governments in 8 western states.
# Most use June 30 (month=6); Idaho counties typically use September 30 (month=9).
# Verify for individual counties from CoG FYENDMO field when available.
FY_END_MONTHS: dict[str, int] = {
    "06": 6,  # CA
    "08": 6,  # CO (some home rule counties may vary)
    "16": 9,  # ID (county governments follow state FY ending Sep 30)
    "30": 6,  # MT
    "41": 6,  # OR
    "49": 6,  # UT
    "53": 6,  # WA (most counties; verify individual counties)
    "56": 6,  # WY
}

# ---------------------------------------------------------------------------
# URL PATTERNS
# ---------------------------------------------------------------------------
COG_HIST_URL = (
    "https://www2.census.gov/programs-surveys/gov-finances/datasets/historical/"
    "_IndFin_1967-2012.zip"
)
HIST_YEARS = set(range(2000, 2013))   # covered by historical archive

# 2013-2016: individual unit files exist under datasets/{year}/public-use-datasets/
# Filename patterns vary by year; resolved dynamically in parse_individual_unit_file().
GAP_YEAR_BASE = "https://www2.census.gov/programs-surveys/gov-finances/datasets/{year}/public-use-datasets/"
GAP_YEAR_FILES: dict[int, str] = {
    2013: "https://www2.census.gov/programs-surveys/gov-finances/datasets/2013/public-use-datasets/2013-individual-unit-file-revised.zip",
    2014: "https://www2.census.gov/programs-surveys/gov-finances/datasets/2014/public-use-datasets/2014-individual-unit-file.zip",
    2015: "https://www2.census.gov/programs-surveys/gov-finances/datasets/2015/public-use-datasets/2015-individual-unit-file.zip",
    2016: "https://www2.census.gov/programs-surveys/gov-finances/datasets/2016/public-use-datasets/2016_Individual_Unit_file.zip",
}

# 2017-2021: individual unit files under tables/{year}/
NEW_FORMAT_URLS: dict[int, str] = {
    yr: (
        f"https://www2.census.gov/programs-surveys/gov-finances/tables/{yr}/"
        f"{yr}_Individual_Unit_File.zip"
    )
    for yr in range(2017, 2022)
}

# Fixed-width record layout by era
# 2013-2016: 34-char records; gov ID is 14 chars
FW_2013_COLSPECS = [(0, 14), (14, 17), (17, 29), (29, 33), (33, 34)]
# 2017-2021: 32-char records; gov ID is 12 chars
FW_2017_COLSPECS = [(0, 12), (12, 15), (15, 27), (27, 31), (31, 32)]
FW_NAMES = ["govid", "item", "amount_str", "year_str", "flag"]

# ---------------------------------------------------------------------------
# Historical archive column -> output variable mapping
# ---------------------------------------------------------------------------
# These are the descriptive column names used in IndFinYYa/b/c.Txt (wide format).
HIST_COL_MAP = {
    "Property Tax":          "rev_proptax",
    "Total Taxes":           "rev_tax_total",
    "Total Fed IG Revenue":  "rev_igt_federal",
    "Total State IG Revenue":"rev_igt_state",
    "Total IG Revenue":      "rev_intergovt",
    "Gen Rev-Own Sources":   "rev_own_sources",
    "General Revenue":       "rev_total",
    "General Expenditure":   "exp_total",
    "Total Capital Outlays": "exp_capital",
    # Long-term debt: try multiple possible column names across vintages
    "Long-Term Debt Out":    "debt_lt",
    "LT Debt Outstanding":   "debt_lt",
    "Total Long-Term Debt":  "debt_lt",
    "Long Term Debt":        "debt_lt",
}

# New-format item codes (CoG fixed-width long format)
NEW_ITEMS = {
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

# ---------------------------------------------------------------------------
# Download helpers
# ---------------------------------------------------------------------------

def _fetch(url: str, dest: Path, label: str) -> Path | None:
    if dest.exists():
        return dest
    print(f"  Downloading {label}... ", end="", flush=True)
    try:
        r = requests.get(url, timeout=600, stream=True)
        r.raise_for_status()
        with dest.open("wb") as fh:
            for chunk in r.iter_content(chunk_size=1 << 20):
                fh.write(chunk)
        print(f"OK ({dest.stat().st_size // 1024:,} KB)")
        time.sleep(0.5)
        return dest
    except Exception as e:
        print(f"FAILED ({e})")
        if dest.exists():
            dest.unlink()
        return None

# ---------------------------------------------------------------------------
# Historical archive parser (2000-2012, wide format)
# ---------------------------------------------------------------------------

def parse_historical_year(archive_zip: Path, year: int) -> pd.DataFrame | None:
    """
    Extract one year from the _IndFin_1967-2012 archive.
    Files inside are named IndFinYYa/b/c.Txt (YY = 2-digit year, a/b/c = parts).
    Each file is a wide CSV: one row per government, columns are fiscal item names.
    """
    yy = str(year)[2:].zfill(2)  # e.g. 2007 -> "07"
    try:
        with zipfile.ZipFile(archive_zip) as zf:
            parts = [n for n in zf.namelist() if re.match(rf"IndFin{yy}[a-cA-C]\.Txt", n, re.IGNORECASE)]
            if not parts:
                print(f"  [WARN] {year}: no IndFin{yy}*.Txt files in historical archive")
                return None
            frames = []
            for part in parts:
                raw = zf.read(part)
                df = pd.read_csv(io.BytesIO(raw), dtype=str, low_memory=False, encoding="latin-1")
                frames.append(df)
            df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    except Exception as e:
        print(f"  [WARN] {year}: historical archive read error — {e}")
        return None

    # Normalise column names
    df.columns = [c.strip() for c in df.columns]

    # Filter to county governments in western states
    type_col = next((c for c in df.columns if c in ("Type Code", "TypeCode", "TYPECODE")), None)
    state_col = next((c for c in df.columns if c in ("FIPS Code-State", "State Code", "STATE")), None)
    county_col = next((c for c in df.columns if c in ("County", "COUNTY")), None)
    yr_col = next((c for c in df.columns if c in ("Year4", "YEAR4", "SurveyYr")), None)

    if type_col is None or state_col is None:
        print(f"  [WARN] {year}: cannot locate type/state columns in historical archive")
        return None

    df[state_col] = df[state_col].str.strip().str.zfill(2)
    df[type_col] = df[type_col].str.strip()
    mask = (df[type_col] == COUNTY_TYPE) & (df[state_col].isin(WEST_STATES))
    df = df[mask].copy()

    if df.empty:
        print(f"  [WARN] {year}: no western county governments in historical archive for year {year}")
        return None

    # Build 5-digit FIPS
    if county_col:
        df["fips"] = df[state_col].str.zfill(2) + df[county_col].str.strip().str.zfill(3)
    else:
        print(f"  [WARN] {year}: no county FIPS column; skipping")
        return None

    # Map descriptive columns to output variables
    out: dict[str, pd.Series] = {"fips": df["fips"], "year_cog": pd.Series([year] * len(df), index=df.index)}
    debt_assigned = False
    for hist_col, out_col in HIST_COL_MAP.items():
        if hist_col in df.columns:
            if out_col == "debt_lt" and debt_assigned:
                continue  # use first matching debt column
            out[out_col] = pd.to_numeric(df[hist_col].str.strip(), errors="coerce") * 1000
            if out_col == "debt_lt":
                debt_assigned = True

    result = pd.DataFrame(out)
    return result

# ---------------------------------------------------------------------------
# Individual unit file parser — handles 2013-2016 (34-char) and 2017-2021 (32-char)
# ---------------------------------------------------------------------------
#
# 2013-2016 layout (34 chars/record):
#   [0:14]  Government ID (14 chars): [0:2]=state FIPS, [2]=type, [3:6]=county, [6:14]=local ID
#   [14:17] Item code
#   [17:29] Amount in $thousands (12 chars, right-justified)
#   [29:33] Survey year (4 digits)
#   [33]    Revision flag
#
# 2017-2021 layout (32 chars/record):
#   [0:12]  Government ID (12 chars): [0:2]=state FIPS, [2]=type, [3:6]=county, [6:12]=local ID
#   [12:15] Item code
#   [15:27] Amount in $thousands (12 chars, right-justified)
#   [27:31] Survey year (4 digits)
#   [31]    Revision flag


def parse_individual_unit_file(zip_path: Path, year: int) -> pd.DataFrame | None:
    """
    Parse a CoG Individual Unit File (fixed-width long format).
    Handles both the 2013-2016 (34-char, 14-char gov ID) and
    2017-2021 (32-char, 12-char gov ID) record layouts.
    Filters to county governments (type=1) in WEST_STATES.
    """
    try:
        with zipfile.ZipFile(zip_path) as zf:
            data_files = [n for n in zf.namelist() if "FinEstDAT" in n and n.lower().endswith(".txt")]
            if not data_files:
                data_files = [
                    n for n in zf.namelist()
                    if n.lower().endswith(".txt")
                    and not any(k in n.lower() for k in ("statetype", "gid", "documentation", "disclaimer"))
                ]
            if not data_files:
                print(f"  [WARN] {year}: no FinEstDAT file found in zip")
                return None
            raw = zf.read(data_files[0])
    except Exception as e:
        print(f"  [WARN] {year}: zip error - {e}")
        return None

    # Detect record length from first non-empty line to choose layout
    first_line = next((l for l in raw.split(b"\n") if l.strip()), b"")
    rec_len = len(first_line.rstrip(b"\r\n"))
    if rec_len >= 34:
        colspecs = FW_2013_COLSPECS   # 2013-2016: 34 chars, 14-char gov ID
        govid_len = 14
    else:
        colspecs = FW_2017_COLSPECS   # 2017-2021: 32 chars, 12-char gov ID
        govid_len = 12

    try:
        df = pd.read_fwf(
            io.BytesIO(raw),
            colspecs=colspecs,
            names=FW_NAMES,
            dtype=str,
            encoding="latin-1",
            header=None,
        )
    except Exception as e:
        print(f"  [WARN] {year}: fixed-width parse error - {e}")
        return None

    df = df.dropna(subset=["govid"])
    df["govid"] = df["govid"].str.strip()
    df = df[df["govid"].str.len() == govid_len].copy()

    df["state"]   = df["govid"].str[0:2]
    df["gtype"]   = df["govid"].str[2]
    df["county3"] = df["govid"].str[3:6]
    df["fips"]    = df["state"] + df["county3"]

    mask = (df["state"].isin(WEST_STATES)) & (df["gtype"] == COUNTY_TYPE)
    df = df[mask].copy()
    if df.empty:
        print(f"  [WARN] {year}: no county governments in western states")
        return None

    df["item"]   = df["item"].str.strip().str.upper()
    df = df[df["item"].isin(NEW_ITEMS)].copy()
    df["amount"] = pd.to_numeric(df["amount_str"].str.strip(), errors="coerce") * 1000

    wide = df.pivot_table(index="fips", columns="item", values="amount", aggfunc="first")
    wide.columns.name = None
    wide = wide.reset_index()
    wide = wide.rename(columns=NEW_ITEMS)
    wide["year_cog"] = year
    return wide

# ---------------------------------------------------------------------------
# Fiscal year recoding and derived outcomes
# ---------------------------------------------------------------------------

def recode_fy(df: pd.DataFrame) -> pd.DataFrame:
    """Recode CoG FY-end year to FY-begin year. Adds 'year' column."""
    df = df.copy()
    df["fips"] = df["fips"].astype(str).str.strip()
    df["state"] = df["fips"].str[0:2]
    df["fy_end_month"] = df["state"].map(FY_END_MONTHS).fillna(6).astype(int)
    df["year"] = df.apply(
        lambda r: int(r["year_cog"]) - 1 if r["fy_end_month"] < 12 else int(r["year_cog"]),
        axis=1
    )
    return df


def derive_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if "exp_total" in df.columns and "exp_capital" in df.columns:
        df["exp_current"] = df["exp_total"] - df["exp_capital"]
    if "rev_total" in df.columns and "exp_total" in df.columns:
        df["fiscal_balance"] = df["rev_total"] - df["exp_total"]
    return df

# ---------------------------------------------------------------------------
# Coverage audit
# ---------------------------------------------------------------------------

def coverage_audit(panel: pd.DataFrame,
                   n_years: int = 21,
                   min_primary: float = 0.85,
                   min_robust: float = 0.70) -> pd.DataFrame:
    counts = panel.groupby("fips")["year"].nunique().rename("n_years_obs")
    cov = counts.reset_index()
    cov["coverage_pct"] = cov["n_years_obs"] / n_years
    cov["pass_primary"] = cov["coverage_pct"] >= min_primary
    cov["pass_robust"] = cov["coverage_pct"] >= min_robust

    all_yrs = set(range(2000, 2021))
    post_fire = set(range(2015, 2022))
    rows = []
    for fips, grp in panel.groupby("fips"):
        obs = set(grp["year"])
        miss = all_yrs - obs
        miss_post = miss & post_fire
        rows.append({
            "fips": fips,
            "n_missing_total": len(miss),
            "n_missing_post_fire": len(miss_post),
            "post_fire_share": len(miss_post) / len(miss) if miss else 0.0,
        })
    miss_df = pd.DataFrame(rows)
    cov = cov.merge(miss_df, on="fips", how="left")
    cov["attrition_risk"] = (cov["post_fire_share"] > 0.5) & (cov["n_missing_total"] > 0)

    print(f"\nCoverage audit ({n_years}-year panel):")
    print(f"  Total counties in data:          {len(cov):,}")
    print(f"  Pass >=85% primary threshold:    {cov['pass_primary'].sum():,}")
    print(f"  Pass >=70% robustness threshold: {cov['pass_robust'].sum():,}")
    n_risk = cov["attrition_risk"].sum()
    print(f"  Attrition risk (>50% missing in post-fire window): {n_risk}")
    if n_risk > 0:
        print("  WARNING: these counties should NOT be imputed — exclude and document:")
        print(cov[cov["attrition_risk"]][["fips", "n_years_obs", "n_missing_post_fire"]].to_string(index=False))

    return cov

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== Census of Governments Annual Survey Pull ===")
    print(f"Sample years: {SAMPLE_YEARS[0]}-{SAMPLE_YEARS[-1]}")
    print(f"States: {sorted(WEST_STATES)}")

    frames: list[pd.DataFrame] = []

    # ---- HISTORICAL ARCHIVE (2000-2012) ----
    hist_zip = _fetch(COG_HIST_URL, RAW / "cog_hist_1967_2012.zip", "1967-2012 archive")
    if hist_zip:
        for year in tqdm(sorted(HIST_YEARS), desc="Historical 2000-2012"):
            df = parse_historical_year(hist_zip, year)
            if df is not None and not df.empty:
                frames.append(df)
    else:
        print("ERROR: Could not download historical archive.")

    # ---- GAP YEARS (2013-2016): public-use-datasets path ----
    for year, url in tqdm(sorted(GAP_YEAR_FILES.items()), desc="Gap years 2013-2016"):
        zip_path = _fetch(url, RAW / f"cog_{year}.zip", str(year))
        if zip_path is None:
            continue
        df = parse_individual_unit_file(zip_path, year)
        if df is not None and not df.empty:
            frames.append(df)

    # ---- NEW FORMAT (2017-2021) ----
    for year, url in tqdm(sorted(NEW_FORMAT_URLS.items()), desc="New format 2017-2021"):
        zip_path = _fetch(url, RAW / f"cog_{year}.zip", str(year))
        if zip_path is None:
            continue
        df = parse_individual_unit_file(zip_path, year)
        if df is not None and not df.empty:
            frames.append(df)

    if not frames:
        print("\nERROR: No data parsed. Check downloads and parsers.")
        return

    # Combine and recode
    panel = pd.concat(frames, ignore_index=True)
    panel = recode_fy(panel)
    panel = derive_outcomes(panel)
    panel = panel.sort_values(["fips", "year"]).reset_index(drop=True)

    # Drop rows with invalid FIPS
    panel = panel[panel["fips"].str.len() == 5].copy()

    print(f"\nRaw panel: {len(panel):,} county-year observations")
    print(f"  Unique counties: {panel['fips'].nunique():,}")
    print(f"  Year range: {panel['year'].min()}-{panel['year'].max()}")

    yrs_available = sorted(int(y) for y in panel["year"].unique())
    yrs_missing = [y for y in range(2000, 2021) if y not in yrs_available]
    print(f"  Years present: {yrs_available}")
    if yrs_missing:
        print(f"  Years MISSING: {yrs_missing}")

    # Coverage audit
    cov = coverage_audit(panel)
    cov.to_csv(RAW / "cog_coverage_audit.csv", index=False)
    print(f"\nCoverage audit written -> {RAW / 'cog_coverage_audit.csv'}")

    # Apply primary filter
    valid = set(cov.loc[cov["pass_primary"], "fips"])
    pf = panel[panel["fips"].isin(valid)].copy()
    print(f"\nFiltered (>=85%): {len(pf):,} obs, {pf['fips'].nunique():,} counties")

    # Flag outlier revenue values
    for col in [c for c in pf.columns if c.startswith("rev_")]:
        if pf[col].notna().any():
            state_yr_med = pf.groupby(["state", "year"])[col].transform("median")
            pf[f"flag_{col}"] = (pf[col] < 0) | (pf[col] > 3 * state_yr_med)

    pf.to_parquet(OUT / "cog_panel_raw.parquet", index=False)
    print(f"Panel written -> {OUT / 'cog_panel_raw.parquet'}")

    # FY end month sanity check
    fy_dist = pf.groupby("fy_end_month").size()
    print(f"\nFY end month distribution:\n{fy_dist.to_string()}")
    print("  (Expected: most at month 6=June. Any deviation should be verified.)")

    print("\nNext: merge ACS population denominators in 07_panel_assemble.py")


if __name__ == "__main__":
    main()
