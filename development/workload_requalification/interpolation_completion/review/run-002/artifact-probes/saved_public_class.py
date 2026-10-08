class InterpolationMissingOptionErrorTransportTestCase(unittest.TestCase):
    """InterpolationMissingOptionError obtained from real ConfigParser.get
    calls, verified for class, arguments, attributes, diagnostic text,
    shallow copy, deep copy and every pickle protocol."""

    def _make_basic_config(self):
        cf = configparser.ConfigParser(
            interpolation=configparser.BasicInterpolation())
        cf.read_string(textwrap.dedent("""
            [Interpolation Error]
            name = %(reference)s
        """))
        return cf

    def _make_extended_config(self):
        cf = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(),
            default_section='common')
        cf.read_string(textwrap.dedent("""
            [common]
            value = something

            [test]
            name = ${missing_ref}
        """))
        return cf

    def _make_extended_cross_section_config(self):
        cf = configparser.ConfigParser(
            interpolation=configparser.ExtendedInterpolation(),
            default_section='common')
        cf.read_string(textwrap.dedent("""
            [common]
            value = something

            [test]
            name = ${other:missing}
        """))
        return cf

    def _assert_error_transport(self, e, expected_args):
        import copy
        import pickle

        self.assertIsInstance(
            e, configparser.InterpolationMissingOptionError)
        self.assertEqual(e.args, expected_args)
        self.assertEqual(e.option, expected_args[0])
        self.assertEqual(e.section, expected_args[1])
        self.assertEqual(e.reference, expected_args[3])
        self.assertEqual(str(e), str(expected_args))

        # Shallow copy preserves all attributes
        e2 = copy.copy(e)
        self.assertIsInstance(
            e2, configparser.InterpolationMissingOptionError)
        self.assertEqual(e2.args, e.args)
        self.assertEqual(e2.option, e.option)
        self.assertEqual(e2.section, e.section)
        self.assertEqual(e2.reference, e.reference)
        self.assertEqual(str(e2), str(e))

        # Deep copy preserves all attributes
        e3 = copy.deepcopy(e)
        self.assertIsInstance(
            e3, configparser.InterpolationMissingOptionError)
        self.assertEqual(e3.args, e.args)
        self.assertEqual(e3.option, e.option)
        self.assertEqual(e3.section, e.section)
        self.assertEqual(e3.reference, e.reference)
        self.assertEqual(str(e3), str(e))

        # Pickle round-trip for every available protocol
        for protocol in range(pickle.HIGHEST_PROTOCOL + 1):
            with self.subTest(protocol=protocol):
                data = pickle.dumps(e, protocol=protocol)
                e4 = pickle.loads(data)
                self.assertIsInstance(
                    e4, configparser.InterpolationMissingOptionError)
                self.assertEqual(e4.args, e.args)
                self.assertEqual(e4.option, e.option)
                self.assertEqual(e4.section, e.section)
                self.assertEqual(e4.reference, e.reference)
                self.assertEqual(str(e4), str(e))

    def test_basic_interpolation_missing_reference(self):
        cf = self._make_basic_config()
        try:
            cf.get("Interpolation Error", "name")
        except configparser.InterpolationMissingOptionError as e:
            pass
        else:
            self.fail("expected InterpolationMissingOptionError")

        self._assert_error_transport(
            e, ('name', 'Interpolation Error',
                '%(reference)s', 'reference'))

        # raw=True returns the unresolved value
        self.assertEqual(
            cf.get("Interpolation Error", "name", raw=True),
            '%(reference)s')

        # Successful lookup once the referenced setting exists
        cf.set("Interpolation Error", "reference", "the_value")
        self.assertEqual(
            cf.get("Interpolation Error", "name"), 'the_value')

    def test_extended_interpolation_missing_reference(self):
        cf = self._make_extended_config()
        try:
            cf.get("test", "name")
        except configparser.InterpolationMissingOptionError as e:
            pass
        else:
            self.fail("expected InterpolationMissingOptionError")

        self._assert_error_transport(
            e, ('name', 'test', '${missing_ref}', 'missing_ref'))

        # raw=True returns the unresolved value
        self.assertEqual(
            cf.get("test", "name", raw=True), '${missing_ref}')

        # Successful lookup once the referenced setting exists
        cf.set("test", "missing_ref", "resolved")
        self.assertEqual(cf.get("test", "name"), 'resolved')

    def test_extended_interpolation_missing_cross_section(self):
        cf = self._make_extended_cross_section_config()
        try:
            cf.get("test", "name")
        except configparser.InterpolationMissingOptionError as e:
            pass
        else:
            self.fail("expected InterpolationMissingOptionError")

        self._assert_error_transport(
            e, ('name', 'test', '${other:missing}', 'other:missing'))

        # raw=True returns the unresolved value
        self.assertEqual(
            cf.get("test", "name", raw=True), '${other:missing}')

        # Successful lookup once the cross-section reference exists
        cf.add_section('other')
        cf.set('other', 'missing', 'cross_value')
        self.assertEqual(cf.get("test", "name"), 'cross_value')
