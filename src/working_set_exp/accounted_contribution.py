"""Opt-in authored working account and declared, scope-bound edit checks.

An account is recorded before an accompanying action, not inferred from thinking
or endorsed by execution. Existing contribution behavior remains the default.
"""
from __future__ import annotations

import copy

from . import working_view
from .contribution_session import ContributionSession
from .jsonutil import canonical_json_bytes, sha256_bytes
from .candidate import canonical_path
from .tools import SessionState, ToolExecutor


def action_rule(check_ids):
    rule = copy.deepcopy(working_view.schema()["json_schema"]["schema"])
    for form in rule["oneOf"]:
        if form["properties"]["action"]["const"] == "check":
            form["properties"]["check_id"]["enum"] = list(check_ids)
    return rule


def account_rule():
    return working_view.obj(dict(action=dict(type="string", const="record_account"),
                                 text=dict(type="string")))


def reply_schema(check_ids):
    discussion, account = dict(type="string"), dict(type="string")
    operation = action_rule(check_ids)
    forms = [working_view.obj(dict(discussion=discussion)),
             working_view.obj(dict(discussion=discussion, operation=operation)),
             working_view.obj(dict(discussion=discussion, account=account)),
             working_view.obj(dict(discussion=discussion, account=account, operation=operation))]
    return dict(type="json_schema", json_schema=dict(name="accounted_contribution_v1", strict=True,
                                                     schema=dict(oneOf=forms)))


class AccountedSession(ContributionSession):
    def __init__(self, candidate, checkers, task, *, edit_checks, **kwargs):
        if (not checkers or "public" not in checkers or
                any(not isinstance(k, str) or not k or not isinstance(v, bytes)
                    for k, v in checkers.items())):
            raise ValueError("named checker bytes including public are required")
        if any(canonical_path(p) not in candidate.file_map or scope not in checkers
               for p, scope in edit_checks.items()):
            raise ValueError("edit check must identify an existing path and registered scope")
        self.checkers = dict(checkers)
        self.edit_checks = {canonical_path(p): scope for p, scope in edit_checks.items()}
        super().__init__(candidate, self.checkers["public"], task, **kwargs)

    def action_rule(self):
        return {"oneOf": [*action_rule(self.checkers)["oneOf"], account_rule()]}

    def commit_admission_error(self, action):
        if action["action"] == "record_account":
            return "The complete account cannot fit beside the selected material; the previous account remains current. No account text was truncated."
        return super().commit_admission_error(action)

    def working_account(self):
        for sequence in range(len(self.pairs), 0, -1):
            pair = self.pairs[sequence - 1]
            if pair["response"]["action"] == "record_account" and pair["result"].get("accepted"):
                return dict(author="model", text=pair["response"]["text"],
                    action_handle=f"EVT-{sequence:04d}",
                    input_candidate_id=pair["result"]["input_candidate_id"],
                    written_during_request=pair["result"]["written_during_request"])
        return None

    def scoped_check_state(self, scope):
        for sequence in range(len(self.pairs), 0, -1):
            pair = self.pairs[sequence - 1]
            result = pair["result"]
            if (pair["response"]["action"] == "check" and result.get("accepted")
                    and result.get("check_id") == scope and "passed" in result):
                candidate_matches = result["checked_candidate_id"] == self.candidate.candidate_id
                definition_matches = result.get("check_definition_sha256") == sha256_bytes(self.checkers[scope])
                return dict(handle=f"RES-{sequence:04d}", check_id=scope,
                    candidate_id=result["checked_candidate_id"], passed=result["passed"],
                    candidate_matches=candidate_matches, check_definition_matches=definition_matches,
                    applies_to_current=candidate_matches and definition_matches)
        return None

    def check_state(self):
        return self.scoped_check_state("public")

    def view(self, **kwargs):
        result = super().view(**kwargs)
        result["working_account"] = self.working_account()
        result["verification"] = dict(
            available_checks=list(self.checkers),
            after_accepted_edit=dict(self.edit_checks),
            scoped_checks={scope: self.scoped_check_state(scope) for scope in self.checkers if scope != "public"},
            submission_check="public")
        return result

    def mark_delivered(self, view):
        expected = self.view()
        if any(view.get(k) != expected[k] for k in ("working_account", "verification")):
            raise ValueError("delivered account or verification state differs")
        super().mark_delivered(view)

    def _record(self, action, result):
        super()._record(action, result)
        if action["action"] == "record_account":
            # The current account carries the text once. History retains exact
            # update bytes in EVT, without an ever-growing resident account log.
            self.last["action_summary"].pop("text", None)

    def _ordinary(self, action):
        if action["action"] == "record_account":
            return dict(accepted=True, input_candidate_id=self.candidate.candidate_id,
                        written_during_request=self.requests_used,
                        account_handle=f"EVT-{len(self.pairs) + 1:04d}", cleared=action["text"] == "")
        if action["action"] != "check":
            return super()._ordinary(action)
        scope = action["check_id"]
        checker = self.checkers[scope]
        state = SessionState(self.candidate, stage="continuation")
        executor = ToolExecutor(state, required_full_reads=(), prefork_checker=b"", public_checker=checker,
                                final_target="", probe_id=None, probe_body=None, hierarchical_p0=True,
                                read_mode="maximal_bounded_page")
        result = executor.execute({**action, "check_id": "public"})
        return {**result, "check_id": scope, "check_definition_sha256": sha256_bytes(checker)}


