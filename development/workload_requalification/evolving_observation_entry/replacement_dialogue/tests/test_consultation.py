"""Protect exact quotation and the absence of task execution/answer leakage."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import consult


class CompositionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.old, cls.reply = consult.original()
        cls.system = (consult.AREA / 'SYSTEM.txt').read_text(encoding='utf-8')
        cls.question = (consult.AREA / 'QUESTION_1.txt').read_text(encoding='utf-8')

    def test_exact_only_declared_quoted_evidence(self):
        request = consult.compose(self.old, self.reply, self.system, self.question)
        consult.validate(request, self.old, self.reply, self.system, self.question)
        self.assertFalse(consult.composition.EXECUTION_KEYS & request.keys())
        self.assertEqual(len(request['messages']), 2)
        for message in self.old['messages']:
            self.assertIn(message['content'], request['messages'][1]['content'])
        self.assertIn(self.reply, request['messages'][1]['content'])
        self.assertTrue(consult.native_for(request).endswith(b'<|im_start|>assistant\n<think>\n'))

    def test_extra_outcome_and_policy_changes_rejected(self):
        request = consult.compose(self.old, self.reply, self.system, self.question)
        for field in ('messages', 'max_tokens', 'grammar'):
            changed = copy.deepcopy(request)
            if field == 'messages':
                changed[field][1]['content'] += '\nLater result: accepted'
            else:
                changed[field] = 512 if field == 'max_tokens' else 'root ::= "x"'
            with self.assertRaises(ValueError):
                consult.validate(changed, self.old, self.reply, self.system, self.question)

    def test_no_automatic_clarification(self):
        with self.assertRaises(ValueError):
            consult.request_for(2, consult.AREA / 'QUESTION_1.txt')


if __name__ == '__main__':
    unittest.main()
