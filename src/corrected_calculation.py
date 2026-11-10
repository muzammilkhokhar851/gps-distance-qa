
from pathlib import Path
from datetime import timedelta

import pandas as pd


# --------------------------------
# CONFIGURATION
# --------------------------------

ROOT = Path(__file__).resolve().parent.parent

INPUT = ROOT / "data" / "synthetic_gps_pings.csv"
OUTPUT = ROOT / "reports" / "corrected_distance_report.csv"

MAX_OFFSET_M = 100
MAX_SPEED_KMH = 150
ZONE_START = 2000
ZONE_END = 9000
MAX_GAP_SECONDS = 30

LOCAL_OFFSET = timedelta(hours=9)


# --------------------------------
# CAMPAIGN ZONE CALCULATION
# --------------------------------

def clip_zone_distance(x1, x2):
    """
    Calculate the distance travelled inside
    the campaign zone along a straight road.
    """

    low = min(x1, x2)
    high = max(x1, x2)

    overlap_start = max(low, ZONE_START)
    overlap_end = min(high, ZONE_END)

    return max(0.0, overlap_end - overlap_start)


def calculate_zone_interval(previous, current, elapsed):
    """
    Find the exact fraction of a segment that
    lies inside the campaign zone.

    Assumption:
    Vehicle movement is linear and at constant
    speed between consecutive GPS pings.
    """

    x1 = previous.x_m
    x2 = current.x_m

    dx = x2 - x1

    if dx == 0:
        return None

    # Fraction where the vehicle crosses
    # the campaign-zone boundaries.
    f_start = (ZONE_START - x1) / dx
    f_end = (ZONE_END - x1) / dx

    entry_fraction = max(
        0.0,
        min(1.0, min(f_start, f_end))
    )

    exit_fraction = max(
        0.0,
        min(1.0, max(f_start, f_end))
    )

    if exit_fraction <= entry_fraction:
        return None

    zone_entry_time = (
        previous.timestamp_utc
        + timedelta(seconds=elapsed * entry_fraction)
    )

    zone_exit_time = (
        previous.timestamp_utc
        + timedelta(seconds=elapsed * exit_fraction)
    )

    distance_m = (
        abs(dx) * (exit_fraction - entry_fraction)
    )

    return zone_entry_time, zone_exit_time, distance_m


# --------------------------------
# CORRECTED DISTANCE CALCULATION
# --------------------------------

