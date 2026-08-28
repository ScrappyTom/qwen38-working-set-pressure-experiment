from __future__ import annotations

import json
import subprocess
from pathlib import Path
from typing import Any

from working_set_exp.fixture import load_fixture
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.progress import BRANCH_CALL_LIMIT, PREFIX_CALL_LIMIT, progress_pointer, verify_bank
from working_set_exp.reasoning_measured import seal_response_tree, verify_executable_closure
from working_set_exp.runner import ScriptedActor, run_branch, run_prefix, verify_run
from working_set_exp.runtime import LiveActor, OwnedServer, PORT, load_runtime, port_free


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "004_reasoning_transition_diagnostic"
DEVELOPMENT_BANK = ROOT / "experiments" / "003_progress_pointer_diagnostic" / "fresh_bank"
OUTPUT = Path(r"C:\e4r-dev")


def _clean_checkout() -> None:
    completed = subprocess.run(["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, check=True, text=True)
    if completed.stdout:
        raise RuntimeError("reasoning development uptake requires a clean checkout")


def _prefix_policy(fixture):
    required_index = 0
    readiness_read = False
    patched = False
    checked = False
    probed = False

    def policy(request: dict[str, Any]) -> dict[str, Any]:
        nonlocal required_index, readiness_read, patched, checked, probed
        if request["stage"] == "setup":
            return {"action": "begin"}
        candidate_id = request["candidate_id"]
        if not probed:
            probed = True
            return {"action": "probe", "probe_id": fixture.probe_id}
        if required_index < len(fixture.required_full_reads):
            path = fixture.required_full_reads[required_index]
            required_index += 1
            return {"action": "read", "path": path, "start_line": 1, "line_count": 500}
        if not readiness_read:
            readiness_read = True
            return {"action": "read", "path": "staging/readiness.py", "start_line": 1, "line_count": 100}
        if not patched:
            patched = True
            latest = request["history"][-1]["result"]
            return {
                "action": "patch", "path": "staging/readiness.py",
                "old": "    return 0", "new": "    return len(CERT_GROUPS)",
                "expected_candidate_id": candidate_id, "expected_file_sha256": latest["file_sha256"],
            }
        if not checked:
            checked = True
            return {"action": "check", "check_id": "prefork", "expected_candidate_id": candidate_id}
        return {"action": "fork_ready", "expected_candidate_id": candidate_id}

    return policy


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError("reasoning development output root already exists")
    _clean_checkout()
    authorization = load_json_strict((EXPERIMENT / "DEVELOPMENT_UPTAKE_AUTHORIZATION.json").read_bytes())
    if authorization != {
        "actor_sha256": "d416fa422c9035605c778f60d90a94b288c38b4f9ec2126b58ef938ce8d5f716",
        "attempts_per_call": 1, "authorized": True,
        "development_fixture_bank_id": "E3BANK-8ab108d7d784f5384881c00dcabc06dfa6689a2a85131c90520a0c2222fb2aee",
        "development_fixture_id": "E3-OBSERVATION", "fresh_experiment_004_bank_exposure": False,
        "maximum_completion_calls": 8, "owner_statement": "Great, proceed as you recommended",
        "reasoning_budget_tokens": 512, "repairs": 0, "rescues": 0, "retries": 0,
        "schema_version": "experiment-004-development-uptake-authorization-v1",
    }:
        raise RuntimeError("development reasoning authorization differs")
    closure = verify_executable_closure(ROOT, EXPERIMENT / "MEASURED_EXECUTABLE_CLOSURE.json")
    bank = verify_bank(DEVELOPMENT_BANK)
    if bank["bank_id"] != authorization["development_fixture_bank_id"]:
        raise RuntimeError("development bank differs")
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    if profile.model_sha256 != authorization["actor_sha256"] or not port_free(PORT):
        raise RuntimeError("development runtime preflight differs")
    OUTPUT.mkdir(parents=True)
    receipt: dict[str, Any] = {
        "schema_version": "experiment-004-development-uptake-receipt-v1",
        "started_at_utc": utc_now(), "status": "started", "authorization_sha256": sha256_file(EXPERIMENT / "DEVELOPMENT_UPTAKE_AUTHORIZATION.json"),
        "closure": closure, "bank": bank, "fixture_id": "E3-OBSERVATION",
        "fresh_experiment_004_bank_exposed": False, "model_calls": 0,
    }
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    fixture = load_fixture(DEVELOPMENT_BANK, "E3-OBSERVATION")
    scripted = ScriptedActor(profile, 424242, _prefix_policy(fixture))
    prefix = run_prefix(
        fixture, seed=424242, actor=scripted, output_dir=OUTPUT / "scripted_prefix",
        profile=profile, fixed_record_timestamp="2026-08-28T00:00:00Z",
        prefix_call_limit=PREFIX_CALL_LIMIT, continuation_call_limit=BRANCH_CALL_LIMIT,
        one_shot_probe=True,
    )
    verify_run(prefix.output_dir)
    try:
        with OwnedServer(profile, OUTPUT, port=PORT, reasoning_mode="auto"):
            summary = run_branch(
                fixture, prefix, condition="R1", seed=424242,
                actor=LiveActor(profile, seed=424242, reasoning_enabled=True),
                output_dir=OUTPUT / "R1",
                progress_pointer=progress_pointer(DEVELOPMENT_BANK, fixture.fixture_id),
                prefix_call_limit=PREFIX_CALL_LIMIT, branch_call_limit=BRANCH_CALL_LIMIT,
            )
            verify_run(OUTPUT / "R1")
        records = (OUTPUT / "R1" / "records.jsonl").read_text(encoding="utf-8").splitlines()
        action_records = [load_json_strict(line) for line in records if load_json_strict(line)["kind"] == "action_result"]
        reasoning_records = [row for row in action_records if row["payload"].get("reasoning_content_bytes", 0) > 0]
        actions = [row["payload"]["action"].get("action") for row in action_records]
        seal = seal_response_tree(OUTPUT)
        receipt.update(
            {
                "status": "completed_and_response_sealed", "completed_at_utc": utc_now(),
                "summary": summary, "model_calls": len(action_records), "actions": actions,
                "nonempty_reasoning_calls": len(reasoning_records),
                "reasoning_transport_qualified": len(reasoning_records) == len(action_records) and len(action_records) > 0,
                "patch_reached_executor": "patch" in actions,
                "response_seal_sha256": sha256_file(OUTPUT / "RESPONSE_SEAL.json"),
                "response_aggregate_sha256": seal["aggregate_sha256"],
                "server_shutdown_verified": port_free(PORT), "fresh_experiment_004_bank_exposed": False,
            }
        )
    except Exception as exc:
        receipt.update(
            {
                "status": "infrastructure_or_integrity_stopped", "completed_at_utc": utc_now(),
                "error_type": type(exc).__name__, "error": str(exc),
                "server_shutdown_verified": port_free(PORT),
            }
        )
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
        raise
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
