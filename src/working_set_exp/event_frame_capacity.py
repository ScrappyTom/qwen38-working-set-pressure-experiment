from __future__ import annotations

import random
import string
from typing import Any

from .candidate import Candidate
from .event_frame import BODY_FIELDS, event_from_pair, resident_pair, verify_event_sequence
from .event_frame_placement import build_event_request
from .jsonutil import canonical_json_bytes, sha256_bytes
from .phase_receipts import PhaseSpec, ReceiptFixture
from .runtime import OUTPUT_TOKENS, RuntimeProfile, guard, tokenizer_count
from .tools import MAX_ACTION_BYTES, SessionState, ToolExecutor, strict_action


EXPERIMENT_ID = "016_event_frame_capacity_stress"
ACTIVE_PHASE_EVENT_LIMIT = 16
CONTROL_FRAGMENT_CHARACTERS = 170
ASCII_FRAGMENT_CHARACTERS = 512


def _ascii_fragments() -> list[tuple[str, str]]:
    rng = random.Random(160016)
    alphabet = string.ascii_letters + string.digits + "_-"
    rows = []
    for _ in range(ACTIVE_PHASE_EVENT_LIMIT):
        old = "".join(rng.choice(alphabet) for _ in range(ASCII_FRAGMENT_CHARACTERS))
        new = "".join(rng.choice(alphabet) for _ in range(ASCII_FRAGMENT_CHARACTERS))
        rows.append((old, new))
    return rows


def _fragments(kind: str) -> list[tuple[str, str]]:
    if kind == "reasoning_budget_compatible_control_escape_patch":
        return [
            ("\x00" * CONTROL_FRAGMENT_CHARACTERS, "\x01" * CONTROL_FRAGMENT_CHARACTERS)
            for _ in range(ACTIVE_PHASE_EVENT_LIMIT)
        ]
    if kind == "maximum_schema_ascii_patch":
        return _ascii_fragments()
    raise ValueError("unknown event-frame stress kind")


def stress_fixture(kind: str) -> ReceiptFixture:
    files = {
        f"stress/file_{index:02d}.dat": old.encode("utf-8")
        for index, (old, _) in enumerate(_fragments(kind), 1)
    }
    initial = Candidate.create(files)
    phase_a = PhaseSpec("A", "Phase A is mechanically complete.", (), "__none__", b"", None, None)
    phase_b = PhaseSpec(
        "B",
        "Phase B is an offline contract stress: retain the exact accepted action/effect order.",
        (),
        "__none__",
        b"",
        None,
        None,
    )
    return ReceiptFixture(
        f"E16-{kind.upper().replace('_', '-')}",
        "offline_event_frame_contract_stress",
        "Preserve the exact active-phase event order and current candidate binding.",
        initial,
        {"A": phase_a, "B": phase_b},
        b"",
    )


def accepted_patch_sequence(kind: str) -> tuple[ReceiptFixture, Candidate, list[dict[str, Any]]]:
    """Construct sixteen real, accepted, candidate-bound patch events."""
    fixture = stress_fixture(kind)
    state = SessionState(fixture.initial, stage="continuation")
    executor = ToolExecutor(
        state,
        required_full_reads=(),
        prefork_checker=b"",
        public_checker=b"",
        final_target="__none__",
        probe_id=None,
        probe_body=None,
        read_mode="maximal_bounded_page",
        hierarchical_p0=True,
    )
    pairs: list[dict[str, Any]] = []
    for index, (old, new) in enumerate(_fragments(kind), 1):
        path = f"stress/file_{index:02d}.dat"
        action = {
            "action": "patch",
            "path": path,
            "old": old,
            "new": new,
            "expected_candidate_id": state.candidate.candidate_id,
            "expected_file_sha256": state.candidate.file_sha256(path),
        }
        raw = canonical_json_bytes(action)
        if strict_action(raw) != action or len(raw) > MAX_ACTION_BYTES:
            raise RuntimeError("stress patch action is outside the accepted host contract")
        if len(old) > 512 or len(new) > 512:
            raise RuntimeError("stress patch action is outside the frozen response schema")
        result = executor.execute(action)
        if not result.get("accepted"):
            raise RuntimeError("stress patch action was not accepted")
        pairs.append({"response": action, "result": result})
    if len(pairs) != ACTIVE_PHASE_EVENT_LIMIT:
        raise RuntimeError("stress event count differs")
    if pairs[-1]["result"]["candidate_id"] != state.candidate.candidate_id:
        raise RuntimeError("stress candidate chain differs")
    return fixture, state.candidate, pairs


