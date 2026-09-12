"""Prospective saved-report continuation using the existing tools and V3 view.

No oracle or completion transport is imported here. Historical proposal actions
are replayed in their own scope; the closed compiler trajectory is not resumed.
"""
from __future__ import annotations

import copy
from pathlib import Path

import run_compiler_incident as compiler
from working_set_exp.candidate import Candidate
from working_set_exp.ecological_pilot_v2 import build_request
from working_set_exp.event_frame_v3 import resident_pair_v3
from working_set_exp.interface_consultation import endpoint_request, new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_file

ROOT = compiler.ROOT
AREA = ROOT / "development/saved_work_continuation"
PROPOSAL = ROOT / "development/delivery_dialogue/proposal-check-001"
PACKAGE = AREA / "preparation-001"
ACTOR = dict(compiler.pilot.ACTOR)
INPUT_CEILING = 23_808
PHASE_LIMIT = 8
MAX_CALLS = 2 * PHASE_LIMIT
SEED = 86028121
REPORT = "reports/incident.json"
SUCCESSOR = "f7939c49b60d57f19b88dde8d31c6deb0ea036b6a3746c5d27b61d5ce0b99fd6"
require, pilot = compiler.require, compiler.pilot


def read(path):
    return load_json_strict(path.read_bytes())


def verify_start():
    compiler.verified_package()
    seal = read(PROPOSAL / "SEAL.json")
    require(seal["status"] == "completed_offline_checks", "proposal check incomplete")
    for row in seal["files"]:
        path = PROPOSAL / row["path"]
        require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"],
                "saved proposal changed: " + row["path"])
    require(sha256_file(ROOT / "development/delivery_dialogue/check_proposals.py") == seal["source_sha256"],
            "proposal source changed")
    require(sha256_file(ROOT / "development/delivery_dialogue/turn-02/RESPONSE_SEAL.json") == seal["d2_seal_sha256"],
            "D2 seal changed")
    require(ACTOR["context"] - ACTOR["generation_reserve"] == INPUT_CEILING,
            "selected physical context/reserve differs")


def starting_state():
    value = new_state("saved-work-development", compiler.load_fixture())
    pairs = read(PROPOSAL / "scripted-pairs.json")
    require(len(pairs) == 3, "saved contribution history changed")
    for pair in pairs:
        require(value.execute(pair["response"]) == pair["result"], "saved contribution replay differs")
    require(value.state.candidate.candidate_id == SUCCESSOR, "wrong saved successor")
    require(pilot.reference.candidate_bytes(value.state.candidate) == (PROPOSAL / "candidate.json").read_bytes(),
            "saved candidate bytes differ")
    require(value.state.candidate.file_map[REPORT] == b'{"builds": []}\n', "report is not initially empty")
    return value


def assemble(value, phase, *, record=lambda action, result: None):
    """Researcher-selected exact acquisitions, explicitly outside actor allowance."""
    require(phase in (1, 2), "unknown phase")
    actions = []
    if phase == 2:
        require(value.pairs[-1]["response"]["action"] == "check", "restart requires the actual preceding check")
        actions.append(dict(action="reopen_result", handle=f"RES-{len(value.pairs):04d}"))
    actions += [dict(action="read", path=name, start_line=1) for name in ("README.md", REPORT)]
    actions += [dict(action="reopen_observation", handle=name)
                for name in ("OBS-0001", "OBS-0002" if phase == 1 else "OBS-0003")]
    sequences = []
    for action in actions:
        result = value.execute(action)
        record(action, result)
        require(result.get("accepted") is True, "assisted acquisition rejected")
        if action["action"] == "read":
            require(result["returned_start_line"] == 1 and result["next_start_line"] is None and
                    result["content"].encode() == value.state.candidate.file_map[action["path"]],
                    "assisted source is not complete current text")
        sequences.append(len(value.pairs))
    return sequences


