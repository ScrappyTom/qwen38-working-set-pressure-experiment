from __future__ import annotations

import shutil
import sys
from pathlib import Path
from typing import Any

from working_set_exp.ecological_pilot_v2 import (
    CALL_LIMIT,
    CASE_IDS,
    _admit_externalization,
    _executor,
    _fork_binding,
    _record_pair,
    admitted_donor_candidate,
    build_request,
    closure,
    construct_package,
    hidden_grade,
    inspection_status,
    load_fixture,
    verify_bank,
    verify_package,
)
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, sha256_bytes, sha256_file, utc_now
from working_set_exp.recurrent_pressure import verify_closure
from working_set_exp.runtime import PHYSICAL_CONTEXT, T25_TOTAL_CEILING, guard, load_runtime
from working_set_exp.tools import SessionState


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "020_owner_controlled_ecological_pilot_v2"
BANK = EXPERIMENT / "fresh_bank"


FIXES: dict[str, tuple[tuple[str, str, str], ...]] = {
    CASE_IDS[0]: (
        (
            "src/addressable_information_layer/importers.py",
            "if path.stat().st_size >= max_file_bytes:",
            "if path.stat().st_size > max_file_bytes:",
        ),
        (
            "src/addressable_information_layer/importers.py",
            "if len(artifacts) > max_files:",
            "if len(artifacts) >= max_files:",
        ),
        (
            "src/addressable_information_layer/saved_runs.py",
            """        for idx, item in enumerate(_read_jsonl_lines(path), start=1):
            if idx >= MAX_JSONL_LINES:
                break
            event = _event_from_item(item, path, detected)""",
            """        for idx, item in enumerate(_read_jsonl_lines(path), start=1):
            if idx > MAX_JSONL_LINES:
                break
            event = _event_from_item(item, path, detected)""",
        ),
        (
            "src/addressable_information_layer/saved_runs.py",
            "if idx >= MAX_JSONL_LINES or len(artifacts) >= MAX_EMBEDDED_ARTIFACTS:",
            "if idx > MAX_JSONL_LINES or len(artifacts) >= MAX_EMBEDDED_ARTIFACTS:",
        ),
    ),
    CASE_IDS[1]: (
        (
            "src/addressable_information_layer/verifiers.py",
            'if path.is_absolute() and ".." in path.parts or not path.parts:',
            'if path.is_absolute() or ".." in path.parts or not path.parts:',
        ),
        (
            "src/addressable_information_layer/verifiers.py",
            "return max(1, max(timeout, MAX_COMMAND_TIMEOUT_SECONDS))",
            "return max(1, min(timeout, MAX_COMMAND_TIMEOUT_SECONDS))",
        ),
    ),
}


def _scripted_actions(fixture, state: SessionState, executor, pairs, events, results):
    if fixture.observations:
        action = {"action": "reopen_observation", "handle": "OBS-0002"}
        yield action
    for path in fixture.required_inspection_paths:
        start = 1
        while start is not None:
            action = {"action": "read", "path": path, "start_line": start}
            result = yield action
            start = result["next_start_line"]
    for path, old, new in FIXES[fixture.fixture_id]:
        yield {
            "action": "patch",
            "path": path,
            "old": old,
            "new": new,
            "expected_candidate_id": state.candidate.candidate_id,
            "expected_file_sha256": state.candidate.file_sha256(path),
        }
    yield {"action": "check", "check_id": "public", "expected_candidate_id": state.candidate.candidate_id}
    yield {"action": "submit", "expected_candidate_id": state.candidate.candidate_id}


