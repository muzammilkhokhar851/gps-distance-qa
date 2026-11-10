
from pathlib import Path

import numpy as np
import pandas as pd


# Resolve paths relative to the project root.
PROJECT_ROOT = Path(__file__).resolve().parent.parent

INPUT_FILE = PROJECT_ROOT / "data" / "synthetic_gps_pings.csv"
OUTPUT_FILE = PROJECT_ROOT / "reports" / "flawed_distance_report.csv"


def calculate_flawed_distance(df):
    """
    INTENTIONALLY INCORRECT REFERENCE IMPLEMENTATION.

    Known defects:
    1. Uses exported arrival order rather than GPS timestamp order.
    2. Does not remove duplicate timestamps.
    3. Does not filter off-road GPS noise.
    4. Does not reject impossible speeds.
    5. Counts distance outside the campaign zone.
    6. Groups reports by UTC date rather than UTC+9.
    """

    data = df.copy()

    # Convert timestamp strings into UTC datetime objects.
    data["timestamp_utc"] = pd.to_datetime(
        data["timestamp_utc"], utc=True
    )

    # BUG: UTC date instead of local UTC+9 date.
    data["report_date"] = data["timestamp_utc"].dt.date

    # BUG: Uses exported row order, not chronological order.
    data = data.sort_values(
        ["driver_id", "export_row_order"]
    )

    # Calculate distance between consecutive records.
    data["previous_x"] = data.groupby("driver_id")["x_m"].shift(1)
    data["previous_y"] = data.groupby("driver_id")["y_offset_m"].shift(1)

    data["distance_m"] = np.sqrt(
        (data["x_m"] - data["previous_x"]) ** 2
        + (data["y_offset_m"] - data["previous_y"]) ** 2
    )

    # First ping for each driver has no previous point.
    data["distance_m"] = data["distance_m"].fillna(0)

    # BUG: No GPS filtering, zone clipping or daily splitting.
    report = (
        data.groupby(["driver_id", "report_date"], as_index=False)
        ["distance_m"]
        .sum()
    )

    report["distance_km"] = report["distance_m"] / 1000

    return report


def main():
    print("=" * 60)
    print("INTENTIONALLY FLAWED GPS DISTANCE CALCULATION")
    print("=" * 60)

    df = pd.read_csv(INPUT_FILE)

    print(f"Input records: {len(df)}")

    report = calculate_flawed_distance(df)

    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)

    report.to_csv(OUTPUT_FILE, index=False)

    print("\nDistance per driver and UTC day:")
    print(report.to_string(index=False))

    print("\nTotal reported distance:")
    print(f"{report['distance_km'].sum():.3f} km")

    print(f"\nReport saved to: {OUTPUT_FILE}")

    print("\nWARNING: These results are intentionally incorrect.")


if __name__ == "__main__":
    main()
