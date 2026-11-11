# Final GPS Distance QA Directive and Handoff

## Objective

Demonstrate that an incorrect fictional GPS distance-billing calculation can be detected, explained, corrected in a reproducible reference implementation, and guarded by regression tests. All data and scenarios are synthetic.

## Scope

Included: deterministic synthetic dataset (2,410 pings), flawed baseline, record-level QA validator, corrected straight-road reference calculation, per-driver/day comparisons, and automated regression evidence. Excluded: production GPS/map matching, live ingestion, advertiser billing integration, real financial impact estimates, and private data.

## Business rules and modeling assumptions

| Requirement | Implementation / verification |
| --- | --- |
| Deduplicate same driver and UTC timestamp | Sort and keep one deterministically; duplicate test |
| Reject road offset >100 m | Off-road filter; 100 m boundary test |
| Reject implied speed >150 km/h | Greedy segment screening; impossible-speed and 150 km/h boundary tests |
| Use GPS timestamp, not arrival order | Chronological sort; out-of-order test |
| Report at UTC+9 midnight | In-zone interval split at local midnight; boundary test |
| Count only inside campaign zone | Clip linear road segments to 2,000–9,000 m; zone tests |
| Separate sessions | `session_id` used in synthetic model; session test |
| Avoid interpolation over long gaps | Additional 30-second gap assumption; gap test |

Linear, constant-speed interpolation between valid pings is assumed. `x_m` is road progress and `y_offset_m` is lateral noise. The reference is not production map matching.

## Completion criteria

- [x] Generate and clearly label at least 2,000 synthetic GPS pings.
- [x] Find and rank at least three problems and explain discovery methods (`intent.md`).
- [x] Provide a runnable QA validator with record-level evidence.
- [x] Preserve the flawed calculation and implement a corrected candidate.
- [x] Produce before/after distance by driver and UTC+9 local day.
- [x] Run business-rule tests and demonstrate a shared assertion failing on the flawed implementation and passing on the corrected one.

## Results and handoff appendix

### Dataset and validator

| Metric | Observed |
| --- | ---: |
| Synthetic records | 2,410 |
| Drivers | 5 |
| Duplicate keys | 10 |
| Off-road records | 30 |
| Out-of-order flags | 1,194 |
| Speed-anomaly candidate segments | 20 |
| Outside-zone records | 990 |

Flags may overlap. Outside-zone pings are not inherently invalid. Speed flags identify suspect segments, not necessarily distinct invalid points.

### Before and after

| Metric | Observed |
| --- | ---: |
| Flawed distance | 9,612.863 km |
| Corrected candidate distance | 70.000 km |
| Difference | 9,542.863 km |
| Reduction | approximately 99.27% |

The source baseline originally groups by UTC date. The `daily_before_after.csv` comparison re-groups the **still-flawed** distance by UTC+9 local date so that both sides share the same calendar. The baseline still assigns a full segment to the ending ping's date; it is not a midnight-accurate reference. The corrected candidate splits the in-zone interval at local midnight. See the CSV for the full 15-row driver/day comparison. No real advertiser losses or savings are inferred.

### Regression evidence

- Core suite: **10 passed** in the observed run.
- Shared strict zone-boundary assertion: flawed **FAIL** (150 m actual vs 50 m expected); corrected **PASS** (50 m).
- AI-assisted first correction had a zone-plus-midnight allocation bug, found with a targeted test and corrected before the observed passing run.
- Additional before/after comparison test: **PASS**, confirming both outputs on the same controlled fixture.

### Reproduction

From the repository root on Windows PowerShell:

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

$env:GPS_IMPLEMENTATION="flawed"
python -m pytest tests/test_strict_regression.py -v -s
# Intentionally fails
$env:GPS_IMPLEMENTATION="corrected"
python -m pytest tests/test_strict_regression.py -v -s
# Passes
Remove-Item Env:GPS_IMPLEMENTATION
```

### Supporting repository links

**Repository:** https://github.com/muzammilkhokhar851/gps-distance-qa

- **Runnable QA tool:** https://github.com/muzammilkhokhar851/gps-distance-qa/blob/main/src/gps_validator.py
- **Synthetic dataset:** https://github.com/muzammilkhokhar851/gps-distance-qa/blob/main/data/synthetic_gps_pings.csv
- **Dataset generator:** https://github.com/muzammilkhokhar851/gps-distance-qa/blob/main/src/generate_data.py
- **Flawed baseline:** https://github.com/muzammilkhokhar851/gps-distance-qa/blob/main/src/flawed_calculation.py
- **Corrected calculation:** https://github.com/muzammilkhokhar851/gps-distance-qa/blob/main/src/corrected_calculation.py
- **Daily comparison:** https://github.com/muzammilkhokhar851/gps-distance-qa/blob/main/reports/daily_before_after.csv
- **Regression tests:** https://github.com/muzammilkhokhar851/gps-distance-qa/tree/main/tests
- **Old failing result:** https://github.com/muzammilkhokhar851/gps-distance-qa/blob/main/reports/regression_old_failure.txt
- **Corrected passing result:** https://github.com/muzammilkhokhar851/gps-distance-qa/blob/main/reports/regression_fixed_pass.txt
- **Core test results:** https://github.com/muzammilkhokhar851/gps-distance-qa/blob/main/reports/regression_results.txt
- **Validation summary:** https://github.com/muzammilkhokhar851/gps-distance-qa/blob/main/reports/validation_summary.csv


## AI usage, checks and corrections

AI was used for initial code and test scaffolding and documentation drafting. The work was executed and checked in Windows VS Code. A targeted regression exposed a bug in the first corrected version: it allocated billable distance across midnight using the full segment duration rather than the precise in-zone interval. The implementation was revised to calculate zone-entry and zone-exit times before splitting. The strict old-versus-fixed test uses the same independent 50 m expectation.

## Known limitations and residual risks

The synthetic straight-road model cannot establish correctness for arbitrary road networks. The speed filter is greedy and can mishandle clustered outliers or missing pings. The 30-second gap policy and session boundaries are additional assumptions. Duplicate conflicts use a deterministic but arbitrary tie-breaker. The full export shuffle exaggerates out-of-order arrival. The validator's speed flags are diagnostic candidates, not an independently verified count of invalid pings. Future work would add an independent oracle for complex trajectories, more adversarial tests, realistic arrival delays, GPS uncertainty, and production road-map matching.

## Final handoff checks

- **Actual effort:** 6 H
- **Work reused from before the Quest:** Nill
- **Repository public access checked:** YES
- **Documentation and supporting artifacts:** `intent.md`, `directive.md`, and linked repository files (video details to be added separately).
