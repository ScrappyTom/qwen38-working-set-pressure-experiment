"""Run the frozen execution engine with test-only replies; no runtime or network."""
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT / "tests"))
from test_compiler_execution import rehearse


if __name__ == "__main__":
    seal = rehearse(ROOT / "development/compiler_incident/execution-rehearsal-001")
    print({"actual_model_completion_requests":seal["actual_model_completion_requests"],
           "mocked_completion_responses":seal["mocked_completion_responses"],
           "record_count":seal["record_count"],"aggregate_sha256":seal["aggregate_sha256"]})
