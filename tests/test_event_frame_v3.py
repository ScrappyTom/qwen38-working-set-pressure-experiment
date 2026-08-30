from working_set_exp.event_frame_v3 import (
    capture_original_result_payload,
    event_from_pair_v3,
    verify_event_sequence_v3,
)


def _reopen_result(handle: str, body: str) -> tuple[dict, dict]:
    action = {"action": "reopen_result", "handle": handle}
    result = {
        "accepted": True,
        "handle": handle,
        "exact_result_utf8": body,
        "exact_result_sha256": "a" * 64,
        "size_bytes": len(body.encode("utf-8")),
    }
    return action, result


def test_repeated_reopen_events_retain_one_canonical_result_address() -> None:
    action1, result1 = _reopen_result("RES-0001", '{"content":"governing fact"}')
    action2, result2 = _reopen_result("RES-0001", '{"content":"governing fact"}')
    events = [
        event_from_pair_v3(action1, result1, sequence=2, payload_residency="external"),
        event_from_pair_v3(action2, result2, sequence=3, payload_residency="external"),
    ]
    # Verification requires the full event sequence, so inspect the identity
    # invariant directly for this two-event fragment.
    assert events[0]["event_handle"] == "EVT-0002"
    assert events[1]["event_handle"] == "EVT-0003"
    assert events[0]["result_body"]["canonical_source"] == {
        "access": "reopen_result",
        "handle": "RES-0001",
        "origin": "preexisting_exact_payload",
    }
    assert events[1]["result_body"]["canonical_source"] == events[0]["result_body"]["canonical_source"]


def test_observation_reopen_retains_observation_identity() -> None:
    action = {"action": "reopen_observation", "handle": "OBS-0002"}
    result = {
        "accepted": True,
        "handle": "OBS-0002",
        "exact_result_utf8": '{"marker":"HARBOR-K9"}',
        "exact_result_sha256": "b" * 64,
        "size_bytes": 22,
    }
    event = event_from_pair_v3(action, result, sequence=1, payload_residency="external")
    assert event["result_body"]["canonical_source"] == {
        "access": "reopen_observation",
        "handle": "OBS-0002",
        "origin": "preexisting_exact_payload",
    }
    verification = verify_event_sequence_v3([event])
    assert verification["canonical_payload_reuse_events"] == 1


def test_reopen_does_not_mint_result_of_result_payload() -> None:
    reopenable: dict[str, bytes] = {"RES-0001": b'{"content":"original"}'}
    action, result = _reopen_result("RES-0001", '{"content":"original"}')
    handle = capture_original_result_payload(
        action,
        result,
        sequence=2,
        result_reopenable=reopenable,
    )
    assert handle == "RES-0001"
    assert set(reopenable) == {"RES-0001"}


def test_new_result_receives_one_sequence_bound_payload_address() -> None:
    reopenable: dict[str, bytes] = {}
    action = {"action": "read", "path": "a.py", "start_line": 1}
    result = {"accepted": True, "path": "a.py", "content": "x\n", "complete": True}
    handle = capture_original_result_payload(
        action,
        result,
        sequence=1,
        result_reopenable=reopenable,
    )
    assert handle == "RES-0001"
    assert set(reopenable) == {"RES-0001"}
