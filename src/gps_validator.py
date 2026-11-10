
from pathlib import Path

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parent.parent
INPUT = ROOT / "data" / "synthetic_gps_pings.csv"
REPORTS = ROOT / "reports"

MAX_OFFSET_M = 100
MAX_SPEED_KMH = 150
ZONE_START_M = 2000
ZONE_END_M = 9000


def validate_gps(df):
    data = df.copy()

    data["timestamp_utc"] = pd.to_datetime(
        data["timestamp_utc"], utc=True
    )

    # 1. Detect duplicates
    data["is_duplicate"] = data.duplicated(
        subset=["driver_id", "timestamp_utc"],
        keep="first"
    )

    # 2. Detect off-road GPS noise
    data["is_offroad"] = (
        data["y_offset_m"].abs() > MAX_OFFSET_M
    )

    # 3. Detect arrival-order problems
    arrival = data.sort_values(
        ["driver_id", "export_row_order"]
    ).copy()

    arrival["previous_timestamp"] = (
        arrival.groupby("driver_id")["timestamp_utc"].shift()
    )

    arrival["is_out_of_order"] = (
        arrival["timestamp_utc"] <
        arrival["previous_timestamp"]
    )

    data = data.merge(
        arrival[["record_id", "is_out_of_order"]],
        on="record_id",
        how="left",
        validate="one_to_one"
    )

    # 4. Detect impossible speed candidates
    chronological = data.sort_values(
        ["driver_id", "timestamp_utc", "export_row_order"]
    ).copy()

    chronological["previous_x"] = (
        chronological.groupby("driver_id")["x_m"].shift()
    )

    chronological["previous_y"] = (
        chronological.groupby("driver_id")["y_offset_m"].shift()
    )

    chronological["previous_timestamp"] = (
        chronological.groupby("driver_id")["timestamp_utc"].shift()
    )

    dx = chronological["x_m"] - chronological["previous_x"]
    dy = chronological["y_offset_m"] - chronological["previous_y"]

    chronological["segment_distance_m"] = np.sqrt(
        dx ** 2 + dy ** 2
    )

    chronological["time_difference_s"] = (
        chronological["timestamp_utc"]
        - chronological["previous_timestamp"]
    ).dt.total_seconds()

    valid_time = chronological["time_difference_s"] > 0

    chronological["speed_kmh"] = np.where(
        valid_time,
        chronological["segment_distance_m"]
        / chronological["time_difference_s"]
        * 3.6,
        np.nan
    )

    chronological["is_speed_anomaly"] = (
        chronological["speed_kmh"] > MAX_SPEED_KMH
    )

    data = data.merge(
        chronological[
            ["record_id", "speed_kmh", "is_speed_anomaly"]
        ],
        on="record_id",
        how="left",
        validate="one_to_one"
    )

    # 5. Identify records outside the zone
    data["is_outside_zone"] = (
        (data["x_m"] < ZONE_START_M)
        | (data["x_m"] > ZONE_END_M)
    )

    # These flags are diagnostic, not final billing decisions.
    flags = [
        "is_duplicate",
        "is_offroad",
        "is_out_of_order",
        "is_speed_anomaly",
        "is_outside_zone",
    ]

    data["issue_count"] = data[flags].sum(axis=1)

    return data


def main():
    REPORTS.mkdir(parents=True, exist_ok=True)

    df = pd.read_csv(INPUT)

    results = validate_gps(df)

    results.to_csv(
        REPORTS / "gps_validation_report.csv",
        index=False
    )

    summary = {
        "duplicate_records": int(results["is_duplicate"].sum()),
        "offroad_records": int(results["is_offroad"].sum()),
        "out_of_order_records": int(
            results["is_out_of_order"].sum()
        ),
        "speed_anomaly_candidates": int(
            results["is_speed_anomaly"].sum()
        ),
        "outside_zone_records": int(
            results["is_outside_zone"].sum()
        ),
    }

    pd.DataFrame(
        list(summary.items()),
        columns=["issue", "count"]
    ).to_csv(
        REPORTS / "validation_summary.csv",
        index=False
    )

    print("\nGPS QA VALIDATION RESULTS")
    print("=" * 45)

    for issue, count in summary.items():
        print(f"{issue}: {count}")

    print("\nReports generated:")
    print("reports/gps_validation_report.csv")
    print("reports/validation_summary.csv")


if __name__ == "__main__":
    main()
