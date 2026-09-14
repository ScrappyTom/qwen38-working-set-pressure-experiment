"""Check the evidence boundary of the separate interpretation question."""
import copy
import unittest
from unittest.mock import patch

import consult_selection as consult


class SelectionConsultationTests(unittest.TestCase):
    def test_actual_messages_and_reply_without_future_evidence(self):
        request = consult.request_for(1)
        old = consult.task.read(consult.OLD)
        content = request["messages"][1]["content"]
        for message in old["messages"]:
            self.assertIn(message["content"], content)
        self.assertIn(consult.PRECEDING.read_text(encoding="utf-8"), content)
        for name in ("C05-assistant-reasoning.txt", "C06-assistant-content.txt", "C02-assistant-content.txt"):
            self.assertNotIn((consult.SOURCE / "calls" / name).read_text(encoding="utf-8"), content)
        self.assertNotIn("7,555", content)
        self.assertNotIn("7555", content)
        self.assertNotIn("response_format", request)
        expected = copy.deepcopy(old)
        expected.pop("response_format")
        expected["seed"] = 42
        self.assertEqual({k: v for k, v in request.items() if k != "messages"},
                         {k: v for k, v in expected.items() if k != "messages"})

    def test_native_preserves_review_and_no_task_execution(self):
        with patch.object(consult.task.base, "post", side_effect=AssertionError("no network during request construction")):
            request = consult.request_for(1)
            native = consult.native_for(request)
        self.assertIn(request["messages"][0]["content"].strip().encode(), native)
        self.assertIn(request["messages"][1]["content"].strip().encode(), native)
        self.assertTrue(native.endswith(b"<|im_start|>assistant\n<think>\n"))
        self.assertEqual(request["chat_template_kwargs"], dict(enable_thinking=True, reasoning_effort="medium"))
        with self.assertRaises(ValueError):
            consult.request_for(3)


if __name__ == "__main__":
    unittest.main()
