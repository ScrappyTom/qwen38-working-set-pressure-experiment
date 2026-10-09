"""Evaluator implementation only; never included in the actor's candidate/input."""
import unnamed_material as material

EXCEPTION = '''class UnnamedSectionDisabledError(Error):
    """Raised when unnamed section support has not been enabled."""

    def __init__(self):
        Error.__init__(self, 'Unnamed sections are disabled')


class _UnnamedSection:
    def __repr__(self):
        return '<UNNAMED_SECTION>'


UNNAMED_SECTION = _UnnamedSection()


'''

# Small independent integration into the actual saved older parser. No wholesale
# replacement with upstream, which changes unrelated existing behaviors.
CHANGES = [
    ('           "DEFAULTSECT", "MAX_INTERPOLATION_DEPTH")',
     '           "DEFAULTSECT", "MAX_INTERPOLATION_DEPTH",\n'
     '           "UNNAMED_SECTION", "UnnamedSectionDisabledError")'),
    ('class Interpolation:', EXCEPTION+'class Interpolation:'),
    ('                 interpolation=_UNSET, converters=_UNSET):',
     '                 interpolation=_UNSET, converters=_UNSET,\n'
     '                 allow_unnamed_section=False):'),
    ('        self._allow_no_value = allow_no_value',
     '        self._allow_no_value = allow_no_value\n'
     '        self._allow_unnamed_section = allow_unnamed_section'),
    ('        if section in self._sections:\n            raise DuplicateSectionError(section)',
     '        if section is UNNAMED_SECTION and not self._allow_unnamed_section:\n'
     '            raise UnnamedSectionDisabledError()\n'
     '        if section in self._sections:\n            raise DuplicateSectionError(section)'),
    ('            section = str(section)',
     '            if section is not UNNAMED_SECTION:\n                section = str(section)'),
    ('        if self._defaults:\n            self._write_section(fp, self.default_section,\n'
     '                                    self._defaults.items(), d)\n'
     '        for section in self._sections:\n            self._write_section(fp, section,\n'
     '                                self._sections[section].items(), d)',
     '        if self._sections.get(UNNAMED_SECTION):\n'
     '            self._write_section(fp, UNNAMED_SECTION,\n'
     '                                self._sections[UNNAMED_SECTION].items(), d)\n'
     '        if self._defaults:\n            self._write_section(fp, self.default_section,\n'
     '                                    self._defaults.items(), d)\n'
     '        for section in self._sections:\n'
     '            if section is not UNNAMED_SECTION:\n'
     '                self._write_section(fp, section,\n'
     '                                    self._sections[section].items(), d)'),
    ('        fp.write("[{}]\\n".format(section_name))',
     '        if section_name is not UNNAMED_SECTION:\n'
     '            fp.write("[{}]\\n".format(section_name))'),
    ('                # continuation line?',
     '                if (cursect is None and self._allow_unnamed_section\n'
     '                    and not self.SECTCRE.match(value)):\n'
     '                    sectname = UNNAMED_SECTION\n'
     '                    if sectname not in self._sections:\n'
     '                        self.add_section(sectname)\n'
     '                    cursect = self._sections[sectname]\n'
     '                    elements_added.add(sectname)\n'
     '                # continuation line?'),
    ('        if not isinstance(section, str):\n            raise TypeError("section names must be strings")',
     '        if section is UNNAMED_SECTION:\n'
     '            if not self._allow_unnamed_section:\n'
     '                raise UnnamedSectionDisabledError()\n'
     '        elif not isinstance(section, str):\n'
     '            raise TypeError("section names must be strings")'),
]


def library():
    text = material.baseline_files()[material.LIBRARY].decode()
    for old, new in CHANGES:
        assert text.count(old) == 1, old
        text = text.replace(old, new)
    return text.encode()


