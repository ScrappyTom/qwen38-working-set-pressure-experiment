from __future__ import annotations

import json
from pathlib import Path

from working_set_exp.bank import verify_bank
from working_set_exp.fixture import load_fixture
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, sha256_file, utc_now
from working_set_exp.runner import run_branch, run_prefix, verify_run
from working_set_exp.runtime import LiveActor, OwnedServer, PORT, load_runtime, port_free


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "002_single_boundary_reconstruction"
OUTPUT = EXPERIMENT / "development_live_rehearsal"


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError("development rehearsal is immutable and already exists")
    OUTPUT.mkdir(parents=True)
    bank = EXPERIMENT / "development_bank"
    bank_verification = verify_bank(bank)
    fixture = load_fixture(bank, "DEV-RECONSTRUCTION")
    longest_candidate_path = max(len(path) for path, _ in fixture.initial.files)
    prospective_path_chars = len(str(OUTPUT / "prefix" / "snap" / ("f" * 32))) + longest_candidate_path + 24
    if prospective_path_chars >= 248:
        raise RuntimeError("development custody path budget is unsafe before server launch")
    profile_path = EXPERIMENT / "RUNTIME_PROFILE.json"
    profile = load_runtime(profile_path)
    receipt: dict[str, object] = {
        "schema_version": "experiment-002-development-live-rehearsal-receipt-v1",
        "started_at_utc": utc_now(),
        "bank_verification": bank_verification,
        "runtime_profile_sha256": sha256_file(profile_path),
        "actor_sha256": profile.model_sha256,
        "port": PORT,
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
            prefix = run_prefix(
                fixture,
                seed=271828,
                actor=LiveActor(profile, seed=271828),
                output_dir=OUTPUT / "prefix",
                profile=profile,
            )
            branches: dict[str, object] = {}
            for condition in ("T25", "C50"):
                summary = run_branch(
                    fixture,
                    prefix,
                    condition=condition,
                    seed=271828,
                    actor=LiveActor(profile, seed=271828),
                    output_dir=OUTPUT / condition,
                )
                verify_run(OUTPUT / condition)
                branches[condition] = summary
            verify_run(OUTPUT / "prefix")
        receipt.update(
            {
                "status": "completed",
                "completed_at_utc": utc_now(),
                "prefix_summary": json.loads((OUTPUT / "prefix" / "SUMMARY.json").read_text(encoding="utf-8")),
                "branches": branches,
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
