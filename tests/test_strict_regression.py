
import os
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from flawed_calculation import calculate_flawed_distance
from corrected_calculation import calculate_corrected_distance


def test_zone_boundary_business_rule():
    """
    Independent business expectation:

    Vehicle travels from x=1900 to x=2050.
    Campaign zone starts at x=2000.

    Expected billable distance = 50 metres.
    """

    df = pd.DataFrame([
        {
            "record_id": "REG_001",
            "driver_id": "REGRESSION_DRIVER",
            "session_id": 1,
            "export_row_order": 1,
            "timestamp_utc": "2026-11-01T10:00:00Z",
            "x_m": 1900.0,
            "y_offset_m": 0.0,
        },
        {
            "record_id": "REG_002",
            "driver_id": "REGRESSION_DRIVER",
            "session_id": 1,
            "export_row_order": 2,
            "timestamp_utc": "2026-11-01T10:00:10Z",
            "x_m": 2050.0,
            "y_offset_m": 0.0,
        },
    ])

    implementation = os.environ.get(
        "GPS_IMPLEMENTATION", "corrected"
    )

    if implementation == "flawed":
        report = calculate_flawed_distance(df)
    elif implementation == "corrected":
        report = calculate_corrected_distance(df)
    else:
        pytest.fail(
            f"Unknown implementation: {implementation}"
        )

    actual_distance = report["distance_m"].sum()

    print(
        f"\nImplementation: {implementation}"
        f"\nActual distance: {actual_distance:.2f}m"
        f"\nExpected distance: 50.00m"
    )

    assert actual_distance == pytest.approx(50.0)
