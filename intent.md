# intent.md — GPS Distance QA Quest

## Intent

Investigate a fictional GPS-based advertising billing calculation, identify and rank defects affecting advertiser charges and driver records, implement a runnable QA checker, correct a narrow reference calculation, and verify the outcome with reproducible synthetic evidence.

**Data disclaimer:** All drivers, pings, campaign geometry, and scenarios are synthetic. No live incidents or financial losses are claimed.

## How I investigated

I generated 2,410 deterministic synthetic pings for five fictional drivers, including duplicate driver/timestamp keys, lateral road noise, position spikes, out-of-order export rows, and segments spanning campaign-zone and local-day boundaries. I ran an intentionally flawed reference calculation, built a record-level validator, inspected its issue counts, and used independent small fixtures to test business rules. The generator uses an intentionally strong shuffle to expose arrival-order dependence; its distribution is not claimed to be realistic production traffic.

## Findings and impact ranking

The rankings below combine direct billing relevance with observed impact in this synthetic run. Exact monetary impact cannot be calculated because no advertiser price per kilometre was supplied.

| Priority | Problem | Evidence / discovery method | Advertiser impact | Driver impact |
| --- | --- | --- | --- | --- |
| 1 | Arrival-order calculation instead of GPS timestamp order | Shuffled export; validator flagged 1,194 backward-in-time rows; baseline reported 9,612.863 km versus 70.000 km for the corrected candidate | Very high risk of overbilling | Highly inflated activity/distance records |
| 2 | Counting distance outside the campaign zone | Validator found 990 outside-zone records; independent 1,900→2,050 m fixture: flawed 150 m, expected and corrected 50 m | Direct overbilling for noneligible kilometres | Incorrect credited distance |
| 3 | Off-road noise and impossible-speed spikes | Validator found 30 off-road pings and 20 speed-anomaly candidate segments; targeted threshold tests | False billable movement | Unfair or implausible trip attribution |
| 4 | Duplicate driver/timestamp keys | 10 duplicates detected by key comparison | Possible overcounting / unstable path reconstruction | Duplicate activity records |
| 5 | UTC daily grouping instead of UTC+9 | Original report had UTC dates; corrected report spans three local dates; midnight/zone regression exposed a separate allocation bug | Incorrect daily reconciliation | Incorrect day-level attribution |

The counts above are **diagnostic flags**, not mutually exclusive counts of invalid records. In particular, outside-zone pings are not invalid GPS observations, and 20 speed anomalies are candidate segments rather than 20 proven bad individual pings. The baseline's overall error cannot be attributed quantitatively to ordering alone without an isolated ablation analysis.

## First problem selected and why

I prioritized **arrival-order distance calculation** after seeing its severe distortion of the synthetic baseline. The first targeted strict regression also addressed the **campaign-zone boundary**, because it provides a simple, independent, monetary business-rule oracle: a 150 m movement from 1,900 m to 2,050 m includes exactly 50 m inside the campaign zone. The old calculation returned 150 m and the corrected candidate returned 50 m.

The corrected reference addresses the related defects together because sorting alone would still leave duplicate, noise, zone, session, and timezone errors. The scope remains a small deterministic reference implementation rather than a production GPS pipeline.

## What AI produced and what I checked

AI assisted with the Python scaffolding for synthetic data generation, the flawed baseline, QA validator, corrected reference, reports, and pytest tests. I ran the commands in Windows VS Code and inspected the outputs. The first corrected implementation allocated in-zone distance proportionally over the **entire** GPS segment when splitting at midnight. A focused boundary-plus-midnight test failed; I then used a revised implementation that calculates zone-entry and zone-exit times before splitting. Both zone tests passed after the change. A shared strict test failed against the flawed implementation (150 m vs expected 50 m) and passed against the corrected candidate (50 m).

I did not accept the initial AI-generated implementation as final simply because it produced a plausible 70 km total. I retained the failed and passing regression evidence. These observations are specific to the synthetic dataset and tests; they do not establish correctness on arbitrary GPS traces.

## Results observed

- Synthetic records: **2,410**; drivers: **5**.
- Validator: **10** duplicate keys, **30** off-road records, **1,194** out-of-order flags, **20** speed-anomaly candidate segments, **990** outside-zone records.
- Original flawed total: **9,612.863 km**.
- Corrected candidate total: **70.000 km**.
- Reduction in synthetic reported distance: approximately **99.27%**.
- Ten core tests passed; the shared strict boundary test failed for the flawed implementation and passed for the corrected implementation.
- `reports/daily_before_after.csv` provides 15 rows of per-driver/day comparisons on a UTC+9 calendar.

The 70 km total also matches a simple independent geometric sanity check: five drivers × two sessions × 7 km of campaign-zone coverage. This is a sanity check for the designed dataset, not a proof for all possible inputs.

## Deliberately excluded / unresolved

Real-road map matching, curved routes, GPS uncertainty, multiple zones, production ingestion, advertiser pricing, and live billing were excluded. The greedy spike filter, arbitrary duplicate conflict resolution, synthetic session boundaries, and 30-second maximum gap assumption require further work. The generator's full-record shuffle exaggerates disorder. The original UTC daily baseline and local-day-aligned baseline use different date grouping; the latter exists specifically to compare daily distances on the same calendar.

## Project repository

[GPS Distance QA — GitHub](https://github.com/muzammilkhokhar851/gps-distance-qa)

## Effort and prior work

**Actual effort:** 6 H

**Pre-existing work:** None; the project was created for this Quest.

**Tools used:** Windows, VS Code, Python, pandas, NumPy, pytest, Git, GitHub, and AI assistance.
