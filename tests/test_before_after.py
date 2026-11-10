
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from flawed_calculation import calculate_flawed_distance
from corrected_calculation import calculate_corrected_distance


def test_old_vs_fixed_zone_distance():
    """
    Independent expected result:
    Vehicle moves from x=1900 to x=2050.

    Only 50m is inside the campaign zone.

    The flawed calculation counts 150m.
    The corrected calculation counts 50m.
    """

    df = pd.DataFrame([
        {
            "record_id": "TEST_A",
            "driver_id": "TEST_DRIVER",
            "session_id": 1,
            "export_row_order": 1,
            "timestamp_utc": "2026-11-01T10:00:00Z",
            "x_m": 1900.0,
            "y_offset_m": 0.0,
        },
        {
            "record_id": "TEST_B",
            "driver_id": "TEST_DRIVER",
            "session_id": 1,
            "export_row_order": 2,
            "timestamp_utc": "2026-11-01T10:00:10Z",
            "x_m": 2050.0,
            "y_offset_m": 0.0,
        },
    ])

    old_report = calculate_flawed_distance(df)
    fixed_report = calculate_corrected_distance(df)

    old_distance = old_report["distance_m"].sum()
    fixed_distance = fixed_report["distance_m"].sum()

    print(f"\nOld calculation: {old_distance} metres")
    print(f"Fixed calculation: {fixed_distance} metres")

    # The old implementation violates the business rule.
    assert old_distance == pytest.approx(150)

    # The corrected implementation follows the rule.
    assert fixed_distance == pytest.approx(50)
