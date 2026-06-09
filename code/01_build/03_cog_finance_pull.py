"""
Download and parse Census of Governments (CoG) quinquennial census data.

Produces a county-level panel for the 7 quinquennial census years
(1992, 1997, 2002, 2007, 2012, 2017, 2022) for county governments (CoG type
code 1) in the 8-state western sample.

DESIGN RATIONALE:
  The quinquennial census covers ALL government units (no sampling). This
  guarantees complete county coverage for the 8-state sample without any
  coverage restriction, in contrast to the Annual Survey which samples ~70%
  of smaller counties. Using census years only aligns with the staggered DiD
  design: C&S groups are defined at census-year granularity (g=2017 for fires
  2013-2016; g=2022 for fires 2017-2021).

FISCAL YEAR ALIGNMENT RULE (Q4 decision):
  Assign CoG fiscal data to the calendar year in which the fiscal year BEGINS.
  FY July 2016 – June 2017 -> year 2016. CoG labels fiscal years by the year
  in which the FY ENDS; we recode to FY-begin convention by subtracting 1 when
  FY end month != December. All 8 western states have non-December FY ends.

DATA SOURCES BY ERA:

  1992-2012:  Historical archive (wide CSV, one row per government per year)
              https://www2.census.gov/programs-surveys/gov-finances/datasets/
              historical/_IndFin_1967-2012.zip
              Files inside: IndFin92a/b/c.Txt, IndFin97a/b/c.Txt, ..., IndFin12a/b/c.Txt
              Key columns: Year4, Type Code, FIPS Code-State, County,
              Property Tax, General Revenue, General Expenditure, etc.

  2017:       Fixed-width long format (32-char records, 12-char gov ID)
              https://www2.census.gov/programs-surveys/gov-finances/tables/
              2017/2017_Individual_Unit_File.zip

  2022:       Fixed-width long format (32-char records, 12-char gov ID)
              https://www2.census.gov/programs-surveys/gov-finances/tables/
              2022/2022_Individual_Unit_File.zip

ITEM CODES (CoG):
  T01  Property tax revenue
  T09  Total taxes
  B01  Intergovernmental revenue from federal government
  B20  Intergovernmental revenue from state government
  B80  Total intergovernmental revenue (federal + state)
  C89  Total general revenue from own sources
  A15  Total general revenue
  E61  Total general expenditure
  E04  Capital outlays
  F01  Long-term debt outstanding at end of year
  Current operations expenditure = E61 - E04
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
RAW  = ROOT / "data" / "raw" / "cog"
OUT  = ROOT / "data" / "processed"
RAW.mkdir(parents=True, exist_ok=True)
OUT.mkdir(parents=True, exist_ok=True)

WEST_STATES  = {"06", "08", "16", "30", "41", "49", "53", "56"}  # CA CO ID MT OR UT WA WY
COUNTY_TYPE  = "1"   # CoG government type code for county governments

# Quinquennial census years: complete coverage of all government units
CENSUS_YEARS = [1992, 1997, 2002, 2007, 2012, 2017, 2022]

# Fiscal year end months for county governments (all 8 states use non-Dec FY ends)
FY_END_MONTHS: dict[str, int] = {
    "06": 6,   # CA  — FY Jul–Jun
    "08": 6,   # CO  — FY Jul–Jun
    "16": 9,   # ID  — FY Oct–Sep
    "30": 6,   # MT  — FY Jul–Jun
    "41": 6,   # OR  — FY Jul–Jun
    "49": 6,   # UT  — FY Jul–Jun
    "53": 6,   # WA  — FY Jul–Jun
    "56": 6,   # WY  — FY Jul–Jun
}

# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------
COG_HIST_URL = (
    "https://www2.census.gov/programs-surveys/gov-finances/datasets/historical/"
    "_IndFin_1967-2012.zip"
)
HIST_CENSUS_YEARS = {1992, 1997, 2002, 2007, 2012}   # in historical archive

# 2017 and 2022 use the tables/{year}/ path (32-char fixed-width format)
INDIV_UNIT_URLS: dict[int, str] = {
    yr: (
        f"https://www2.census.gov/programs-surveys/gov-finances/tables/{yr}/"
        f"{yr}_Individual_Unit_File.zip"
    )
    for yr in [2017, 2022]
}

# Fixed-width record layout — 2017 and 2022 (32-char, 12-char gov ID):
#   [0:12]  Government ID: [0:2]=state FIPS, [2]=type, [3:6]=county FIPS, [6:12]=local ID
#   [12:15] Item code (e.g. T01, A15, E61)
#   [15:27] Amount in $thousands (right-justified)
#   [27:31] Survey year (4 digits)
#   [31]    Revision flag
FW_COLSPECS = [(0, 12), (12, 15), (15, 27), (27, 31), (31, 32)]
FW_NAMES    = ["govid", "item", "amount_str", "year_str", "flag"]

# ---------------------------------------------------------------------------
# Historical column -> output variable mapping (wide CSV format, 1992-2012)
# ---------------------------------------------------------------------------
HIST_COL_MAP = {
    "Property Tax":           "rev_proptax",
    "Total Taxes":            "rev_tax_total",
    "Total Fed IG Revenue":   "rev_igt_federal",
    "Total State IG Revenue": "rev_igt_state",
    "Total IG Revenue":       "rev_intergovt",
    "Gen Rev-Own Sources":    "rev_own_sources",
    "General Revenue":        "rev_total",
    "General Expenditure":    "exp_total",
    "Total Capital Outlays":  "exp_capital",
    # Long-term debt: multiple column names across vintages — use first match
    "Long-Term Debt Out":     "debt_lt",
    "LT Debt Outstanding":    "debt_lt",
    "Total Long-Term Debt":   "debt_lt",
    "Long Term Debt":         "debt_lt",
}

# Item codes for fixed-width long format (2017, 2022)
FW_ITEMS = {
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
# Download helper
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
# Historical archive parser (1992-2012, wide CSV format)
# ---------------------------------------------------------------------------

NATL_COUNTY_URL = (
    "https://www2.census.gov/geo/docs/reference/codes/files/national_county.txt"
)

# Manual overrides for names that differ between CoG and Census reference:
# key = (state_fips2, normalized_cog_name), value = census_county_fips3
NAME_OVERRIDES: dict[tuple[str, str], str] = {
    # MT consolidated city-counties — CoG uses original county name
    ("30", "silver bow"):      "093",   # Butte-Silver Bow
    ("30", "deer lodge"):      "023",
    # WY name variant
    ("56", "laramie"):         "021",   # Albany co is 001; Laramie co is 021
}


def build_name_crosswalk(cache_dir: Path) -> dict[tuple[str, str], str]:
    """
    Download Census national county file and build:
    {(state_fips2, normalized_county_name): county_fips3}

    Normalization: strip trailing ' COUNTY', ' PARISH', ' BOROUGH',
    ' CENSUS AREA', ' MUNICIPALITY', ' CITY AND BOROUGH'; lowercase; strip.
    """
    cache = cache_dir / "national_county.txt"
    if not cache.exists():
        print("  Downloading national county FIPS reference... ", end="", flush=True)
        try:
            r = requests.get(NATL_COUNTY_URL, timeout=60)
            r.raise_for_status()
            cache.write_bytes(r.content)
            print(f"OK ({cache.stat().st_size // 1024} KB)")
        except Exception as e:
            print(f"FAILED ({e})")
            return {}

    crosswalk: dict[tuple[str, str], str] = {}
    _SUFFIXES = (
        " census area", " city and borough", " municipality",
        " borough", " parish", " county",
    )
    with cache.open(encoding="latin-1") as fh:
        for line in fh:
            parts = line.strip().split(",")
            if len(parts) < 4:
                continue
            state_fips = parts[1].strip().zfill(2)
            county_fips = parts[2].strip().zfill(3)
            county_name = parts[3].strip().lower()
            for sfx in _SUFFIXES:
                if county_name.endswith(sfx):
                    county_name = county_name[: -len(sfx)].strip()
                    break
            crosswalk[(state_fips, county_name)] = county_fips

    crosswalk.update(NAME_OVERRIDES)
    return crosswalk


def parse_historical_year(
    archive_zip: Path,
    year: int,
    name_crosswalk: dict[tuple[str, str], str],
) -> pd.DataFrame | None:
    """
    Extract one census year from _IndFin_1967-2012.zip.
    Files inside: IndFinYYa/b/c.Txt (YY = 2-digit year).
    Wide CSV: one row per government, columns = fiscal item names.
    """
    yy = str(year)[2:].zfill(2)   # 1992 -> "92", 2002 -> "02"
    try:
        with zipfile.ZipFile(archive_zip) as zf:
            parts = [n for n in zf.namelist()
                     if re.match(rf"IndFin{yy}[a-cA-C]\.Txt", n, re.IGNORECASE)]
            if not parts:
                print(f"  [WARN] {year}: no IndFin{yy}*.Txt in archive")
                return None
            frames = []
            for part in parts:
                raw = zf.read(part)
                df = pd.read_csv(io.BytesIO(raw), dtype=str, low_memory=False,
                                 encoding="latin-1")
                frames.append(df)
            df = pd.concat(frames, ignore_index=True) if len(frames) > 1 else frames[0]
    except Exception as e:
        print(f"  [WARN] {year}: archive read error - {e}")
        return None

    df.columns = [c.strip() for c in df.columns]

    type_col        = next((c for c in df.columns if c in ("Type Code", "TypeCode", "TYPECODE")), None)
    fips_state_col  = next((c for c in df.columns if c == "FIPS Code-State"), None)
    alpha_state_col = next((c for c in df.columns if c == "State Code"), None)
    county_col      = next((c for c in df.columns if c in ("County", "COUNTY")), None)

    if type_col is None or fips_state_col is None:
        print(f"  [WARN] {year}: cannot locate Type Code / FIPS Code-State columns")
        return None

    df[fips_state_col] = df[fips_state_col].str.strip().str.zfill(2)
    df[type_col]       = df[type_col].str.strip()
    df = df[(df[type_col] == COUNTY_TYPE) & (df[fips_state_col].isin(WEST_STATES))].copy()
    if df.empty:
        print(f"  [WARN] {year}: no western county governments found")
        return None

    name_col = next((c for c in df.columns if c == "Name"), None)
    if name_col is None:
        print(f"  [WARN] {year}: no Name column; skipping")
        return None

    _SUFFIXES = (
        " census area", " city and borough", " municipality",
        " borough", " parish", " county",
    )

    def _normalize(raw: str) -> str:
        s = str(raw).strip().lower()
        for sfx in _SUFFIXES:
            if s.endswith(sfx):
                return s[: -len(sfx)].strip()
        return s

    def _lookup(row: pd.Series) -> str | None:
        st   = row[fips_state_col]
        name = _normalize(row[name_col])
        co3  = name_crosswalk.get((st, name))
        return (st + co3) if co3 is not None else None

    df["fips"] = df.apply(_lookup, axis=1)
    n_miss = df["fips"].isna().sum()
    if n_miss > 0:
        print(f"  [WARN] {year}: {n_miss}/{len(df)} rows not in name crosswalk -> dropped")
        if n_miss <= 10:
            print(df[df["fips"].isna()][[fips_state_col, name_col]].to_string(index=False))
    df = df[df["fips"].notna()].copy()

    out: dict[str, pd.Series] = {
        "fips": df["fips"],
        "year_cog": pd.Series([year] * len(df), index=df.index),
    }
    debt_assigned = False
    for hist_col, out_col in HIST_COL_MAP.items():
        if hist_col in df.columns:
            if out_col == "debt_lt" and debt_assigned:
                continue
            out[out_col] = pd.to_numeric(df[hist_col].str.strip(), errors="coerce") * 1000
            if out_col == "debt_lt":
                debt_assigned = True

    return pd.DataFrame(out)

# ---------------------------------------------------------------------------
# Individual unit file parser (2017, 2022 — fixed-width 32-char format)
# ---------------------------------------------------------------------------

def parse_individual_unit_file(zip_path: Path, year: int) -> pd.DataFrame | None:
    """
    Parse a CoG Individual Unit File (fixed-width 32-char records).
    Filters to county governments (type=1) in WEST_STATES, pivots to wide.
    """
    try:
        with zipfile.ZipFile(zip_path) as zf:
            data_files = [n for n in zf.namelist()
                          if "FinEstDAT" in n and n.lower().endswith(".txt")]
            if not data_files:
                data_files = [
                    n for n in zf.namelist()
                    if n.lower().endswith(".txt")
                    and not any(k in n.lower()
                                for k in ("statetype", "gid", "documentation", "disclaimer",
                                          "methodology", "readme"))
                ]
            if not data_files:
                print(f"  [WARN] {year}: no data file found in zip")
                return None
            raw = zf.read(data_files[0])
    except Exception as e:
        print(f"  [WARN] {year}: zip error - {e}")
        return None

    try:
        df = pd.read_fwf(
            io.BytesIO(raw),
            colspecs=FW_COLSPECS,
            names=FW_NAMES,
            dtype=str,
            encoding="latin-1",
            header=None,
        )
    except Exception as e:
        print(f"  [WARN] {year}: parse error - {e}")
        return None

    df = df.dropna(subset=["govid"])
    df["govid"] = df["govid"].str.strip()
    df = df[df["govid"].str.len() == 12].copy()

    df["state"]   = df["govid"].str[0:2]
    df["gtype"]   = df["govid"].str[2]
    df["county3"] = df["govid"].str[3:6]
    df["fips"]    = df["state"] + df["county3"]

    df = df[(df["state"].isin(WEST_STATES)) & (df["gtype"] == COUNTY_TYPE)].copy()
    if df.empty:
        print(f"  [WARN] {year}: no western county governments after filter")
        return None

    df["item"]   = df["item"].str.strip().str.upper()
    df = df[df["item"].isin(FW_ITEMS)].copy()
    df["amount"] = pd.to_numeric(df["amount_str"].str.strip(), errors="coerce") * 1000

    wide = df.pivot_table(index="fips", columns="item", values="amount", aggfunc="first")
    wide.columns.name = None
    wide = wide.reset_index()
    wide = wide.rename(columns=FW_ITEMS)
    wide["year_cog"] = year
    return wide

# ---------------------------------------------------------------------------
# FY-begin recoding and derived outcomes
# ---------------------------------------------------------------------------

def recode_fy(df: pd.DataFrame) -> pd.DataFrame:
    """Recode CoG FY-end year label to FY-begin year. Adds 'year' column."""
    df = df.copy()
    df["fips"]         = df["fips"].astype(str).str.strip()
    df["state"]        = df["fips"].str[0:2]
    df["fy_end_month"] = df["state"].map(FY_END_MONTHS).fillna(6).astype(int)
    # All 8 states have non-Dec FY ends, so always subtract 1
    df["year"] = df["year_cog"].astype(int) - 1
    return df


def derive_outcomes(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    if {"exp_total", "exp_capital"}.issubset(df.columns):
        df["exp_current"]    = df["exp_total"] - df["exp_capital"]
    if {"rev_total", "exp_total"}.issubset(df.columns):
        df["fiscal_balance"] = df["rev_total"] - df["exp_total"]
    return df

# ---------------------------------------------------------------------------
# Completeness check (census = full coverage by design)
# ---------------------------------------------------------------------------

def completeness_check(panel: pd.DataFrame) -> None:
    n_census = len(CENSUS_YEARS)
    counts = panel.groupby("fips")["year_cog"].nunique()
    complete = (counts == n_census).sum()
    print(f"\nCompleteness check ({n_census} census years):")
    print(f"  Total counties: {len(counts):,}")
    print(f"  Counties in all {n_census} census years: {complete:,}")
    n_partial = (counts < n_census).sum()
    if n_partial > 0:
        print(f"  Counties missing at least 1 year: {n_partial} (inspect manually)")
        partial = counts[counts < n_census].reset_index()
        partial.columns = ["fips", "n_years_obs"]
        print(partial.to_string(index=False))

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def main() -> None:
    print("=== Census of Governments — Quinquennial Census Pull ===")
    print(f"Census years: {CENSUS_YEARS}")
    print(f"States: {sorted(WEST_STATES)}")
    print("Complete coverage by design — no sampling restriction applied.")

    frames: list[pd.DataFrame] = []

    # ---- HISTORICAL ARCHIVE (1992-2012 census years) ----
    hist_zip = _fetch(COG_HIST_URL, RAW / "cog_hist_1967_2012.zip", "1967-2012 archive")
    if hist_zip:
        name_crosswalk = build_name_crosswalk(RAW)
        print(f"  Name crosswalk loaded: {len(name_crosswalk):,} county entries")
        for year in tqdm(sorted(HIST_CENSUS_YEARS), desc="Historical census years"):
            df = parse_historical_year(hist_zip, year, name_crosswalk)
            if df is not None and not df.empty:
                frames.append(df)
    else:
        print("ERROR: Could not download historical archive.")

    # ---- INDIVIDUAL UNIT FILES (2017, 2022) ----
    for year, url in tqdm(sorted(INDIV_UNIT_URLS.items()), desc="Census years 2017-2022"):
        zip_path = _fetch(url, RAW / f"cog_{year}.zip", str(year))
        if zip_path is None:
            continue
        df = parse_individual_unit_file(zip_path, year)
        if df is not None and not df.empty:
            frames.append(df)

    if not frames:
        print("\nERROR: No data parsed.")
        return

    panel = pd.concat(frames, ignore_index=True)
    panel = recode_fy(panel)
    panel = derive_outcomes(panel)
    panel = panel[panel["fips"].str.len() == 5].copy()
    panel = panel.sort_values(["fips", "year_cog"]).reset_index(drop=True)

    print(f"\nRaw panel: {len(panel):,} county observations across {len(CENSUS_YEARS)} census years")
    print(f"  Unique counties: {panel['fips'].nunique():,}")
    print(f"  CoG census years present: {sorted(int(y) for y in panel['year_cog'].unique())}")
    print(f"  FY-begin years (recode): {sorted(int(y) for y in panel['year'].unique())}")

    completeness_check(panel)

    # Flag implausible revenue values (< 0 or > 3x state-census-year median)
    for col in [c for c in panel.columns if c.startswith("rev_")]:
        if panel[col].notna().any():
            med = panel.groupby(["state", "year_cog"])[col].transform("median")
            panel[f"flag_{col}"] = (panel[col] < 0) | (panel[col] > 3 * med)

    panel.to_parquet(OUT / "cog_census_panel.parquet", index=False)
    print(f"\nPanel written -> {OUT / 'cog_census_panel.parquet'}")

    fy_dist = panel.groupby("fy_end_month").size()
    print(f"\nFY end month distribution:\n{fy_dist.to_string()}")

    print("\nNext: merge population denominators (ACS/decennial) in 07_panel_assemble.py")


if __name__ == "__main__":
    main()
