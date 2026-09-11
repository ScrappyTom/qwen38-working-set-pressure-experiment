"""Selected offline regressions and historical artifact compatibility; no model calls."""
import argparse
import importlib
import inspect
import io
from pathlib import Path
import subprocess
import sys
import unittest

from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file

ROOT = Path(__file__).resolve().parents[2]
PIN = "3faf24e9e4a525bff00ca00ac32549ca662735bf"
MODULES = ["test_result_return_boundaries", "test_navigation_return_boundary", "test_core",
           "test_measurement_repairs", "test_event_frame_v3", "test_ecological_pilot_v2", "test_interface_consultation"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    sys.path[:0] = [str(ROOT / "tests"), str(ROOT / "scripts")]
    suite = unittest.TestSuite()
    for name in MODULES:
        module = importlib.import_module(name)
        suite.addTests(unittest.defaultTestLoader.loadTestsFromModule(module))
        for label, function in inspect.getmembers(module, inspect.isfunction):
            if label.startswith("test_") and function.__module__ == name and not inspect.signature(function).parameters:
                suite.addTest(unittest.FunctionTestCase(function))
    stream = io.StringIO()
    result = unittest.TextTestRunner(stream=stream, verbosity=2).run(suite)
    report = {"scope":"selected tests plus sealed historical artifact and patched-host replay checks; not a full suite or new model evidence",
              "model_completions":0, "modules":MODULES, "tests_run":result.testsRun,
              "failures":len(result.failures), "errors":len(result.errors), "skips":len(result.skipped),
              "successful":result.wasSuccessful(), "test_output":stream.getvalue(),
              "source_sha256":{p.relative_to(ROOT).as_posix():sha256_file(p) for p in sorted((ROOT/"src").rglob("*.py"))},
              "test_sha256":{name:sha256_file(ROOT/"tests"/(name+".py")) for name in MODULES},
              "script_sha256":sha256_file(Path(__file__))}
    if result.wasSuccessful():
        # Read-only compatibility, deliberately not run.load_manifest(): that
        # correctly requires the old execution source rather than this repair.
        import run_interface_wording as run
        seal = load_json_strict((run.RUN/"RESPONSE_SEAL.json").read_bytes())
        assert sha256_file(run.RUN/"RESPONSE_SEAL.json") == "cabbc0b0eb92cc11d0a0f1ede059e11edabdd1ceb2914bb0effd864efa452718"
        for row in seal["files"]:
            raw = (run.RUN/row["path"]).read_bytes()
            assert len(raw) == row["size_bytes"] and sha256_bytes(raw) == row["sha256"]
        records = verify_records(run.RUN/"records.jsonl", run.RUN)
        plan = load_json_strict(run.MANIFEST.read_bytes())
        changed = []
        for path, expected in plan["execution_source_sha256"].items():
            pinned = subprocess.run(["git", "show", PIN+":"+path], cwd=ROOT, capture_output=True, check=True).stdout
            assert sha256_bytes(pinned) == expected, path
            if sha256_file(ROOT/path) != expected:
                changed.append(path)
        replays = []
        for row in plan["rows"]:
            value, raw = run.fresh_state(row)
            saved = lambda suffix: (run.RUN/"calls"/(row["id"]+"-"+suffix)).read_bytes()
            assert raw == saved("endpoint-request.json")
            assert run.prep.reference.candidate_bytes(value.state.candidate) == saved("candidate-before.json")
            assert run.prep.reference.session_bytes(value.state) == saved("state-before.json")
            action = load_json_strict(saved("action.json"))
            actual = value.execute(action)
            assert actual == load_json_strict(saved("host-result.json"))["result"]
            assert run.prep.reference.candidate_bytes(value.state.candidate) == saved("candidate-after.json")
            assert run.prep.reference.session_bytes(value.state) == saved("state-after.json")
            replays.append(row["id"])
        report["historical_compatibility"] = {"source_pin":PIN,"pinned_source_identities":len(plan["execution_source_sha256"]),
            "current_source_differences":changed,"public_files_verified":len(seal["files"]),"chained_records":len(records),
            "patched_host_exact_replays":replays,"private_runtime_reverified":False,"tokenizer_rerun":False,
            "historical_closures_rewritten":False}
    args.output.write_bytes(canonical_json_bytes(report))
    print({key:report[key] for key in ("tests_run","failures","errors","successful")})
    if "historical_compatibility" in report:
        print(report["historical_compatibility"])
    if not result.wasSuccessful():
        print(stream.getvalue())
        raise SystemExit(1)


if __name__ == "__main__":
    main()
