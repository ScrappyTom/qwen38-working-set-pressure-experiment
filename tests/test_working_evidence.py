"""Exercise actual delivery/selection/edit sequences, including historical access."""
import unittest

from test_working_session import session, act, read, edit


def release(s):
    return act(s, dict(action="work_on", sources=[], results=[]))


def reopen(s, handle="RES-0001", meter=lambda view: 1000):
    return act(s, dict(action="reopen_result", handle=handle, offset=0), meter)


class WorkingEvidenceTests(unittest.TestCase):
    def test_complete_recovered_read_supports_edit_in_feedback_or_selection(self):
        for location in ("feedback", "selection"):
            with self.subTest(location=location):
                s = session()
                read(s)
                release(s)
                self.assertIsNone(reopen(s)["next_offset"])
                if location == "selection":
                    act(s, dict(action="tree", path=".", offset=0, limit=8))
                self.assertEqual(s.ranges, [])
                self.assertTrue(edit(s, "value = 1", "value = 2")["accepted"])
                self.assertEqual(s.candidate.file_map["app.py"], b"value = 2\n")

    def test_partial_serialized_read_is_not_credited(self):
        s = session()
        read(s)
        release(s)
        def meter(view):
            feedback = view.get("latest_feedback") or {}
            text = feedback.get("result", {}).get("exact_utf8", "")
            return 1000 if len(text) < 60 else 999999
        self.assertIsNotNone(reopen(s, meter=meter)["next_offset"])
        before = s.candidate
        self.assertFalse(edit(s, "value = 1", "value = 2")["accepted"])
        self.assertEqual(s.candidate, before)

    def test_recovered_stale_file_does_not_support_even_unchanged_fragment(self):
        s = session({"app.py": b"value = 1\nother = 0\n"})
        read(s)
        self.assertTrue(edit(s, "other = 0", "other = 1")["accepted"])
        release(s)
        reopen(s)
        before = s.candidate
        self.assertFalse(edit(s, "value = 1", "value = 2")["accepted"])
        self.assertEqual(s.candidate, before)

    def test_unchanged_file_survives_other_file_edit_but_stale_guard_does_not(self):
        s = session({"app.py": b"value = 1\n", "other.py": b"other = 0\n"})
        read(s)
        old = s.candidate
        read(s, "other.py")
        self.assertTrue(edit(s, "other = 0", "other = 1", "other.py")["accepted"])
        release(s)
        reopen(s)
        stale = dict(action="patch", path="app.py", old="value = 1", new="value = 2",
                     expected_candidate_id=old.candidate_id, expected_file_sha256=old.file_sha256("app.py"))
        self.assertFalse(act(s, stale)["accepted"])
        self.assertTrue(edit(s, "value = 1", "value = 2")["accepted"])

    def test_recovered_group_sources_support_edit(self):
        s = session()
        act(s, dict(action="work_on", sources=[dict(path="app.py", start_line=1, end_line=0)], results=[]))
        release(s)
        act(s, dict(action="work_on", sources=[], results=["RES-0001"]))
        self.assertTrue(edit(s, "value = 1", "value = 2")["accepted"])

    def test_legacy_read_and_incorrect_archived_content(self):
        for correct in (True, False):
            with self.subTest(correct=correct):
                base = session()
                source = base.source(dict(path="app.py", start_line=1, end_line=0))
                source.pop("kind")
                source["accepted"] = True
                if not correct:
                    source["content"] = "value = 1\nmade up\n"
                s = session(pairs=[dict(response=dict(action="read", path="app.py"), result=source)])
                reopen(s)
                self.assertEqual(edit(s, "value = 1", "value = 2")["accepted"], correct)

    def test_search_and_saved_action_are_not_exact_source_acquisitions(self):
        for handle in ("RES-0001", "EVT-0001"):
            with self.subTest(handle=handle):
                s = session()
                act(s, dict(action="search", path="app.py", query="value", offset=0, limit=8))
                name = "reopen_result" if handle.startswith("RES") else "reopen_event"
                act(s, dict(action=name, handle=handle, offset=0))
                self.assertFalse(edit(s, "value = 1", "value = 2")["accepted"])

    def test_search_query_identifies_recent_and_paged_history_after_feedback_changes(self):
        s = session()
        for query in ("value", "missing"):
            act(s, dict(action="search", path="app.py", query=query, offset=0, limit=8))
        act(s, dict(action="tree", path=".", offset=0, limit=8))
        rows = s.view()["recent_activity"][:2]
        self.assertEqual([r["query"] for r in rows], ["value", "missing"])
        self.assertNotIn("matches", rows[0])
        history = act(s, dict(action="history", before=3, path="app.py"))
        self.assertEqual([r["query"] for r in history["entries"]], ["missing", "value"])


if __name__ == "__main__":
    unittest.main()
