from pathlib import Path

import pytest

from working_set_exp.event_frame_v2 import (
    action_payload_bytes,
    event_from_pair_v2,
    resident_pair_v2,
    verify_event_sequence_v2,
    verify_reopened_action_payload,
)
from working_set_exp.event_frame_v2_qualification import (
    DONOR_CASES,
    SIGNAL_CASE,
    branch_inputs,
    initial_request,
)
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import load_json_strict
from working_set_exp.tools import SessionState, ToolExecutor, action_schema


ROOT = Path(__file__).resolve().parents[1]
DONOR_BANK = ROOT / "experiments" / "014_unified_active_phase_receipts" / "fresh_bank"


def _patch_pair() -> tuple[dict, dict]:
    action = {
        "action": "patch",
        "path": "src/a.py",
        "old": "return 0",
        "new": "return 1",
        "expected_candidate_id": "a" * 64,
        "expected_file_sha256": "b" * 64,
    }
    result = {
        "accepted": True,
        "path": "src/a.py",
        "previous_candidate_id": "a" * 64,
        "candidate_id": "c" * 64,
        "file_sha256": "d" * 64,
        "diff": "-return 0\n+return 1\n",
    }
    return action, result


def test_v2_external_event_keeps_signal_not_patch_payload() -> None:
    action, result = _patch_pair()
    event = event_from_pair_v2(
        action,
        result,
        sequence=1,
        event_handle="EVT-0001",
        result_handle="RES-0001",
        payload_residency="external",
    )
    assert event["action"] == {
        "action": "patch",
        "path": "src/a.py",
        "expected_candidate_id": "a" * 64,
        "expected_file_sha256": "b" * 64,
    }
    assert event["result"]["accepted"] is True
    assert event["result"]["candidate_id"] == "c" * 64
    assert event["action_payload"]["field_names"] == ["new", "old"]
    assert event["action_payload"]["fields"] is None
    assert event["result_body"]["field_names"] == ["diff"]
    assert event["result_body"]["fields"] is None
    verification = verify_event_sequence_v2([event])
    assert verification["signal_contract"]["opaque_handle_is_not_the_progress_signal"] is True
    with pytest.raises(ValueError):
        resident_pair_v2(event)


def test_v2_resident_event_roundtrips_exact_pair() -> None:
    action, result = _patch_pair()
    event = event_from_pair_v2(
        action,
        result,
        sequence=1,
        event_handle="EVT-0001",
        result_handle="RES-0001",
        payload_residency="resident",
    )
    assert resident_pair_v2(event) == {"response": action, "result": result}


def test_reopen_event_returns_exact_action_payload() -> None:
    action, result = _patch_pair()
    event = event_from_pair_v2(
        action,
        result,
        sequence=1,
        event_handle="EVT-0001",
        result_handle="RES-0001",
        payload_residency="external",
    )
    executor = ToolExecutor(
        SessionState(Candidate.create({"a.txt": b"x\n"}), stage="continuation"),
        required_full_reads=(),
        prefork_checker=b"",
        public_checker=b"",
        final_target="__none__",
        probe_id=None,
        probe_body=None,
        event_reopenable={"EVT-0001": action_payload_bytes(action)},
    )
    reopened = executor.execute({"action": "reopen_event", "handle": "EVT-0001"})
    assert verify_reopened_action_payload(event, reopened)["verified"] is True


def test_event_reopen_schema_is_opt_in() -> None:
    without = action_schema("continuation", probe_id=None)
    with_event = action_schema("continuation", probe_id=None, event_reopen=True)
    assert "reopen_event" not in str(without)
    assert "reopen_event" in str(with_event)


@pytest.mark.parametrize("fixture_id", (*DONOR_CASES, SIGNAL_CASE))
def test_initial_v2_request_exposes_signal_and_exact_access(fixture_id: str) -> None:
    request = load_json_strict(initial_request(DONOR_BANK, fixture_id))
    frame = request["active_phase_event_frame"]
    assert frame["resident_signal_contract"]["handles"].startswith("addresses")
    assert request["event_frame_verification"]["signal_contract"]["opaque_handle_is_not_the_progress_signal"]
    assert "reopen_event" in request["available_actions"]
    assert "history" not in request
    assert "active_phase_receipt_ledger" not in request
    assert frame["events"]
    assert all(event["action"].get("action") for event in frame["events"])
    assert all("accepted" in event["result"] for event in frame["events"])


def test_signal_case_removed_value_exists_only_in_external_payload() -> None:
    values = branch_inputs(DONOR_BANK, SIGNAL_CASE)
    request = initial_request(DONOR_BANK, SIGNAL_CASE)
    assert b"ARCHIVE-Z7" not in request
    assert b"ARCHIVE-Z7" in values["event_reopenable"]["EVT-0001"]
    assert b"ARCHIVE-Z7" not in values["state"].candidate.file_map["archive/source.dat"]
