"""A smaller read can add a source fragment and cost more complete input."""
import copy
import unittest

from test_working_session import session, act, read
from working_set_exp.working_session import INPUT_LIMIT, WorkingSession


class PageLayoutCapacityTests(unittest.TestCase):
    def prepared(self):
        s = session({"app.py": b"source line\n" * 77})
        read(s, first=1, last=20)
        return s

    def layout_cost(self, view):
        sources = view["working_set"]["sources"] + WorkingSession.feedback_sources(view["latest_feedback"])
        visible = {i for source in sources for i in range(source["returned_start_line"], source["returned_end_line"]+1)}
        # A proxy for the measured C03 geometry: already-visible content is
        # not charged again, but each serialized source fragment has overhead.
        return 23414 + 167*len(sources) + 14*(len(visible)-20)

    def test_interior_fitting_page_is_found_without_releasing_selected_source(self):
        s = self.prepared()
        prior = copy.deepcopy(s.ranges)
        result = act(s, dict(action="read", path="app.py", start_line=12, end_line=77), self.layout_cost)
        self.assertTrue(result["accepted"], result)
        self.assertEqual(result["source"]["returned_end_line"], 21)
        self.assertEqual(result["source"]["next_start_line"], 22)
        self.assertLessEqual(self.layout_cost(s.view()), INPUT_LIMIT)
        self.assertEqual(s.ranges, [dict(path="app.py", start_line=1, end_line=21)])
        self.assertEqual(prior, [dict(path="app.py", start_line=1, end_line=20)])
        self.assertEqual(s.calls_used, 2)

    def test_no_fitting_page_still_rejects_without_committing_source(self):
        s = self.prepared()
        prior = copy.deepcopy(s.ranges)
        def only_rejection_fits(view):
            return 500 if "error" in view["latest_feedback"]["result"] else INPUT_LIMIT+1
        result = act(s, dict(action="read", path="app.py", start_line=12, end_line=77), only_rejection_fits)
        self.assertFalse(result["accepted"])
        self.assertEqual(s.ranges, prior)
        self.assertEqual(s.calls_used, 2)

    def test_unrelated_file_ranges_do_not_become_read_coordinates(self):
        s = session({"app.py": b"source line\n"*77, "other.py": b"other\n"*20})
        read(s, "other.py", first=1, last=20)
        tested = []
        def too_large(view):
            source = view["latest_feedback"]["result"].get("source")
            if source:
                tested.append(source["returned_end_line"])
            return INPUT_LIMIT+1 if source else 500
        result = act(s, dict(action="read", path="app.py", start_line=12, end_line=77), too_large)
        self.assertFalse(result["accepted"])
        self.assertNotIn(20, tested)
        self.assertNotIn(21, tested)


if __name__ == "__main__":
    unittest.main()
