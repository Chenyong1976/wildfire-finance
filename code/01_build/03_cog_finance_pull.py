"""
Download and parse Census of Governments (CoG) quinquennial census data.

Produces a county-level panel for the 7 quinquennial census years
(1992, 1997, 2002, 2007, 2012, 2017, 2022) for county governments (CoG type
code 1) in all lower-48 states.

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
  FY end month != December. December FY-end (calendar-year) counties: no subtraction.
  See FY_END_MONTHS for per-state classification and statutory citations.

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

ITEM CODES (CoG) — 2017/2022 IUF AGGREGATION RULES:
  Historical (1992-2012): pre-computed summary codes (A15=total GR, T09=total taxes,
    B80=total IGR, E61=total GE, F01=LT debt). Used directly via HIST_COL_MAP.

  2017/2022 IUF: summary codes absent. Aggregates must be constructed from components.
    Derived from Finance_Aggregate_Lines_2017.xlsx (item code crosswalk inside zip):

  rev_proptax:   T01
  rev_tax_total: sum(T-prefix codes)
  rev_igt_federal: sum(B-prefix codes)  [federal IGR]
  rev_igt_state:  sum(C-prefix codes)  [state IGR to county; absent in historical cols]
  rev_intergovt: sum(B+C prefix codes) [total IGR = federal + state]
  rev_own_sources: sum(A-prefix) + sum(T-prefix) + sum(U-prefix)
  rev_total:     sum(A+B+C+T+U prefix codes)
  exp_total:     sum(E01-E89) + sum(F01-F89) + sum(G01-G89) + I89 + J19+J67+J68+J85
                 [direct general expenditure, excl. utilities E/F/G 90-94 and insurance]
  exp_capital:   sum(F01-F89) + sum(G01-G89)  [construction + other capital outlay]
  debt_lt:       44T + 49U  [long-term debt outstanding]
  exp_current:   exp_total - exp_capital  [derived]
  fiscal_balance: rev_total - exp_total   [derived]
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

# All lower-48 state FIPS codes (excludes AK=02, HI=15, DC=11, territories)
LOWER_48 = {
    "01","04","05","06","08","09","10","12","13",
    "16","17","18","19","20","21","22","23","24","25","26","27","28","29",
    "30","31","32","33","34","35","36","37","38","39","40","41","42","44",
    "45","46","47","48","49","50","51","53","54","55","56",
}
COUNTY_TYPE  = "1"   # CoG government type code for county governments

# Quinquennial census years: complete coverage of all government units
CENSUS_YEARS = [1992, 1997, 2002, 2007, 2012, 2017, 2022]

# Fiscal year end months for county governments (predominant end month per state).
# Rule: if end month != 12, FY-begin year = CoG year - 1; if 12, FY-begin = CoG year.
# Sources: NASBO, ICMA Form of Government, CoG methodology guide, state statutes.
# June 30 (6) is the default for most states. Confirmed exceptions below.
FY_END_MONTHS: dict[str, int] = {
    "01": 9,   # AL  — FY Oct–Sep (most AL county govts follow state FY)
    "04": 6,   # AZ  — FY Jul–Jun
    "05": 6,   # AR  — FY Jul–Jun
    "06": 6,   # CA  — FY Jul–Jun
    "08": 6,   # CO  — FY Jul–Jun
    "09": 6,   # CT  — FY Jul–Jun (county govts abolished 1960; will yield 0 rows)
    "10": 6,   # DE  — FY Jul–Jun
    "12": 9,   # FL  — FY Oct–Sep (Florida counties follow Oct–Sep state FY)
    "13": 6,   # GA  — FY Jul–Jun
    "16": 9,   # ID  — FY Oct–Sep
    "17": 6,   # IL  — FY Jul–Jun
    "18": 12,  # IN  — Calendar year (Jan–Dec; confirmed by ICMA county survey)
    "19": 6,   # IA  — FY Jul–Jun
    "20": 6,   # KS  — FY Jan–Dec? Most KS counties use Jul–Jun; use 6
    "21": 12,  # KY  — Calendar year (Jan–Dec; KRS §68.005)
    "22": 6,   # LA  — FY Jul–Jun
    "23": 6,   # ME  — FY Jul–Jun
    "24": 6,   # MD  — FY Jul–Jun
    "25": 6,   # MA  — FY Jul–Jun
    "26": 9,   # MI  — FY Oct–Sep (most MI counties follow state FY)
    "27": 12,  # MN  — Calendar year (Jan–Dec; Minn. Stat. §375.10)
    "28": 9,   # MS  — FY Oct–Sep (most MS counties follow state Oct–Sep FY)
    "29": 12,  # MO  — Calendar year (Jan–Dec; RSMo §50.010)
    "30": 6,   # MT  — FY Jul–Jun
    "31": 6,   # NE  — FY Jul–Jun
    "32": 6,   # NV  — FY Jul–Jun
    "33": 12,  # NH  — Calendar year (Jan–Dec; many NH counties use calendar year)
    "34": 12,  # NJ  — Calendar year (Jan–Dec; N.J.S.A. 40A:4-5)
    "35": 6,   # NM  — FY Jul–Jun
    "36": 12,  # NY  — Calendar year (Jan–Dec; NY County Law §350)
    "37": 6,   # NC  — FY Jul–Jun
    "38": 12,  # ND  — Calendar year (Jan–Dec; NDCC §11-01-01)
    "39": 12,  # OH  — Calendar year (Jan–Dec; ORC §5705.34)
    "40": 6,   # OK  — FY Jul–Jun
    "41": 6,   # OR  — FY Jul–Jun
    "42": 12,  # PA  — Calendar year (Jan–Dec; 53 P.S. §5001)
    "44": 6,   # RI  — FY Jul–Jun (RI counties largely administrative; few type-1 rows)
    "45": 6,   # SC  — FY Jul–Jun
    "46": 12,  # SD  — Calendar year (Jan–Dec; SDCL §7-21-1)
    "47": 6,   # TN  — FY Jul–Jun
    "48": 9,   # TX  — FY Oct–Sep (Tex. Local Gov't Code §111.001)
    "49": 6,   # UT  — FY Jul–Jun
    "50": 6,   # VT  — FY Jul–Jun
    "51": 6,   # VA  — FY Jul–Jun
    "53": 6,   # WA  — FY Jul–Jun
    "54": 12,  # WV  — Calendar year (Jan–Dec; W.Va. Code §11-8-6)
    "55": 12,  # WI  — Calendar year (Jan–Dec; Wis. Stat. §65.90)
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
    # Long-term debt outstanding at end of year (equivalent to 44T+49U in IUF format)
    # Column name varies across vintage/part files — use first match
    "Total LTD Out":          "debt_lt",
    "Total Long-Term Debt Out": "debt_lt",
    "Long-Term Debt Out":     "debt_lt",
    "LT Debt Outstanding":    "debt_lt",
    "Total Long-Term Debt":   "debt_lt",
    "Long Term Debt":         "debt_lt",
}

# ---------------------------------------------------------------------------
# 2017/2022 IUF aggregation sets (derived from Finance_Aggregate_Lines_2017.xlsx)
# ---------------------------------------------------------------------------

# Prefixes that make up each aggregate.  Keys = set of item code PREFIXES (1-3 chars).
# Single-code items (T01, 44T, 49U) are listed explicitly.

# General Revenue components
_GR_A = {"A01","A03","A09","A10","A12","A16","A18","A21","A36","A44","A45",
          "A50","A54","A56","A59","A60","A61","A80","A81","A87","A89"}
# B-codes = federal IGR; C-codes = state IGR to local (absent from historical summary A15,
# handled correctly there).  Both must be summed for total intergovernmental revenue.
_GR_B = {"B01","B21","B22","B30","B42","B43","B46","B50","B54","B59","B79",
          "B80","B89","B91","B92","B93","B94"}
_GR_C = {"C21","C30","C42","C46","C50","C79","C80","C89","C91","C92","C93","C94"}
_GR_T = {"T01","T09","T10","T11","T12","T13","T14","T15","T16","T19","T20",
          "T21","T22","T23","T24","T25","T27","T28","T29","T40","T41","T50",
          "T51","T53","T99"}
_GR_U = {"U01","U11","U20","U21","U30","U40","U41","U50","U95","U99"}

# Direct General Expenditure components (excludes utilities 90-94, insurance X/Y, IGR S-codes)
_GE_E = {f"E{s}" for s in ["01","03","04","05","12","16","18","21","22","23",
         "24","25","26","27","29","31","32","36","44","45","50","52","54","55",
         "56","59","60","61","62","66","74","75","77","79","80","81","85","87","89"]}
_GE_F = {f"F{s}" for s in ["01","03","04","05","12","16","18","21","22","23",
         "24","25","26","27","29","31","32","36","44","45","50","52","54","55",
         "56","59","60","61","62","66","77","79","80","81","85","87","89"]}
_GE_G = {f"G{s}" for s in ["01","03","04","05","12","16","18","21","22","23",
         "24","25","26","27","29","31","32","36","44","45","50","52","54","55",
         "56","59","60","61","62","66","77","79","80","81","85","87","89"]}
_GE_OTHER = {"I89","J19","J67","J68","J85"}   # interest on general debt + assistance

# Capital outlay within direct general exp = F + G codes above
_CAP_CODES = _GE_F | _GE_G

# Long-term debt outstanding
_DEBT_LT = {"44T", "49U"}

# All codes we need to pull from the IUF
_ALL_FW_CODES = _GR_A | _GR_B | _GR_C | _GR_T | _GR_U | _GE_E | _GE_F | _GE_G | _GE_OTHER | _DEBT_LT

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
            parts = sorted(
                [n for n in zf.namelist()
                 if re.match(rf"IndFin{yy}[a-cA-C]\.Txt", n, re.IGNORECASE)]
            )
            if not parts:
                print(f"  [WARN] {year}: no IndFin{yy}*.Txt in archive")
                return None
            # Parts a/b/c are horizontal splits: same rows, different column groups.
            # Merge on 'ID' rather than vertically concatenating.
            frames = []
            for part in parts:
                raw = zf.read(part)
                f = pd.read_csv(io.BytesIO(raw), dtype=str, low_memory=False,
                                encoding="latin-1")
                f.columns = [c.strip() for c in f.columns]
                frames.append(f)
            if len(frames) == 1:
                df = frames[0]
            else:
                df = frames[0]
                for extra in frames[1:]:
                    # Drop columns already present (except the join key)
                    dup_cols = [c for c in extra.columns if c in df.columns and c != "ID"]
                    df = df.merge(extra.drop(columns=dup_cols), on="ID", how="outer")
    except Exception as e:
        print(f"  [WARN] {year}: archive read error - {e}")
        return None

    type_col        = next((c for c in df.columns if c in ("Type Code", "TypeCode", "TYPECODE")), None)
    fips_state_col  = next((c for c in df.columns if c == "FIPS Code-State"), None)
    alpha_state_col = next((c for c in df.columns if c == "State Code"), None)
    county_col      = next((c for c in df.columns if c in ("County", "COUNTY")), None)

    if type_col is None or fips_state_col is None:
        print(f"  [WARN] {year}: cannot locate Type Code / FIPS Code-State columns")
        return None

    df[fips_state_col] = df[fips_state_col].str.strip().str.zfill(2)
    df[type_col]       = df[type_col].str.strip()
    df = df[(df[type_col] == COUNTY_TYPE) & (df[fips_state_col].isin(LOWER_48))].copy()
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
    Filters to county governments (type=1) in LOWER_48, pivots to wide.
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

    df = df[(df["state"].isin(LOWER_48)) & (df["gtype"] == COUNTY_TYPE)].copy()
    if df.empty:
        print(f"  [WARN] {year}: no western county governments after filter")
        return None

    df["item"]   = df["item"].str.strip().str.upper()
    df = df[df["item"].isin(_ALL_FW_CODES)].copy()
    df["amount"] = pd.to_numeric(df["amount_str"].str.strip(), errors="coerce") * 1000

    # Aggregate to county level
    totals = df.groupby(["fips", "item"])["amount"].sum().unstack(fill_value=0)
    totals.columns.name = None
    totals = totals.reset_index()

    def _sum_codes(row: pd.Series, codes: set) -> float:
        return sum(row.get(c, 0) for c in codes if c in row.index)

    wide = pd.DataFrame({"fips": totals["fips"]})
    wide["rev_proptax"]     = totals.reindex(columns=["T01"], fill_value=0).sum(axis=1).values
    wide["rev_tax_total"]   = totals.reindex(columns=list(_GR_T), fill_value=0).sum(axis=1)
    wide["rev_igt_federal"] = totals.reindex(columns=list(_GR_B), fill_value=0).sum(axis=1)
    wide["rev_igt_state"]   = totals.reindex(columns=list(_GR_C), fill_value=0).sum(axis=1)
    wide["rev_intergovt"]   = (totals.reindex(columns=list(_GR_B | _GR_C), fill_value=0)
                                     .sum(axis=1))
    wide["rev_own_sources"] = (totals.reindex(columns=list(_GR_A), fill_value=0).sum(axis=1)
                               + totals.reindex(columns=list(_GR_T), fill_value=0).sum(axis=1)
                               + totals.reindex(columns=list(_GR_U), fill_value=0).sum(axis=1))
    wide["rev_total"]       = (totals.reindex(columns=list(_GR_A | _GR_B | _GR_C | _GR_T | _GR_U),
                                              fill_value=0).sum(axis=1))
    wide["exp_total"]       = (totals.reindex(columns=list(_GE_E | _GE_F | _GE_G | _GE_OTHER),
                                              fill_value=0).sum(axis=1))
    wide["exp_capital"]     = totals.reindex(columns=list(_CAP_CODES), fill_value=0).sum(axis=1)
    wide["debt_lt"]         = totals.reindex(columns=list(_DEBT_LT), fill_value=0).sum(axis=1)
    wide["year_cog"] = year
    return wide

# ---------------------------------------------------------------------------
# FY-begin recoding and derived outcomes
# ---------------------------------------------------------------------------

def recode_fy(df: pd.DataFrame) -> pd.DataFrame:
    """Recode CoG FY-end year label to FY-begin year. Adds 'year' column.

    For non-December FY ends (Jun, Sep, etc.): FY-begin = CoG year - 1.
    For December FY ends (calendar year counties): FY-begin = CoG year (no subtraction).
    """
    df = df.copy()
    df["fips"]         = df["fips"].astype(str).str.strip()
    df["state"]        = df["fips"].str[0:2]
    df["fy_end_month"] = df["state"].map(FY_END_MONTHS).fillna(6).astype(int)
    import numpy as np
    df["year"] = np.where(
        df["fy_end_month"] == 12,
        df["year_cog"].astype(int),
        df["year_cog"].astype(int) - 1,
    )
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
    print(f"States: {sorted(LOWER_48)}")
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
