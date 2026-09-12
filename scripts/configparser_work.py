"""Current task view and unchanged oldest-prefix admission for the larger-source pilot."""
import configparser_backport as task
import prepare_investigation_loop as pilot
from prepare_episode_framing import annotate
from working_set_exp.ecological_pilot_v2 import build_request
from working_set_exp.interface_consultation import endpoint_request
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict

ACTOR = dict(pilot.ACTOR)
INPUT_CEILING = 23_808
CALL_LIMIT = 40
SEED = 961207
require = pilot.require


def request_for(value, externalized=0):
    used = len(value.pairs)
    require(used < CALL_LIMIT and not value.state.submitted, "terminal state has no new request")
    require(value.state.candidate.max_file_bytes == task.FILE_LIMIT, "candidate lost selected admission policy")
    state = load_json_strict(build_request(value.fixture, candidate=value.state.candidate, pairs=value.pairs,
        externalized_payload_count=externalized, calls_used=used, fork_binding=None))
    require(state["resource_state"].pop(pilot.wording.RESOURCE_KEY) == pilot.wording.RESOURCE_EXAMPLE,
            "resource wording source changed")
    state["resource_state"].update(call_limit=CALL_LIMIT, calls_used=used,
        calls_remaining=CALL_LIMIT-used, reasoning_budget_tokens=-1)
    value.request = canonical_json_bytes(state)
    request = endpoint_request(value, seed=42, mode="action")
    request["model"], request["seed"] = pilot.base.ALIAS, SEED
    system = request["messages"][0]["content"]
    require(system.count(pilot.wording.OLD_NAVIGATION) == 1, "navigation source changed")
    reference = pilot.tool_reference(request["response_format"], candidate=value.state.candidate)
    request["messages"][0]["content"] = system.replace(pilot.wording.OLD_NAVIGATION, pilot.wording.NEW_NAVIGATION) + "\n\n" + reference
    require(ACTOR["context"] == 56576 and ACTOR["generation_reserve"] == 32768
            and ACTOR["context"] - ACTOR["generation_reserve"] == INPUT_CEILING, "runtime allowance differs")
    return annotate(request, report_precedes_session=True)


def select_input(value, *, previous, render):
    for prefix in range(previous, len(value.pairs)+1):
        request = request_for(value, prefix)
        result = render(request, prefix)
        if result["prompt_tokens"] <= INPUT_CEILING:
            return dict(request=request, externalized=prefix, **result)
    return None


def latest_result_delivered(request, value):
    if not value.pairs:
        return True
    events = load_json_strict(request["messages"][1]["content"].encode())["active_phase_event_frame"]["events"]
    body = events[-1]["result_body"]
    if body["present"] and body["residency"] != "resident":
        return False
    return {**events[-1]["result"], **(body["fields"] or {})} == value.pairs[-1]["result"]
