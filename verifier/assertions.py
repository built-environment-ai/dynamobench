import math
from typing import Any


def validate_record_schema(records: Any, spec: dict) -> list[str]:
    """Validate that candidate output is a list of dicts matching output_contract."""
    errors = []
    if not isinstance(records, list):
        return [f"Expected top-level list of records, got {type(records).__name__}."]

    contract = spec["output_contract"]
    required_fields = contract["required_fields"]
    field_types = contract["field_types"]

    type_map = {
        "string": (str,),
        "number": (int, float),
        "boolean": (bool,),
    }

    for idx, rec in enumerate(records):
        if not isinstance(rec, dict):
            errors.append(f"Record[{idx}] is {type(rec).__name__}, expected dict.")
            continue
        for field in required_fields:
            if field not in rec:
                errors.append(f"Record[{idx}] missing required field '{field}'.")
                continue
            val = rec[field]
            expected_type = field_types[field]
            if expected_type == "number" and isinstance(val, bool):
                errors.append(f"Record[{idx}].{field} is bool, expected number.")
            elif not isinstance(val, type_map[expected_type]):
                errors.append(
                    f"Record[{idx}].{field} has type {type(val).__name__}, expected {expected_type}."
                )
            elif expected_type == "number" and (math.isnan(val) or math.isinf(val)):
                errors.append(f"Record[{idx}].{field} is NaN or Inf.")
    return errors


def find_duplicates(records: list[dict], primary_key: str) -> tuple[list[dict], list[dict]]:
    """Return (deduplicated_records, duplicate_records) keyed by trimmed primary_key."""
    seen = set()
    unique = []
    duplicates = []
    for rec in records:
        key = str(rec[primary_key]).strip()
        if key in seen:
            duplicates.append(rec)
        else:
            seen.add(key)
            unique.append(rec)
    return unique, duplicates


def compare_record_values(expected: dict, actual: dict, area_tol: float) -> list[dict]:
    """Compare expected vs actual field values for a matched record across tasks."""
    mismatches = []
    for field, exp_val in expected.items():
        if field == "number":
            continue
        act_val = actual.get(field)
        if isinstance(exp_val, (int, float)) and not isinstance(exp_val, bool):
            exp_num = float(exp_val)
            act_num = float(act_val) if isinstance(act_val, (int, float)) and not isinstance(act_val, bool) else 0.0
            diff = abs(exp_num - act_num)
            if diff > area_tol:
                mismatches.append({
                    "field": field,
                    "expected": exp_num,
                    "actual": act_num,
                    "abs_diff": round(diff, 6),
                    "tolerance": area_tol,
                })
        else:
            exp_str = str(exp_val).strip() if exp_val is not None else ""
            act_str = str(act_val).strip() if act_val is not None else ""
            if exp_str != act_str:
                mismatches.append({
                    "field": field,
                    "expected": exp_str,
                    "actual": act_str,
                })
    return mismatches
