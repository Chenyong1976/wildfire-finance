"""
Compile home rule / Dillon's Rule classification for county governments.

Sources:
  - State doctrine: National League of Cities; state constitutional provisions
  - County charter status: ICMA, state archives, MRSC (WA), CGJA (CA)
  - Adoption dates: state legislative archives, county clerk records

Output:
  data/raw/home_rule/home_rule_counties.csv    — county-level charter status
  data/raw/home_rule/home_rule_states.csv      — state-level doctrine classification

Key notes:
  - home_rule_county = 1 if county has adopted a home rule charter
  - dillons_rule_state = 1 if state follows Dillon's Rule for county powers
  - charter_year must be < 2015 for use as pre-determined control in 2015-2019 window
  - Clark County WA (charter 2015) is EXCLUDED from home rule analysis
  - Montana charter dates unconfirmed — flagged pending archive verification
  - UT: statewide home rule by statute (State v. Hutchinson 1980); no individual charters
  - WY: home rule applies to municipalities only; counties follow Dillon's Rule effectively

WEST_STATES used in analysis: CA, CO, ID, MT, OR, UT, WA, WY
"""

from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
OUT = ROOT / "data" / "raw" / "home_rule"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# STATE-LEVEL DOCTRINE CLASSIFICATION
# ---------------------------------------------------------------------------
# dillons_rule_state = 1  → county powers must be explicitly granted by state
# dillons_rule_state = 0  → county has broad inherent/home rule authority
# Classification based on NLC, state constitutions, and NACO County Authority report (2010)
# WY coded as 1 (Dillon's Rule for counties, though municipalities have HR since 1972)
# UT coded as 0 (Dillon's Rule abolished by State v. Hutchinson 1980; statewide HR by statute)

