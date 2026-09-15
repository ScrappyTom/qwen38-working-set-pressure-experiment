"""Stage checks for real port-access coverage and executable documentation.

Injected inputs: _BASELINE_FILES, _SCOPE, _EXAMPLES_HELPER. Only this frozen
task checker chooses coverage; the operating host does not judge explanations.
"""
import ast
import contextlib
import difflib
import functools
import io
import json
from pathlib import Path
import sys
import types
import unittest
sys.path.insert(0, str(Path("Lib").resolve()))
for imported in ("urllib.parse", "urllib"):
    sys.modules.pop(imported, None)
import urllib.parse as parser

exec(_EXAMPLES_HELPER)
TARGET = "Lib/test/test_urlparse.py"
DOC = "Doc/library/urllib.parse.rst"
assert Path(parser.__file__).resolve() == Path("Lib/urllib/parse.py").resolve(), "wrong implementation imported"


def methods(source):
    tree = ast.parse(source)
    return {(node.name, part.name): ast.dump(part, include_attributes=False)
            for node in tree.body if isinstance(node, ast.ClassDef)
            for part in node.body if isinstance(part, (ast.FunctionDef, ast.AsyncFunctionDef))}


def load(source, name):
    module = types.ModuleType(name)
    module.__file__ = TARGET
    sys.modules[name] = module
    exec(compile(source, TARGET, "exec"), module.__dict__)
    return module


def cases(suite):
    for value in suite:
        if isinstance(value, unittest.TestSuite):
            yield from cases(value)
        else:
            yield value


def run_suite(suite):
    result = unittest.TextTestRunner(stream=io.StringIO(), verbosity=0).run(suite)
    return dict(tests=result.testsRun, failures=len(result.failures), errors=len(result.errors),
                skipped=len(result.skipped), successful=result.wasSuccessful(),
                details=[dict(test=t.id(), trace=text[-700:]) for t, text in
                         [*result.failures, *result.errors]][:1])


baseline_ids = {t.id().split(".", 1)[1] for t in cases(
    unittest.defaultTestLoader.loadTestsFromModule(load(_BASELINE_FILES[TARGET], "saved_url_tests")))}
current = Path(TARGET).read_text(encoding="utf-8")


def added_suite(name):
    return unittest.TestSuite(t for t in cases(unittest.defaultTestLoader.loadTestsFromModule(load(current, name)))
                             if t.id().split(".", 1)[1] not in baseline_ids)


def category(value):
    raw = value._hostinfo[1]
    if raw is None:
        return "empty" if value.netloc.endswith(b":" if isinstance(value.netloc, bytes) else ":") else "absent"
    text = raw.decode("ascii") if isinstance(raw, bytes) else raw
    if text in ("0", "65535", "65536", "-1"):
        return {"0": "zero", "65535": "maximum", "65536": "too_high", "-1": "negative"}[text]
    if text.isdigit() and not text.isascii():
        return "unicode_digits"
    if text.isascii() and not text.isdigit():
        return "noninteger"
    return "other"


