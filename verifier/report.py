import argparse
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
import jsonschema
from verifier.comparison import evaluate_candidate


def sha256_of_file(path: Path) -> str:
    if not path.is_file():
        return "FILE_NOT_FOUND"
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def build_report(
    spec: dict,
    expected_records: list[dict],
    candidate_records: list[dict],
    execution_meta: dict,
    candidate_meta: dict,
    environment_meta: dict,
    full_revit_state: dict | None = None,
) -> dict:
    eval_result = evaluate_candidate(
        spec=spec,
        expected_records=expected_records,
        candidate_records=candidate_records,
        execution_meta=execution_meta,
        full_revit_state=full_revit_state,
    )

    return {
        "schema_version": "0.1.0",
        "run_id": f"{spec['task_id']}_{uuid.uuid4().hex[:8]}",
        "timestamp_utc": datetime.now(timezone.utc).isoformat(),
        "task_id": spec["task_id"],
        "candidate_workflow": {
            "filename": candidate_meta.get("filename", "unknown.dyn"),
            "sha256": candidate_meta.get("sha256", "UNKNOWN"),
            "label": candidate_meta.get("label", "unlabeled"),
            "generator": candidate_meta.get("generator", "unknown"),
        },
        "environment": {
            "revit_version": environment_meta.get("revit_version", "2027"),
            "dynamo_version": environment_meta.get("dynamo_version", "unknown"),
            "revit_locale": environment_meta.get("revit_locale", "unknown"),
            "dynamo_packages": environment_meta.get("dynamo_packages", []),
            "seed_model_filename": environment_meta.get(
                "seed_model_filename", spec["seed_model"]["filename"]
            ),
            "seed_model_sha256": environment_meta.get(
                "seed_model_sha256", spec["seed_model"]["sha256"]
            ),
        },
        "execution": {
            "execution_passed": bool(execution_meta.get("execution_passed", False)),
            "node_error_count": int(execution_meta.get("node_error_count", 0)),
            "node_warning_count": int(execution_meta.get("node_warning_count", 0)),
            "duration_ms": float(execution_meta.get("duration_ms", 0.0)),
            "warnings": execution_meta.get("warnings", []),
            "errors": execution_meta.get("errors", []),
        },
        "verification": {
            "semantic_passed": eval_result["semantic_passed"],
            "silent_failure": eval_result["silent_failure"],
            "expected_count": eval_result["expected_count"],
            "actual_count": eval_result["actual_count"],
            "matched_count": eval_result["matched_count"],
            "missing_count": eval_result["missing_count"],
            "unexpected_count": eval_result["unexpected_count"],
            "duplicate_count": eval_result["duplicate_count"],
            "value_mismatch_count": eval_result["value_mismatch_count"],
        },
        "discrepancies": eval_result["discrepancies"],
        "failure_categories": eval_result["failure_categories"],
    }


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate DynamoBench evaluation report.")
    parser.add_argument("--spec", required=True, type=Path)
    parser.add_argument("--expected", required=True, type=Path)
    parser.add_argument("--candidate", required=True, type=Path)
    parser.add_argument("--revit-state", required=False, type=Path)
    parser.add_argument("--schema", required=True, type=Path)
    parser.add_argument("--out", required=True, type=Path)
    parser.add_argument("--label", default="candidate_run")
    parser.add_argument("--generator", default="manual_or_llm")
    parser.add_argument("--dyn-file", required=False, type=Path)
    parser.add_argument("--revit-locale", default="French")
    parser.add_argument("--dynamo-version", default="3.x")
    args = parser.parse_args()

    spec = json.loads(args.spec.read_text(encoding="utf-8-sig"))
    expected_records = json.loads(args.expected.read_text(encoding="utf-8-sig"))
    candidate_payload = json.loads(args.candidate.read_text(encoding="utf-8-sig"))
    schema = json.loads(args.schema.read_text(encoding="utf-8-sig"))

    full_revit_state = None
    if args.revit_state and args.revit_state.is_file():
        full_revit_state = json.loads(args.revit_state.read_text(encoding="utf-8-sig"))

    if isinstance(candidate_payload, dict) and "records" in candidate_payload:
        candidate_records = candidate_payload["records"]
        execution_meta = candidate_payload.get("execution", {"execution_passed": True})
    else:
        candidate_records = candidate_payload
        execution_meta = {"execution_passed": True, "node_error_count": 0, "node_warning_count": 0, "duration_ms": 0.0}

    env_block = full_revit_state.get("environment", {}) if full_revit_state else {}
    environment_meta = {
        "revit_version": env_block.get("revit_version", "2027"),
        "dynamo_version": args.dynamo_version,
        "revit_locale": args.revit_locale,
        "dynamo_packages": [],
        "seed_model_filename": spec["seed_model"]["filename"],
        "seed_model_sha256": env_block.get("model_sha256", spec["seed_model"]["sha256"]),
    }

    candidate_meta = {
        "filename": args.dyn_file.name if args.dyn_file else args.candidate.name,
        "sha256": sha256_of_file(args.dyn_file) if args.dyn_file else sha256_of_file(args.candidate),
        "label": args.label,
        "generator": args.generator,
    }

    report = build_report(
        spec=spec,
        expected_records=expected_records,
        candidate_records=candidate_records,
        execution_meta=execution_meta,
        candidate_meta=candidate_meta,
        environment_meta=environment_meta,
        full_revit_state=full_revit_state,
    )

    jsonschema.Draft202012Validator(schema).validate(report)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")

    print(f"Report saved: {args.out}")
    print(f"  Execution Passed : {report['execution']['execution_passed']}")
    print(f"  Semantic Passed  : {report['verification']['semantic_passed']}")
    print(f"  Silent Failure   : {report['verification']['silent_failure']}")
    print(f"  Failure Categories: {report['failure_categories']}")


if __name__ == "__main__":
    main()
