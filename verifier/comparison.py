from typing import Any
from verifier.assertions import (
    compare_record_values,
    find_duplicates,
    validate_record_schema,
)


def classify_unexpected_record(
    rec: dict,
    revit_rooms_by_number: dict[str, dict],
    spec: dict,
) -> tuple[str, list[str]]:
    """Diagnose why an unexpected room appeared in candidate output."""
    num = rec["number"].strip()
    target_levels = {lvl.strip().lower() for lvl in spec["parameters"]["target_level_names"]}
    threshold = float(spec["parameters"]["area_threshold_m2"])
    categories = []

    if num not in revit_rooms_by_number:
        return "Room number does not exist in Revit document.", ["UNEXPECTED_NON_QUALIFYING_RECORDS"]

    truth = revit_rooms_by_number[num]
    reasons = []
    if not truth.get("is_placed", True) or not truth.get("is_enclosed", True):
        reasons.append("Room is unplaced or unbounded in Revit.")
        categories.append("UNEXPECTED_NON_QUALIFYING_RECORDS")

    if truth.get("level", "").strip().lower() not in target_levels:
        reasons.append(f"Room is on '{truth.get('level')}', not target level.")
        categories.append("WRONG_LEVEL_FILTER")

    if float(truth.get("area_m2", 0.0)) <= threshold:
        reasons.append(
            f"Room area {truth.get('area_m2')} m² does not exceed {threshold} m²."
        )
        categories.append("AREA_UNIT_OR_THRESHOLD_ERROR")

    if not reasons:
        reasons.append("Non-qualifying record included.")
        categories.append("UNEXPECTED_NON_QUALIFYING_RECORDS")

    return " ".join(reasons), categories


def evaluate_candidate(
    spec: dict,
    expected_records: list[dict],
    candidate_records: Any,
    execution_meta: dict,
    full_revit_state: dict | None = None,
) -> dict:
    """Compare candidate workflow output against deterministic expected records."""
    exec_passed = bool(execution_meta.get("execution_passed", False))
    node_errors = int(execution_meta.get("node_error_count", 0))
    node_warnings = int(execution_meta.get("node_warning_count", 0))

    categories: set[str] = set()
    if not exec_passed or node_errors > 0:
        categories.add("EXECUTION_NODE_ERROR")
    if node_warnings > 0:
        categories.add("EXECUTION_NODE_WARNING")

    schema_errors = validate_record_schema(candidate_records, spec)
    if schema_errors:
        categories.add("SCHEMA_OR_TYPE_ERROR")
        return {
            "semantic_passed": False,
            "silent_failure": bool(exec_passed),
            "expected_count": len(expected_records),
            "actual_count": len(candidate_records) if isinstance(candidate_records, list) else 0,
            "matched_count": 0,
            "missing_count": len(expected_records),
            "unexpected_count": 0,
            "duplicate_count": 0,
            "value_mismatch_count": 0,
            "discrepancies": {
                "missing_records": expected_records,
                "unexpected_records": [],
                "duplicate_records": [],
                "incorrect_values": [{"schema_error": e} for e in schema_errors],
            },
            "failure_categories": sorted(categories),
        }

    pk = spec["output_contract"]["primary_key"]
    area_tol = float(spec["tolerances"]["area_m2_abs"])

    unique_actual, duplicate_records = find_duplicates(candidate_records, pk)
    if duplicate_records:
        categories.add("DUPLICATE_RECORDS")

    expected_map = {str(r[pk]).strip(): r for r in expected_records}
    actual_map = {str(r[pk]).strip(): r for r in unique_actual}

    revit_by_num = {}
    if full_revit_state and "rooms" in full_revit_state:
        revit_by_num = {str(r["number"]).strip(): r for r in full_revit_state["rooms"]}

    missing_records = [
        expected_map[k] for k in sorted(expected_map.keys() - actual_map.keys())
    ]
    if missing_records:
        categories.add("MISSING_QUALIFYING_RECORDS")

    unexpected_records = []
    for k in sorted(actual_map.keys() - expected_map.keys()):
        rec = actual_map[k]
        reason, cats = classify_unexpected_record(rec, revit_by_num, spec)
        categories.update(cats)
        unexpected_records.append({**rec, "reason": reason})

    incorrect_values = []
    matched_count = 0
    for k in sorted(expected_map.keys() & actual_map.keys()):
        mismatches = compare_record_values(expected_map[k], actual_map[k], area_tol)
        if mismatches:
            incorrect_values.extend(mismatches)
            for m in mismatches:
                if m["field"] == "area_m2":
                    ratio = m["actual"] / m["expected"] if m["expected"] > 0 else 0
                    if 10.5 <= ratio <= 11.0:
                        categories.add("AREA_UNIT_OR_THRESHOLD_ERROR")
                    else:
                        categories.add("PARAMETER_VALUE_MISMATCH")
                else:
                    categories.add("PARAMETER_VALUE_MISMATCH")
        else:
            matched_count += 1

    semantic_passed = (
        len(missing_records) == 0
        and len(unexpected_records) == 0
        and len(duplicate_records) == 0
        and len(incorrect_values) == 0
    )

    if semantic_passed and not categories:
        categories.add("NONE")

    silent_failure = bool(exec_passed and not semantic_passed)

    return {
        "semantic_passed": semantic_passed,
        "silent_failure": silent_failure,
        "expected_count": len(expected_records),
        "actual_count": len(candidate_records),
        "matched_count": matched_count,
        "missing_count": len(missing_records),
        "unexpected_count": len(unexpected_records),
        "duplicate_count": len(duplicate_records),
        "value_mismatch_count": len(incorrect_values),
        "discrepancies": {
            "missing_records": missing_records,
            "unexpected_records": unexpected_records,
            "duplicate_records": duplicate_records,
            "incorrect_values": incorrect_values,
        },
        "failure_categories": sorted(categories),
    }
