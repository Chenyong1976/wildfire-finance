"""
Compile home rule / Dillon's Rule classification for county governments.

Expanded to all lower-48 states for the national sample.

Sources:
  - State doctrine: NACO "County Authority: A State by State Report" (2010);
    National League of Cities; Briffault (1990); state constitutional provisions
  - County charter status: ICMA Form of Government Survey; NACO; state archives;
    MRSC (WA), CGJA (CA), FL Div of Elections, NY Dept of State, MD MDP, etc.
  - Adoption dates: state legislative archives, county clerk records

Output:
  data/raw/home_rule/home_rule_counties.csv    — county-level charter status
  data/raw/home_rule/home_rule_states.csv      — state-level doctrine classification

Key notes:
  - home_rule_county = 1 if county has adopted a home rule charter
  - dillons_rule_state = 1 if state follows Dillon's Rule for county powers
  - dillons_rule_state = 0 covers both full home rule and "modified Dillon" states where
    counties have meaningful inherent or broad statutory powers (NACO 2010 classification)
  - charter_year must be < 2015 for use as pre-determined control
  - Clark County WA (charter 2015): EXCLUDED
  - States with broad statutory HR (no individual charters): MN, NC, OR, SC, UT
    — dillons_rule_state=0 but home_rule_county=0 for individual counties
  - CT: county governments abolished 1960; produces 0 CoG type=1 rows
  - RI: counties largely administrative; minimal type=1 rows
  - VA: independent cities separate from county governments; only chartered counties coded
"""

from pathlib import Path
import pandas as pd

HERE = Path(__file__).parent
ROOT = HERE.parent.parent
OUT = ROOT / "data" / "raw" / "home_rule"
OUT.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# STATE-LEVEL DOCTRINE CLASSIFICATION — All lower-48 states
# ---------------------------------------------------------------------------
# dillons_rule_state = 1  → county powers must be explicitly granted by state law
# dillons_rule_state = 0  → county has broad inherent, home rule, or broad statutory powers
# Primary source: NACO "County Authority: A State by State Report" (2010)
# Secondary: NLC, Briffault (1990), state constitutions and statutes

