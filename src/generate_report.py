
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
REPORTS = ROOT / "reports"

OLD_FILE = REPORTS / "flawed_distance_report.csv"
NEW_FILE = REPORTS / "corrected_distance_report.csv"

old = pd.read_csv(OLD_FILE)
new = pd.read_csv(NEW_FILE)

old = old.rename(columns={
    "report_date": "utc_date",
    "distance_km": "flawed_distance_km"
})

new = new.rename(columns={
    "report_date": "local_date_utc_plus_9",
    "distance_km": "corrected_distance_km"
})

# Keep each report's date basis explicit.
old.to_csv(
    REPORTS / "flawed_utc_breakdown.csv",
    index=False
)

new.to_csv(
    REPORTS / "corrected_local_breakdown.csv",
    index=False
)

# Compare totals by driver without matching
# incompatible UTC and local calendar dates.
old_totals = old.groupby("driver_id", as_index=False)[
    "flawed_distance_km"
].sum()

new_totals = new.groupby("driver_id", as_index=False)[
    "corrected_distance_km"
].sum()

comparison = old_totals.merge(
    new_totals,
    on="driver_id",
    how="outer"
).fillna(0)

comparison["difference_km"] = (
    comparison["flawed_distance_km"]
    - comparison["corrected_distance_km"]
)

comparison["reduction_percent"] = (
    comparison["difference_km"]
    / comparison["flawed_distance_km"].replace(0, float("nan"))
    * 100
)

comparison.to_csv(
    REPORTS / "before_after_by_driver.csv",
    index=False
)

print("\nBEFORE VS AFTER — DRIVER TOTALS")
print("=" * 65)
print(comparison.to_string(index=False))

print("\nFLAWED REPORT — UTC DAYS")
print(old[[
    "driver_id", "utc_date", "flawed_distance_km"
]].to_string(index=False))

print("\nCORRECTED REPORT — UTC+9 LOCAL DAYS")
print(new[[
    "driver_id",
    "local_date_utc_plus_9",
    "corrected_distance_km"
]].to_string(index=False))

print("\nReports generated successfully.")