def _simulate_ideal(fixture, profile, *, condition: str) -> dict[str, Any]:
    state = SessionState(fixture.initial, stage="continuation")
    pairs: list[dict[str, Any]] = []
    event_reopenable: dict[str, bytes] = {}
    result_reopenable: dict[str, bytes] = {}
    executor = _executor(
        fixture,
        state,
        result_reopenable=result_reopenable,
        event_reopenable=event_reopenable,
    )
    calls = 0
    boundary = None
    binding = None
    externalized = 0
    minimum_headroom = PHYSICAL_CONTEXT
    first_check_calls_remaining = None
    generator = _scripted_actions(fixture, state, executor, pairs, event_reopenable, result_reopenable)
    action = next(generator)
    while True:
        resident = build_request(
            fixture,
            candidate=state.candidate,
            pairs=pairs,
            externalized_payload_count=0,
            calls_used=calls,
            fork_binding=binding,
        )
        own = guard(profile, resident, active_total_ceiling=T25_TOTAL_CEILING, reasoning_enabled=True)
        physical = guard(profile, resident, active_total_ceiling=PHYSICAL_CONTEXT, reasoning_enabled=True)
        if boundary is None and not own["authorized"]:
            if not physical["authorized"]:
                raise RuntimeError("ideal path reached physical limit before authentic 25k boundary")
            before = inspection_status(pairs, fixture.required_inspection_paths)
            if before["first_mutation_sequence"] is not None:
                raise RuntimeError("ideal path mutated before authentic 25k boundary")
            binding = _fork_binding(fixture, seed=0, state=state, pairs=pairs, calls=calls)
            boundary = {
                "calls_completed": calls,
                "event_count": len(pairs),
                "candidate_id": state.candidate.candidate_id,
                "event_prefix_sha256": binding["event_prefix_sha256"],
                "request_sha256": sha256_bytes(resident),
                "t25": own,
                "r50": physical,
                "inspection_status": before,
            }
        if boundary is None:
            if not own["authorized"]:
                raise AssertionError("unreachable")
            request = resident
            admission = own
            ceiling = T25_TOTAL_CEILING
        elif condition == "X25":
            externalized, request, admission = _admit_externalization(
                profile,
                fixture,
                state=state,
                pairs=pairs,
                calls=calls,
                fork_binding=binding,
                starting_count=externalized,
            )
            ceiling = T25_TOTAL_CEILING
        else:
            if not physical["authorized"]:
                raise RuntimeError("R50 ideal path became physically inadmissible")
            request = resident
            admission = physical
            ceiling = PHYSICAL_CONTEXT
        adjusted = admission["adjusted_prompt_tokens"] + admission["output_allowance_tokens"]
        minimum_headroom = min(minimum_headroom, ceiling - adjusted)
        if action["action"] == "check" and first_check_calls_remaining is None:
            first_check_calls_remaining = CALL_LIMIT - calls
        result = executor.execute(action)
        if not result.get("accepted"):
            raise RuntimeError(f"ideal action rejected: {action} -> {result}")
        calls += 1
        _record_pair(pairs, action, result, event_reopenable, result_reopenable)
        try:
            action = generator.send(result)
        except StopIteration:
            break
    inspections = inspection_status(pairs, fixture.required_inspection_paths)
    known_good = admitted_donor_candidate(BANK)
    if boundary is None:
        raise RuntimeError("ideal path did not reach an authentic 25k boundary")
    if not inspections["all_completed_before_first_mutation"]:
        raise RuntimeError("ideal path did not complete exact inspection before mutation")
    if state.candidate.candidate_id != known_good.candidate_id:
        raise RuntimeError("ideal path did not reach the exact known-good candidate")
    if not state.public_check_passed or not state.submitted:
        raise RuntimeError("ideal path did not check and submit")
    if first_check_calls_remaining is None or first_check_calls_remaining < 4:
        raise RuntimeError("ideal path lacks a full correction-cycle action reserve")
    if minimum_headroom < 1_000:
        raise RuntimeError("ideal path lacks the frozen minimum total-token headroom")
    return {
        "fixture_id": fixture.fixture_id,
        "condition": condition,
        "calls": calls,
        "calls_remaining": CALL_LIMIT - calls,
        "first_check_calls_remaining": first_check_calls_remaining,
        "boundary": boundary,
        "inspection_status": inspections,
        "externalized_payload_count": externalized,
        "minimum_total_headroom_tokens": minimum_headroom,
        "known_good_candidate_id": known_good.candidate_id,
        "public_check_passed": True,
        "submitted": True,
        "request_bytes_last_admitted": len(request),
    }


