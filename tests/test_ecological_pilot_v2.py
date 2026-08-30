from pathlib import Path

from working_set_exp.ecological_pilot_v2 import CASE_IDS, build_request, load_fixture, verify_bank
from working_set_exp.jsonutil import load_json_strict


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "020_owner_controlled_ecological_pilot_v2"


def test_bank_is_fresh_owner_controlled_and_unexposed() -> None:
    result = verify_bank(EXPERIMENT / "fresh_bank")
    assert result["verified"] is True
    manifest = load_json_strict((EXPERIMENT / "fresh_bank" / "BANK_MANIFEST.json").read_bytes())
    assert manifest["freshness"]["real_owner_controlled_source_snapshot"] is True
    assert manifest["freshness"]["fresh_sibling_tasks_not_reused_from_experiment_019"] is True
    assert manifest["freshness"]["not_exposed_to_measured_actor"] is True
    assert manifest["evaluator_bytes_model_visible"] is False


def test_tasks_freeze_a_real_premutation_inspection_obligation() -> None:
    for fixture_id in CASE_IDS:
        fixture = load_fixture(EXPERIMENT / "fresh_bank", fixture_id, include_evaluator=False)
        assert len(fixture.required_inspection_paths) >= 10
        assert "Before the first mutation" in fixture.task
        assert "required audit deliverable" in fixture.task
        assert "Run check `public`" in fixture.task
        for path in fixture.required_inspection_paths:
            assert path in fixture.task


def test_current_observation_reopen_preserves_canonical_payload_identity() -> None:
    fixture = load_fixture(EXPERIMENT / "fresh_bank", CASE_IDS[1], include_evaluator=False)
    action = {"action": "reopen_observation", "handle": "OBS-0002"}
    result = {
        "accepted": True,
        "handle": "OBS-0002",
        "exact_result_utf8": '{"status":"failed"}',
        "exact_result_sha256": "a" * 64,
        "size_bytes": 19,
    }
    request = load_json_strict(
        build_request(
            fixture,
            candidate=fixture.initial,
            pairs=[{"response": action, "result": result}],
            externalized_payload_count=1,
            calls_used=1,
            fork_binding=None,
        )
    )
    event = request["active_phase_event_frame"]["events"][0]
    assert event["result_body"]["canonical_source"]["handle"] == "OBS-0002"
    assert event["result_body"]["canonical_source"]["access"] == "reopen_observation"


def test_injected_candidates_fail_and_exact_donor_passes_both_checkers() -> None:
    from working_set_exp.ecological_pilot_v2 import admitted_donor_candidate, hidden_grade
    from working_set_exp.isolation import run_checker

    bank = EXPERIMENT / "fresh_bank"
    known_good = admitted_donor_candidate(bank)
    for fixture_id in CASE_IDS:
        fixture = load_fixture(bank, fixture_id, include_evaluator=True)
        assert run_checker(fixture.initial, fixture.public_checker)["passed"] is False
        assert hidden_grade(fixture, fixture.initial)["passed"] is False
        assert run_checker(known_good, fixture.public_checker)["passed"] is True
        assert hidden_grade(fixture, known_good)["passed"] is True


def test_model_free_ideal_paths_cross_before_mutation_and_reserve_correction() -> None:
    result = load_json_strict((EXPERIMENT / "IDEAL_PATH_QUALIFICATION.json").read_bytes())
    assert result["authentic_25k_boundary_before_first_mutation"] is True
    assert result["full_correction_cycle_reserved"] is True
    assert len(result["rows"]) == 4
    for row in result["rows"]:
        assert row["boundary"]["inspection_status"]["first_mutation_sequence"] is None
        assert row["inspection_status"]["all_completed_before_first_mutation"] is True
        assert row["first_check_calls_remaining"] >= 4
        assert row["minimum_total_headroom_tokens"] >= 1_000
        assert row["public_check_passed"] is True
        assert row["submitted"] is True


def test_live_authority_is_absent_and_future_payload_binds_schedule() -> None:
    from working_set_exp.ecological_pilot_v2 import expected_authorization
    from working_set_exp.jsonutil import sha256_file

    assert not (EXPERIMENT / "MEASURED_AUTHORIZATION.json").exists()
    expected = expected_authorization(EXPERIMENT)
    assert expected["schedule_sha256"] == sha256_file(EXPERIMENT / "SCHEDULE.json")
    assert expected["ideal_path_qualification_sha256"] == sha256_file(
        EXPERIMENT / "IDEAL_PATH_QUALIFICATION.json"
    )
