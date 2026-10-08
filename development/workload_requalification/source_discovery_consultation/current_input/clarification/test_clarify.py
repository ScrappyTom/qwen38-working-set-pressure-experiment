"""Qualify evidence inclusion, unchanged policy and the nonexecuting boundary."""
import json
import unittest
import clarify


class ClarificationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old, cls.view, cls.source = clarify.reviewed_material()
        cls.request = clarify.request_for(2, clarify.FOLLOW)
        cls.user = cls.request['messages'][1]['content']

    def test_exact_evidence_with_no_private_draft_or_task_completion(self):
        for value in (self.old['messages'][0]['content'], self.view['task'],
                      json.dumps(self.source, ensure_ascii=False, indent=2),
                      (clarify.FIRST/'calls/D1-assistant-content.txt').read_text(encoding='utf-8'),
                      (clarify.AREA/'SOURCE_FACTS.json').read_text(encoding='utf-8')):
            self.assertIn(value, self.user)
        self.assertNotIn(self.old['messages'][1]['content'], self.user)
        self.assertNotIn((clarify.FIRST/'calls/D1-assistant-reasoning.txt').read_text(encoding='utf-8'), self.user)
        self.assertFalse(hasattr(clarify.dialogue.task, 'process_reply'))
        self.assertFalse(clarify.first.composition.EXECUTION_KEYS & self.request.keys())

    def test_policy_and_native_template(self):
        for key, value in self.old.items():
            if key not in clarify.first.composition.EXECUTION_KEYS | {'messages', 'seed'}:
                self.assertEqual(self.request[key], value, key)
        self.assertEqual(self.request['seed'], 42)
        self.assertTrue(clarify.first.native_for(self.request).endswith(b'<|im_start|>assistant\n<think>\n'))

    def test_only_the_one_reviewed_followup(self):
        for turn, follow in ((1, clarify.FOLLOW), (2, None), (3, clarify.FOLLOW)):
            with self.assertRaises(ValueError):
                clarify.request_for(turn, follow)


if __name__ == '__main__':
    unittest.main()