def request_for(value, *, phase, phase_used, total_used, externalized, setup_ranges):
    require(phase in (1, 2) and 0 <= phase_used < PHASE_LIMIT and 0 <= total_used < MAX_CALLS,
            "action allowance exhausted")
    require(not value.state.submitted, "submitted state cannot receive another request")
    state = read_bytes(build_request(value.fixture, candidate=value.state.candidate,
        pairs=value.pairs, externalized_payload_count=externalized, calls_used=total_used, fork_binding=None))
    state["resource_state"].pop(pilot.wording.RESOURCE_KEY)
    state["resource_state"].update(calls_used=total_used, call_limit=MAX_CALLS,
        calls_remaining=MAX_CALLS-total_used, phase_call_limit=PHASE_LIMIT,
        phase_calls_used=phase_used, phase_calls_remaining=PHASE_LIMIT-phase_used,
        reasoning_budget_tokens=-1)
    phase_text = (AREA / f"PHASE_{phase}.txt").read_text(encoding="utf-8").strip()
    state["active_user_authored_step"] = dict(id=f"SAVED-REPORT-{phase}", text=phase_text, host_inference=False,
        episode_annotation=(
            "Task-author context: OBS-0001/0002/0003 are historical captures made before the saved optimizer repair. "
            "Events 1-3 are separately recorded reviewer-scripted acquisition, application of Qwen's proposed patch, "
            "and its offline check. That check passed 25 optimizer cases; the empty report was the sole failure. "
            "It was not a Qwen-executed repair loop. Later events belong to this development continuation; "
            "the listed setup ranges are researcher-selected acquisitions and all other later events are model actions. "
            "Older captures remain bound to their original candidate; checks concern the candidate they explicitly name. "
            "The closed earlier compiler trajectory and consultation thinking are not part of this working history."))
    state["development_setup_sequence_ranges"] = setup_ranges
    value.request = canonical_json_bytes(state)
    request = endpoint_request(value, seed=42, mode="action")
    request["model"], request["seed"] = pilot.base.ALIAS, SEED
    system = request["messages"][0]["content"]
    require(system.count(pilot.wording.OLD_NAVIGATION) == 1, "navigation source changed")
    request["messages"][0]["content"] = system.replace(pilot.wording.OLD_NAVIGATION, pilot.wording.NEW_NAVIGATION) + "\n\n" + pilot.tool_reference(pilot.grammar_for(value))
    return request


def read_bytes(raw):
    return load_json_strict(raw)


def select_input(value, *, previous, render, **kwargs):
    """Unchanged oldest-prefix rule; no restoration or protected-set override."""
    for prefix in range(previous, len(value.pairs)+1):
        request = request_for(value, externalized=prefix, **kwargs)
        rendered = render(request, prefix)
        if rendered["prompt_tokens"] <= INPUT_CEILING:
            return dict(request=request, externalized=prefix, **rendered)
    return None


def delivered(request, value, sequences):
    events = read_bytes(request["messages"][1]["content"].encode())["active_phase_event_frame"]["events"]
    for sequence in sequences:
        try:
            if resident_pair_v3(events[sequence-1]) != value.pairs[sequence-1]:
                return False
        except ValueError:
            return False
    return True


def result_delivered(request, value, sequence):
    """Delivery of feedback is distinct from residency of a patch's old/new text."""
    events = read_bytes(request["messages"][1]["content"].encode())["active_phase_event_frame"]["events"]
    event = events[sequence-1]
    body = event["result_body"]
    if body["present"] and body["residency"] != "resident":
        return False
    return {**event["result"], **(body["fields"] or {})} == value.pairs[sequence-1]["result"]


def report_changed(action, result):
    return action.get("action") == "patch" and action.get("path") == REPORT and result.get("accepted") is True


def phase_finished(action, result, edited):
    # No oracle, report correctness, or hidden content controls this transition.
    return edited and action.get("action") == "check" and result.get("accepted") is True


def sources():
    original = compiler.verified_package()["source_sha256"]
    paths = [Path(__file__), ROOT / "scripts/prepare_saved_work_continuation.py",
        ROOT / "scripts/run_saved_work_continuation.py", ROOT / "tests/test_saved_work_continuation.py",
        ROOT / "scripts/run_compiler_incident.py", ROOT / "scripts/qualify_compiler_delivery.py",
        AREA / "SPEC.md", AREA / "PHASE_1.txt", AREA / "PHASE_2.txt"]
    return {**original, **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}
