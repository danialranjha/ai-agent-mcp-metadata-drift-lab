"""Prove critical tests detect two broken gates, without modifying source files."""
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

import gate

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "tests"))
from test_gate import GateTests


def remove_descriptions(value):
    if isinstance(value, dict):
        return {k: remove_descriptions(v) for k, v in value.items() if k != "description"}
    if isinstance(value, list):
        return [remove_descriptions(v) for v in value]
    return value


def ignore_descriptions(before, after):
    return gate.canonical(remove_descriptions(before)) == gate.canonical(remove_descriptions(after))


def main():
    checks = []
    for name, replacement in (("skip_definition_comparison", lambda a, b: True),
                              ("ignore_all_descriptions", ignore_descriptions)):
        suite = unittest.TestSuite(GateTests(test) for test in (
            "test_critical_description_ab", "test_benign_description_change_also_requires_review"))
        with patch.object(gate, "same_definitions", replacement):
            result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
        checks.append({"mutation": name, "tests_run": result.testsRun,
                       "failures": len(result.failures), "errors": len(result.errors),
                       "failed_tests": [test.id() for test, _ in result.failures],
                       "detected": len(result.failures) == 2 and not result.errors})
    report = {"all_detected": all(c["detected"] for c in checks), "checks": checks,
              "source_files_modified": False}
    (ROOT / "artifacts").mkdir(exist_ok=True)
    (ROOT / "artifacts/mutation-checks.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report))
    return 0 if report["all_detected"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
