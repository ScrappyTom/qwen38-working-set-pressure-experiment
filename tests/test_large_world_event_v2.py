from __future__ import annotations

import tempfile
from pathlib import Path

import pytest

from working_set_exp.event_frame_v2 import event_from_pair_v2
from working_set_exp.jsonutil import load_json_strict
from working_set_exp.large_world_event_v2 import CASE_IDS, build_request, construct_bank, load_fixture, verify_bank
from working_set_exp.tools import SessionState


def test_fresh_bank_reconstructs() -> None:
    with tempfile.TemporaryDirectory(prefix="e18-test-") as raw:
        target = Path(raw) / "bank"
        manifest = construct_bank(target)
        assert verify_bank(target)["bank_id"] == manifest["bank_id"]
        assert set(manifest["case_ids"]) == set(CASE_IDS)


@pytest.mark.parametrize("fixture_id", CASE_IDS)
def test_request_uses_one_signal_bearing_event_plane(fixture_id: str) -> None:
    with tempfile.TemporaryDirectory(prefix="e18-request-") as raw:
        bank = Path(raw) / "bank"
        construct_bank(bank)
        fixture = load_fixture(bank, fixture_id, include_evaluator=False)
        state = SessionState(fixture.initial, stage="continuation")
        pair = {"response": {"action": "read", "path": "x.py", "start_line": 1},
                "result": {"accepted": True, "path": "x.py", "content": "signal\n",
                           "candidate_id": fixture.initial.candidate_id, "complete": True}}
        request = load_json_strict(build_request(fixture, candidate=fixture.initial, state=state, pairs=[pair],
                                                 externalized_payload_count=1, calls_used=1, fork_binding=None))
        assert "history" not in request
        assert "active_phase_receipt_ledger" not in request
        event = request["active_phase_event_frame"]["events"][0]
        assert event["action"]["path"] == "x.py"
        assert event["result"]["accepted"] is True
        assert event["result_body"]["fields"] is None
        assert event["result_body"]["access"] == "reopen_result"


def test_observation_rows_carry_signal_not_only_handles() -> None:
    with tempfile.TemporaryDirectory(prefix="e18-observation-") as raw:
        bank = Path(raw) / "bank"
        construct_bank(bank)
        fixture = load_fixture(bank, CASE_IDS[1], include_evaluator=False)
        rows = list(fixture.observations)
        assert len(rows) == 2
        assert {row["target"] for row in rows} == {"marker"}
        assert rows[0]["candidate_id"] != rows[1]["candidate_id"]
        assert all(row["size_bytes"] > 0 and row["sha256"] for row in rows)
