import random
from datetime import datetime, timedelta, timezone

import numpy as np
import pandas as pd


# --------------------------------
# CONFIGURATION
# --------------------------------

RANDOM_SEED = 42

DRIVERS = ["DRIVER_001", "DRIVER_002", "DRIVER_003", "DRIVER_004", "DRIVER_005"]

PINGS_PER_SESSION = 240

PING_INTERVAL_SECONDS = 10

CAMPAIGN_ZONE_START = 2000
CAMPAIGN_ZONE_END = 9000

DATASET_LABEL = "SYNTHETIC"


# --------------------------------
# DATA GENERATION
# --------------------------------

random.seed(RANDOM_SEED)

rng = np.random.default_rng(RANDOM_SEED)

session_starts = [
    datetime(2026, 11, 1, 14, 40, tzinfo=timezone.utc),
    datetime(2026, 11, 2, 14, 40, tzinfo=timezone.utc),
]

records = []

record_number = 1

for driver in DRIVERS:

    for session_number, session_start in enumerate(session_starts, start=1):

        for i in range(PINGS_PER_SESSION):

            timestamp = session_start + timedelta(
                seconds=i * PING_INTERVAL_SECONDS
            )

            x_position = i * 50

            y_offset = float(rng.normal(0, 3))

            fault_type = "NONE"

            # Inject GPS noise
            if i in [40, 110, 200]:
                y_offset = 150
                fault_type = "GPS_NOISE"

            # Inject impossible speed
            if i == 80:
                x_position += 2000
                fault_type = "IMPOSSIBLE_SPEED"

            record = {
                "record_id": f"PING_{record_number:05d}",
                "dataset_label": DATASET_LABEL,
                "driver_id": driver,
                "session_id": session_number,
                "source_sequence": (session_number - 1) * PINGS_PER_SESSION + i,
                "timestamp_utc": timestamp.isoformat(),
                "x_m": float(x_position),
                "y_offset_m": y_offset,
                "fault_type": fault_type,
            }

            records.append(record)

            record_number += 1

        # Inject duplicate ping
        original = records[-(PINGS_PER_SESSION - 150)]

        duplicate = original.copy()

        duplicate["record_id"] = f"PING_{record_number:05d}"
        duplicate["x_m"] += 25
        duplicate["fault_type"] = "DUPLICATE"

        records.append(duplicate)

        record_number += 1


# --------------------------------
# SHUFFLE RECORDS
# Simulates late/out-of-order arrival
# --------------------------------

random.shuffle(records)

df = pd.DataFrame(records)

df["export_row_order"] = range(1, len(df) + 1)

# --------------------------------
# SAVE DATASET
# --------------------------------

output_file = "data/synthetic_gps_pings.csv"

df.to_csv(output_file, index=False)

print("=" * 50)
print("SYNTHETIC GPS DATASET GENERATED")
print("=" * 50)

print(f"Total GPS records: {len(df)}")
print(f"Unique drivers: {df['driver_id'].nunique()}")
print(f"Dataset label: {DATASET_LABEL}")
print(f"Output file: {output_file}")

print("\nFault distribution:")

print(df["fault_type"].value_counts())

print("\nFirst five records:")

print(df.head())