def main() -> None:
    if sys.argv[1:] == ["--reset-preseal-generated"]:
        if (EXPERIMENT / "MEASURED_AUTHORIZATION.json").exists() or (EXPERIMENT / "measured_run").exists():
            raise RuntimeError("Experiment 020 generated evidence is no longer preseal")
        for path in (
            EXPERIMENT / "execution_package",
            EXPERIMENT / "EXECUTABLE_CLOSURE.json",
            EXPERIMENT / "IDEAL_PATH_QUALIFICATION.json",
            EXPERIMENT / "OFFLINE_QUALIFICATION_RECEIPT.json",
        ):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        print("Experiment 020 preseal generated evidence reset")
        return
    bank = verify_bank(BANK)
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    fixture_checks = []
    ideal_paths = []
    donor = admitted_donor_candidate(BANK)
    for fixture_id in CASE_IDS:
        fixture = load_fixture(BANK, fixture_id, include_evaluator=True)
        initial_public = run_checker(fixture.initial, fixture.public_checker)
        initial_hidden = hidden_grade(fixture, fixture.initial)
        good_public = run_checker(donor, fixture.public_checker)
        good_hidden = hidden_grade(fixture, donor)
        if initial_public["passed"] or initial_hidden["passed"] or not good_public["passed"] or not good_hidden["passed"]:
            raise RuntimeError("Experiment 020 fixture qualification differs")
        fixture_checks.append(
            {
                "fixture_id": fixture_id,
                "initial_public_passed": False,
                "initial_hidden_passed": False,
                "known_good_public_passed": True,
                "known_good_hidden_passed": True,
                "required_inspection_paths": list(fixture.required_inspection_paths),
            }
        )
        rows = [_simulate_ideal(fixture, profile, condition=condition) for condition in ("R50", "X25")]
        if rows[0]["boundary"]["event_prefix_sha256"] != rows[1]["boundary"]["event_prefix_sha256"]:
            raise RuntimeError("paired ideal path boundary ancestry differs")
        ideal_paths.extend(rows)
    atomic_write(
        EXPERIMENT / "IDEAL_PATH_QUALIFICATION.json",
        canonical_json_bytes(
            {
                "schema_version": "experiment-020-ideal-path-qualification-v1",
                "status": "qualified_model_free",
                "no_padding_or_duplicated_filler": True,
                "authentic_25k_boundary_before_first_mutation": True,
                "full_correction_cycle_reserved": True,
                "rows": ideal_paths,
            }
        ),
    )
    package_dir = EXPERIMENT / "execution_package"
    if not package_dir.exists():
        construct_package(package_dir, bank=BANK, profile=profile)
    package = verify_package(package_dir, bank=BANK, profile=profile)
    closure_path = EXPERIMENT / "EXECUTABLE_CLOSURE.json"
    observed_closure = closure(ROOT)
    atomic_write(closure_path, canonical_json_bytes(observed_closure))
    verified_closure = verify_closure(ROOT, closure_path)
    receipt = {
        "schema_version": "experiment-020-offline-qualification-v1",
        "status": "offline_qualified_awaiting_separate_owner_live_authorization",
        "qualified_at_utc": utc_now(),
        "bank": bank,
        "package": package,
        "closure": verified_closure,
        "fixture_checks": fixture_checks,
        "ideal_path_qualification_sha256": sha256_file(EXPERIMENT / "IDEAL_PATH_QUALIFICATION.json"),
        "runtime_profile_sha256": sha256_file(EXPERIMENT / "RUNTIME_PROFILE.json"),
        "controller_semantic_changes_from_experiment_019": [],
        "capacity_hygiene_changes_from_experiment_019": [
            "X25 externalizes additional oldest exact payloads until at least 1000 total tokens of headroom remain"
        ],
        "canonical_payload_identity": {
            "reopen_is_access_not_new_payload": True,
            "model_request_required_for_every_reopen": True,
            "automatic_reuse": False,
        },
        "model_calls": 0,
        "endpoint_requests": 0,
        "gpu_launches": 0,
    }
    atomic_write(EXPERIMENT / "OFFLINE_QUALIFICATION_RECEIPT.json", canonical_json_bytes(receipt))
    print(canonical_json_bytes(receipt).decode())


if __name__ == "__main__":
    main()
