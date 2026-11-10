
from pathlib import Path

import numpy as np
import pandas as pd

from corrected_calculation import calculate_corrected_distance


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "synthetic_gps_pings.csv"
REPORTS = ROOT / "reports"

REPORTS.mkdir(parents=True, exist_ok=True)


def calculate_flawed_local_day_baseline(df):
    """
    Reproduce the flawed distance calculation,
    but group results by UTC+9 local date.

    This changes only the reporting date basis.
    It deliberately preserves the distance bugs:
    - arrival-order processing
    - duplicate counting
    - GPS noise inclusion
    - impossible-speed inclusion
    - outside-zone counting
    - cross-session connections

    It is a comparison baseline, not a corrected fix.
    """

    data = df.copy()

    data["timestamp_utc"] = pd.to_datetime(
        data["timestamp_utc"], utc=True
    )

    data["report_date"] = (
        data["timestamp_utc"]
        + pd.Timedelta(hours=9)
    ).dt.date

    data = data.sort_values(
        ["driver_id", "export_row_order"]
    )

    data["previous_x"] = (
        data.groupby("driver_id")["x_m"].shift()
    )

    data["previous_y"] = (
        data.groupby("driver_id")["y_offset_m"].shift()
    )

    data["distance_m"] = np.sqrt(
        (data["x_m"] - data["previous_x"]) ** 2
        + (data["y_offset_m"] - data["previous_y"]) ** 2
    ).fillna(0)

    report = (
        data.groupby(
            ["driver_id", "report_date"],
            as_index=False
        )["distance_m"]
        .sum()
    )

    return report


def main():
    df = pd.read_csv(DATA)

    flawed = calculate_flawed_local_day_baseline(df)
    corrected = calculate_corrected_distance(df)

    flawed = flawed.rename(
        columns={"distance_m": "before_distance_m"}
    )

    corrected = corrected.rename(
        columns={"distance_m": "after_distance_m"}
    )

    comparison = flawed.merge(
        corrected[
            ["driver_id", "report_date", "after_distance_m"]
        ],
        on=["driver_id", "report_date"],
        how="outer"
    ).fillna(0)

    comparison["before_km"] = (
        comparison["before_distance_m"] / 1000
    )

    comparison["after_km"] = (
        comparison["after_distance_m"] / 1000
    )

    comparison["difference_km"] = (
        comparison["before_km"]
        - comparison["after_km"]
    )

    comparison = comparison[
        [
            "driver_id",
            "report_date",
            "before_km",
            "after_km",
            "difference_km"
        ]
    ].sort_values(
        ["driver_id", "report_date"]
    )

    output = REPORTS / "daily_before_after.csv"

    comparison.to_csv(output, index=False)

    print("\nDAILY BEFORE VS AFTER (UTC+9)")
    print("=" * 70)

    print(comparison.to_string(index=False))

    print("\nTOTALS")
    print(
        f"Before: {comparison['before_km'].sum():.3f} km"
    )
    print(
        f"After:  {comparison['after_km'].sum():.3f} km"
    )

    print(f"\nSaved to: {output}")


if __name__ == "__main__":
    main()
