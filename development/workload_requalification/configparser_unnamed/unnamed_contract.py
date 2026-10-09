"""Independent public-API feature and saved-work integration obligations."""
import io
import unittest


class UnnamedContract(unittest.TestCase):
    library = None

    def parsers(self, **kwargs):
        for cls in (self.library.ConfigParser, self.library.RawConfigParser):
            yield cls(allow_unnamed_section=True, **kwargs)

    def test_exported_api(self):
        for name in ('UNNAMED_SECTION', 'UnnamedSectionDisabledError'):
            self.assertIn(name, self.library.__all__)
        self.assertNotIsInstance(self.library.UNNAMED_SECTION, str)
        self.assertIsNotNone(self.library.UNNAMED_SECTION)
        self.assertTrue(issubclass(self.library.UnnamedSectionDisabledError, self.library.Error))

    def test_disabled_read_and_programmatic_add(self):
        for cls in (self.library.ConfigParser, self.library.RawConfigParser):
            with self.subTest(parser=cls.__name__):
                with self.assertRaises(self.library.MissingSectionHeaderError):
                    cls().read_string('key = value\n')
                with self.assertRaises(self.library.UnnamedSectionDisabledError):
                    cls().add_section(self.library.UNNAMED_SECTION)

    def test_headerless_prefix_is_separate(self):
        for parser in self.parsers():
            parser.read_string('; start\n\nKey = value\n[named]\nx = yes\n')
            self.assertEqual(parser[self.library.UNNAMED_SECTION]['key'], 'value')
            self.assertEqual(dict(parser['named']), {'x': 'yes'})
            self.assertEqual(parser.defaults(), {})
            self.assertIn(self.library.UNNAMED_SECTION, parser.sections())

    def test_file_and_multiple_source_merge(self):
        for parser in self.parsers():
            parser.read_file(io.StringIO('first=1\nreplace=old\n'), source='one.ini')
            parser.read_string('second=2\nreplace=new\n[named]\nthird=3\n')
            self.assertEqual(dict(parser[self.library.UNNAMED_SECTION]),
                {'first': '1', 'replace': 'new', 'second': '2'})
            self.assertEqual(parser.get('named', 'third'), '3')

    def test_duplicate_options_scope_and_lenient_override(self):
        for cls in (self.library.ConfigParser, self.library.RawConfigParser):
            with self.assertRaises(self.library.DuplicateOptionError):
                cls(allow_unnamed_section=True).read_string('Key=1\nkey=2\n')
            parser = cls(allow_unnamed_section=True, strict=False)
            parser.read_string('Key=1\nkey=2\n')
            self.assertEqual(parser.get(self.library.UNNAMED_SECTION, 'KEY'), '2')

    def test_programmatic_section_and_proxy(self):
        section = self.library.UNNAMED_SECTION
        for parser in self.parsers():
            parser.add_section(section)
            parser.set(section, 'Name', 'first')
            parser[section]['Name'] = 'second'
            self.assertEqual(parser.get(section, 'NAME'), 'second')
            with self.assertRaises(self.library.DuplicateSectionError):
                parser.add_section(section)
            self.assertTrue(parser.remove_section(section))
            self.assertFalse(parser.has_section(section))

    def test_dictionary_and_mapping_preserve_sentinel(self):
        section = self.library.UNNAMED_SECTION
        for parser in self.parsers():
            parser.read_dict({section: {'count': 7}, 22: {'size': 3}})
            self.assertEqual(parser.getint(section, 'count'), 7)
            self.assertEqual(parser.getint('22', 'size'), 3)
            self.assertNotIn(str(section), parser.sections())
            parser[section] = {'replacement': 'ok'}
            self.assertEqual(dict(parser[section]), {'replacement': 'ok'})
            self.assertIn('22', parser.sections())

    def test_defaults_and_interpolation_do_not_absorb_unnamed(self):
        parser = self.library.ConfigParser(allow_unnamed_section=True,
            defaults={'base': 'root'}, converters={'twice': lambda value: int(value)*2})
        parser.read_string('derived=%(base)s/file\nnumber=3\n[named]\nx=y\n')
        section = self.library.UNNAMED_SECTION
        self.assertEqual(parser.get(section, 'derived'), 'root/file')
        self.assertEqual(parser[section].gettwice('number'), 6)
        self.assertFalse(parser.has_option('named', 'derived'))
        self.assertEqual(parser.defaults(), {'base': 'root'})

    def test_writer_order_and_defaults_round_trip(self):
        section = self.library.UNNAMED_SECTION
        for parser in self.parsers(default_section='common'):
            parser['named'] = {'same': 'named'}
            parser['common'] = {'base': 'default'}
            parser.add_section(section)
            parser.set(section, 'same', 'unnamed')
            for space in (True, False):
                output = io.StringIO()
                parser.write(output, space_around_delimiters=space)
                text = output.getvalue()
                self.assertTrue(text.startswith('same = unnamed\n' if space else 'same=unnamed\n'), text)
                self.assertEqual(text.count('[named]'), 1)
                restored = type(parser)(allow_unnamed_section=True, default_section='common')
                restored.read_string(text)
                self.assertEqual(restored.defaults(), {'base': 'default'})
                self.assertEqual(dict(restored[section]), dict(parser[section]))
                self.assertEqual(dict(restored['named']), dict(parser['named']))

    def test_empty_unnamed_has_no_written_header(self):
        for parser in self.parsers():
            parser.add_section(self.library.UNNAMED_SECTION)
            parser.add_section('named')
            out = io.StringIO()
            parser.write(out)
            self.assertEqual(out.getvalue(), '[named]\n\n')

    def test_continuations_delimiters_and_valueless(self):
        for parser in self.parsers(allow_no_value=True, delimiters=('->',)):
            parser.read_string('text->first\n  second\nflag\n[named]\nx->y\n')
            section = self.library.UNNAMED_SECTION
            self.assertEqual(parser.get(section, 'text'), 'first\nsecond')
            self.assertIsNone(parser.get(section, 'flag'))
            out = io.StringIO()
            parser.write(out, space_around_delimiters=False)
            restored = type(parser)(allow_unnamed_section=True, allow_no_value=True, delimiters=('->',))
            restored.read_string(out.getvalue())
            self.assertEqual(dict(restored[section]), dict(parser[section]))

    def test_saved_multiline_error_also_in_unnamed(self):
        for parser in self.parsers(allow_no_value=True):
            with self.assertRaises(self.library.MultilineContinuationError) as caught:
                parser.read_string('flag\n  bad continuation\n', source='unnamed.ini')
            self.assertIs(type(caught.exception), self.library.MultilineContinuationError)
            self.assertEqual(caught.exception.args, ('unnamed.ini', 2, '  bad continuation\n'))

    def test_saved_write_guard_also_in_unnamed(self):
        for cls in (self.library.ConfigParser, self.library.RawConfigParser):
            for key in ('bad->key', '[pretend]section'):
                parser = cls(allow_unnamed_section=True, allow_no_value=True, delimiters=('->',))
                parser.add_section(self.library.UNNAMED_SECTION)
                parser.set(self.library.UNNAMED_SECTION, key, None)
                with self.assertRaises(self.library.InvalidWriteError) as caught:
                    parser.write(io.StringIO())
                self.assertIn(key, str(caught.exception))

    def test_ordinary_feature_disabled_behavior_unchanged(self):
        for cls in (self.library.ConfigParser, self.library.RawConfigParser):
            parser = cls()
            parser.read_dict({'DEFAULT': {'d': 'v'}, 'named': {'x': 'y'}})
            out = io.StringIO()
            parser.write(out)
            self.assertEqual(out.getvalue(), '[DEFAULT]\nd = v\n\n[named]\nx = y\n\n')
