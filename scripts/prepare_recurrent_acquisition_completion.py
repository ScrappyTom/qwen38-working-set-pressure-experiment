from __future__ import annotations

import json
from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes
from working_set_exp.recurrent_acquisition_completion import verify_prior_partial
from working_set_exp.recurrent_pressure import build_closure, verify_closure


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "011_recurrent_acquisition_granularity"


def main() -> None:
    closure_path = EXPERIMENT / "EXECUTABLE_CLOSURE_COMPLETION.json"
    if closure_path.exists():
        raise FileExistsError(closure_path)
    closure = build_closure(ROOT, entrypoint="scripts/run_recurrent_acquisition_completion.py")
    atomic_write(closure_path, canonical_json_bytes(closure))
    result = {
        "schema_version": "experiment-011-completion-offline-preparation-v1",
        "prior_partial": verify_prior_partial(EXPERIMENT),
        "closure": verify_closure(ROOT, closure_path),
        "launcher_bound_separately_by_authorization": True,
        "model_calls": 0,
    }
    atomic_write(EXPERIMENT / "COMPLETION_OFFLINE_PREPARATION.json", canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
