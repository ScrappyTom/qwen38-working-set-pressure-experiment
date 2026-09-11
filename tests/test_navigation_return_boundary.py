"""Directory discovery must not fail on a file-outline presentation limit."""
import copy
import unittest
from pathlib import Path

from working_set_exp.ecological_pilot_v2 import admitted_donor_candidate
from working_set_exp.candidate import Candidate
from working_set_exp.tools import SessionState, ToolExecutor


def host(candidate):
    return ToolExecutor(SessionState(candidate, stage="continuation"), required_full_reads=(),
                        prefork_checker=b"", public_checker=b"", final_target="__none__",
                        probe_id=None, probe_body=None, hierarchical_p0=True,
                        read_mode="maximal_bounded_page")


class NavigationReturnBoundaryTests(unittest.TestCase):
    def test_actual_donor_directory_survives_unrelated_long_signature(self):
        root = Path(__file__).resolve().parents[1]
        candidate = admitted_donor_candidate(root / "experiments/020_owner_controlled_ecological_pilot_v2/fresh_bank")
        executor = host(candidate)
        before = copy.deepcopy(executor.state)
        directory = executor.execute({"action":"p0_page", "path":"src/addressable_information_layer", "offset":0})
        self.assertTrue(directory["accepted"], directory)
        rows = {row["path"]:row for row in directory["entries"]}
        self.assertIn("src/addressable_information_layer/patching.py", rows)
        self.assertEqual(rows["src/addressable_information_layer/renderer.py"]["symbol_count"], 8)
        outline = executor.execute({"action":"p0_page", "path":"src/addressable_information_layer/renderer.py", "offset":0})
        self.assertEqual(outline, {"accepted":False, "error_code":"tool_rejected", "detail":"signature exceeds bound"})
        self.assertEqual(executor.state, before)
        read = executor.execute({"action":"read", "path":"src/addressable_information_layer/renderer.py", "start_line":1})
        self.assertTrue(read["accepted"], read)
        self.assertEqual(read["content"].encode(), candidate.file_map[read["path"]])

    def test_invalid_page_or_unparseable_source_is_a_normal_rejection(self):
        executor = host(Candidate.create({"src/broken.py":b"def broken(\n"}))
        before = copy.deepcopy(executor.state)
        for action in ({"action":"p0_page", "path":"src", "offset":-1},
                       {"action":"p0_page", "path":"src", "offset":0},
                       {"action":"p0_page", "path":"src/broken.py", "offset":0}):
            with self.subTest(action=action):
                result = executor.execute(action)
                self.assertFalse(result["accepted"])
                self.assertEqual(result["error_code"], "tool_rejected")
                self.assertEqual(executor.state, before)


if __name__ == "__main__":
    unittest.main()
