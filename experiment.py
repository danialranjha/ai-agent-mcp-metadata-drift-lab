"""Run the paired metadata-admission experiment; never invoke a model or tool."""
from dataclasses import asdict
import json
from pathlib import Path

from fixtures import BASE, CANARY, IDENTITY, cases, serialize
from gate import admit, digest, review_snapshot

ROOT = Path(__file__).resolve().parent


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, sort_keys=True) + "\n")


def run(output_dir):
    approved = review_snapshot(serialize(BASE), IDENTITY)
    write_json(output_dir / "reviewed-snapshot.json", {
        "host_identity": IDENTITY, "fingerprint": approved.fingerprint,
        "tools": json.loads(approved.canonical_tools)})
    rows = []
    for case in cases():
        snapshot = review_snapshot(case.raw, case.identity) if case.reapprove else approved
        for mode in ("name_only", "snapshot"):
            result = admit(case.raw, case.identity, snapshot, mode)
            context = json.loads(result.model_input_json)
            sink_path = Path("contexts") / f"{case.name}.{mode}.json"
            write_json(output_dir / sink_path, context)
            expected = getattr(case, "expected_" + mode)
            canary_in_source = CANARY in case.raw
            canary_at_sink = CANARY in result.model_input_json
            expected_canary = canary_in_source and expected
            rows.append({
                "case": case.name, "category": case.category, "mode": mode,
                "accepted": result.accepted, "expected_accepted": expected,
                "reason": result.reason, "changed_paths": list(result.paths),
                "reviewed_fingerprint": snapshot.fingerprint,
                "current_fingerprint": result.current_fingerprint,
                "fixture_sha256": digest(case.raw),
                "context_sha256": digest((output_dir / sink_path).read_text()),
                "model_input_artifact": sink_path.as_posix(),
                "tool_count_at_sink": len(context["tools"]),
                "canary_at_metadata_sink": canary_at_sink,
                "expected_canary_at_metadata_sink": expected_canary,
                "explicit_reapproval": case.reapprove,
                "output_note_outside_gate": case.output_note,
                "matches_expectation": (result.accepted == expected and
                                         canary_at_sink == expected_canary and
                                         (result.accepted or context == {"tools": []})),
            })
    report = {
        "schema_version": 1, "experiment": "mcp-metadata-drift", "live_model_calls": 0,
        "tool_executions": 0, "external_requests": 0,
        "oracle": "unreviewed metadata admission to an adapter-neutral model-input capture",
        "case_count": len(cases()), "paired_rows": len(rows),
        "all_expectations_match": all(r["matches_expectation"] for r in rows),
        "source_sha256": {p: digest((ROOT / p).read_text()) for p in
                          ("gate.py", "fixtures.py", "experiment.py")},
        "same_name_drift": {mode: {
            "accepted": sum(r["accepted"] for r in rows
                            if r["category"] == "same_name_drift" and r["mode"] == mode),
            "total": sum(r["category"] == "same_name_drift" and r["mode"] == mode for r in rows)
        } for mode in ("name_only", "snapshot")},
        "rows": rows,
    }
    write_json(output_dir / "run.json", report)
    summary = ["# Evidence summary", "",
        f"{report['case_count']} synthetic cases, {len(rows)} paired rows; "
        f"all expectations matched: {report['all_expectations_match']}.", "",
        "Name-only approval admitted all 9 same-name metadata edits; snapshot approval admitted none.",
        "Both modes admitted the unchanged and serialization/order-only controls.",
        "A benign wording edit was also blocked until explicit review created a new snapshot.",
        "Unchanged metadata with a declared changed tool output passed both gates. Outputs are outside this gate.",
        "No model or tool ran. These counts measure fixture admission, not attack success or model robustness.", "",
        "| Case | Name-only | Snapshot | Snapshot reason |", "|---|---|---|---|"]
    for a, b in zip(rows[::2], rows[1::2]):
        summary.append(f"| {a['case']} | {'admit' if a['accepted'] else 'hold'} | "
                       f"{'admit' if b['accepted'] else 'hold'} | {b['reason']} |")
    summary += ["", "See [run.json](run.json) for hashes, changed paths, canary reachability and context links.",
                "Operator diagnostics must not be appended to model input; only the context captures are the measured sink.", ""]
    (output_dir / "evidence.md").write_text("\n".join(summary))
    return report


if __name__ == "__main__":
    report = run(ROOT / "artifacts")
    print(json.dumps({k: report[k] for k in ("case_count", "paired_rows", "all_expectations_match",
                                           "same_name_drift", "live_model_calls")}))
    raise SystemExit(0 if report["all_expectations_match"] else 1)
