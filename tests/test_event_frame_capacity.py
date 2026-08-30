from working_set_exp.event_frame_capacity import (
    ACTIVE_PHASE_EVENT_LIMIT,
    accepted_patch_sequence,
    phase_transition_proof,
    stress_request,
)


def test_capacity_stress_uses_real_accepted_actions() -> None:
    for kind in ("maximum_schema_ascii_patch", "reasoning_budget_compatible_control_escape_patch"):
        fixture, candidate, pairs = accepted_patch_sequence(kind)
        assert fixture.initial.candidate_id != candidate.candidate_id
        assert len(pairs) == ACTIVE_PHASE_EVENT_LIMIT
        assert all(pair["result"]["accepted"] for pair in pairs)
        request, rebuilt_pairs, rebuilt_candidate = stress_request(
            kind, externalized_body_count=ACTIVE_PHASE_EVENT_LIMIT
        )
        assert rebuilt_pairs == pairs
        assert rebuilt_candidate == candidate
        assert b'"externalized_body_through_sequence":16' in request


def test_capacity_stress_phase_transition_is_scoped() -> None:
    _, _, pairs = accepted_patch_sequence("maximum_schema_ascii_patch")
    proof = phase_transition_proof(pairs)
    assert proof["verified"] is True
    assert proof["old_event_sequence"]["event_count"] == ACTIVE_PHASE_EVENT_LIMIT
    assert proof["new_event_sequence"]["event_count"] == 1
    assert proof["new_sequence_starts_at"] == 1
    assert proof["phase_scoped_handles"] is True
