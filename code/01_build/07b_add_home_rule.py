"""
Patch panel_final.parquet / panel_final.csv with home rule columns.

Adds:
  dillons_rule_state  — 1 if county's state follows Dillon's Rule for counties
  home_rule_county    — 1 if county has adopted a confirmed pre-2015 home rule charter
  state_fips          — 2-digit state FIPS (also useful as a covariate)

Run this instead of re-running the full 07_panel_assemble.py when only
home rule data needs to be added to an existing panel.
"""

from pathlib import Path
import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
DATA_RAW       = ROOT / "data" / "raw"
DATA_PROCESSED = ROOT / "data" / "processed"

hr_states_path   = DATA_RAW / "home_rule" / "home_rule_states.csv"
hr_counties_path = DATA_RAW / "home_rule" / "home_rule_counties.csv"
panel_path       = DATA_PROCESSED / "panel_final.parquet"

print("Loading panel...")
panel = pd.read_parquet(panel_path)
panel["fips"] = panel["fips"].astype(str).str.zfill(5)
print(f"  {len(panel):,} rows × {len(panel.columns)} cols")

# Drop existing home rule columns if present (safe re-run)
for col in ["state_fips", "dillons_rule_state", "home_rule_county"]:
    if col in panel.columns:
        panel = panel.drop(columns=[col])
        print(f"  Dropped existing column: {col}")

# ── State-level doctrine ──────────────────────────────────────────────────────
print("\nMerging state-level Dillon's Rule doctrine...")
hr_states = pd.read_csv(hr_states_path, dtype={"state_fips": str})
hr_states["state_fips"] = hr_states["state_fips"].str.zfill(2)

panel["state_fips"] = panel["fips"].str[:2]
panel = panel.merge(
    hr_states[["state_fips", "dillons_rule_state"]],
    on="state_fips", how="left"
)
panel["dillons_rule_state"] = panel["dillons_rule_state"].fillna(0).astype(int)

base = panel[panel["year_cog"] == 2012]
n_dr = (base["dillons_rule_state"] == 1).sum()
n_hr = (base["dillons_rule_state"] == 0).sum()
print(f"  Dillon's Rule counties: {n_dr}")
print(f"  Home rule / broad statutory: {n_hr}")

# ── County-level charter status ───────────────────────────────────────────────
print("\nMerging county-level charter status...")
hr_counties = pd.read_csv(hr_counties_path, dtype={"fips": str})
hr_counties["fips"] = hr_counties["fips"].str.zfill(5)

# Only use entries with confirmed pre-2015 charter
hr_valid = hr_counties[hr_counties["pre2015_valid"] == True][
    ["fips", "home_rule_county"]
].drop_duplicates("fips")

panel = panel.merge(hr_valid, on="fips", how="left")
panel["home_rule_county"] = panel["home_rule_county"].fillna(0).astype(int)

n_charter = (panel[panel["year_cog"] == 2012]["home_rule_county"] == 1).sum()
print(f"  Confirmed pre-2015 charter counties: {n_charter}")

# ── Save ──────────────────────────────────────────────────────────────────────
print(f"\nSaving updated panel ({len(panel.columns)} cols)...")
panel.to_parquet(panel_path, index=False)
panel.to_csv(DATA_PROCESSED / "panel_final.csv", index=False)
print(f"  Written: {panel_path}")

# Summary by state doctrine for treated counties
print("\nTreatment × doctrine (year_cog = 2012):")
cross = (
    panel[panel["year_cog"] == 2012]
    .assign(treated=lambda d: (d["g"] > 0).astype(int))
    .groupby(["dillons_rule_state", "treated"])
    .size()
    .unstack(fill_value=0)
    .rename(columns={0: "control", 1: "treated"})
)
print(cross.to_string())
print("\nDone.")
