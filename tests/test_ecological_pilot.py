from pathlib import Path

from working_set_exp.ecological_pilot import CASE_IDS, build_request, load_fixture, verify_bank
from working_set_exp.jsonutil import load_json_strict


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "019_owner_controlled_ecological_pilot"


def test_bank_is_owner_controlled_fresh_and_sealed() -> None:
    result = verify_bank(EXPERIMENT / "fresh_bank")
    assert result["verified"] is True
    manifest = load_json_strict((EXPERIMENT / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    assert manifest["freshness"]["real_owner_controlled_source_snapshot"] is True
    assert manifest["evaluator_bytes_model_visible"] is False


def test_tasks_have_clear_unambiguous_acceptance_contracts() -> None:
    for fixture_id in CASE_IDS:
        fixture = load_fixture(EXPERIMENT / "fresh_bank", fixture_id, include_evaluator=False)
        assert "Do not modify tests" in fixture.task or "do not modify tests" in fixture.task
        assert "Run check `public`" in fixture.task
        assert "ideal path" not in fixture.task.lower()


def test_event_frame_reuses_canonical_source_after_reopen() -> None:
    fixture = load_fixture(EXPERIMENT / "fresh_bank", CASE_IDS[1], include_evaluator=False)
    action = {"action": "reopen_observation", "handle": "OBS-0002"}
    result = {
        "accepted": True,
        "handle": "OBS-0002",
        "exact_result_utf8": '{"status":"failed"}',
        "exact_result_sha256": "a" * 64,
        "size_bytes": 19,
    }
    request = load_json_strict(build_request(
        fixture,
        candidate=fixture.initial,
        pairs=[{"response": action, "result": result}],
        externalized_payload_count=1,
        calls_used=1,
        fork_binding=None,
    ))
    event = request["active_phase_event_frame"]["events"][0]
    assert event["result_body"]["canonical_source"]["handle"] == "OBS-0002"
    assert event["result_body"]["canonical_source"]["access"] == "reopen_observation"
    assert request["event_frame_verification"]["signal_contract"]["reopen_is_access_not_new_payload"]


def test_public_and_hidden_checkers_reject_injected_candidates() -> None:
    from working_set_exp.ecological_pilot import hidden_grade
    from working_set_exp.isolation import run_checker

    for fixture_id in CASE_IDS:
        fixture = load_fixture(EXPERIMENT / "fresh_bank", fixture_id, include_evaluator=True)
        assert run_checker(fixture.initial, fixture.public_checker)["passed"] is False
        assert hidden_grade(fixture, fixture.initial)["passed"] is False


def test_exact_owner_controlled_donor_is_a_known_good_successor() -> None:
    from working_set_exp.ecological_pilot import admitted_donor_candidate, hidden_grade
    from working_set_exp.isolation import run_checker

    known_good = admitted_donor_candidate(EXPERIMENT / "fresh_bank")
    for fixture_id in CASE_IDS:
        fixture = load_fixture(EXPERIMENT / "fresh_bank", fixture_id, include_evaluator=True)
        assert run_checker(known_good, fixture.public_checker)["passed"] is True
        assert hidden_grade(fixture, known_good)["passed"] is True