def boundary_binding(fixture: ReceiptFixture, candidate: Candidate, pairs: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "experiment-016-offline-boundary-v1",
        "fixture_id": fixture.fixture_id,
        "completed_phase_ids": ["A"],
        "pending_phase": "B",
        "candidate_id": candidate.candidate_id,
        "task_sha256": sha256_bytes(fixture.task.encode("utf-8")),
        "active_event_prefix_sha256": sha256_bytes(canonical_json_bytes(pairs)),
        "host_semantic_selection": False,
    }


def stress_request(
    kind: str,
    *,
    externalized_body_count: int,
) -> tuple[bytes, list[dict[str, Any]], Candidate]:
    fixture, candidate, pairs = accepted_patch_sequence(kind)
    request = build_event_request(
        fixture,
        candidate=candidate,
        observations=[],
        boundary_binding=boundary_binding(fixture, candidate, pairs),
        calls_used=ACTIVE_PHASE_EVENT_LIMIT,
        pairs=pairs,
        externalized_body_count=externalized_body_count,
    )
    return request, pairs, candidate


def _tokenized(profile: RuntimeProfile, value: Any) -> dict[str, int]:
    raw = canonical_json_bytes(value)
    return {"bytes": len(raw), "tokens": tokenizer_count(profile, raw)}


def component_costs(profile: RuntimeProfile, pairs: list[dict[str, Any]]) -> dict[str, Any]:
    actions = [pair["response"] for pair in pairs]
    structural_results = [
        {key: value for key, value in pair["result"].items() if key not in BODY_FIELDS}
        for pair in pairs
    ]
    result_body_fields = [
        {key: value for key, value in pair["result"].items() if key in BODY_FIELDS}
        for pair in pairs
    ]
    resident_events = [
        event_from_pair(
            pair["response"], pair["result"], sequence=index, handle=f"RES-{index:04d}",
            body_residency="resident",
        )
        for index, pair in enumerate(pairs, 1)
    ]
    external_events = [
        event_from_pair(
            pair["response"], pair["result"], sequence=index, handle=f"RES-{index:04d}",
            body_residency="external",
        )
        for index, pair in enumerate(pairs, 1)
    ]
    action_rows = [
        {
            "sequence": index,
            "bytes": len(canonical_json_bytes(action)),
            "tokens": tokenizer_count(profile, canonical_json_bytes(action)),
        }
        for index, action in enumerate(actions, 1)
    ]
    return {
        "actions": _tokenized(profile, actions),
        "structural_results": _tokenized(profile, structural_results),
        "result_body_fields": _tokenized(profile, result_body_fields),
        "resident_events": _tokenized(profile, resident_events),
        "externalized_result_events": _tokenized(profile, external_events),
        "single_action_max": max(action_rows, key=lambda row: (row["tokens"], row["bytes"])),
    }


def phase_transition_proof(pairs: list[dict[str, Any]]) -> dict[str, Any]:
    old_events = [
        event_from_pair(
            pair["response"], pair["result"], sequence=index, handle=f"RES-{index:04d}",
            body_residency="external",
        )
        for index, pair in enumerate(pairs, 1)
    ]
    old_verification = verify_event_sequence(old_events)
    current_candidate = pairs[-1]["result"]["candidate_id"]
    next_pair = {
        "response": {"action": "check", "check_id": "public", "expected_candidate_id": current_candidate},
        "result": {
            "accepted": True,
            "check_id": "public",
            "checked_candidate_id": current_candidate,
            "passed": True,
            "stdout": "public passed\n",
            "stderr": "",
        },
    }
    new_event = event_from_pair(
        next_pair["response"], next_pair["result"], sequence=1, handle="RES-0001", body_residency="resident"
    )
    if resident_pair(new_event) != next_pair:
        raise RuntimeError("new-phase resident event does not round-trip")
    new_verification = verify_event_sequence([new_event])
    old_custody = {
        f"phase-b/RES-{index:04d}": sha256_bytes(canonical_json_bytes(pair["result"]))
        for index, pair in enumerate(pairs, 1)
    }
    new_custody = {"phase-c/RES-0001": sha256_bytes(canonical_json_bytes(next_pair["result"]))}
    if set(old_custody) & set(new_custody):
        raise RuntimeError("phase-scoped event custody collided")
    return {
        "verified": True,
        "old_active_phase": "B",
        "old_event_sequence": old_verification,
        "new_active_phase": "C",
        "new_event_sequence": new_verification,
        "new_sequence_starts_at": 1,
        "phase_scoped_handles": True,
        "old_exact_result_custody": old_custody,
        "new_exact_result_custody": new_custody,
    }


