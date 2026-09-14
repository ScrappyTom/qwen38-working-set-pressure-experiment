"""Regression boundaries observed in the completed effort comparison."""
import copy
import unittest

from test_working_session import session, act, read, edit, cheap_count
from working_set_exp.contribution_reply import process_reply


class SourceUnionTests(unittest.TestCase):
    def setUp(self):
        self.s = session({"app.py": b"one\ntwo\nthree\nfour\nfive\n"})

    def spans(self, sources):
        return [(s["returned_start_line"], s["returned_end_line"]) for s in sources]

    def test_contained_feedback_is_not_repeated_and_cross_boundary_edit_works(self):
        read(self.s, first=1, last=5)
        read(self.s, first=3, last=3)
        feedback = copy.deepcopy(self.s.last)
        view = self.s.view()
        self.assertEqual(self.spans(view["working_set"]["sources"]), [(1, 2), (4, 5)])
        self.assertEqual(view["latest_feedback"], feedback)
        self.assertEqual(self.spans(self.s.sources()), [(1, 5)])
        self.assertTrue(edit(self.s, "two\nthree\nfour", "replacement")["accepted"])
        self.assertEqual(self.s.candidate.file_map["app.py"], b"one\nreplacement\nfive\n")

    def test_adjacent_feedback_then_navigation_preserves_source_union(self):
        read(self.s, first=1, last=2)
        read(self.s, first=3, last=5)
        self.assertEqual(self.spans(self.s.view()["working_set"]["sources"]), [(1, 2)])
        act(self.s, dict(action="tree", path=".", depth=1))
        self.assertEqual(self.spans(self.s.view()["working_set"]["sources"]), [(1, 5)])

    def test_multiple_overlapping_feedback_regions(self):
        result = act(self.s, dict(action="work_on", sources=[
            dict(path="app.py", start_line=1, end_line=3),
            dict(path="app.py", start_line=3, end_line=5)], results=[]))
        self.assertEqual(self.s.view()["working_set"]["sources"], [])
        self.assertEqual(self.s.last["result"], result)
        self.assertTrue(edit(self.s, "two\nthree\nfour", "joined")["accepted"])

    def test_unread_gap_cannot_be_bridged(self):
        act(self.s, dict(action="work_on", sources=[
            dict(path="app.py", start_line=1, end_line=2),
            dict(path="app.py", start_line=4, end_line=5)], results=[]))
        candidate = self.s.candidate
        self.assertFalse(edit(self.s, "two\nthree\nfour", "hidden")["accepted"])
        self.assertEqual(self.s.candidate, candidate)

    def test_stale_or_inexact_fragment_cannot_hide_or_authorize_source(self):
        read(self.s, first=1, last=5)
        for field, bad in (("content", "invented"), ("candidate_id", "stale"),
                           ("file_sha256", "stale"), ("returned_end_line", 99)):
            with self.subTest(field=field):
                s = self.s.clone()
                s.last = copy.deepcopy(self.s.last)
                s.last["result"]["source"][field] = bad
                self.assertEqual(self.spans(s.view()["working_set"]["sources"]), [(1, 5)])
                s.delivered_sources = [s.last["result"]["source"]]
                result = s.execute(dict(action="patch", path="app.py", old="two", new="bad",
                    expected_candidate_id=s.candidate.candidate_id,
                    expected_file_sha256=s.candidate.file_sha256("app.py")), cheap_count)
                self.assertFalse(result["accepted"])

    def test_empty_and_no_final_newline(self):
        for data, old, new in ((b"", "", "first"), (b"one\ntwo\nthree", "two\nthree", "last")):
            with self.subTest(data=data):
                s = session({"app.py": data})
                read(s)
                read(s, first=1 if not data else 3, last=0)
                self.assertTrue(edit(s, old, new)["accepted"])


class RequestAllowanceTests(unittest.TestCase):
    def configured(self, count=2):
        s = session()
        s.request_limit = count
        return s

    def dispatch(self, s, reply):
        s.mark_delivered(s.view())
        s.begin_request()
        return process_reply(s, reply, cheap_count, [])

    def test_one_request_can_run_two_operations_and_last_request_can_submit(self):
        s = self.configured()
        read(s)
        self.assertEqual(s.view()["allowance"]["requests_remaining"], 2)
        result = self.dispatch(s, dict(discussion="", operation=dict(action="patch", path="app.py",
            old="value = 1", new="value = 2", expected_candidate_id=s.candidate.candidate_id,
            expected_file_sha256=s.candidate.file_sha256("app.py")), check_after="public"))
        self.assertEqual(len(result["operations"]), 2)
        self.assertTrue(result["operations"][1]["result"]["passed"])
        self.assertEqual(s.requests_used, 1)
        self.assertEqual(s.calls_used, 3)
        self.dispatch(s, dict(discussion="", operation=dict(action="submit", expected_candidate_id=s.candidate.candidate_id)))
        self.assertTrue(s.submitted)
        self.assertEqual(s.view()["allowance"]["requests_remaining"], 0)
        with self.assertRaises(ValueError):
            s.begin_request()

    def test_rejected_operation_consumes_one_request_and_action(self):
        s = self.configured(1)
        result = self.dispatch(s, dict(discussion="", operation=dict(action="patch", path="app.py",
            old="value = 1", new="value = 2", expected_candidate_id=s.candidate.candidate_id,
            expected_file_sha256=s.candidate.file_sha256("app.py")), check_after="public"))
        self.assertFalse(result["operations"][0]["result"]["accepted"])
        self.assertEqual((s.requests_used, s.calls_used), (1, 1))
        with self.assertRaises(ValueError):
            s.begin_request()

    def test_discussion_only_consumes_request_without_operation(self):
        s = self.configured(1)
        result = self.dispatch(s, dict(discussion="Stopping here."))
        self.assertFalse(result["executed"])
        self.assertEqual((s.requests_used, s.calls_used), (1, 0))

    def test_legacy_session_does_not_invent_a_request_limit(self):
        s = session()
        self.assertNotIn("requests_remaining", s.view()["allowance"])
        s.begin_request()
        self.assertEqual(s.requests_used, 0)


if __name__ == "__main__":
    unittest.main()