TESTS = '''import configparser
import io
import unittest


class UnnamedSectionTests(unittest.TestCase):
    def test_parse_and_named_isolation(self):
        p = configparser.ConfigParser(allow_unnamed_section=True)
        p.read_string('port=8080\\n[named]\\nname=service\\n')
        self.assertEqual(p[configparser.UNNAMED_SECTION].getint('port'), 8080)
        self.assertFalse(p.has_option('named', 'port'))

    def test_defaults_write_round_trip(self):
        p = configparser.ConfigParser(allow_unnamed_section=True)
        p['DEFAULT'] = {'base': 'one'}
        p[configparser.UNNAMED_SECTION] = {'local': 'two'}
        p['named'] = {'third': 'three'}
        out = io.StringIO()
        p.write(out)
        self.assertTrue(out.getvalue().startswith('local = two\\n'))
        q = configparser.ConfigParser(allow_unnamed_section=True)
        q.read_string(out.getvalue())
        self.assertEqual(q.defaults(), {'base': 'one'})
        self.assertEqual(dict(q[configparser.UNNAMED_SECTION]), {'base': 'one', 'local': 'two'})
        self.assertFalse(q.has_option('named', 'local'))

    def test_mapping_identity_and_replace(self):
        p = configparser.RawConfigParser(allow_unnamed_section=True)
        p.read_dict({configparser.UNNAMED_SECTION: {'old': 1}})
        p[configparser.UNNAMED_SECTION] = {'new': '2'}
        self.assertEqual(p.sections(), [configparser.UNNAMED_SECTION])
        self.assertEqual(dict(p[configparser.UNNAMED_SECTION]), {'new': '2'})

    def test_default_disabled(self):
        with self.assertRaises(configparser.MissingSectionHeaderError):
            configparser.ConfigParser().read_string('a=1')
        with self.assertRaises(configparser.UnnamedSectionDisabledError):
            configparser.ConfigParser().add_section(configparser.UNNAMED_SECTION)

    def test_multiple_sources(self):
        p = configparser.ConfigParser(allow_unnamed_section=True)
        p.read_string('a=1\\nb=2')
        p.read_file(io.StringIO('b=3\\nc=4'))
        self.assertEqual(dict(p[configparser.UNNAMED_SECTION]), {'a': '1', 'b': '3', 'c': '4'})

    def test_duplicate_and_continuation(self):
        p = configparser.ConfigParser(allow_unnamed_section=True)
        with self.assertRaises(configparser.DuplicateOptionError):
            p.read_string('a=1\\na=2')
        p = configparser.ConfigParser(allow_unnamed_section=True, allow_no_value=True)
        with self.assertRaises(configparser.MultilineContinuationError):
            p.read_string('flag\\n  bad')

    def test_write_safety_and_empty_unnamed(self):
        p = configparser.ConfigParser(allow_unnamed_section=True)
        p.add_section(configparser.UNNAMED_SECTION)
        out = io.StringIO()
        p.write(out)
        self.assertEqual(out.getvalue(), '')
        p.set(configparser.UNNAMED_SECTION, 'bad=key', 'value')
        with self.assertRaises(configparser.InvalidWriteError):
            p.write(io.StringIO())
'''

DOC_ADDITION = '''

Unnamed sections
----------------

Both parser classes accept the keyword-only ``allow_unnamed_section`` argument,
which defaults to ``False``. When enabled, options before the first section
header belong to :data:`UNNAMED_SECTION`, separately from defaults and named
sections. Ordinary duplicate, interpolation and continuation rules still apply.

.. data:: UNNAMED_SECTION

   A non-string sentinel identifying the unnamed section. Use it with
   ``add_section()``, ``read_dict()``, getters and section-proxy access. It also
   works as the key in parser mapping assignment; replacing its mapping replaces
   its own options, not defaults. For example::

      >>> import configparser
      >>> parser = configparser.ConfigParser(allow_unnamed_section=True)
      >>> parser.read_string('port=8080\\n[service]\\nname=worker')
      >>> parser[configparser.UNNAMED_SECTION].getint('port')
      8080
      >>> parser.has_option('service', 'port')
      False

.. exception:: UnnamedSectionDisabledError

   Subclass of :exc:`Error`, raised when adding :data:`UNNAMED_SECTION` without
   enabling support. Headerless option input with support disabled still raises
   :exc:`MissingSectionHeaderError`.

Writing emits nonempty unnamed options before every header, including defaults,
so reading with support enabled preserves their separation. An empty unnamed
section emits nothing. Existing formatting and :exc:`InvalidWriteError` key
checks apply, including to unnamed options. Writes are not atomic: earlier output
may already have been emitted when an error is raised.
'''


def files():
    return {**material.starting_files(), material.LIBRARY: library(),
            material.NEW_TESTS: TESTS.encode(),
            material.DOC: material.baseline_files()[material.DOC]+DOC_ADDITION.encode()}
