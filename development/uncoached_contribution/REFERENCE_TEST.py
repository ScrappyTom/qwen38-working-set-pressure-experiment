# Offline qualification only. This file is never in the actor candidate/input.
class MultilineContinuationTransportTestCase(unittest.TestCase):
    def test_roundtrip_diagnostics(self):
        import copy
        import pickle
        for ending in ("\n", ""):
            with self.subTest(ending=ending):
                parser = configparser.ConfigParser(allow_no_value=True)
                line = "    continued" + ending
                with self.assertRaises(configparser.ParsingError) as caught:
                    parser.read_string("[section]\nflag\n" + line,
                                       source="roundtrip.ini")
                original = caught.exception
                restored_errors = [copy.copy(original), copy.deepcopy(original)]
                restored_errors.extend(pickle.loads(pickle.dumps(original, p))
                                       for p in range(pickle.HIGHEST_PROTOCOL + 1))
                for restored in restored_errors:
                    self.assertIs(type(restored), configparser.MultilineContinuationError)
                    self.assertEqual(restored.args, ("roundtrip.ini", 3, line))
                    self.assertEqual(restored.source, "roundtrip.ini")
                    self.assertEqual(restored.lineno, 3)
                    self.assertEqual(restored.line, line)
                    self.assertEqual(restored.errors, [(3, line)])
                    self.assertEqual(restored.message, original.message)
                    self.assertEqual(str(restored), str(original))


