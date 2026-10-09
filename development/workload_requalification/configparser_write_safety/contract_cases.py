"""Independent behavior cases, executed through the public parser API."""
import io
import re
import unittest


class WriteSafetyContract(unittest.TestCase):
    library = None

    def parsers(self, **kwargs):
        for cls in (self.library.ConfigParser, self.library.RawConfigParser):
            yield cls(**kwargs)

    def reject(self, parser, key, *, section='settings', value='value', space=True):
        if section != parser.default_section:
            parser.add_section(section)
        parser.set(section, key, value)
        with self.assertRaises(self.library.InvalidWriteError) as caught:
            parser.write(io.StringIO(), space_around_delimiters=space)
        self.assertIs(type(caught.exception), self.library.InvalidWriteError)
        self.assertIn(key, str(caught.exception))
        self.assertTrue(str(caught.exception))

    def test_public_exception(self):
        self.assertTrue(issubclass(self.library.InvalidWriteError, self.library.Error))
        self.assertIn('InvalidWriteError', self.library.__all__)
        self.assertEqual(str(self.library.InvalidWriteError('bad key')), 'bad key')

    def test_section_header_prefix(self):
        for parser in self.parsers():
            for key in ('[new section]', '[new]suffix'):
                with self.subTest(parser=type(parser).__name__, key=key):
                    self.reject(type(parser)(), key)

    def test_every_configured_delimiter(self):
        for cls in (self.library.ConfigParser, self.library.RawConfigParser):
            for delimiter in ('=', ':'):
                for space in (True, False):
                    with self.subTest(parser=cls.__name__, delimiter=delimiter, space=space):
                        self.reject(cls(), 'first'+delimiter+'second', space=space)

    def test_multicharacter_delimiters(self):
        for cls in (self.library.ConfigParser, self.library.RawConfigParser):
            for delimiter in ('->', '::'):
                with self.subTest(parser=cls.__name__, delimiter=delimiter):
                    self.reject(cls(delimiters=('->', '::')), 'first'+delimiter+'second')

    def test_default_section(self):
        for parser in self.parsers(default_section='common'):
            with self.subTest(parser=type(parser).__name__):
                self.reject(parser, 'a:b', section='common')

    def test_valueless_options(self):
        for cls in (self.library.ConfigParser, self.library.RawConfigParser):
            for key in ('a=b', '[looks like section]'):
                with self.subTest(parser=cls.__name__, key=key):
                    self.reject(cls(allow_no_value=True), key, value=None)

    def test_custom_section_pattern(self):
        for parser in self.parsers():
            parser.SECTCRE = re.compile(r'<(?P<header>[^>]+)>')
            with self.subTest(parser=type(parser).__name__):
                self.reject(parser, '<group>suffix')

    def test_section_pattern_must_match_start(self):
        for parser in self.parsers():
            parser['settings'] = {'prefix[group]': 'kept', '[unclosed': 'also kept'}
            out = io.StringIO()
            parser.write(out)
            restored = type(parser)()
            restored.read_string(out.getvalue())
            self.assertEqual(dict(restored['settings']), dict(parser['settings']))

    def test_unconfigured_delimiters_are_ordinary_key_characters(self):
        for parser in self.parsers(delimiters=('=',)):
            parser['settings'] = {'first:second': 'third:fourth'}
            out = io.StringIO()
            parser.write(out)
            restored = type(parser)(delimiters=('=',))
            restored.read_string(out.getvalue())
            self.assertEqual(restored['settings']['first:second'], 'third:fourth')

    def test_multicharacter_delimiter_fragments_remain_valid(self):
        for parser in self.parsers(delimiters=('->', '::')):
            parser['settings'] = {'a-b': 'one', 'c>d': 'two', 'e:f': 'three'}
            out = io.StringIO()
            parser.write(out, space_around_delimiters=False)
            restored = type(parser)(delimiters=('->', '::'))
            restored.read_string(out.getvalue())
            self.assertEqual(dict(restored['settings']), dict(parser['settings']))

    def test_values_formatting_and_valueless_round_trip(self):
        for parser in self.parsers(allow_no_value=True):
            parser['DEFAULT'] = {'base': 'left=right:middle'}
            parser['settings'] = {'key': 'first\nsecond', 'flag': None}
            for space in (True, False):
                with self.subTest(parser=type(parser).__name__, space=space):
                    out = io.StringIO()
                    parser.write(out, space_around_delimiters=space)
                    self.assertIn('key = first' if space else 'key=first', out.getvalue())
                    restored = type(parser)(allow_no_value=True)
                    restored.read_string(out.getvalue())
                    self.assertEqual(dict(restored['settings']), dict(parser['settings']))

    def test_existing_interpolation(self):
        parser = self.library.ConfigParser()
        parser['settings'] = {'base': 'value', 'derived': '%(base)s!'}
        out = io.StringIO()
        parser.write(out)
        restored = self.library.ConfigParser()
        restored.read_string(out.getvalue())
        self.assertEqual(restored['settings']['derived'], 'value!')
