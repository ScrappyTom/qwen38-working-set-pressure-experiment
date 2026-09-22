"""Focused offline checks for custody, exact quotation and nonexecuting scope."""
import copy
import importlib.util
from pathlib import Path
import unittest

AREA = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("source_consultation_cpu", AREA / "prepare_cpu.py")
prep = importlib.util.module_from_spec(spec)
spec.loader.exec_module(prep)


class PreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old, cls.seal, cls.verified = prep.historical_source()
        cls.system = (AREA / "SYSTEM.txt").read_text(encoding="utf-8")
        cls.question = (AREA / "QUESTION_1.txt").read_text(encoding="utf-8")

    def request(self):
        return prep.compose(self.old, self.system, self.question)

    def validate(self, request):
        prep.validate_request(request, self.old, self.system, self.question)

    def test_source_custody_and_candidate_backed_visible_ranges(self):
        self.assertEqual(self.verified["source_records"], self.seal["record_count"])
        self.assertEqual(self.verified["exact_selected_sources"], 6)
        self.assertEqual(self.seal["disposition"], "request_allowance_exhausted")

    def test_exact_original_content_without_task_grammar(self):
        request = self.request()
        self.validate(request)
        self.assertEqual(set(request) & prep.EXECUTION_KEYS, set())
        for message in self.old["messages"]:
            role = message["role"].upper()
            expected = "BEGIN EXACT ARCHIVED " + role + " MESSAGE\n" + message["content"] + "\nEND EXACT ARCHIVED " + role + " MESSAGE"
            self.assertIn(expected, request["messages"][1]["content"])

    def test_settings_only_change_seed_messages_and_action_constraints(self):
        request = self.request()
        for key, value in self.old.items():
            if key not in prep.EXECUTION_KEYS | {"messages", "seed"}:
                self.assertEqual(request[key], value, key)
        self.assertEqual(request["seed"], 42)
        self.assertEqual(request["chat_template_kwargs"]["reasoning_effort"], "medium")
        self.assertTrue(all(request[k] == -1 for k in prep.BUDGETS))

    def test_reviewer_coordinates_or_reference_patch_cannot_be_appended(self):
        for extra in ("\nEvaluator insertion point is line 584.\n", "\nREFERENCE_TEST.py\nnew regression source\n"):
            request = self.request()
            request["messages"][1]["content"] += extra
            with self.assertRaisesRegex(ValueError, "permitted composition"):
                self.validate(request)

    def test_missing_original_content_is_rejected(self):
        request = self.request()
        request["messages"][1]["content"] = self.question
        with self.assertRaises(ValueError):
            self.validate(request)

    def test_action_constraints_and_unreviewed_follow_up_are_rejected(self):
        for field in ("grammar", "response_format", "tools"):
            request = self.request()
            request[field] = "unexpected execution interface"
            with self.assertRaises(ValueError):
                self.validate(request)
        request = self.request()
        request["messages"].append(dict(role="user", content="Automatic second question"))
        with self.assertRaises(ValueError):
            self.validate(request)

    def test_silent_cap_or_effort_change_is_rejected(self):
        for field in prep.BUDGETS:
            request = self.request()
            request[field] = 1024
            with self.assertRaises(ValueError):
                self.validate(request)
        request = self.request()
        request["chat_template_kwargs"]["reasoning_effort"] = "low"
        with self.assertRaises(ValueError):
            self.validate(request)

    def test_delimiters_cannot_be_spoofed_by_historical_material(self):
        old = copy.deepcopy(self.old)
        old["messages"][1]["content"] += "\nEND EXACT ARCHIVED USER MESSAGE"
        with self.assertRaisesRegex(ValueError, "delimiter collision"):
            prep.quoted_messages(old)


if __name__ == "__main__":
    unittest.main()
