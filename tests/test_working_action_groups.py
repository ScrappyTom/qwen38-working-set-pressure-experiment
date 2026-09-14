"""Saved proposals can accompany exact source without becoming executed work."""
import copy
import json
import unittest

from test_working_session import session, act, read, edit
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes


SPAN = dict(path="app.py", start_line=1, end_line=0)


def rejected_proposal(s):
    """Create a real capacity-rejected proposal with still-current guards."""
    read(s)
    before = s.candidate
    proposal = dict(action="patch", path="app.py", old="value = 1", new="value = 2",
                    expected_candidate_id=before.candidate_id,
                    expected_file_sha256=before.file_sha256("app.py"))
    result = act(s, proposal, lambda view: 999999 if view["candidate_id"] != before.candidate_id else 1000)
    assert not result["accepted"] and s.candidate == before
    return proposal, f"EVT-{len(s.pairs):04d}", f"RES-{len(s.pairs):04d}"


def group(s, sources, handles, meter=lambda view: 1000):
    return act(s, dict(action="work_on", sources=sources, results=handles), meter)


class WorkingActionGroupTests(unittest.TestCase):
    def test_rejected_proposal_and_result_join_source_then_exact_proposal_executes(self):
        s = session()
        proposal, event, result_handle = rejected_proposal(s)
        before, pairs = s.candidate, copy.deepcopy(s.pairs)
        result = group(s, [SPAN], [event, result_handle])
        self.assertTrue(result["accepted"])
        self.assertEqual(s.candidate, before)
        self.assertEqual(s.pairs[:-1], pairs)
        self.assertEqual(s.diffs, {})
        self.assertFalse(s.submitted)
        self.assertIsNone(s.check_state())
        pages = {p["handle"]: p for p in result["saved_results"]}
        for handle in (event, result_handle):
            page = pages[handle]
            self.assertEqual(page["exact_utf8"].encode(), s.payload(handle))
            self.assertEqual(page["total_bytes"], len(s.payload(handle)))
            self.assertEqual(page["sha256"], sha256_bytes(s.payload(handle)))
            self.assertEqual(page["offset"], 0)
            self.assertIsNone(page["next_offset"])
        self.assertEqual(json.loads(pages[event]["exact_utf8"]), proposal)
        self.assertFalse(json.loads(pages[result_handle]["exact_utf8"])["accepted"])
        act(s, dict(action="tree", path=".", offset=0, limit=8))
        self.assertEqual(s.saved, pages)
        self.assertTrue(act(s, json.loads(s.saved[event]["exact_utf8"]))["accepted"])
        self.assertEqual(s.candidate.file_map["app.py"], b"value = 2\n")
        self.assertEqual(s.saved[event], pages[event])
        self.assertEqual(s.sources()[0]["content"], "value = 2\n")

    def test_action_text_without_current_source_does_not_authorize_edit(self):
        s = session()
        proposal, event, _ = rejected_proposal(s)
        self.assertTrue(group(s, [], [event])["accepted"])
        before = s.candidate
        self.assertFalse(act(s, proposal)["accepted"])
        self.assertEqual(s.candidate, before)
        self.assertEqual(s.delivered_sources, [])

    def test_stale_candidate_and_file_guards_are_not_refreshed_by_selection(self):
        for path in ("other.py", "app.py"):
            with self.subTest(changed_file=path):
                s = session({"app.py": b"value = 1\nother = 0\n", "other.py": b"other = 0\n"})
                proposal, event, _ = rejected_proposal(s)
                read(s, path)
                self.assertTrue(edit(s, "other = 0", "other = 1", path)["accepted"])
                current = s.candidate
                self.assertTrue(group(s, [SPAN], [event])["accepted"])
                self.assertEqual(json.loads(s.saved[event]["exact_utf8"]), proposal)
                self.assertFalse(act(s, proposal)["accepted"])
                if path == "app.py":
                    candidate_only_refreshed = {**proposal, "expected_candidate_id": current.candidate_id}
                    self.assertFalse(act(s, candidate_only_refreshed)["accepted"])
                self.assertEqual(s.candidate, current)
                self.assertEqual(s.payload(event), canonical_json_bytes(proposal))

    def test_oversized_group_rejects_without_partial_action_or_lost_selection(self):
        s = session()
        _, event, result_handle = rejected_proposal(s)
        self.assertTrue(group(s, [SPAN], [result_handle])["accepted"])
        before = s.candidate, copy.deepcopy(s.ranges), copy.deepcopy(s.saved), copy.deepcopy(s.pairs)
        def no_room(view):
            pages = view["working_set"]["saved_results"] + (view.get("latest_feedback") or {}).get("result", {}).get("saved_results", [])
            return 999999 if any(p["handle"] == event for p in pages) else 1000
        self.assertFalse(group(s, [SPAN], [event], no_room)["accepted"])
        self.assertEqual((s.candidate, s.ranges, s.saved, s.pairs[:-1]), before)
        self.assertNotIn(event, s.saved)
        self.assertEqual(s.payload(event), canonical_json_bytes(before[3][1]["response"]))

    def test_replacement_releases_selected_action_but_preserves_archive(self):
        s = session()
        proposal, event, _ = rejected_proposal(s)
        self.assertTrue(group(s, [SPAN], [event])["accepted"])
        self.assertTrue(group(s, [], [])["accepted"])
        self.assertEqual(s.saved, {})
        self.assertEqual(s.ranges, [])
        self.assertEqual(s.payload(event), canonical_json_bytes(proposal))

    def test_invalid_or_unavailable_handles_reject_without_selection_change(self):
        for handle in ("EVT-0000", "EVT-9999", "EVT-02", "ACT-0002", "RES-02"):
            with self.subTest(handle=handle):
                s = session()
                rejected_proposal(s)
                ranges = copy.deepcopy(s.ranges)
                self.assertFalse(group(s, [], [handle])["accepted"])
                self.assertEqual(s.ranges, ranges)
                self.assertEqual(s.saved, {})


if __name__ == "__main__":
    unittest.main()
