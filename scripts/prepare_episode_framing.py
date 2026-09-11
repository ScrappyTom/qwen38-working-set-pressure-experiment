"""Add task-author episode context to a prospective ordinary-action input.

This is a preparation helper, not an execution path or a default host policy.
The task author must establish that the report precedes the repair session.
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path

from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict

EPISODE_ANNOTATION = (
    "Task-author context: the problem reported in task and this step's text precedes this repair session. "
    "active_phase_event_frame records this session's actions and results. "
    "Repetition of the report is not a new observation after those actions."
)


def annotate(request, *, report_precedes_session):
    if report_precedes_session is not True:
        raise ValueError("The task author must establish the report/session relationship")
    result = copy.deepcopy(request)
    messages = result.get("messages", [])
    if [m.get("role") for m in messages] != ["system", "user"] or "response_format" not in result:
        raise ValueError("Expected the ordinary two-message action request")
    state = load_json_strict(messages[1]["content"].encode("utf-8"))
    step = state.get("active_user_authored_step", {})
    if not state.get("task") or step.get("text") != state["task"]:
        raise ValueError("Task and active step must carry the same declared report")
    if "episode_annotation" in step:
        raise ValueError("An episode annotation is already present; review it explicitly")
    if not isinstance(state.get("active_phase_event_frame", {}).get("events"), list):
        raise ValueError("Expected the actual active-phase event frame")
    step["episode_annotation"] = EPISODE_ANNOTATION
    messages[1]["content"] = canonical_json_bytes(state).decode("utf-8")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--report-precedes-session", action="store_true", required=True)
    args = parser.parse_args()
    request = load_json_strict(args.input.read_bytes())
    result = annotate(request, report_precedes_session=args.report_precedes_session)
    with args.output.open("xb") as stream:
        stream.write(canonical_json_bytes(result))
