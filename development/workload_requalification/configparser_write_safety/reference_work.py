"""Evaluator-only route; no contents are included in the actor's task material."""
import material

TESTS = '''import configparser
import io
import unittest


class WriteSafetyTests(unittest.TestCase):
    def test_rejects_ambiguous_option_names(self):
        for cls in (configparser.ConfigParser, configparser.RawConfigParser):
            for key in ('a=b', 'a:b', '[section]'):
                with self.subTest(parser=cls.__name__, key=key):
                    parser = cls()
                    parser['settings'] = {key: 'value'}
                    with self.assertRaises(configparser.InvalidWriteError):
                        parser.write(io.StringIO())

    def test_custom_delimiter_keeps_colon_and_multiline_values(self):
        parser = configparser.ConfigParser(delimiters=('->',))
        parser['settings'] = {'a:b': 'one\\ntwo'}
        output = io.StringIO()
        parser.write(output)
        restored = configparser.ConfigParser(delimiters=('->',))
        restored.read_string(output.getvalue())
        self.assertEqual(dict(restored['settings']), {'a:b': 'one\\ntwo'})
        parser.set('settings', 'a->b', 'value')
        with self.assertRaises(configparser.InvalidWriteError):
            parser.write(io.StringIO())
'''


def documentation():
    original = material.baseline_files()[material.DOC].decode()
    marker = '.. exception:: MultilineContinuationError'
    assert original.count(marker) == 1
    return original.replace(marker,
        '.. exception:: InvalidWriteError\n\n'
        '   Raised by :meth:`ConfigParser.write` when an option name begins with\n'
        '   the parser\'s section-header pattern or contains one of its configured\n'
        '   delimiters. These checks apply to defaults and named sections. They do\n'
        '   not promise that every custom parser configuration round-trips, or that\n'
        '   the output stream is unchanged when writing fails.\n\n' + marker).encode()


def files():
    return {**material.starting_files(), material.LIBRARY: material.reference_library(),
            material.NEW_TESTS: TESTS.encode(), material.DOC: documentation()}