def exercise(fault=None):
    original_property = parser._NetlocResultMixinBase.port
    originals = {name: getattr(parser, name) for name in ("urlsplit", "urlparse")}
    objects, accesses = {}, set()
    active = 0
    class DifferentValueError(ValueError):
        pass
    def observed_port(value):
        identified = objects.get(id(value))
        if identified is not None and identified[0] is value:
            accesses.add((identified[1], identified[2], category(value)))
        try:
            result = original_property.fget(value)
        except ValueError as error:
            if fault == "error_class":
                raise DifferentValueError(*error.args) from None
            if fault == "error_arguments":
                raise ValueError(*error.args, "unexpected second argument") from None
            if fault == "error_message":
                raise ValueError("incorrect port diagnostic") from None
            raise
        kind = category(value)
        if fault == "empty_port" and kind == "empty":
            return 0
        if fault == "zero_port" and kind == "zero":
            return None
        if fault == "maximum_port" and kind == "maximum":
            return 65534
        return result
    def wrap(name):
        @functools.wraps(originals[name])
        def call(url, *args, **kwargs):
            nonlocal active
            outer = active == 0
            active += 1
            try:
                value = originals[name](url, *args, **kwargs)
            finally:
                active -= 1
            if outer:
                objects[id(value)] = (value, name, "bytes" if isinstance(url, bytes) else "str")
                if fault == "eager_validation":
                    value.port
            return value
        if hasattr(originals[name], "cache_clear"):
            call.cache_clear = originals[name].cache_clear
        return call
    try:
        parser._NetlocResultMixinBase.port = property(observed_port)
        for name in originals:
            setattr(parser, name, wrap(name))
        result = run_suite(added_suite("observed_url_tests"))
    finally:
        parser._NetlocResultMixinBase.port = original_property
        for name, original in originals.items():
            setattr(parser, name, original)
    needed = {(api, typ, kind) for api in originals for typ in ("str", "bytes")
              for kind in ("absent", "empty", "zero", "maximum", "too_high", "negative", "noninteger")}
    needed |= {(api, "str", "unicode_digits") for api in originals}
    result["missing_paths"] = [list(row) for row in sorted(needed - accesses)]
    result["complete"] = not result["missing_paths"] and result["tests"] > 0 and not result["skipped"]
    return result


def assess():
    unchanged = all(Path(p).read_bytes() == raw.encode() for p, raw in _BASELINE_FILES.items()
                    if p not in (TARGET, DOC))
    old, new = methods(_BASELINE_FILES[TARGET]), methods(current)
    unchanged = unchanged and all(new.get(k) == value for k, value in old.items())
    doc = Path(DOC).read_text(encoding="utf-8")
    changes = difflib.SequenceMatcher(None, _BASELINE_FILES[DOC].splitlines(True), doc.splitlines(True), autojunk=False)
    doc_preserved = all(row[0] in ("equal", "insert") for row in changes.get_opcodes())
    report = dict(scope=_SCOPE, existing_work_preserved=unchanged,
                  documentation_preserved=doc_preserved, documentation_prose_requires_direct_review=True)
    if _SCOPE in ("tests", "public"):
        report["saved_suite"] = run_suite(unittest.defaultTestLoader.loadTestsFromModule(load(_BASELINE_FILES[TARGET], "saved_url_tests")))
        report["edited_suite"] = run_suite(unittest.defaultTestLoader.loadTestsFromModule(load(current, "edited_url_tests")))
        report["observed_paths"] = exercise()
        report["fault_sensitivity"] = {fault: exercise(fault) for fault in
            ("error_class", "error_arguments", "error_message", "eager_validation", "empty_port", "zero_port", "maximum_port")}
        tests_pass = all(report[key]["successful"] for key in ("saved_suite", "edited_suite", "observed_paths"))
        tests_pass = tests_pass and report["observed_paths"]["complete"]
        tests_pass = tests_pass and all(r["tests"] and not r["successful"] for r in report["fault_sensitivity"].values())
        report["tests_passed"] = tests_pass
    if _SCOPE in ("examples", "public"):
        report["examples"] = check_added_examples(_BASELINE_FILES[DOC], doc, DOC)
    report["passed"] = (unchanged and doc_preserved and report.get("tests_passed", True)
                         and report.get("examples", {"successful": True})["successful"])
    return report


try:
    report = assess()
except Exception as error:
    report = dict(scope=_SCOPE, passed=False, assessment_error=f"{type(error).__name__}: {error}")
encode = lambda: json.dumps(report, ensure_ascii=True, separators=(",", ":"))
if len(encode().encode()) > 6500:
    report["diagnostics_omitted_for_size"] = True
    for part in report.values():
        if isinstance(part, dict):
            part.pop("details", None)
    for part in report.get("fault_sensitivity", {}).values():
        part.pop("details", None)
        part.pop("missing_paths", None)
assert len(encode().encode()) <= 6500, "checker result exceeds qualified size"
print(encode())
raise SystemExit(0 if report["passed"] else 1)
