"""Opt-in edit/check coordination over the existing bounded working host.

The model chooses a patch and may request its public check in the same reply.
Only the host can bind that check to the observed successor. Historical action
forms, custody, source eligibility and check semantics remain unchanged.
"""
from __future__ import annotations

import copy

from . import working_view


def reply_schema():
    action = working_view.schema()["json_schema"]["schema"]
    patch = next(form for form in action["oneOf"]
                 if form["properties"]["action"]["const"] == "patch")
    discussion = dict(type="string")
    return dict(type="json_schema", json_schema=dict(
        name="reviewed_contribution_reply", strict=True, schema=dict(oneOf=[
            working_view.obj(dict(discussion=discussion)),
            working_view.obj(dict(discussion=discussion, operation=action)),
            working_view.obj(dict(discussion=discussion, operation=patch,
                                  check_after=dict(type="string", const="public"))),
        ])))


def process_reply(session, reply, measure, preceding_feedback, record_operation=None):
    """Execute at most two ordered operations, never inventing a model guard.

    ``preceding_feedback`` is included by the caller in every measured input.
    It holds the exact edit receipt while latest_feedback holds the check. The
    actual operations still consume two actions. A failed/rejected check never
    rolls back a saved edit. A rejected patch never triggers a check.
    """
    working_view.validate(reply, reply_schema()["json_schema"]["schema"])
    paired = "check_after" in reply
    needed = 2 if paired else int("operation" in reply)
    if session.call_limit - session.calls_used < needed:
        raise ValueError("insufficient action allowance for the complete requested contribution")
    preceding_feedback.clear()
    if "operation" not in reply:
        return dict(executed=False, discussion_only=True, operations=[])

    action = reply["operation"]
    result = session.execute(action, measure)
    operations = [dict(origin="model", action=copy.deepcopy(action), result=copy.deepcopy(result))]
    if record_operation:
        record_operation(1, operations[0])
    outcome = dict(executed=True, operations=operations)
    if not paired:
        return outcome
    if not result.get("accepted") or session.delivery_blocked:
        outcome["check_after"] = dict(executed=False, reason="edit_not_accepted_or_feedback_blocked")
        return outcome

    # The edit receipt remains present while the check is measured and delivered.
    # Never credit an intermediate host operation as a model-received input.
    preceding_feedback.append(copy.deepcopy(session.last))
    check = dict(action="check", check_id=reply["check_after"],
                 expected_candidate_id=session.candidate.candidate_id)
    result = session.execute(check, measure)
    operations.append(dict(origin="host_bound_check_requested_by_model",
                           action=check, result=copy.deepcopy(result)))
    if record_operation:
        record_operation(2, operations[1])
    outcome["check_after"] = dict(executed=True, checked_candidate_id=check["expected_candidate_id"])
    return outcome
