from __future__ import annotations

import json
from pathlib import Path

import qualify_recurrent_pressure as recurrent_qualifier
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes
from working_set_exp.recurrent_acquisition import READ_MODES, verify_package
from working_set_exp.recurrent_acquisition_completion import FIXTURE_ID, OUTPUT_ROOT, SEED, verify_prior_partial
from working_set_exp.recurrent_pressure import verify_bank, verify_closure
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "011_recurrent_acquisition_granularity"


def main() -> None:
    if Path(OUTPUT_ROOT).exists():
        raise FileExistsError("completion output root already exists")
    recurrent_qualifier.EXPERIMENT = EXPERIMENT
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    paths = [
        recurrent_qualifier._run_case(
            FIXTURE_ID,
            SEED,
            read_mode=read_mode,
            acquisition_contract=True,
            observation_directory_version=2,
        )
        for read_mode in READ_MODES.values()
    ]
    result = {
        "schema_version": "experiment-011-completion-offline-qualification-v1",
        "prior_partial": verify_prior_partial(EXPERIMENT),
        "bank": verify_bank(EXPERIMENT / "fresh_bank"),
        "package": verify_package(EXPERIMENT / "execution_package", bank=EXPERIMENT / "fresh_bank", profile=profile),
        "closure": verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE_COMPLETION.json"),
        "paths": paths,
        "path_count": len(paths),
        "hidden_passes": sum(row["final_hidden_pass"] for row in paths),
        "output_root_absent": True,
        "model_calls": 0,
    }
    atomic_write(EXPERIMENT / "COMPLETION_OFFLINE_QUALIFICATION.json", canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
