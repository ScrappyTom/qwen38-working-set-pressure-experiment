from __future__ import annotations

import json
import subprocess
from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file, utc_now
from working_set_exp.observation_recurrence import FINAL_DEVELOPMENT_V2_OUTPUT_ROOT
from working_set_exp.reasoning_measured import seal_response_tree
from working_set_exp.recurrent_host_v2 import run_t25_final_operational
from working_set_exp.recurrent_pressure import (
    CandidateBoundProbeExecutor,
    MiddleOutcome,
    _capture_observation,
    load_recurrent_fixture,
    recurrent_binding,
    verify_bank,
    verify_closure,
)
from working_set_exp.runtime import LiveActor, OwnedServer, PORT, REASONING_BUDGET, load_runtime, port_free
from working_set_exp.tools import SessionState


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "009_recurrent_observation_validity"
DEVELOPMENT = EXPERIMENT / "final_path_rehearsal_v2"
OUTPUT = Path(FINAL_DEVELOPMENT_V2_OUTPUT_ROOT)


def _constructed_middle() -> tuple[object, MiddleOutcome]:
    fixture = load_recurrent_fixture(DEVELOPMENT / "bank", "E9-DEV-OBS-EPSILON")
    truth = load_json_strict((DEVELOPMENT / "bank" / "evaluator_only" / fixture.fixture_id / "TRUTH.json").read_bytes())
    after_a, _ = fixture.initial.patch(
        path=truth["phase_a_patch"]["path"],
        old=truth["phase_a_patch"]["old"],
        new=truth["phase_a_patch"]["new"],
        expected_candidate_id=fixture.initial.candidate_id,
        expected_file_sha256=fixture.initial.file_sha256(truth["phase_a_patch"]["path"]),
    )
    state = SessionState(after_a, stage="recurrent")
    observations: list[dict] = []
    reopenable: dict[str, bytes] = {}
    executor = CandidateBoundProbeExecutor(
        state,
        required_full_reads=(),
        prefork_checker=fixture.phase_a_checker,
        public_checker=fixture.phase_b_checker,
        final_target=fixture.phase_c_target,
        probe_id=fixture.probe_id,
        probe_body=fixture.probe_v1,
        reopenable=reopenable,
        baseline_candidate_id=after_a.candidate_id,
        probe_v1=fixture.probe_v1,
        probe_v2=fixture.probe_v2,
    )
    old_action = {"action": "probe", "probe_id": fixture.probe_id}
    old_result = executor.execute(old_action)
    _capture_observation(
        old_action, old_result, sequence=1, state=state, observations=observations, reopenable=reopenable
    )
    patch = truth["phase_b_patch"]
    patch_action = {
        "action": "patch",
        "path": patch["path"],
        "old": patch["old"],
        "new": patch["new"],
        "expected_candidate_id": state.candidate.candidate_id,
        "expected_file_sha256": state.candidate.file_sha256(patch["path"]),
    }
    patch_result = executor.execute(patch_action)
    if not patch_result.get("accepted"):
        raise AssertionError(patch_result)
    current_action = {"action": "probe", "probe_id": fixture.probe_id}
    current_result = executor.execute(current_action)
    _capture_observation(
        current_action,
        current_result,
        sequence=3,
        state=state,
        observations=observations,
        reopenable=reopenable,
    )
    state.public_check_passed = True
    state.fork_ready = True
    active_history = [
        {
            "response": {"action": "fork_ready", "expected_candidate_id": state.candidate.candidate_id},
            "result": {"accepted": True, "candidate_id": state.candidate.candidate_id, "boundary_ready": True},
        }
    ]
    prior = {"schema_version": "experiment-009-constructed-prior-binding-v1", "candidate_id": after_a.candidate_id}
    binding = recurrent_binding(
        fixture,
        seed=271828,
        condition="T25",
        candidate=state.candidate,
        active_history=active_history,
        observations=observations,
        prior_binding=prior,
        last_record_sha256=sha256_bytes(b"experiment-009-qualified-constructed-middle"),
    )
    middle = MiddleOutcome(
        state=state,
        active_history=active_history,
        observations=observations,
        reopenable=reopenable,
        binding=binding,
        calls=8,
        http_completion_calls=8,
        output_dir=DEVELOPMENT,
        disposition="second_boundary_eligible",
    )
    return fixture, middle


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    if subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, check=True, text=True
    ).stdout:
        raise RuntimeError("final-path rehearsal requires a clean checkout")
    bank = verify_bank(DEVELOPMENT / "bank")
    closure = verify_closure(ROOT, DEVELOPMENT / "EXECUTABLE_CLOSURE.json")
    authorization = load_json_strict((DEVELOPMENT / "AUTHORIZATION.json").read_bytes())
    if authorization["bank_manifest_sha256"] != sha256_file(DEVELOPMENT / "bank" / "BANK_MANIFEST.json"):
        raise ValueError("final-path bank authorization differs")
    if authorization["closure_manifest_sha256"] != sha256_file(DEVELOPMENT / "EXECUTABLE_CLOSURE.json"):
        raise ValueError("final-path closure authorization differs")
    if authorization["closure_aggregate_sha256"] != closure["aggregate_sha256"]:
        raise ValueError("final-path closure aggregate differs")
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    fixture, middle = _constructed_middle()
    if not port_free(PORT):
        raise RuntimeError("final-path development port is occupied")
    OUTPUT.mkdir(parents=True)
    receipt = {
        "schema_version": "experiment-009-final-path-development-receipt-v1",
        "started_at_utc": utc_now(),
        "status": "started",
        "bank": bank,
        "closure": closure,
        "authorization_sha256": sha256_file(DEVELOPMENT / "AUTHORIZATION.json"),
        "measured_bank_exposure": False,
        "attempts_per_call": 1,
        "retries": 0,
        "repairs": 0,
        "rescues": 0,
    }
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    try:
        verify_closure(ROOT, DEVELOPMENT / "EXECUTABLE_CLOSURE.json")
        with OwnedServer(profile, OUTPUT, port=PORT, reasoning_mode="auto", reasoning_budget=REASONING_BUDGET):
            summary = run_t25_final_operational(
                fixture,
                middle,
                seed=271828,
                actor=LiveActor(profile, seed=271828, reasoning_enabled=True),
                output_dir=OUTPUT / "phase-c",
            )
        seal = seal_response_tree(OUTPUT)
        receipt.update(
            {
                "status": "completed_and_response_sealed",
                "completed_at_utc": utc_now(),
                "summary": summary,
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