STATE_DOCTRINE = [
    {"state_fips": "06", "state": "CA", "dillons_rule_state": 0,
     "doctrine_note": "Home rule option; CA Constitution Art. XI §3; individual counties may adopt charters"},
    {"state_fips": "08", "state": "CO", "dillons_rule_state": 0,
     "doctrine_note": "Mixed: most counties statutory (Dillon's Rule); charter option available; CRS §30-35-103"},
    {"state_fips": "16", "state": "ID", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; no county home rule provision in Idaho Constitution"},
    {"state_fips": "30", "state": "MT", "dillons_rule_state": 0,
     "doctrine_note": "Self-government; MT Constitution Art. XI §6; broad local powers"},
    {"state_fips": "41", "state": "OR", "dillons_rule_state": 0,
     "doctrine_note": "Home rule all counties; ORS ch. 203 grants broad authority; charter option since 1958"},
    {"state_fips": "49", "state": "UT", "dillons_rule_state": 0,
     "doctrine_note": "Dillon's Rule abolished (State v. Hutchinson 1980); statewide HR by statute"},
    {"state_fips": "53", "state": "WA", "dillons_rule_state": 0,
     "doctrine_note": "Home rule option; WA Constitution Art. XI §4; 7/39 counties have adopted charters"},
    {"state_fips": "56", "state": "WY", "dillons_rule_state": 1,
     "doctrine_note": "HR amendment (1972) applies to municipalities only; counties follow Dillon's Rule"},
]

# ---------------------------------------------------------------------------
# COUNTY-LEVEL CHARTER STATUS
# home_rule_county = 1 if county has adopted a home rule charter pre-2015
# Excludes: Clark County WA (2015 adoption — not pre-determined)
# ---------------------------------------------------------------------------
# Format: fips, county, state, charter_year, home_rule_county, pre2015_valid, date_source

CHARTER_COUNTIES = [
    # ---- CALIFORNIA (14 confirmed charter counties with pre-2015 adoption) ----
    {"fips": "06001", "county": "Alameda",        "state": "CA", "charter_year": 1927, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "CGJA"},
    {"fips": "06007", "county": "Butte",           "state": "CA", "charter_year": 1917, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "CGJA"},
    {"fips": "06017", "county": "El Dorado",       "state": "CA", "charter_year": 1994, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "CGJA"},
    {"fips": "06019", "county": "Fresno",          "state": "CA", "charter_year": 1933, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "CGJA"},
    {"fips": "06037", "county": "Los Angeles",     "state": "CA", "charter_year": 1913, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "CA Legislature"},
    {"fips": "06059", "county": "Orange",          "state": "CA", "charter_year": 2002, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "CGJA"},
    {"fips": "06061", "county": "Placer",          "state": "CA", "charter_year": 1980, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "CGJA"},
    {"fips": "06067", "county": "Sacramento",      "state": "CA", "charter_year": 1933, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "CGJA"},
    {"fips": "06071", "county": "San Bernardino",  "state": "CA", "charter_year": 1913, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "CA Legislature"},
    {"fips": "06073", "county": "San Diego",       "state": "CA", "charter_year": 1933, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "CGJA"},
    {"fips": "06075", "county": "San Francisco",   "state": "CA", "charter_year": 1932, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "CA Legislature"},
    {"fips": "06081", "county": "San Mateo",       "state": "CA", "charter_year": 1933, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "CGJA"},
    {"fips": "06085", "county": "Santa Clara",     "state": "CA", "charter_year": 1951, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "CGJA"},
    {"fips": "06089", "county": "Shasta",          "state": "CA", "charter_year": None, "home_rule_county": 1, "pre2015_valid": None,  "date_source": "CGJA; date unconfirmed"},
    {"fips": "06103", "county": "Tehama",          "state": "CA", "charter_year": 1917, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "CGJA"},
    # ---- COLORADO (2 home rule counties) ----
    {"fips": "08097", "county": "Pitkin",          "state": "CO", "charter_year": 1978, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "Colorado Leg."},
    {"fips": "08123", "county": "Weld",            "state": "CO", "charter_year": 1976, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "Weld County; Colorado Leg."},
    # ---- MONTANA (3 consolidated city-county charters; adoption dates unconfirmed) ----
    {"fips": "30001", "county": "Butte-Silver Bow","state": "MT", "charter_year": None, "home_rule_county": 1, "pre2015_valid": None,  "date_source": "MT State; date unconfirmed — verify via MT Secretary of State"},
    {"fips": "30023", "county": "Deer Lodge",      "state": "MT", "charter_year": None, "home_rule_county": 1, "pre2015_valid": None,  "date_source": "MT State; date unconfirmed — verify via MT Secretary of State"},
    {"fips": "30027", "county": "Fergus",          "state": "MT", "charter_year": None, "home_rule_county": 1, "pre2015_valid": None,  "date_source": "MT State; date unconfirmed — verify via MT Secretary of State"},
    # ---- OREGON (9 home rule charter counties) ----
    {"fips": "41003", "county": "Benton",          "state": "OR", "charter_year": 1972, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "OR Legislature"},
    {"fips": "41007", "county": "Clatsop",         "state": "OR", "charter_year": 1988, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "OR Legislature"},
    {"fips": "41027", "county": "Hood River",      "state": "OR", "charter_year": 1964, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "OR Legislature"},
    {"fips": "41029", "county": "Jackson",         "state": "OR", "charter_year": 1978, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "OR Legislature"},
    {"fips": "41033", "county": "Josephine",       "state": "OR", "charter_year": 1980, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "OR Legislature"},
    {"fips": "41039", "county": "Lane",            "state": "OR", "charter_year": 1962, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "OR Legislature"},
    {"fips": "41051", "county": "Multnomah",       "state": "OR", "charter_year": 1967, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "OR Legislature"},
    {"fips": "41069", "county": "Umatilla",        "state": "OR", "charter_year": 1993, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "OR Legislature"},
    {"fips": "41071", "county": "Washington",      "state": "OR", "charter_year": 1962, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "OR Legislature"},
    # ---- WASHINGTON (6 valid pre-2015 charter counties; Clark excluded) ----
    {"fips": "53009", "county": "Clallam",         "state": "WA", "charter_year": 1977, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "MRSC"},
    # Clark County (53011) adopted charter 2015 — EXCLUDED; not pre-determined
    {"fips": "53033", "county": "King",            "state": "WA", "charter_year": 1969, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "HistoryLink.org"},
    {"fips": "53053", "county": "Pierce",          "state": "WA", "charter_year": 1981, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "MRSC"},
    {"fips": "53055", "county": "San Juan",        "state": "WA", "charter_year": 2006, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "MRSC"},
    {"fips": "53061", "county": "Snohomish",       "state": "WA", "charter_year": 1980, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "MRSC"},
    {"fips": "53073", "county": "Whatcom",         "state": "WA", "charter_year": 1978, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "Whatcom County"},
]

EXCLUDED_COUNTIES = [
    {"fips": "53011", "county": "Clark", "state": "WA", "charter_year": 2015,
     "reason": "Charter adopted 2015; not pre-determined for 2015-2019 treatment window"},
]


def main() -> None:
    df_states = pd.DataFrame(STATE_DOCTRINE)
    df_states.to_csv(OUT / "home_rule_states.csv", index=False)
    print(f"Wrote {len(df_states)} state rows → {OUT / 'home_rule_states.csv'}")

    df_counties = pd.DataFrame(CHARTER_COUNTIES)
    df_excluded = pd.DataFrame(EXCLUDED_COUNTIES)

    n_unconfirmed = df_counties["pre2015_valid"].isna().sum()
    if n_unconfirmed > 0:
        print(f"WARNING: {n_unconfirmed} charter counties have unconfirmed adoption dates:")
        print(df_counties[df_counties["pre2015_valid"].isna()][["fips", "county", "state", "date_source"]].to_string(index=False))
        print("  → Verify via Montana Secretary of State and California County Clerk records before using in analysis.")

    df_counties.to_csv(OUT / "home_rule_counties.csv", index=False)
    df_excluded.to_csv(OUT / "home_rule_excluded.csv", index=False)

    print(f"\nWrote {len(df_counties)} charter county rows → {OUT / 'home_rule_counties.csv'}")
    print(f"Wrote {len(df_excluded)} excluded county rows → {OUT / 'home_rule_excluded.csv'}")
    print(f"\nSummary by state:")
    print(df_counties.groupby("state")["home_rule_county"].sum().to_string())


if __name__ == "__main__":
    main()
