from __future__ import annotations

from pathlib import Path

from working_set_exp.bank import verify_bank
from working_set_exp.fixture import load_fixture
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, sha256_file, utc_now
from working_set_exp.runner import replay_prefix, run_branch, verify_run
from working_set_exp.runtime import LiveActor, OwnedServer, PORT, load_runtime, port_free


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "002_single_boundary_reconstruction"
PREFIX = EXPERIMENT / "dev_a4_capacity" / "prefix"
OUTPUT = EXPERIMENT / "development_live_c50_followup"


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError("development C50 follow-up is immutable and already exists")
    bank = EXPERIMENT / "development_bank"
    bank_verification = verify_bank(bank)
    fixture = load_fixture(bank, "DEV-RECONSTRUCTION")
    prefix = replay_prefix(fixture, PREFIX)
    profile_path = EXPERIMENT / "RUNTIME_PROFILE.json"
    profile = load_runtime(profile_path)
    OUTPUT.mkdir(parents=True)
    receipt: dict[str, object] = {
        "schema_version": "experiment-002-development-c50-followup-receipt-v1",
        "started_at_utc": utc_now(),
        "source_prefix_summary_sha256": sha256_file(PREFIX / "SUMMARY.json"),
        "bank_verification": bank_verification,
        "actor_sha256": profile.model_sha256,
        "condition": "C50",
        "attempts_per_call": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "measured_fixture_exposure": False,
        "status": "started",
    }
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    try:
        with OwnedServer(profile, OUTPUT):
            summary = run_branch(
                fixture,
                prefix,
                condition="C50",
                seed=271828,
                actor=LiveActor(profile, seed=271828),
                output_dir=OUTPUT / "C50",
            )
            verify_run(OUTPUT / "C50")
        receipt.update(
            {
                "status": "completed",
                "completed_at_utc": utc_now(),
                "branch": summary,
                "server_shutdown_verified": port_free(PORT),
            }
        )
    except Exception as exc:
        receipt.update(
            {
                "status": "stopped",
                "completed_at_utc": utc_now(),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "server_shutdown_verified": port_free(PORT),
            }
        )
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        raise
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    print(receipt)


if __name__ == "__main__":
    main()
