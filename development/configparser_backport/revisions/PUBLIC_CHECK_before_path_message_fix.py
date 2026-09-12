"""Frozen acceptance harness; source constants are supplied by task preparation."""
import copy
import importlib.util
import io
import json
import pathlib
import pickle
import sys
import tempfile
import types
import unittest

sys.path.insert(0, str(pathlib.Path("Lib").resolve()))
import configparser as candidate_parser


class ContinuationContract(unittest.TestCase):
    def kind(self):
        error = getattr(candidate_parser, "MultilineContinuationError", None)
        self.assertTrue(isinstance(error, type), "public MultilineContinuationError is missing")
        self.assertTrue(issubclass(error, candidate_parser.ParsingError))
        self.assertIn("MultilineContinuationError", candidate_parser.__all__)
        return error

    def observed(self, text, *, reader="string", parser_class=None, **options):
        parser = (parser_class or candidate_parser.ConfigParser)(allow_no_value=True, **options)
        with tempfile.TemporaryDirectory() as raw:
            filename = str(pathlib.Path(raw) / "customer.ini")
            if reader == "path":
                pathlib.Path(filename).write_text(text, encoding="utf-8", newline="")
                operation = lambda: parser.read(filename, encoding="utf-8")
                source = filename
            elif reader == "file":
                operation = lambda: parser.read_file(io.StringIO(text), source="uploaded.ini")
                source = "uploaded.ini"
            else:
                operation = lambda: parser.read_string(text, source="inline.ini")
                source = "inline.ini"
            with self.assertRaises(self.kind()) as caught:
                operation()
            return caught.exception, source

    def test_public_exception_and_location_across_readers(self):
        text = "[service]\noptional_flag\n    continuation\n"
        for parser_class in (candidate_parser.ConfigParser, candidate_parser.RawConfigParser):
            for reader in ("string", "file", "path"):
                with self.subTest(parser=parser_class.__name__, reader=reader):
                    error, source = self.observed(text, parser_class=parser_class, reader=reader)
                    self.assertEqual((error.source, error.lineno, error.line), (source, 3, "    continuation\n"))
                    self.assertEqual(error.args, (source, 3, "    continuation\n"))
                    self.assertIn(source, str(error))
                    self.assertIn("continuation", str(error))

    def test_exception_roundtrip(self):
        kind = self.kind()
        error = kind("copy.ini", 7, "  continued\n")
        for restored in (copy.copy(error), copy.deepcopy(error), pickle.loads(pickle.dumps(error))):
            self.assertIs(type(restored), kind)
            self.assertEqual(restored.args, error.args)
            self.assertEqual((restored.source, restored.lineno, restored.line), ("copy.ini", 7, "  continued\n"))
            self.assertEqual(str(restored), str(error))

    def test_comments_and_blank_lines_keep_actual_location(self):
        cases = (
            ("[s]\nflag\n    # comment\n    continued\n", {}, 4, "    continued\n"),
            ("[s]\nflag\n\n\tcontinued\n", {}, 4, "\tcontinued\n"),
            ("[DEFAULT]\nflag\n    continued # detail\n", {"inline_comment_prefixes": ("#",)}, 3, "    continued # detail\n"),
            ("[s]\nflag\n    continued", {"empty_lines_in_values": False}, 3, "    continued"),
        )
        for text, options, lineno, line in cases:
            with self.subTest(text=text, options=options):
                error, _ = self.observed(text, **options)
                self.assertEqual((error.lineno, error.line), (lineno, line))

    def test_bare_options_and_comments_still_parse(self):
        for cls in (candidate_parser.ConfigParser, candidate_parser.RawConfigParser):
            for empty in (True, False):
                with self.subTest(parser=cls.__name__, empty=empty):
                    parser = cls(allow_no_value=True, empty_lines_in_values=empty)
                    parser.read_string("[s]\nflag\n    # comment\nnext = yes\n")
                    self.assertIsNone(parser.get("s", "flag"))
                    self.assertEqual(parser.get("s", "next"), "yes")

    def test_actual_values_keep_multiline_behavior(self):
        for initial, expected in (("one", "one\ntwo"), ("", "\ntwo")):
            for delimiter in ("=", ":", "=>"):
                with self.subTest(initial=initial, delimiter=delimiter):
                    parser = candidate_parser.ConfigParser(allow_no_value=True, delimiters=(delimiter,))
                    parser.read_string(f"[s]\nvalue {delimiter} {initial}\n    two\n")
                    self.assertEqual(parser.get("s", "value"), expected)

    def test_empty_line_can_end_continuation(self):
        parser = candidate_parser.ConfigParser(allow_no_value=True, empty_lines_in_values=False)
        parser.read_string("[s]\nflag\n\n    another_flag\n")
        self.assertEqual(dict(parser.items("s", raw=True)), {"flag": None, "another_flag": None})

    def test_dictionary_and_read_value_semantics_unchanged(self):
        parser = candidate_parser.ConfigParser(allow_no_value=True)
        parser.read_dict({"s": {"flag": None, "text": "first\nsecond"}})
        self.assertIsNone(parser.get("s", "flag"))
        self.assertEqual(dict(parser.items("s"))["flag"], "")
        self.assertEqual(dict(parser.items("s", raw=True))["flag"], None)
        self.assertEqual(parser.get("s", "text"), "first\nsecond")

    def test_disallowed_bare_option_remains_a_parsing_error(self):
        parser = candidate_parser.ConfigParser(allow_no_value=False)
        with self.assertRaises(candidate_parser.ParsingError):
            parser.read_string("[s]\nflag\n", source="strict.ini")


