import unittest

from working_set_exp.thinking_grammar import OPEN_SUFFIX, require_open_thinking, with_thinking


class ThinkingGrammarTests(unittest.TestCase):
    def test_requires_actual_open_prefix(self):
        require_open_thinking(b'instructions\n' + OPEN_SUFFIX)
        for raw in (b'', OPEN_SUFFIX + b'</think>\n', b'<think>\n'):
            with self.assertRaises(ValueError):
                require_open_thinking(raw)

    def test_refuses_unknown_or_already_wrapped_root(self):
        for grammar in ('x ::= "a"', 'root ::= "a"\nroot ::= "b"',
                        'root ::= root "a"', 'channel-other ::= "a"\nroot ::= "b"'):
            with self.assertRaises(ValueError):
                with_thinking(grammar)

    def test_preserves_final_productions(self):
        original = 'root ::= reply\nreply ::= "ok"\n'
        fixed = with_thinking(original)
        self.assertTrue(fixed.startswith('channel-final ::= reply\nreply ::= "ok"\n'))
        self.assertIn('channel-think-7 ::= ">" channel-space channel-final', fixed)


if __name__ == '__main__':
    unittest.main()
