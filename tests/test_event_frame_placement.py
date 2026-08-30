from pathlib import Path

import pytest

from working_set_exp.event_frame import event_from_pair, resident_pair, verify_event_sequence
from working_set_exp.event_frame_placement import (
    CASE_IDS,
    CONDITIONS,
    branch_inputs,
    build_event_request,
    build_legacy_request,
    initial_request,
)
from working_set_exp.jsonutil import load_json_strict


ROOT = Path(__file__).resolve().parents[1]
BANK = ROOT / "experiments" / "014_unified_active_phase_receipts" / "fresh_bank"


def test_resident_event_roundtrips_exact_pair() -> None:
    action = {"action": "read", "path": "src/a.py", "start_line": 1}
    result = {"accepted": True, "path": "src/a.py", "content": "x = 1\n", "complete": True}
    event = event_from_pair(action, result, sequence=1, handle="RES-0001", body_residency="resident")
    assert resident_pair(event) == {"response": action, "result": result}
    assert verify_event_sequence([event])["resident_body_count"] == 1


def test_external_event_has_identity_without_body_fields() -> None:
    event = event_from_pair(
        {"action": "read", "path": "src/a.py", "start_line": 1},
        {"accepted": True, "content": "secret exact body\n", "complete": True},
        sequence=1,
        handle="RES-0001",
        body_residency="external",
    )
    assert event["result_body"]["fields"] is None
    assert "content" not in event["result"]
    assert verify_event_sequence([event])["external_body_count"] == 1
    with pytest.raises(ValueError):
        resident_pair(event)


def test_sequence_and_handle_are_monotonic() -> None:
    event = event_from_pair(
        {"action": "check", "check_id": "public"},
        {"accepted": True, "passed": True},
        sequence=1,
        handle="RES-0001",
        body_residency="resident",
    )
    event["sequence"] = 2
    with pytest.raises(ValueError):
        verify_event_sequence([event])


@pytest.mark.parametrize("fixture_id", CASE_IDS)
def test_constructed_world_is_exact_and_hidden_correct(fixture_id: str) -> None:
    values = branch_inputs(BANK, fixture_id)
    assert len(values["pairs"]) == 5
    assert len(values["receipts"]) == 5
    assert values["fixture"].phases["B"].checker
    assert all(pair["result"]["accepted"] for pair in values["pairs"])


@pytest.mark.parametrize("fixture_id", CASE_IDS)
def test_event_frame_removes_dual_history_and_receipt_surfaces(fixture_id: str) -> None:
    request = load_json_strict(initial_request(BANK, fixture_id, CONDITIONS[1]))
    assert "history" not in request
    assert "history_contract" not in request
    assert "active_phase_receipt_ledger" not in request
    assert request["active_phase_event_frame"]["complete_through_sequence"] == 5
    assert request["event_frame_verification"] == {
        "verified": True,
        "event_count": 5,
        "resident_body_count": 0,
        "external_body_count": 5,
    }


def test_event_frame_adds_live_result_once() -> None:
    values = branch_inputs(BANK, CASE_IDS[0])
    action = {
        "action": "check",
        "check_id": "public",
        "expected_candidate_id": values["state"].candidate.candidate_id,
    }
    result = {
        "accepted": True,
        "check_id": "public",
        "checked_candidate_id": values["state"].candidate.candidate_id,
        "passed": True,
    }
    request = load_json_strict(
        build_event_request(
            values["fixture"],
            candidate=values["state"].candidate,
            observations=values["observations"],
            boundary_binding=values["binding"],
            calls_used=1,
            pairs=[*values["pairs"], {"response": action, "result": result}],
            externalized_body_count=5,
        )
    )
    event = request["active_phase_event_frame"]["events"][-1]
    assert event["action"] == action
    assert event["result"]["passed"] is True
    assert event["result_body"]["residency"] == "resident"
    serialized = str(request)
    assert "active_phase_receipt_ledger" not in serialized
    assert "history_contract" not in serialized


def test_future_resident_and_externalized_conditions_share_prepressure_bytes() -> None:
    values = branch_inputs(BANK, CASE_IDS[0])
    kwargs = dict(
        fixture=values["fixture"],
        candidate=values["state"].candidate,
        observations=values["observations"],
        boundary_binding=values["binding"],
        calls_used=0,
        pairs=values["pairs"],
        externalized_body_count=0,
    )
    resident_control = build_event_request(**kwargs)
    future_externalization_treatment_before_pressure = build_event_request(**kwargs)
    assert resident_control == future_externalization_treatment_before_pressure


def test_legacy_surface_retains_the_qualified_dual_contract() -> None:
    values = branch_inputs(BANK, CASE_IDS[0])
    request = load_json_strict(
        build_legacy_request(
            values["fixture"],
            candidate=values["state"].candidate,
            observations=values["observations"],
            boundary_binding=values["binding"],
            calls_used=0,
            recent_history=[],
            receipts=values["receipts"],
            externalized_body_count=5,
        )
    )
    assert "history" in request
    assert "active_phase_receipt_ledger" in request
