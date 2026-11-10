
import sys
from pathlib import Path

import pandas as pd
import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from corrected_calculation import calculate_corrected_distance


def make_ping(record_id, timestamp, x, y=0, session=1):
    return {
        "record_id": record_id,
        "driver_id": "TEST_DRIVER",
        "session_id": session,
        "timestamp_utc": timestamp,
        "x_m": float(x),
        "y_offset_m": float(y),
    }


def distance(df):
    report = calculate_corrected_distance(pd.DataFrame(df))
    return report["distance_m"].sum()


def test_duplicate_ping_counted_once():
    pings = [
        make_ping("A", "2026-11-01T10:00:00Z", 2000),
        make_ping("B", "2026-11-01T10:00:10Z", 2050),
        make_ping("C", "2026-11-01T10:00:10Z", 2050),
        make_ping("D", "2026-11-01T10:00:20Z", 2100),
    ]

    assert distance(pings) == pytest.approx(100)


def test_out_of_order_pings():
    pings = [
        make_ping("C", "2026-11-01T10:00:20Z", 2100),
        make_ping("A", "2026-11-01T10:00:00Z", 2000),
        make_ping("B", "2026-11-01T10:00:10Z", 2050),
    ]

    assert distance(pings) == pytest.approx(100)


def test_offroad_noise_rejected():
    pings = [
        make_ping("A", "2026-11-01T10:00:00Z", 2000),
        make_ping("B", "2026-11-01T10:00:10Z", 2050, y=150),
        make_ping("C", "2026-11-01T10:00:20Z", 2100),
    ]

    assert distance(pings) == pytest.approx(100)


def test_exactly_100m_offset_accepted():
    pings = [
        make_ping("A", "2026-11-01T10:00:00Z", 2000, y=100),
        make_ping("B", "2026-11-01T10:00:10Z", 2050, y=100),
    ]

    assert distance(pings) == pytest.approx(50)


def test_impossible_speed_rejected():
    pings = [
        make_ping("A", "2026-11-01T10:00:00Z", 2000),
        make_ping("B", "2026-11-01T10:00:10Z", 4000),
        make_ping("C", "2026-11-01T10:00:20Z", 2100),
    ]

    assert distance(pings) == pytest.approx(100)


def test_exactly_150_kmh_accepted():
    pings = [
        make_ping("A", "2026-11-01T10:00:00Z", 2000),
        make_ping(
            "B",
            "2026-11-01T10:00:12Z",
            2500
        ),
    ]

    assert distance(pings) == pytest.approx(500)


def test_separate_sessions_not_connected():
    pings = [
        make_ping("A", "2026-11-01T10:00:00Z", 2000, session=1),
        make_ping("B", "2026-11-01T10:00:10Z", 2050, session=1),
        make_ping("C", "2026-11-01T11:00:00Z", 6000, session=2),
        make_ping("D", "2026-11-01T11:00:10Z", 6050, session=2),
    ]

    assert distance(pings) == pytest.approx(100)


def test_long_gap_not_interpolated():
    pings = [
        make_ping("A", "2026-11-01T10:00:00Z", 2000),
        make_ping("B", "2026-11-01T10:01:00Z", 2100),
    ]

    assert distance(pings) == pytest.approx(0)
