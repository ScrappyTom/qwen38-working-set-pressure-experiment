from __future__ import annotations

import json
import subprocess
from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.observation_recurrence import DEVELOPMENT_OUTPUT_ROOT
from working_set_exp.reasoning_measured import seal_response_tree
from working_set_exp.recurrent_host_v2 import run_t25_final_operational
from working_set_exp.recurrent_pressure import (
    MIDDLE_CALL_LIMIT,
    PREFIX_CALL_LIMIT,
    load_recurrent_fixture,
    run_final,
    run_middle,
    verify_bank,
    verify_closure,
)
from working_set_exp.runner import run_prefix, verify_run
from working_set_exp.runtime import LiveActor, OwnedServer, PORT, REASONING_BUDGET, load_runtime, port_free


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "009_recurrent_observation_validity"
DEVELOPMENT = EXPERIMENT / "development_rehearsal"
OUTPUT = Path(DEVELOPMENT_OUTPUT_ROOT)


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError("Experiment 009 development output already exists")
    if subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, check=True, text=True
    ).stdout:
        raise RuntimeError("development rehearsal requires a clean checkout")
    bank = verify_bank(DEVELOPMENT / "bank")
    closure = verify_closure(ROOT, DEVELOPMENT / "EXECUTABLE_CLOSURE.json")
    authorization = load_json_strict((DEVELOPMENT / "AUTHORIZATION.json").read_bytes())
    expected = {
        **authorization,
        "bank_manifest_sha256": sha256_file(DEVELOPMENT / "bank" / "BANK_MANIFEST.json"),
        "closure_manifest_sha256": sha256_file(DEVELOPMENT / "EXECUTABLE_CLOSURE.json"),
        "closure_aggregate_sha256": closure["aggregate_sha256"],
        "runtime_profile_sha256": sha256_file(EXPERIMENT / "RUNTIME_PROFILE.json"),
    }
    if canonical_json_bytes(expected) != canonical_json_bytes(authorization):
        raise ValueError("development authorization differs")
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    if not port_free(PORT):
        raise RuntimeError("development port is occupied")
    OUTPUT.mkdir(parents=True)
    receipt = {
        "schema_version": "experiment-009-development-rehearsal-receipt-v1",
        "started_at_utc": utc_now(),
        "status": "started",
        "bank": bank,
        "closure": closure,
        "authorization_sha256": sha256_file(DEVELOPMENT / "AUTHORIZATION.json"),
        "prepared_invocations": 0,
        "http_completion_calls": 0,
        "attempts_per_call": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
        "measured_bank_exposure": False,
        "branches": {},
    }
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    fixture = load_recurrent_fixture(DEVELOPMENT / "bank", "E9-DEV-OBS-GAMMA")
    try:
        verify_closure(ROOT, DEVELOPMENT / "EXECUTABLE_CLOSURE.json")
        with OwnedServer(profile, OUTPUT, port=PORT, reasoning_mode="auto", reasoning_budget=REASONING_BUDGET):
            try:
                prefix = run_prefix(
                    fixture.prefix_fixture(),
                    seed=314159,
                    actor=LiveActor(profile, seed=314159, reasoning_enabled=True),
                    output_dir=OUTPUT / "prefix",
                    profile=profile,
                    prefix_call_limit=PREFIX_CALL_LIMIT,
                    continuation_call_limit=MIDDLE_CALL_LIMIT,
                    one_shot_probe=True,
                    reasoning_enabled=True,
                )
            except RuntimeError:
                prefix = None
            verify_run(OUTPUT / "prefix")
            prefix_summary = load_json_strict((OUTPUT / "prefix" / "SUMMARY.json").read_bytes())
            receipt["prefix"] = prefix_summary
            receipt["prepared_invocations"] += prefix_summary["prepared_invocations"]
            receipt["http_completion_calls"] += prefix_summary["http_completion_calls"]
            for condition in authorization["branch_order"] if prefix is not None else []:
                middle = run_middle(
                    fixture,
                    prefix,
                    condition=condition,
                    seed=314159,
                    actor=LiveActor(profile, seed=314159, reasoning_enabled=True),
                    output_dir=OUTPUT / condition / "phase-b",
                )
                verify_run(OUTPUT / condition / "phase-b")
                middle_summary = load_json_strict((OUTPUT / condition / "phase-b" / "SUMMARY.json").read_bytes())
                branch = {"middle": middle_summary}
                receipt["branches"][condition] = branch
                receipt["prepared_invocations"] += middle_summary["prepared_invocations"]
                receipt["http_completion_calls"] += middle_summary["http_completion_calls"]
                final = None
                if condition == "T25" and middle.binding is not None and middle.disposition in {
                    "second_boundary_eligible",
                    "second_boundary_not_reached",
                }:
                    final = run_t25_final_operational(
                        fixture,
                        middle,
                        seed=314159,
                        actor=LiveActor(profile, seed=314159, reasoning_enabled=True),
                        output_dir=OUTPUT / condition / "phase-c",
                    )
                elif condition == "C50" and middle.disposition == "second_boundary_not_reached":
                    final = run_final(
                        fixture,
                        middle,
                        condition=condition,
                        seed=314159,
                        actor=LiveActor(profile, seed=314159, reasoning_enabled=True),
                        output_dir=OUTPUT / condition / "phase-c",
                    )
                if final is not None:
                    verify_run(OUTPUT / condition / "phase-c")
                    branch["final"] = final
                    receipt["prepared_invocations"] += final["prepared_invocations"]
                    receipt["http_completion_calls"] += final["http_completion_calls"]
                atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        seal = seal_response_tree(OUTPUT)
        receipt.update(
            {
                "status": "completed_and_response_sealed",
                "completed_at_utc": utc_now(),
                "response_seal_sha256": sha256_file(OUTPUT / "RESPONSE_SEAL.json"),
                "response_aggregate_sha256": seal["aggregate_sha256"],
                "server_shutdown_verified": port_free(PORT),
            }
        )
    except Exception as exc:
        receipt.update(
            {
                "status": "infrastructure_or_integrity_stopped",
                "completed_at_utc": utc_now(),
                "error_type": type(exc).__name__,
                "error": str(exc),
                "server_shutdown_verified": port_free(PORT),
            }
        )
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        raise
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
