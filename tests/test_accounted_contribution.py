import json
import unittest

from working_set_exp.accounted_contribution import AccountedSession, process_reply, reply_schema
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes
from working_set_exp.working_session import INPUT_LIMIT, WorkingSession
from working_set_exp import working_view


class AccountedContributionTests(unittest.TestCase):
    def session(self, **kwargs):
        files = {"app.py": b"value = 2\n", "test_app.py": b"expected = 1\n", "guide.txt": b"Expected: 1\n"}
        tests = b"from app import value\nfrom test_app import expected\nassert value == expected, (value, expected)\n"
        examples = b"from pathlib import Path\nfrom app import value\nassert Path('guide.txt').read_text() == f'Expected: {value}\\n'\n"
        return AccountedSession(Candidate.create(files),
            {"tests": tests, "examples": examples, "public": tests + examples},
            "Extend tests and docs; the library is authoritative.",
            edit_checks={"test_app.py": "tests", "guide.txt": "public"}, call_limit=kwargs.pop("call_limit", 40),
            request_limit=20, **kwargs)

    def source(self, session, path):
        session.add_source(session.source(dict(path=path, start_line=1, end_line=0)))
        session.mark_delivered(session.view())

    def patch(self, session, path, new):
        return dict(action="patch", path=path, old=session.candidate.file_map[path].decode(), new=new,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256(path))

    def run_reply(self, session, reply, feedback=None, measure=lambda view: 700):
        session.mark_delivered(session.view())
        session.begin_request()
        return process_reply(session, reply, measure, feedback if feedback is not None else [])

    def test_actual_failed_check_correction_documentation_and_checked_submission(self):
        session = self.session()
        self.source(session, "test_app.py")
        original = session.candidate.candidate_id
        feedback = []
        wrong = self.run_reply(session, dict(discussion="Candidate expectation needs execution.",
            account="The expected value is provisional; compare it with actual execution.",
            operation=self.patch(session, "test_app.py", "expected = 3\n")), feedback)
        self.assertEqual([o["origin"] for o in wrong["operations"]],
                         ["model_authored_account", "model", "declared_host_policy"])
        check = wrong["operations"][-1]
        self.assertTrue(check["result"]["accepted"])
        self.assertFalse(check["result"]["passed"])
        self.assertEqual(check["action"]["expected_candidate_id"], session.candidate.candidate_id)
        self.assertEqual(session.candidate.file_map["test_app.py"], b"expected = 3\n")
        self.assertEqual(session.working_account()["input_candidate_id"], original)
        self.assertEqual(session.working_account()["written_during_request"], 1)
        self.assertEqual([r["sequence"] for r in feedback], [1, 2])
        self.assertEqual(session.last["result"], check["result"])
        self.assertEqual(session.requests_used, 1)
        self.assertEqual(session.calls_used, 3)

        fixed = self.run_reply(session, dict(discussion="Use the actual value.",
            account="The check reports value 2; correct the proposed test. Docs remain unfinished.",
            operation=self.patch(session, "test_app.py", "expected = 2\n")))
        self.assertTrue(fixed["operations"][-1]["result"]["passed"])
        self.assertTrue(session.scoped_check_state("tests")["applies_to_current"])
        self.assertIsNone(session.check_state())
        premature = self.run_reply(session, dict(discussion="Premature submission must not pass.",
            operation=dict(action="submit", expected_candidate_id=session.candidate.candidate_id)))
        self.assertFalse(premature["operations"][0]["result"]["accepted"])

        self.run_reply(session, dict(discussion="Change support while retaining the account.",
            operation=dict(action="work_on", sources=[dict(path="guide.txt", start_line=1, end_line=0)], results=[])))
        self.assertIn("Docs remain unfinished", session.working_account()["text"])
        done = self.run_reply(session, dict(discussion="Extend the guide from the observation.",
            operation=self.patch(session, "guide.txt", "Expected: 2\n")))
        self.assertEqual(done["operations"][-1]["action"]["check_id"], "public")
        self.assertTrue(done["operations"][-1]["result"]["passed"])
        self.assertTrue(session.check_state()["applies_to_current"])
        self.assertFalse(session.scoped_check_state("tests")["applies_to_current"])
        self.assertIn("Docs remain unfinished", session.working_account()["text"])  # no semantic auto-update
        self.assertEqual(session.candidate.file_map["test_app.py"], b"expected = 2\n")
        self.run_reply(session, dict(discussion="Use the current full check.",
            account="Tests and guide are now saved; public verification passes on this version.",
            operation=dict(action="submit", expected_candidate_id=session.candidate.candidate_id)))
        self.assertTrue(session.submitted)
        self.assertEqual(session.candidate.file_map["app.py"], b"value = 2\n")

    def test_account_revision_clear_exact_recovery_and_no_private_inference(self):
        session = self.session()
        self.run_reply(session, dict(discussion="PRIVATE_DISCUSSION_DO_NOT_PROMOTE", account="A provisional claim."))
        first = session.working_account()["action_handle"]
        self.run_reply(session, dict(discussion="Another explanation.", account="A corrected claim."))
        self.run_reply(session, dict(discussion="Clear.", account=""))
        self.assertEqual(session.working_account()["text"], "")
        self.assertEqual(json.loads(session.payload(first))["text"], "A provisional claim.")
        self.assertNotIn("PRIVATE_DISCUSSION_DO_NOT_PROMOTE", canonical_json_bytes(session.view()).decode())
        recovered = self.run_reply(session, dict(discussion="Recover the exact earlier account.",
            operation=dict(action="reopen_event", handle=first, offset=0)))
        self.assertIn("A provisional claim.", recovered["operations"][0]["result"]["exact_utf8"])
        self.assertEqual(session.working_account()["text"], "")

    def test_account_alone_does_not_establish_source_eligibility(self):
        session = self.session()
        before = session.candidate.candidate_id
        result = self.run_reply(session, dict(discussion="Account contains source-like text.",
            account="expected = 1\n", operation=self.patch(session, "test_app.py", "expected = 2\n")))
        self.assertFalse(result["operations"][-1]["result"]["accepted"])
        self.assertFalse(result["policy_check"]["executed"])
        self.assertEqual(session.candidate.candidate_id, before)
        self.assertEqual(session.working_account()["text"], "expected = 1\n")

    def test_oversized_account_is_rejected_without_truncation_or_associated_edit(self):
        session = self.session()
        self.source(session, "test_app.py")
        self.run_reply(session, dict(discussion="Initial.", account="Retained."))
        before = session.candidate.candidate_id
        def measure(view):
            return INPUT_LIMIT + 1 if view["working_account"]["text"].startswith("OVERSIZED") else 900
        large = "OVERSIZED" + "quoted \\\"text\" " * 900
        result = self.run_reply(session, dict(discussion="Rejected.", account=large,
            operation=self.patch(session, "test_app.py", "expected = 2\n")), measure=measure)
        self.assertEqual(len(result["operations"]), 1)
        self.assertFalse(result["operations"][0]["result"]["accepted"])
        self.assertEqual(session.working_account()["text"], "Retained.")
        self.assertEqual(session.candidate.candidate_id, before)
        self.assertEqual(json.loads(session.payload("EVT-0002"))["text"], large)
        self.assertFalse(session.delivery_blocked)

    def test_check_applicability_binds_scope_candidate_and_definition(self):
        session = self.session()
        check = dict(action="check", check_id="examples", expected_candidate_id=session.candidate.candidate_id)
        result = self.run_reply(session, dict(discussion="Actual example failure.", operation=check))
        self.assertTrue(result["operations"][0]["result"]["accepted"])
        self.assertFalse(result["operations"][0]["result"]["passed"])
        self.assertTrue(session.scoped_check_state("examples")["applies_to_current"])
        session.checkers["examples"] += b"# changed definition\n"
        self.assertFalse(session.scoped_check_state("examples")["applies_to_current"])
        self.assertIsNone(session.check_state())
        stale = self.run_reply(session, dict(discussion="Stale check request.",
            operation={**check, "expected_candidate_id": "0" * 64}))
        self.assertFalse(stale["operations"][0]["result"]["accepted"])

    def test_rejected_edit_skips_check_and_preserves_authored_account(self):
        session = self.session()
        self.source(session, "test_app.py")
        action = self.patch(session, "test_app.py", "expected = 2\n")
        action["expected_file_sha256"] = "0" * 64
        result = self.run_reply(session, dict(discussion="Stale edit.", account="Still provisional.", operation=action))
        self.assertEqual(len(result["operations"]), 2)
        self.assertFalse(result["policy_check"]["executed"])
        self.assertEqual(session.working_account()["text"], "Still provisional.")

    def test_reserve_complete_operation_allowance_before_any_mutation(self):
        session = self.session(call_limit=2)
        self.source(session, "test_app.py")
        reply = dict(discussion="Needs three operations.", account="Provisional.",
                     operation=self.patch(session, "test_app.py", "expected = 2\n"))
        with self.assertRaisesRegex(ValueError, "insufficient operation allowance"):
            self.run_reply(session, reply)
        self.assertEqual(session.pairs, [])
        self.assertIsNone(session.working_account())

    def test_actual_check_survives_full_feedback_failure(self):
        session = self.session()
        self.source(session, "test_app.py")
        def measure(view):
            result = view["latest_feedback"]["result"] if view["latest_feedback"] else {}
            return INPUT_LIMIT + 1 if "checked_candidate_id" in result else 500
        host = self.run_reply(session, dict(discussion="Check cannot be delivered.",
            operation=self.patch(session, "test_app.py", "expected = 2\n")), measure=measure)
        self.assertTrue(host["policy_check"]["executed"])
        self.assertTrue(session.delivery_blocked)
        self.assertTrue(session.pairs[-1]["result"]["passed"])
        self.assertEqual(session.candidate.file_map["test_app.py"], b"expected = 2\n")

    def test_delivered_account_and_policy_must_match_the_actual_view(self):
        session = self.session()
        view = session.view()
        view["working_account"] = dict(text="Invented")
        with self.assertRaisesRegex(ValueError, "delivered account"):
            session.mark_delivered(view)

    def test_old_accounts_do_not_accumulate_in_the_normal_view(self):
        session = self.session(call_limit=20000)
        for _ in range(10000):
            action = dict(action="record_account", text="Current question; unresolved.")
            session._record(action, session._ordinary(action))
        view = session.view()
        self.assertEqual(len(view["recent_activity"]), 6)
        self.assertEqual(canonical_json_bytes(view).decode().count("Current question; unresolved."), 1)
        self.assertLess(len(canonical_json_bytes(view)), 7000)

    def test_wire_schema_and_default_behavior_remain_distinct(self):
        schema = reply_schema({"tests": b"", "public": b""})
        request = {"response_format": schema, "messages": []}
        wire = json.loads(completion_request_bytes(request))
        for form in wire["response_format"]["json_schema"]["schema"]["oneOf"]:
            self.assertEqual(list(form["properties"]), form["required"])
        working_view.validate(dict(discussion="Record.", account="Unresolved."), schema["json_schema"]["schema"])
        with self.assertRaises(ValueError):
            working_view.validate(dict(discussion="Old optional check form.", operation={}, check_after="public"),
                                  schema["json_schema"]["schema"])
        old = WorkingSession(Candidate.create({"a.py": b"pass\n"}), b"pass\n", "legacy")
        self.assertNotIn("working_account", old.view())
        self.assertFalse(old.execute(dict(action="record_account", text="Not a legacy action."), lambda view: 500)["accepted"])


if __name__ == "__main__":
    unittest.main()