STATE_DOCTRINE = [
    {"state_fips": "01", "state": "AL", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; county powers limited to those expressly granted; AL Const. §104"},
    {"state_fips": "04", "state": "AZ", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; ARS Title 11 strictly limits county powers; no independent charter authority"},
    {"state_fips": "05", "state": "AR", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; county authority limited to state grants; AR Const. Art. 12"},
    {"state_fips": "06", "state": "CA", "dillons_rule_state": 0,
     "doctrine_note": "Home rule; CA Constitution Art. XI §3; individual counties may adopt charters with broad powers"},
    {"state_fips": "08", "state": "CO", "dillons_rule_state": 0,
     "doctrine_note": "Modified home rule; most counties statutory; charter option available (CRS §30-35-103)"},
    {"state_fips": "09", "state": "CT", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; county governments abolished 1960 — no county type-1 CoG rows"},
    {"state_fips": "10", "state": "DE", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; only 3 counties, very limited powers (county government mainly administrative)"},
    {"state_fips": "12", "state": "FL", "dillons_rule_state": 0,
     "doctrine_note": "Modified home rule; FL Const. Art. VIII §1(g): counties may exercise ordinance-making power; 20+ charter counties"},
    {"state_fips": "13", "state": "GA", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; GA Const. Art. IX §2 limits county home rule; major 1983 reforms added some powers"},
    {"state_fips": "16", "state": "ID", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; no county home rule provision in Idaho Constitution"},
    {"state_fips": "17", "state": "IL", "dillons_rule_state": 0,
     "doctrine_note": "Modified home rule; IL Const. Art. VII §6: Cook County has home rule; other counties may vote for it"},
    {"state_fips": "18", "state": "IN", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; county powers strictly enumerated by state; IC Title 36"},
    {"state_fips": "19", "state": "IA", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; Iowa Code §331.301 limits county authority to state grants"},
    {"state_fips": "20", "state": "KS", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; KSA Title 19 limits county authority"},
    {"state_fips": "21", "state": "KY", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; KRS §67 limits county powers to state grants; urban-county govts exception"},
    {"state_fips": "22", "state": "LA", "dillons_rule_state": 0,
     "doctrine_note": "Home rule; LA Const. Art. VI §5: parishes may adopt home rule charters; strong parish tradition"},
    {"state_fips": "23", "state": "ME", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; ME counties have limited powers; municipalities have home rule (30-A MRSA §3001)"},
    {"state_fips": "24", "state": "MD", "dillons_rule_state": 0,
     "doctrine_note": "Home rule; MD Const. Art. XI-A: counties may adopt charters; 9 charter counties"},
    {"state_fips": "25", "state": "MA", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; MA Home Rule Amendment (1966) applies to municipalities; 8 counties abolished"},
    {"state_fips": "26", "state": "MI", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; county powers enumerated by statute (PA 156 of 1851); charter townships differ"},
    {"state_fips": "27", "state": "MN", "dillons_rule_state": 0,
     "doctrine_note": "Broad statutory home rule; Minn. Stat. §375 grants broad county authority; charter option exists"},
    {"state_fips": "28", "state": "MS", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; MS Code §19-3-1 limits county powers"},
    {"state_fips": "29", "state": "MO", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule generally; St. Louis County and Jackson County have broader powers; MO Const. Art. VI §18"},
    {"state_fips": "30", "state": "MT", "dillons_rule_state": 0,
     "doctrine_note": "Self-government; MT Constitution Art. XI §6; broad local powers; charter option"},
    {"state_fips": "31", "state": "NE", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; NRS §23 limits county authority to express state grants"},
    {"state_fips": "32", "state": "NV", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; NRS Title 20 limits county powers; no county charter provision"},
    {"state_fips": "33", "state": "NH", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; NH counties largely administrative arms of state; RSA Title VII"},
    {"state_fips": "34", "state": "NJ", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; county powers enumerated (NJSA 40:23-1 et seq.); Optional County Charter Law gives some flexibility"},
    {"state_fips": "35", "state": "NM", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; NMSA §4-38 limits county authority"},
    {"state_fips": "36", "state": "NY", "dillons_rule_state": 0,
     "doctrine_note": "Home rule; NY Const. Art. IX: counties may adopt charters; ~30 of 62 counties have charters"},
    {"state_fips": "37", "state": "NC", "dillons_rule_state": 0,
     "doctrine_note": "Broad statutory home rule; NC County HR Act 1973 (G.S. §153A) grants broad authority to all counties"},
    {"state_fips": "38", "state": "ND", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; NDCC §11-10 limits county powers to state grants"},
    {"state_fips": "39", "state": "OH", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule generally; OH Const. Art. X §1: charter option exists but rarely used"},
    {"state_fips": "40", "state": "OK", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; Oklahoma counties have very limited powers; 68 OS §§3201-3210"},
    {"state_fips": "41", "state": "OR", "dillons_rule_state": 0,
     "doctrine_note": "Broad home rule; ORS ch. 203 grants all counties broad authority; individual charter option since 1958"},
    {"state_fips": "42", "state": "PA", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; county powers enumerated by class (2nd-8th class); Home Rule Charter and Optional Plans Law allows some flexibility"},
    {"state_fips": "44", "state": "RI", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; RI counties largely administrative; no meaningful county government functions"},
    {"state_fips": "45", "state": "SC", "dillons_rule_state": 0,
     "doctrine_note": "Broad statutory home rule; SC Local Gov't Fund and HR Act 1975: counties have broad ordinance power"},
    {"state_fips": "46", "state": "SD", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; SDCL §7-8 limits county authority"},
    {"state_fips": "47", "state": "TN", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; TCA Title 5 limits county authority to express state grants"},
    {"state_fips": "48", "state": "TX", "dillons_rule_state": 1,
     "doctrine_note": "Strict Dillon's Rule; TX counties are administrative arms of the state; no home rule authority; TX Const. Art. IX"},
    {"state_fips": "49", "state": "UT", "dillons_rule_state": 0,
     "doctrine_note": "Broad statutory home rule; Dillon's Rule abolished (State v. Hutchinson 1980); no individual charters"},
    {"state_fips": "50", "state": "VT", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; VT counties largely administrative; municipalities have home rule"},
    {"state_fips": "51", "state": "VA", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; VA counties strictly limited; 88 independent cities separate from counties"},
    {"state_fips": "53", "state": "WA", "dillons_rule_state": 0,
     "doctrine_note": "Home rule option; WA Constitution Art. XI §4; 7/39 counties have adopted charters"},
    {"state_fips": "54", "state": "WV", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; WV Code §7-1 limits county authority to state grants"},
    {"state_fips": "55", "state": "WI", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; WI counties enumerated powers only; Wis. Stat. §59"},
    {"state_fips": "56", "state": "WY", "dillons_rule_state": 1,
     "doctrine_note": "Dillon's Rule; home rule amendment (1972) applies to municipalities only; counties follow Dillon's Rule"},
]

# ---------------------------------------------------------------------------
# COUNTY-LEVEL CHARTER STATUS
# home_rule_county = 1 if county has adopted a home rule charter pre-2015
# Excludes: Clark County WA (2015 adoption — not pre-determined)
# ---------------------------------------------------------------------------
# Format: fips, county, state, charter_year, home_rule_county, pre2015_valid, date_source

CHARTER_COUNTIES = [
    # ==========================================================================
    # NOTES ON COVERAGE:
    # States where ALL counties operate under broad STATUTORY home rule (no
    # individual charters): MN (Minn. Stat. §375), NC (G.S. §153A), OR (ORS 203),
    # SC (1975 HR Act), UT (State v. Hutchinson). These states have
    # dillons_rule_state=0 but home_rule_county=0 for individual counties.
    # IL: Cook County has home rule by constitutional population threshold (not a
    # charter); included below. Other large IL counties may vote for HR.
    # VA: independent cities are not county governments; excluded.
    # ==========================================================================

    # ---- CALIFORNIA (15 confirmed charter counties, pre-2015 adoption) ----
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
    # ---- COLORADO (2 home rule charter counties) ----
    {"fips": "08097", "county": "Pitkin",          "state": "CO", "charter_year": 1978, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "Colorado Leg."},
    {"fips": "08123", "county": "Weld",            "state": "CO", "charter_year": 1976, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "Weld County; Colorado Leg."},
    # ---- FLORIDA (23 home rule charter counties as of 2013; FL Div of Elections) ----
    {"fips": "12001", "county": "Alachua",         "state": "FL", "charter_year": 1987, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12009", "county": "Brevard",         "state": "FL", "charter_year": 1994, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12011", "county": "Broward",         "state": "FL", "charter_year": 1975, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12015", "county": "Charlotte",       "state": "FL", "charter_year": 1986, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12019", "county": "Clay",            "state": "FL", "charter_year": 1990, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12023", "county": "Columbia",        "state": "FL", "charter_year": 2002, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12031", "county": "Duval",           "state": "FL", "charter_year": 1967, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Div. Elections (Jacksonville consolidated 1968)"},
    {"fips": "12035", "county": "Flagler",         "state": "FL", "charter_year": 1994, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12055", "county": "Highlands",       "state": "FL", "charter_year": 1990, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12057", "county": "Hillsborough",    "state": "FL", "charter_year": 1983, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12071", "county": "Lee",             "state": "FL", "charter_year": 1996, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12073", "county": "Leon",            "state": "FL", "charter_year": 1984, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12081", "county": "Manatee",         "state": "FL", "charter_year": 1970, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12085", "county": "Martin",          "state": "FL", "charter_year": 1990, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12086", "county": "Miami-Dade",      "state": "FL", "charter_year": 1957, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12095", "county": "Orange",          "state": "FL", "charter_year": 1987, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12097", "county": "Osceola",         "state": "FL", "charter_year": 1991, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12099", "county": "Palm Beach",      "state": "FL", "charter_year": 1985, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12103", "county": "Pinellas",        "state": "FL", "charter_year": 1980, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12109", "county": "St. Johns",       "state": "FL", "charter_year": 2002, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12115", "county": "Sarasota",        "state": "FL", "charter_year": 1971, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12117", "county": "Seminole",        "state": "FL", "charter_year": 1991, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    {"fips": "12127", "county": "Volusia",         "state": "FL", "charter_year": 1970, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "FL Division of Elections"},
    # ---- ILLINOIS (Cook County — home rule by constitutional pop threshold) ----
    {"fips": "17031", "county": "Cook",            "state": "IL", "charter_year": 1970, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "IL Const. Art. VII §6(a); >250k threshold"},
    # ---- LOUISIANA (charter parishes; LA Const. Art. VI §5) ----
    {"fips": "22019", "county": "Calcasieu",       "state": "LA", "charter_year": 1989, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NACO; Louisiana Sec. of State"},
    {"fips": "22033", "county": "East Baton Rouge","state": "LA", "charter_year": 1947, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "City-Parish Plan of Gov't 1947"},
    {"fips": "22051", "county": "Jefferson",       "state": "LA", "charter_year": 1958, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "LA Sec. of State"},
    {"fips": "22055", "county": "Lafayette",       "state": "LA", "charter_year": 1996, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "LA Sec. of State; city-parish consolidation"},
    {"fips": "22071", "county": "Orleans",         "state": "LA", "charter_year": 1954, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "New Orleans City-Parish charter 1954"},
    # ---- MARYLAND (9 charter counties; MD Const. Art. XI-A) ----
    {"fips": "24003", "county": "Anne Arundel",    "state": "MD", "charter_year": 1964, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "Maryland MDP; MD Archives"},
    {"fips": "24005", "county": "Baltimore",       "state": "MD", "charter_year": 1956, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "Maryland MDP; Baltimore County Charter"},
    {"fips": "24013", "county": "Carroll",         "state": "MD", "charter_year": 1968, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "Maryland MDP"},
    {"fips": "24021", "county": "Frederick",       "state": "MD", "charter_year": 1992, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "Maryland MDP"},
    {"fips": "24025", "county": "Harford",         "state": "MD", "charter_year": 1972, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "Maryland MDP"},
    {"fips": "24027", "county": "Howard",          "state": "MD", "charter_year": 1968, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "Maryland MDP"},
    {"fips": "24031", "county": "Montgomery",      "state": "MD", "charter_year": 1948, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "Maryland MDP"},
    {"fips": "24033", "county": "Prince George's", "state": "MD", "charter_year": 1970, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "Maryland MDP"},
    {"fips": "24045", "county": "Wicomico",        "state": "MD", "charter_year": 1964, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "Maryland MDP"},
    # ---- MONTANA (consolidated city-county charters; adoption dates unconfirmed) ----
    {"fips": "30001", "county": "Butte-Silver Bow","state": "MT", "charter_year": 1977, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "MT State; NACO — verify via MT Secretary of State"},
    {"fips": "30023", "county": "Deer Lodge",      "state": "MT", "charter_year": 1977, "home_rule_county": 1, "pre2015_valid": None,  "date_source": "MT State; date unconfirmed — verify via MT Secretary of State"},
    {"fips": "30027", "county": "Fergus",          "state": "MT", "charter_year": None, "home_rule_county": 1, "pre2015_valid": None,  "date_source": "MT State; date unconfirmed — verify via MT Secretary of State"},
    {"fips": "30031", "county": "Gallatin",        "state": "MT", "charter_year": 1985, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "MT Secretary of State"},
    {"fips": "30049", "county": "Lewis and Clark", "state": "MT", "charter_year": 1976, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "MT Secretary of State"},
    {"fips": "30063", "county": "Missoula",        "state": "MT", "charter_year": 1975, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "MT Secretary of State"},
    # ---- NEW YORK (~30 charter counties; NY Const. Art. IX; NY Dept of State) ----
    {"fips": "36001", "county": "Albany",          "state": "NY", "charter_year": 1961, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State; Albany County Charter"},
    {"fips": "36007", "county": "Broome",          "state": "NY", "charter_year": 1963, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36011", "county": "Cayuga",          "state": "NY", "charter_year": 1976, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36013", "county": "Chautauqua",      "state": "NY", "charter_year": 1975, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36015", "county": "Chemung",         "state": "NY", "charter_year": 1961, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36019", "county": "Clinton",         "state": "NY", "charter_year": 1978, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36027", "county": "Dutchess",        "state": "NY", "charter_year": 1967, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36029", "county": "Erie",            "state": "NY", "charter_year": 1959, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36037", "county": "Genesee",         "state": "NY", "charter_year": 1963, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36055", "county": "Monroe",          "state": "NY", "charter_year": 1936, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36059", "county": "Nassau",          "state": "NY", "charter_year": 1936, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36063", "county": "Niagara",         "state": "NY", "charter_year": 1975, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36065", "county": "Oneida",          "state": "NY", "charter_year": 1961, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36067", "county": "Onondaga",        "state": "NY", "charter_year": 1961, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36069", "county": "Ontario",         "state": "NY", "charter_year": 1970, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36083", "county": "Rensselaer",      "state": "NY", "charter_year": 1961, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36087", "county": "Rockland",        "state": "NY", "charter_year": 1966, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36089", "county": "St. Lawrence",    "state": "NY", "charter_year": 1978, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36091", "county": "Saratoga",        "state": "NY", "charter_year": 1969, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36093", "county": "Schenectady",     "state": "NY", "charter_year": 1961, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36099", "county": "Seneca",          "state": "NY", "charter_year": 1969, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36103", "county": "Suffolk",         "state": "NY", "charter_year": 1959, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36109", "county": "Tompkins",        "state": "NY", "charter_year": 1967, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36111", "county": "Ulster",          "state": "NY", "charter_year": 1968, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36117", "county": "Wayne",           "state": "NY", "charter_year": 1976, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
    {"fips": "36119", "county": "Westchester",     "state": "NY", "charter_year": 1937, "home_rule_county": 1, "pre2015_valid": True,  "date_source": "NY Dept of State"},
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
     "reason": "Charter adopted 2015; not pre-determined for 2013-2021 treatment window"},
]


def main() -> None:
    df_states = pd.DataFrame(STATE_DOCTRINE)
    df_states.to_csv(OUT / "home_rule_states.csv", index=False)
    print(f"Wrote {len(df_states)} state rows → {OUT / 'home_rule_states.csv'}")
    print(f"  Dillon's Rule states: {(df_states['dillons_rule_state'] == 1).sum()}")
    print(f"  Home rule states:     {(df_states['dillons_rule_state'] == 0).sum()}")

    df_counties = pd.DataFrame(CHARTER_COUNTIES)
    df_excluded = pd.DataFrame(EXCLUDED_COUNTIES)

    n_unconfirmed = df_counties["pre2015_valid"].isna().sum()
    if n_unconfirmed > 0:
        print(f"\nWARNING: {n_unconfirmed} charter counties have unconfirmed adoption dates:")
        print(df_counties[df_counties["pre2015_valid"].isna()][
            ["fips", "county", "state", "date_source"]].to_string(index=False))
        print("  → Verify via state Secretary of State and county clerk records before using in analysis.")
        print("  → Exclude unconfirmed entries from heterogeneity analysis (set pre2015_valid=False).")

    df_counties.to_csv(OUT / "home_rule_counties.csv", index=False)
    df_excluded.to_csv(OUT / "home_rule_excluded.csv", index=False)

    print(f"\nWrote {len(df_counties)} charter county rows → {OUT / 'home_rule_counties.csv'}")
    print(f"Wrote {len(df_excluded)} excluded county rows → {OUT / 'home_rule_excluded.csv'}")
    print(f"\nCharter counties by state:")
    print(df_counties.groupby("state").size().to_string())
    print(f"\nCoverage note: NY charter list is partial (~26/62 NY counties coded).")
    print(f"States with statutory home rule (no individual charters coded): MN, NC, OR, SC, UT.")


if __name__ == "__main__":
    main()