def module_from_source(name, source, filename):
    module = types.ModuleType(name)
    module.__file__ = filename
    sys.modules[name] = module
    exec(compile(source, filename, "exec"), module.__dict__)
    return module


def cases(suite):
    for item in suite:
        if isinstance(item, unittest.TestSuite):
            yield from cases(item)
        else:
            yield item


def run_suite(suite):
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=2).run(suite)
    return dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
        skipped=len(result.skipped), successful=result.wasSuccessful(),
        details=[dict(test=test.id(), trace=trace) for test, trace in (*result.failures, *result.errors)])


def main():
    old_module = module_from_source("upstream_configparser_tests", _UPSTREAM_TEST_SOURCE,
                                   "Lib/test/test_configparser.py (frozen upstream)")
    old_suite = unittest.defaultTestLoader.loadTestsFromModule(old_module)
    # Normalize away the module name so added cases can be identified across loads.
    old_ids = {test.id().split(".", 1)[1] for test in cases(old_suite)}
    result = dict(upstream=run_suite(old_suite))
    if _UPSTREAM_ONLY:
        passed = result["upstream"]["successful"]
    else:
        result["contract"] = run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(ContinuationContract))
        current_source = pathlib.Path("Lib/test/test_configparser.py").read_text(encoding="utf-8")
        current_module = module_from_source("candidate_configparser_tests", current_source,
                                           "Lib/test/test_configparser.py")
        current_suite = unittest.defaultTestLoader.loadTestsFromModule(current_module)
        added_ids = {test.id().split(".", 1)[1] for test in cases(current_suite)} - old_ids
        result["candidate_tests"] = run_suite(current_suite)
        original = sys.modules["configparser"]
        try:
            module_from_source("configparser", _ORIGINAL_PARSER_SOURCE, "original/Lib/configparser.py")
            against_old = module_from_source("regression_against_original", current_source,
                                             "Lib/test/test_configparser.py (original parser)")
            added = unittest.TestSuite(test for test in cases(unittest.defaultTestLoader.loadTestsFromModule(against_old))
                if test.id().split(".", 1)[1] in added_ids)
            result["new_tests_on_original"] = run_suite(added)
        finally:
            sys.modules["configparser"] = original
        doc = pathlib.Path("Doc/library/configparser.rst").read_text(encoding="utf-8")
        result["documentation_directive_present"] = ".. exception:: MultilineContinuationError" in doc
        result["documentation_semantics_require_direct_review"] = True
        result["added_tests"] = sorted(added_ids)
        result["regression_detects_original"] = bool(added_ids) and not result["new_tests_on_original"]["successful"]
        passed = all(result[name]["successful"] for name in ("upstream", "contract", "candidate_tests"))
        passed = passed and result["regression_detects_original"] and result["documentation_directive_present"]
    # Return bounded useful diagnostics; the host additionally preserves stream
    # byte counts, hashes and truncation. Never label omitted detail as absent.
    for part in result.values():
        if isinstance(part, dict) and "details" in part:
            details = part["details"]
            part["detail_entries_omitted"] = max(0, len(details) - 3)
            part["details"] = [dict(test=row["test"], trace=row["trace"][-900:]) for row in details[:3]]
    report = dict(passed=passed, **result)
    encode = lambda: json.dumps(report, ensure_ascii=True, separators=(",", ":"))
    # Leave ample room for the host's complete result and exact-recovery wrapper.
    # Test verdicts/counts remain exact when diagnostic examples must be omitted.
    if len(encode().encode()) > 4096:
        report["diagnostics_omitted_for_byte_limit"] = True
        for part in report.values():
            if isinstance(part, dict) and "details" in part:
                part["detail_entries_omitted"] += len(part["details"])
                part["details"] = []
        if "added_tests" in report:
            report["added_test_count"] = len(report["added_tests"])
            report["added_tests"] = []
    assert len(encode().encode()) <= 4096, "checker summary cannot fit"
    print(encode())
    raise SystemExit(0 if passed else 1)


if __name__ == "__main__":
    main()
