# DynamoBench Evaluation Summary

- **Total Runs:** 7
- **Execution Pass Rate:** 100.0% (7/7)
- **Semantic Pass Rate:** 57.1% (4/7)
- **Silent Failure Rate:** 42.9% (3/7)

| Task ID | Candidate Label | Generator | Exec | Semantic | Silent Fail | Duration (ms) | Failure Categories |
| :--- | :--- | :--- | :---: | :---: | :---: | ---: | :--- |
| `task_001_room_extraction` | `llm_buggy_no_unit_or_level_filter` | `simulated_llm_baseline` | PASS | FAIL | YES | 13.81 | AREA_UNIT_OR_THRESHOLD_ERROR, WRONG_LEVEL_FILTER |
| `task_001_room_extraction` | `valid_reference_dyn` | `human_reference` | PASS | PASS | NO | 13.97 | NONE |
| `task_002_thermal_zone_writeback` | `buggy_raw_sqft_unenclosed_dyn` | `synthetic_failure_baseline` | PASS | FAIL | YES | 44.59 | PARAMETER_VALUE_MISMATCH |
| `task_002_thermal_zone_writeback` | `llm_zero_shot_t002` | `llm_baseline` | PASS | PASS | NO | 45.95 | NONE |
| `task_002_thermal_zone_writeback` | `valid_tx_writeback_dyn` | `human_reference` | PASS | PASS | NO | 46.93 | NONE |
| `task_005_sensor_anchor_placement` | `buggy_raw_feet_3d_sensor_dyn_t005` | `synthetic_failure_baseline` | PASS | FAIL | YES | 33.45 | PARAMETER_VALUE_MISMATCH |
| `task_005_sensor_anchor_placement` | `valid_3d_sensor_placement_dyn_t005` | `human_reference` | PASS | PASS | NO | 5236.24 | NONE |