def process_reply(session, reply, measure, preceding_feedback, record_operation=None):
    working_view.validate(reply, reply_schema(session.checkers)["json_schema"]["schema"])
    action = reply.get("operation")
    triggered = (session.edit_checks.get(action["path"])
                 if action and action["action"] == "patch" else None)
    needed = int("account" in reply) + int(action is not None) + int(triggered is not None)
    if needed > session.call_limit - session.calls_used:
        raise ValueError("insufficient operation allowance for the account, operation and declared check")
    preceding_feedback.clear()
    operations = []
    outcome = dict(executed=bool(needed), operations=operations)
    if not needed:
        return {**outcome, "discussion_only": True}

    def execute(value, origin):
        if operations:
            preceding_feedback.append(copy.deepcopy(session.last))
        result = session.execute(value, measure)
        operation = dict(origin=origin, action=copy.deepcopy(value), result=copy.deepcopy(result))
        operations.append(operation)
        if record_operation:
            record_operation(len(operations), operation)
        return result

    if "account" in reply:
        result = execute(dict(action="record_account", text=reply["account"]), "model_authored_account")
        if not result.get("accepted") or session.delivery_blocked:
            outcome["associated_operation_skipped"] = "account_not_accepted_or_feedback_blocked"
            return outcome
    if action is None:
        return outcome
    result = execute(action, "model")
    if triggered is None:
        return outcome
    if not result.get("accepted") or session.delivery_blocked:
        outcome["policy_check"] = dict(executed=False, scope=triggered,
                                        reason="edit_not_accepted_or_feedback_blocked")
        return outcome
    check = dict(action="check", check_id=triggered, expected_candidate_id=session.candidate.candidate_id)
    execute(check, "declared_host_policy")
    outcome["policy_check"] = dict(executed=True, scope=triggered,
                                    checked_candidate_id=check["expected_candidate_id"])
    return outcome


def operating_reference(check_descriptions):
    instructions = (
        'Reply with one JSON object. Supported forms, in displayed property order: '
        '{"discussion":string,"operation":operation}, '
        '{"discussion":string,"account":string,"operation":operation}, '
        '{"discussion":string,"account":string}, or {"discussion":string}. '
        "Discussion is archived and not carried into the next decision. Discussion alone ends the run; "
        "an account-only reply records the account and continues. The host executes no actions found "
        "inside discussion or account text.\n\n"
        "You may maintain a concise working account: the current question, provisional interpretation, "
        "supporting references and unresolved evidence needed. Include account as a string alongside an "
        "operation, or update it alone. Omit account to retain its exact current text; an empty string "
        "clears it. The host records each update before the accompanying operation, using the input "
        "candidate identity. The account cannot know that operation's result yet. Its text remains "
        "model-authored understanding, not a host-certified explanation. Source changes and checks "
        "do not automatically rewrite or endorse it. Earlier account updates are exactly recoverable "
        "through EVT/RES history. The host measures account size with the complete input; it does not "
        "truncate accounts or silently release selected evidence.\n\n"
        "verification.after_accepted_edit declares which check the host executes after an accepted edit "
        "to each listed path. A rejected edit skips the check; a failing check preserves the saved edit. "
        "The host binds the check to the actual successor and returns the real receipts before your "
        "next decision. Each account update, requested operation and automatic check consumes one "
        "operation; they share one model request when combined. A reply cannot execute an arbitrary "
        "adaptive sequence. Explicit checks remain available. Only a current passing public check "
        "permits submission. Scoped passes establish their reported scope, not full completion.\n\n"
        "A proposed expected value may be saved provisionally. Before using it to explain behavior in "
        "another artifact, obtain support from actual implementation or applicable execution. Repeating "
        "the same authored expectation is not independent confirmation. Keep unresolved questions in "
        "the account when they matter to later work; use real results to revise them. Passing examples "
        "do not validate all surrounding prose, and passing tests do not prove complete coverage."
    )
    effects = dict(working_view.EFFECTS)
    effects["check"] = ("Executes check_id on expected_candidate_id, which must equal the current candidate. "
                        "Returns actual output with scope, candidate and checker identity. A failed check is "
                        "accepted execution. Check scopes: " + canonical_json_bytes(check_descriptions).decode())
    reference = []
    for form in action_rule(check_descriptions)["oneOf"]:
        name = form["properties"]["action"]["const"]
        reference.append(name + ": " + effects[name] + "\nRequired argument forms: " + canonical_json_bytes(form).decode())
    return working_view.INPUT_INTERPRETATION + "\n\n" + instructions + "\n\n" + "\n\n".join(reference)