def calculate_corrected_distance(df):
    """
    Calculate billable GPS distance.

    Rules:
    1. Sort pings by their UTC timestamps.
    2. Count duplicate driver/timestamp keys once.
    3. Reject pings more than 100m off-road.
    4. Reject movements implying speed >150 km/h.
    5. Do not connect separate driving sessions.
    6. Count distance only inside the campaign zone.
    7. Split in-zone distance across UTC+9 days.
    8. Do not bridge gaps longer than 30 seconds.

    The 30-second gap limit is an additional
    synthetic-model assumption, not a Quest rule.
    """

    data = df.copy()

    data["timestamp_utc"] = pd.to_datetime(
        data["timestamp_utc"],
        utc=True
    )

    # --------------------------------
    # STEP 1: SORT GPS PINGS
    # --------------------------------

    data = data.sort_values(
        ["driver_id", "timestamp_utc", "record_id"]
    )

    # --------------------------------
    # STEP 2: REMOVE DUPLICATES
    # --------------------------------

    data = data.drop_duplicates(
        subset=["driver_id", "timestamp_utc"],
        keep="first"
    )

    # --------------------------------
    # STEP 3: REMOVE OFF-ROAD NOISE
    # --------------------------------

    data = data[
        data["y_offset_m"].abs() <= MAX_OFFSET_M
    ].copy()

    results = []

    # --------------------------------
    # STEP 4: PROCESS EACH SESSION
    # --------------------------------

    for (driver, session), group in data.groupby(
        ["driver_id", "session_id"]
    ):

        group = group.sort_values("timestamp_utc")

        points = list(group.itertuples(index=False))

        # --------------------------------
        # STEP 5: FILTER SPEED ANOMALIES
        # --------------------------------

        cleaned = []

        for point in points:

            if not cleaned:
                cleaned.append(point)
                continue

            previous = cleaned[-1]

            elapsed = (
                point.timestamp_utc
                - previous.timestamp_utc
            ).total_seconds()

            if elapsed <= 0:
                continue

            speed_kmh = (
                abs(point.x_m - previous.x_m)
                / elapsed
                * 3.6
            )

            if speed_kmh > MAX_SPEED_KMH:
                continue

            cleaned.append(point)

        # --------------------------------
        # STEP 6: CALCULATE VALID SEGMENTS
        # --------------------------------

        for previous, current in zip(
            cleaned, cleaned[1:]
        ):

            elapsed = (
                current.timestamp_utc
                - previous.timestamp_utc
            ).total_seconds()

            if elapsed <= 0:
                continue

            # Do not interpolate over large gaps.
            if elapsed > MAX_GAP_SECONDS:
                continue

            # Recheck speed for clarity and safety.
            speed_kmh = (
                abs(current.x_m - previous.x_m)
                / elapsed
                * 3.6
            )

            if speed_kmh > MAX_SPEED_KMH:
                continue

            zone_interval = calculate_zone_interval(
                previous,
                current,
                elapsed
            )

            if zone_interval is None:
                continue

            (
                zone_entry_time,
                zone_exit_time,
                zone_distance
            ) = zone_interval

            # --------------------------------
            # STEP 7: CONVERT TO UTC+9
            # --------------------------------

            cursor = zone_entry_time + LOCAL_OFFSET
            local_end = zone_exit_time + LOCAL_OFFSET

            zone_duration = (
                local_end - cursor
            ).total_seconds()

            if zone_duration <= 0:
                continue

            # --------------------------------
            # STEP 8: SPLIT AT LOCAL MIDNIGHT
            # --------------------------------

            while cursor < local_end:

                next_midnight = (
                    cursor.replace(
                        hour=0,
                        minute=0,
                        second=0,
                        microsecond=0
                    )
                    + timedelta(days=1)
                )

                chunk_end = min(
                    local_end,
                    next_midnight
                )

                fraction = (
                    (chunk_end - cursor).total_seconds()
                    / zone_duration
                )

                results.append({
                    "driver_id": driver,
                    "report_date": cursor.date(),
                    "distance_m": zone_distance * fraction
                })

                cursor = chunk_end

    # --------------------------------
    # STEP 9: BUILD FINAL REPORT
    # --------------------------------

    report = pd.DataFrame(
        results,
        columns=[
            "driver_id",
            "report_date",
            "distance_m"
        ]
    )

    if report.empty:
        return pd.DataFrame(
            columns=[
                "driver_id",
                "report_date",
                "distance_m",
                "distance_km"
            ]
        )

    report = (
        report.groupby(
            ["driver_id", "report_date"],
            as_index=False
        )["distance_m"]
        .sum()
    )

    report["distance_km"] = (
        report["distance_m"] / 1000
    )

    report = report.sort_values(
        ["driver_id", "report_date"]
    ).reset_index(drop=True)

    return report


# --------------------------------
# MAIN EXECUTION
# --------------------------------

def main():

    print("=" * 60)
    print("CORRECTED GPS DISTANCE CALCULATION")
    print("=" * 60)

    df = pd.read_csv(INPUT)

    print(f"\nInput GPS records: {len(df)}")

    report = calculate_corrected_distance(df)

    OUTPUT.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    report.to_csv(
        OUTPUT,
        index=False
    )

    print("\nDistance per driver and local day (UTC+9):")
    print(report.to_string(index=False))

    print("\nTotal corrected distance:")
    print(f"{report['distance_km'].sum():.3f} km")

    print(f"\nReport saved to: {OUTPUT}")

    print("\nCalculation completed.")


if __name__ == "__main__":
    main()
