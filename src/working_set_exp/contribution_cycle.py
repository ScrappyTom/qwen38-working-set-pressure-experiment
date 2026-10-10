"""Opt-in local purpose over the existing operation archive and guarded host.

The model selects purpose; the host reports only recorded effects/applicability.
No source selection, semantic completion claim, or new persistence layer.
"""
from __future__ import annotations

import copy

from . import working_view


ACTION = "select_contribution"
REFERENCE = """Contribution coordination is enabled. You may select the immediate
contribution with select_contribution(objective, check_id). State the bounded
result or question you intend to work on; choose an existing check scope, or an
empty check_id when no available scope fits. Required operation fields are
{"action":"select_contribution","objective":string,"check_id":string}.
This is optional and consumes one
operation. Ordinary work does not require a planning operation. The objective
remains current through reads, edits and checks until you select another; empty
objective with empty check_id clears it. An inherited selection from a previous
job remains historical, not the new job's objective. Changing it never changes the task,
source selection, saved work, check applicability, or the spending allowance.

current_contribution separates your selected purpose from recorded effects and
execution. A selected check is not automatically run. A passing scope establishes
only its actual result; it does not certify your objective or the whole task.
Use the existing account when a conclusion, rejected approach or unresolved
question needs to survive the next operation. Account updates are optional;
mechanical edit/check status is supplied separately. Choose the next operation
needed for the current contribution; revise its scope when evidence warrants it.
"""


def selection_rule(checks):
    return working_view.obj(dict(
        action=dict(type="string", const=ACTION),
        objective=dict(type="string"),
        check_id=dict(type="string", enum=["", *checks]),
    ))


def extend_reply_schema(schema, checks):
    value = copy.deepcopy(schema)
    value["json_schema"]["name"] = "contribution_cycle_v1"
    for form in value["json_schema"]["schema"]["oneOf"]:
        operation = form["properties"].get("operation")
        if operation is not None:
            operation["oneOf"].append(selection_rule(checks))
    return value


def reply_grammar(checks, schema, converter_class):
    """Extend the ordinary operation grammar; preserve the literal source channel."""
    from . import decision_view
    inherited = decision_view.reply_schema(checks)["json_schema"]["schema"]
    entries = []

    class Converter(converter_class):
        def visit(self, rule, name):
            if name == "ordinary-reply":
                if entries or rule != inherited:
                    raise ValueError("ordinary grammar boundary changed")
                entries.append(name)
                rule = schema["json_schema"]["schema"]
            return super().visit(rule, name)

    grammar = decision_view.reply_grammar(checks, Converter)
    if entries != ["ordinary-reply"]:
        raise ValueError("ordinary grammar boundary missing")
    return grammar


class ContributionCycleMixin:
    """Place before an existing accounted/decision session in its MRO.

    All state is derived from ordinary archived operations, so the existing
    clone, exact recovery and snapshot/restore machinery remains applicable.
    """

    def action_rule(self):
        value = copy.deepcopy(super().action_rule())
        value["oneOf"].append(selection_rule(self.checkers))
        return value

    def reply_schema(self):
        return extend_reply_schema(super().reply_schema(), self.checkers)

    def _ordinary(self, action):
        if action["action"] != ACTION:
            return super()._ordinary(action)
        if action["objective"] and not action["objective"].strip():
            raise ValueError("objective must contain text or be empty to clear")
        if not action["objective"] and action["check_id"]:
            raise ValueError("clearing a contribution requires an empty check_id")
        return dict(accepted=True, author="model",
                    contribution_handle=f"EVT-{len(self.pairs) + 1:04d}",
                    input_candidate_id=self.candidate.candidate_id,
                    selected_during_request=self.requests_used,
                    cleared=not action["objective"])

    def commit_admission_error(self, action):
        if action["action"] == ACTION:
            return "The objective and complete feedback do not fit; previous contribution retained."
        return super().commit_admission_error(action)

    def _record(self, action, result):
        super()._record(action, result)
        if action["action"] == ACTION:
            self.last["action_summary"].pop("objective", None)

    def current_contribution(self):
        for sequence in range(len(self.pairs), self.starting_archive_length, -1):
            pair = self.pairs[sequence - 1]
            action, result = pair["response"], pair["result"]
            if action["action"] != ACTION or not result.get("accepted"):
                continue
            if not action["objective"]:
                return None
            edits = [p["result"] for p in self.pairs[sequence:]
                     if p["response"]["action"] in self.mutation_actions
                     and p["result"].get("accepted")]
            scope = action["check_id"]
            check = self.scoped_check_state(scope) if scope in self.checkers else None
            if check:
                check = {**check,
                    "recorded_after_selection": int(check["handle"].split("-")[1]) > sequence}
            return dict(
                author="model", objective=action["objective"],
                action_handle=result["contribution_handle"],
                input_candidate_id=result["input_candidate_id"],
                selected_during_request=result["selected_during_request"],
                selected_check_id=scope or None,
                selected_check_available=scope in self.checkers,
                actual_selected_check=check,
                recorded_effects=dict(accepted_edits=len(edits),
                    edited_paths=sorted({e["path"] for e in edits})),
                completion="not_inferred_from_objective_account_or_edit_counts",
            )
        return None

    def view(self, **kwargs):
        value = super().view(**kwargs)
        # Keep the entire task/evidence arrangement. The request adapter exposes
        # this small decision purpose first; it never supplies a proposed answer.
        return {"current_contribution": self.current_contribution(), **value}

    def mark_delivered(self, view):
        if view.get("current_contribution") != self.current_contribution():
            raise ValueError("delivered contribution differs from archived selection")
        return super().mark_delivered(view)


def focus_request(request):
    """Promote purpose without duplicating it; leave sampler/grammar unchanged.

    Intended for the existing two-message snapshot adapter. Full source remains
    in the user message. Do not put model-authored purpose in the system role.
    """
    from .jsonutil import canonical_json_bytes, load_json_strict
    value = copy.deepcopy(request)
    if [m["role"] for m in value["messages"]] != ["system", "user"]:
        raise ValueError("contribution adapter requires the qualified snapshot arrangement")
    payload = load_json_strict(value["messages"][1]["content"])
    focus = payload["workspace"].pop("current_contribution")
    # JSON insertion order is intentional for this presentation. The canonical
    # outer wire preserves the inner content string exactly.
    import json
    payload = {"current_contribution": focus, **payload}
    value["messages"][1]["content"] = json.dumps(payload, ensure_ascii=False,
        separators=(",", ":"), allow_nan=False)
    value["messages"][0]["content"] += "\n\n" + REFERENCE
    assert canonical_json_bytes(value)  # reject non-finite/non-serializable state
    return value
