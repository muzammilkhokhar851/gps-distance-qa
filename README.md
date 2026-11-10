# GPS Distance Synthetic Data - QA Quest

A reproducible QA investigation of a fictional vehicle-advertising platform that bills advertisers for kilometres driven **inside** a campaign zone. This is a synthetic assessment project, **not** a live product or production billing system.

## The problem

The intentionally flawed reference calculation processes GPS pings in exported arrival order, includes duplicates and noise, ignores campaign-zone boundaries, connects separate driving sessions, and groups reports by UTC rather than UTC+9. It dramatically overstates distance on the synthetic dataset.

## Evidence from the executed synthetic dataset

| Measure | Result |
| --- | ---: |
| GPS records | 2,410 |
| Synthetic drivers | 5 |
| Duplicate records | 10 |
| Off-road records (>100 m) | 30 |
| Out-of-order flags | 1,194 |
| Speed anomaly candidate segments (>150 km/h) | 20 |
| Outside-zone records | 990 |
| Flawed distance | 9,612.863 km |
| Corrected candidate distance | 70.000 km |

The reduction is approximately **99.27%**. This is synthetic overcounting, **not** real financial savings. The dataset intentionally exaggerates arrival-order disorder by shuffling the export.

## Model and assumptions

- Road: straight, with position `x_m` along the road and lateral offset `y_offset_m`.
- Campaign zone: `x_m` from 2,000 m to 9,000 m (inclusive).
- Pings more than 100 m off-road are excluded; the 100 m boundary itself is accepted.
- Speeds above 150 km/h are excluded; exactly 150 km/h is accepted.
- Duplicate key: `(driver_id, timestamp_utc)`; the corrected candidate keeps the record with the lexicographically first `record_id` after sorting.
- Timestamps are UTC; daily billing is reported in fixed UTC+9.
- Segments are treated as linear, constant-speed motion between pings. Only the in-zone portion is billable, and its time interval is split at local midnight.
- Synthetic `session_id` boundaries are not connected; gaps longer than 30 seconds are not interpolated. These are **additional modeling assumptions**, not stated Quest requirements.
- Speed screening is greedy and has known limitations with clustered spikes or missing pings. The implementation is a tested reference candidate, not production-grade GPS map matching.

## Requirements

Windows PowerShell (or another terminal), Python 3.11+ recommended, and Git. No API keys, confidential information, paid services, or external GPS data are needed.

## Quick start

From the repository root:

```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python src/generate_data.py
python src/flawed_calculation.py
python src/gps_validator.py
python src/corrected_calculation.py
python src/generate_report.py
python src/generate_daily_comparison.py
python -m pytest tests/ -v
```

Run the generator before the calculations. It uses a fixed random seed, so the dataset can be reproduced. The `data/` and `reports/` folders should be present; scripts create their report output directories as needed. Run commands from the repository root.

## Strict fail-before / pass-after check

The **same assertion** checks that a 150 m segment crossing the campaign boundary contains only 50 m of billable distance.

```powershell
$env:GPS_IMPLEMENTATION="flawed"
python -m pytest tests/test_strict_regression.py -v -s
# Expected: FAIL (actual 150 m, expected 50 m)

$env:GPS_IMPLEMENTATION="corrected"
python -m pytest tests/test_strict_regression.py -v -s
# Expected: PASS (actual 50 m)

Remove-Item Env:GPS_IMPLEMENTATION
```

The old failure is intentional. To run the normal suite with corrected behaviour, ensure `GPS_IMPLEMENTATION` is unset or `corrected`.

## Files and evidence

| Location | Purpose |
| --- | --- |
| `src/generate_data.py` | Deterministic synthetic fault-injection generator |
| `data/synthetic_gps_pings.csv` | Synthetic GPS dataset |
| `src/flawed_calculation.py` | Intentionally flawed baseline |
| `src/gps_validator.py` | Record-level QA flags and summary |
| `src/corrected_calculation.py` | Corrected reference candidate |
| `src/generate_report.py` | Driver totals and separately labelled UTC/local-day reports |
| `src/generate_daily_comparison.py` | Like-for-like UTC+9 per-driver/day comparison |
| `tests/` | Business-rule and regression tests |
| `reports/daily_before_after.csv` | Per-driver, per-local-day comparison |
| `reports/regression_old_failure.txt` | Captured old failure |
| `reports/regression_fixed_pass.txt` | Captured corrected pass |
| `reports/regression_results.txt` | Captured core test run |
| `intent.md` | Investigation and prioritization |
| `directive.md` | Final handoff and completion criteria |

The original flawed report uses UTC calendar dates. The additional aligned comparison changes **only the date grouping** to UTC+9 while preserving flawed distance logic; it is labelled separately and is not a byte-for-byte rerun of the original UTC daily report.

## Known limitations

This synthetic model has no real map matching, curved roads, live ingestion, billing integration, GPS accuracy model, or multi-zone handling. Duplicate conflicts use a deterministic but arbitrary tie-breaker. The greedy speed filter and 30-second gap policy need further validation. The synthetic generator's `fault_type` is an injection label, not a substitute for independent QA assertions.

## AI assistance and verification

AI assisted with the initial generator, validator, calculation, and test scaffolding. Manual review and execution identified a bug in the first corrected version: it split an in-zone distance across local midnight using the **whole segment** time instead of the **in-zone interval**. A targeted test failed before that correction and passed after the implementation was revised. See `intent.md` and `directive.md` for the investigation and handoff.

## License and data

Synthetic assessment data only. No real drivers, advertisers, incidents, credentials, or employer information are represented.