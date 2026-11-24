import json
from pathlib import Path
import jsonschema
from verifier.comparison import evaluate_candidate
from verifier.report import build_report

ROOT = Path(__file__).resolve().parents[1]
SPEC = json.loads((ROOT / "benchmark/tasks/task_001_room_extraction/specification.json").read_text(encoding="utf-8-sig"))
SCHEMA = json.loads((ROOT / "schemas/evaluation.schema.json").read_text(encoding="utf-8-sig"))

FULL_REVIT_STATE = {
    "environment": {
        "revit_version": "2027",
        "revit_locale": "French",
        "model_sha256": "abc123dummy",
    },
    "rooms": [
        {"number": "101", "name": "Living Room", "level": "Niveau 1", "area_m2": 32.5, "is_placed": True, "is_enclosed": True},
        {"number": "201", "name": "Master Bedroom", "level": "Niveau 2", "area_m2": 24.5, "is_placed": True, "is_enclosed": True},
        {"number": "202", "name": "Bathroom", "level": "Niveau 2", "area_m2": 6.2, "is_placed": True, "is_enclosed": True},
        {"number": "203", "name": "Suite", "level": "Niveau 2", "area_m2": 28.0, "is_placed": True, "is_enclosed": True},
    ],
}

EXPECTED = [
    {"number": "201", "name": "Master Bedroom", "area_m2": 24.5},
    {"number": "203", "name": "Suite", "area_m2": 28.0},
]


def test_valid_extraction_within_tolerance():
    candidate = [
        {"number": "201", "name": "Master Bedroom", "area_m2": 24.505},
        {"number": "203", "name": "Suite", "area_m2": 28.0},
    ]
    report = build_report(
        spec=SPEC,
        expected_records=EXPECTED,
        candidate_records=candidate,
        execution_meta={"execution_passed": True, "node_error_count": 0, "node_warning_count": 0, "duration_ms": 120.0},
        candidate_meta={"filename": "valid.dyn", "sha256": "111", "label": "valid_baseline"},
        environment_meta={"revit_version": "2027", "dynamo_version": "3.x", "revit_locale": "French"},
        full_revit_state=FULL_REVIT_STATE,
    )
    jsonschema.Draft202012Validator(SCHEMA).validate(report)
    assert report["verification"]["semantic_passed"] is True
    assert report["verification"]["silent_failure"] is False
    assert report["failure_categories"] == ["NONE"]


def test_silent_failure_missing_qualifying_room():
    candidate = [
        {"number": "201", "name": "Master Bedroom", "area_m2": 24.5},
    ]
    res = evaluate_candidate(SPEC, EXPECTED, candidate, {"execution_passed": True}, FULL_REVIT_STATE)
    assert res["semantic_passed"] is False
    assert res["silent_failure"] is True
    assert "MISSING_QUALIFYING_RECORDS" in res["failure_categories"]


def test_silent_failure_wrong_level_and_sqft_leak():
    candidate = [
        {"number": "101", "name": "Living Room", "area_m2": 32.5},
        {"number": "201", "name": "Master Bedroom", "area_m2": 263.7158},
        {"number": "203", "name": "Suite", "area_m2": 28.0},
    ]
    res = evaluate_candidate(SPEC, EXPECTED, candidate, {"execution_passed": True}, FULL_REVIT_STATE)
    assert res["semantic_passed"] is False
    assert res["silent_failure"] is True
    assert "WRONG_LEVEL_FILTER" in res["failure_categories"]
    assert "AREA_UNIT_OR_THRESHOLD_ERROR" in res["failure_categories"]


def test_duplicate_records_caught():
    candidate = [
        {"number": "201", "name": "Master Bedroom", "area_m2": 24.5},
        {"number": "201", "name": "Master Bedroom", "area_m2": 24.5},
        {"number": "203", "name": "Suite", "area_m2": 28.0},
    ]
    res = evaluate_candidate(SPEC, EXPECTED, candidate, {"execution_passed": True}, FULL_REVIT_STATE)
    assert res["semantic_passed"] is False
    assert "DUPLICATE_RECORDS" in res["failure_categories"]
