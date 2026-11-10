
import sys
from pathlib import Path
from datetime import datetime, timezone

import pandas as pd

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from corrected_calculation import calculate_corrected_distance


def test_zone_boundary_and_midnight():
    """
    Vehicle travels from x=1900 to x=2100 in 10 seconds.

    Campaign zone starts at x=2000.
    Only 100m should count.

    The vehicle crosses the zone boundary 5 seconds
    into the segment, exactly at local midnight.

    Therefore all 100m should belong to Nov 2.
    """

    df = pd.DataFrame([
        {
            "record_id": "TEST_001",
            "driver_id": "TEST_DRIVER",
            "session_id": 1,
            "timestamp_utc": "2026-11-01T14:59:55+00:00",
            "x_m": 1900.0,
            "y_offset_m": 0.0,
        },
        {
            "record_id": "TEST_002",
            "driver_id": "TEST_DRIVER",
            "session_id": 1,
            "timestamp_utc": "2026-11-01T15:00:05+00:00",
            "x_m": 2100.0,
            "y_offset_m": 0.0,
        },
    ])

    report = calculate_corrected_distance(df)

    actual = dict(
        zip(
            report["report_date"].astype(str),
            report["distance_m"]
        )
    )

    assert actual.get("2026-11-01", 0) == 0
    assert actual.get("2026-11-02", 0) == 100


def test_distance_outside_zone_is_zero():
    df = pd.DataFrame([
        {
            "record_id": "TEST_003",
            "driver_id": "TEST_DRIVER",
            "session_id": 1,
            "timestamp_utc": "2026-11-01T10:00:00+00:00",
            "x_m": 1000.0,
            "y_offset_m": 0.0,
        },
        {
            "record_id": "TEST_004",
            "driver_id": "TEST_DRIVER",
            "session_id": 1,
            "timestamp_utc": "2026-11-01T10:00:10+00:00",
            "x_m": 1050.0,
            "y_offset_m": 0.0,
        },
    ])

    report = calculate_corrected_distance(df)

    assert report["distance_m"].sum() == 0
