from __future__ import annotations

from pathlib import Path

from working_set_exp.fixture import load_fixture
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict
from working_set_exp.runner import ScriptedActor, replay_prefix, run_branch, verify_run
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "002_single_boundary_reconstruction"
SOURCE = EXPERIMENT / "dev_a4_capacity"
OUTPUT = ROOT / "offline_capacity_stop_qualification"
FIXED_TIMESTAMP = "2000-01-01T00:00:00.000000+00:00"


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError("capacity-stop qualification evidence already exists")
    fixture = load_fixture(EXPERIMENT / "development_bank", "DEV-RECONSTRUCTION")
    prefix = replay_prefix(fixture, SOURCE / "prefix")
    actions = [
        load_json_strict((SOURCE / "T25" / "transcript" / f"{index:03d}-assistant-content.json").read_bytes())
        for index in range(1, 4)
    ]

    def policy(_: dict[str, object]) -> dict[str, object]:
        if not actions:
            raise AssertionError("capacity guard should stop before another actor response")
        return actions.pop(0)

    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    summary = run_branch(
        fixture,
        prefix,
        condition="T25",
        seed=271828,
        actor=ScriptedActor(profile, 271828, policy),
        output_dir=OUTPUT / "T25",
        fixed_record_timestamp=FIXED_TIMESTAMP,
    )
    if summary["disposition"] != "capacity_stopped_before_http" or actions:
        raise AssertionError("offline capacity-stop classification differs")
    replay = verify_run(OUTPUT / "T25")
    receipt = {
        "schema_version": "experiment-002-offline-capacity-stop-qualification-v1",
        "source_prefix_summary_sha256": prefix.binding["prefix_history_sha256"],
        "source_live_actions_replayed": 3,
        "prospective_denied_http_calls": 0,
        "summary": summary,
        "verification": replay,
        "model_or_endpoint_calls": 0,
    }
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    print(receipt)


if __name__ == "__main__":
    main()
