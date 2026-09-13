import copy
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"scripts"))
import bounded_visibility_dialogue as dialogue


class VisibilityPreparationTests(unittest.TestCase):
    def test_exact_historical_messages_without_old_answer_or_execution_channel(self):
        old=dialogue.task.read(Path(str(dialogue.OLD_STEM)+"-endpoint-request.json"))
        request=dialogue.request_for(1)
        self.assertNotIn("response_format",request)
        self.assertNotIn("tools",request)
        self.assertEqual([m["role"] for m in request["messages"]],["system","user"])
        for message in old["messages"]:
            self.assertIn(message["content"],request["messages"][1]["content"])
        old_answer=(dialogue.task.RUN/"calls/C08-assistant-content.txt").read_text()
        self.assertNotIn(old_answer,request["messages"][1]["content"])
        for key in set(old)-{"messages","response_format","seed"}:
            self.assertEqual(request[key],old[key])
        self.assertEqual(request["seed"],42)
        self.assertEqual(request["chat_template_kwargs"],dict(enable_thinking=True,reasoning_effort="xhigh"))

    def test_native_envelope_preserves_exact_new_messages(self):
        request=dialogue.request_for(1)
        native=dialogue.native_for(request)
        for message in request["messages"]:
            self.assertIn(message["content"].strip().encode(),native)
        self.assertTrue(native.endswith(b"<|im_start|>assistant\n<think>\n"))
        wrong=copy.deepcopy(request);wrong["temperature"]=0.1
        with self.assertRaisesRegex(ValueError,"settings drift"):
            dialogue.native_for(wrong)


if __name__ == "__main__":
    unittest.main()