def capacity_proof(profile: RuntimeProfile) -> tuple[dict[str, Any], dict[str, bytes]]:
    cases = []
    artifacts: dict[str, bytes] = {}
    for kind in ("maximum_schema_ascii_patch", "reasoning_budget_compatible_control_escape_patch"):
        resident, pairs, candidate = stress_request(kind, externalized_body_count=0)
        external, _, _ = stress_request(kind, externalized_body_count=ACTIVE_PHASE_EVENT_LIMIT)
        costs = component_costs(profile, pairs)
        if kind == "reasoning_budget_compatible_control_escape_patch" and (
            costs["single_action_max"]["tokens"] + 512 > OUTPUT_TOKENS
        ):
            raise RuntimeError("control-escape stress action plus reasoning exceeds the frozen output allowance")
        resident_t25 = guard(profile, resident, active_total_ceiling=25_000, reasoning_enabled=True)
        resident_r50 = guard(profile, resident, active_total_ceiling=50_176, reasoning_enabled=True)
        external_t25 = guard(profile, external, active_total_ceiling=25_000, reasoning_enabled=True)
        external_r50 = guard(profile, external, active_total_ceiling=50_176, reasoning_enabled=True)
        artifacts[f"requests/{kind}/resident.json"] = resident
        artifacts[f"requests/{kind}/externalized-results.json"] = external
        for index, pair in enumerate(pairs, 1):
            artifacts[f"custody/{kind}/phase-b/RES-{index:04d}.json"] = canonical_json_bytes(pair["result"])
            artifacts[f"custody/{kind}/phase-b/ACTION-{index:04d}.json"] = canonical_json_bytes(pair["response"])
        cases.append(
            {
                "kind": kind,
                "event_count": len(pairs),
                "current_candidate_id": candidate.candidate_id,
                "all_actions_host_accepted": True,
                "all_actions_within_frozen_patch_schema": True,
                "all_actions_within_raw_action_byte_cap": True,
                "components": costs,
                "resident": {"request_bytes": len(resident), "t25": resident_t25, "r50": resident_r50},
                "externalized_result_bodies": {
                    "request_bytes": len(external), "t25": external_t25, "r50": external_r50
                },
                "result_body_externalization_changes_action_bytes": False,
            }
        )
    control = next(row for row in cases if row["kind"] == "reasoning_budget_compatible_control_escape_patch")
    ascii_case = next(row for row in cases if row["kind"] == "maximum_schema_ascii_patch")
    proof = {
        "schema_version": "experiment-016-event-frame-capacity-proof-v1",
        "experiment_id": EXPERIMENT_ID,
        "offline_only": True,
        "active_phase_event_limit": ACTIVE_PHASE_EVENT_LIMIT,
        "runtime": {
            "model_alias": profile.model_alias,
            "model_sha256": profile.model_sha256,
            "tokenizer_sha256": profile.tokenizer_sha256,
            "server_sha256": profile.server_sha256,
        },
        "cases": cases,
        "phase_transition": phase_transition_proof(accepted_patch_sequence("maximum_schema_ascii_patch")[2]),
        "capacity_conclusion": {
            "current_v1_event_frame_r50_guard_fails_closed": True,
            "current_v1_event_frame_guarantees_sixteen_resident_r50_events": False,
            "current_v1_event_frame_qualified_for_x25_reconstruction": False,
            "reason": "legal accepted action payloads remain resident after result-body externalization",
            "ascii_externalized_x25_authorized": ascii_case["externalized_result_bodies"]["t25"]["authorized"],
            "ascii_externalized_x25_adjusted_margin_before_output": (
                25_000 - ascii_case["externalized_result_bodies"]["t25"]["adjusted_prompt_tokens"] - OUTPUT_TOKENS
            ),
            "control_externalized_x25_authorized": control["externalized_result_bodies"]["t25"]["authorized"],
            "control_externalized_r50_authorized": control["externalized_result_bodies"]["r50"]["authorized"],
            "large_world_fixture_construction_authorized": False,
            "representation_narrowing_earned": "externalize large historical action payload fields behind an exact event handle",
            "live_model_calls_authorized": False,
        },
    }
    return proof, artifacts
