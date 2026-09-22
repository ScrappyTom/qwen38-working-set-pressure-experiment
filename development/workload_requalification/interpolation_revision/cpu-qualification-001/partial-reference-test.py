class MissingInterpolationTransportTests(unittest.TestCase):
    def test_real_missing_interpolation_transports(self):
        import copy
        import pickle
        for interpolation, raw, reference in (
            (configparser.BasicInterpolation(), '%(missing)s', 'missing'),
        ):
            with self.subTest(mode=type(interpolation).__name__):
                parser = configparser.ConfigParser(interpolation=interpolation)
                parser.read_string('[main]\nvalue=' + raw + '\n[other]\n')
                with self.assertRaises(configparser.InterpolationMissingOptionError) as ctx:
                    parser.get('main', 'value')
                error = ctx.exception
                expected_args = ('value', 'main', raw, reference)
                self.assertIs(type(error), configparser.InterpolationMissingOptionError)
                self.assertEqual(error.args, expected_args)
                restored = [copy.copy(error), copy.deepcopy(error)]
                restored.extend(pickle.loads(pickle.dumps(error, protocol))
                                for protocol in range(pickle.HIGHEST_PROTOCOL + 1))
                for result in restored:
                    self.assertIs(type(result), type(error))
                    self.assertEqual(result.args, expected_args)
                    self.assertEqual((result.option, result.section, result.reference),
                                     ('value', 'main', reference))
                    self.assertEqual(str(result), str(error))
                    self.assertEqual(result.message, error.message)
                self.assertEqual(parser.get('main', 'value', raw=True), raw)
                parser.set('other' if ':' in reference else 'main', 'missing', 'supplied')
                self.assertEqual(parser.get('main', 'value'), 'supplied')
