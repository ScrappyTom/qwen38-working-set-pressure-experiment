"""Opt-in coordination and spending adapter. No launcher or implicit GPU use.

Use inside an already qualified owned-runtime context. Deadlines close the loop;
the enclosing context closes its server. Native render, existing checks and final
custody drain normally under their own limits. This is not a whole-process kill
deadline and does not truncate an executed edit/check transaction.
"""
from __future__ import annotations

import copy
from dataclasses import asdict

import run_uncoached_contribution as existing
from working_set_exp import decision_view, working_view
from working_set_exp.contribution_cycle import extend_reply_schema, focus_request, reply_grammar
from working_set_exp.contribution_limits import SpendingStop
from working_set_exp.deadline_transport import post as deadline_post, TransportFailure
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes
from working_set_exp.thinking_grammar import with_thinking


class Adapter(existing.Adapter):
    def __init__(self, module, *, checks, converter_class, limits, qualifying_check_ids=("public",)):
        self.original = module
        self.checks = tuple(checks)
        if not set(qualifying_check_ids).issubset(self.checks):
            raise ValueError("spending policy names an unavailable check scope")
        self.schema = extend_reply_schema(module.reply_schema(), self.checks)
        self.constraints = dict(grammar=with_thinking(reply_grammar(self.checks, self.schema, converter_class)))
        # Legacy invoke decodes via actor.module; override that single boundary.
        # All task execution, snapshots, source identities and checkers delegate.
        class ModuleProxy:
            def __getattr__(_, name):
                return getattr(module, name)

            def decode_reply(_, content):
                reply = decision_view.decode_reply(content)
                working_view.validate(reply, self.schema["json_schema"]["schema"])
                return reply

        super().__init__(ModuleProxy())
        self.spending_policy = dict(limits=asdict(limits), qualifying_check_ids=list(qualifying_check_ids))

    def reply_schema(self):
        return copy.deepcopy(self.schema)

    def request_for(self, view):
        request = focus_request(super().request_for(view))
        request.pop("response_format", None)
        request.update(self.constraints)
        request["messages"][0]["content"] += (
            "\nContribution check scopes: " + canonical_json_bytes(["", *self.checks]).decode()
            + "\nDeclared spending policy: " + canonical_json_bytes(self.spending_policy).decode()
            + ". Wall-clock limits can stop a request without an action; they are not a thinking-token budget. "
            "Total elapsed time never resets. After a saved edit, time awaiting an actual applicable check "
            "is bounded; a failed check in a declared scope also supplies an observation. "
            "A selected objective or account update resets neither limit. No automatic retry occurs.")
        return request

    def expected_native(self, request):
        if request.get("grammar") != self.constraints["grammar"]:
            raise ValueError("contribution grammar differs")
        original = copy.deepcopy(request)
        original["grammar"] = self.original.response_constraints()["grammar"]
        return self.original.expected_native(original)


class Loop(existing.Loop):
    def __init__(self, *args, spending, post=None, **kwargs):
        self.spending = spending
        self.transport = post or deadline_post
        self.observed_operations = None
        self.entered = False
        self.first_invocation = True
        self.active_session = None
        super().__init__(*args, post=self._post, **kwargs)
        if self.task.spending_policy != dict(limits=asdict(spending.limits),
                qualifying_check_ids=list(spending.qualifying_check_ids)):
            raise ValueError("rendered spending policy differs from enforced policy")

    def _post(self, url, route, raw, timeout):
        allowance, reason = self.spending.request_allowance()
        started = self.spending.clock()
        try:
            result = self.transport(url, route, raw, min(timeout, allowance))
            if self.spending.clock() - started >= allowance:
                raise SpendingStop(reason, data=result)
            return result
        except (SpendingStop, TransportFailure) as problem:
            failure = self.task.base.ResponseFailure(str(problem), problem.data, problem.status)
            if isinstance(problem, SpendingStop):
                failure.spending_reason = reason
            raise failure from problem

    def stop_requested(self):
        if super().stop_requested():
            return True
        if self.active_session is not None and self.active_session.submitted:
            return False  # Draining an accepted submission must not rewrite its outcome.
        self.spending.remaining()
        return False

    def snapshot(self, session, stem):
        if self.observed_operations is None:
            self.observed_operations = len(session.pairs)
        self.spending.observe_operations(session, self.observed_operations)
        self.observed_operations = len(session.pairs)
        super().snapshot(session, stem)
        self.log.append("spending_saved", dict(stem=stem),
            [self.store.put(stem + "-spending.json", canonical_json_bytes(self.spending.snapshot()))])

    def invoke(self, session):
        self.spending.remaining()
        if self.observed_operations is None:
            self.observed_operations = len(session.pairs)
        if self.first_invocation and self.initial:
            self.measure(session.view())
            entry = self.cache[sha256_bytes(canonical_json_bytes(self.task.request_for(session.view())))]
            if any(entry[k] != self.initial[k] for k in ("prompt_tokens", "request_sha256", "native_sha256", "wire_request_sha256")):
                raise ValueError("first input differs from qualification")
        self.first_invocation = False
        row = super().invoke(session)
        if row:
            self.spending.observe_reply(session, len(session.pairs), row["elapsed_seconds"])
            self.log.append("request_spending_completed", dict(id=row["id"]),
                [self.store.put(f'calls/{row["id"]}-spending.json', canonical_json_bytes(self.spending.snapshot()))])
        return row

    def execute(self, session):
        if self.entered:
            raise ValueError("attempt already entered; no automatic restart")
        if tuple(session.checkers) != self.task.checks or session.reply_schema() != self.task.reply_schema():
            raise ValueError("rendered operations or check scopes differ from the executing session")
        self.entered = True
        self.active_session = session
        self.sent = session.requests_used
        try:
            return super().execute(session)
        except (SpendingStop, self.task.base.ResponseFailure) as problem:
            reason = problem.reason if isinstance(problem, SpendingStop) else getattr(problem, "spending_reason", None)
            if reason is None:
                raise
            # No final reply is recovered from an interrupted response. Previously
            # committed work and exact partial transport remain in the archive.
            self.snapshot(session, "spending-stop")
            result = dict(disposition="spending_limit", reason=reason, sent_requests=self.sent,
                actual_operations=session.calls_used, candidate_id=session.candidate.candidate_id,
                current_check=session.check_state(), submitted=session.submitted,
                spending=self.spending.snapshot())
            self.log.append("task_loop_completed", result, [])
            return result
