"""Aggregate DynamoBench evaluation reports into a multi-task benchmark summary."""
import argparse
import json
import pathlib
from collections import Counter
from datetime import datetime, timezone


def _find_key(obj, key, default=None):
    if isinstance(obj, dict):
        if key in obj:
            return obj[key]
        for v in obj.values():
            found = _find_key(v, key, None)
            if found is not None:
                return found
    return default


def aggregate_reports(reports_dir: pathlib.Path, out_json: pathlib.Path, out_md: pathlib.Path) -> dict:
    eval_files = sorted(reports_dir.glob("eval_*.json"))
    rows = []
    cat_counts = Counter()

    for path in eval_files:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
        task_id = _find_key(data, "task_id", "unknown_task")
        label = _find_key(data, "label", path.stem)
        generator = _find_key(data, "generator", "unknown")
        exec_ok = bool(_find_key(data, "execution_passed", False))
        sem_ok = bool(_find_key(data, "semantic_passed", False))
        silent_fail = bool(_find_key(data, "silent_failure", False))
        duration_ms = float(_find_key(data, "duration_ms", 0.0) or 0.0)
        cats = _find_key(data, "failure_categories", ["UNKNOWN"])

        for c in cats:
            if c != "NONE":
                cat_counts[c] += 1

        rows.append({
            "report_file": path.name,
            "task_id": task_id,
            "label": label,
            "generator": generator,
            "execution_passed": exec_ok,
            "semantic_passed": sem_ok,
            "silent_failure": silent_fail,
            "duration_ms": round(duration_ms, 2),
            "failure_categories": cats,
        })

    from operator import itemgetter
    rows.sort(key=itemgetter('task_id', 'label'))
    total = len(rows)
    exec_pass_n = sum(1 for r in rows if r["execution_passed"])
    sem_pass_n = sum(1 for r in rows if r["semantic_passed"])
    silent_n = sum(1 for r in rows if r["silent_failure"])

    summary = {
        "schema_version": "0.1.0",
        "generated_at_utc": datetime.now(timezone.utc).isoformat(),
        "total_runs": total,
        "metrics": {
            "execution_pass_rate": round(exec_pass_n / total, 4) if total else 0.0,
            "semantic_pass_rate": round(sem_pass_n / total, 4) if total else 0.0,
            "silent_failure_rate": round(silent_n / total, 4) if total else 0.0,
        },
        "failure_category_counts": dict(cat_counts),
        "runs": rows,
    }

    out_json.parent.mkdir(parents=True, exist_ok=True)
    out_json.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")

    md_lines = [
        "# DynamoBench Evaluation Summary",
        "",
        f"- **Total Runs:** {total}",
        f"- **Execution Pass Rate:** {summary['metrics']['execution_pass_rate']*100:.1f}% ({exec_pass_n}/{total})",
        f"- **Semantic Pass Rate:** {summary['metrics']['semantic_pass_rate']*100:.1f}% ({sem_pass_n}/{total})",
        f"- **Silent Failure Rate:** {summary['metrics']['silent_failure_rate']*100:.1f}% ({silent_n}/{total})",
        "",
        "| Task ID | Candidate Label | Generator | Exec | Semantic | Silent Fail | Duration (ms) | Failure Categories |",
        "| :--- | :--- | :--- | :---: | :---: | :---: | ---: | :--- |",
    ]
    for r in rows:
        md_lines.append(
            f"| `{r['task_id']}` | `{r['label']}` | `{r['generator']}` | "
            f"{'PASS' if r['execution_passed'] else 'FAIL'} | "
            f"{'PASS' if r['semantic_passed'] else 'FAIL'} | "
            f"{'YES' if r['silent_failure'] else 'NO'} | "
            f"{r['duration_ms']:.2f} | {', '.join(r['failure_categories'])} |"
        )
    out_md.write_text("\n".join(md_lines) + "\n", encoding="utf-8")
    return summary


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--reports-dir", default="reports")
    parser.add_argument("--out-json", default="reports/benchmark_summary.json")
    parser.add_argument("--out-md", default="reports/BENCHMARK_LEADERBOARD.md")
    args = parser.parse_args()
    s = aggregate_reports(pathlib.Path(args.reports_dir), pathlib.Path(args.out_json), pathlib.Path(args.out_md))
    print(f"Runs: {s['total_runs']} | Exec: {s['metrics']['execution_pass_rate']*100:.0f}% | Semantic: {s['metrics']['semantic_pass_rate']*100:.0f}% | SilentFail: {s['metrics']['silent_failure_rate']*100:.0f}%")
    print("Failure breakdown:", s["failure_category_counts"])
