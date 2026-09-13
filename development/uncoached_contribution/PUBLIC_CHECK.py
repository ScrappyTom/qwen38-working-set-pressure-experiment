"""Coverage acceptance from behavior and isolated restoration faults.

Frozen baseline/harness source is prefixed by task preparation. This runs in the
candidate's temporary directory. It never edits the saved candidate.
"""
import ast
import copy
import io
import json
from pathlib import Path
import pickle
import sys
import unittest

helper = {"__name__": "frozen_backport_harness"}
exec(compile(_LEGACY_HARNESS_SOURCE, "frozen_backport_harness.py", "exec"), helper)
module_from_source, cases, run_suite = (helper[n] for n in ("module_from_source", "cases", "run_suite"))
parser = sys.modules["configparser"]
target = "Lib/test/test_configparser.py"
current = Path(target).read_text(encoding="utf-8")
baseline = _BASELINE_FILES[target]


def suite(source, name):
    return unittest.defaultTestLoader.loadTestsFromModule(module_from_source(name, source, target))


def ids(source, name):
    return {t.id().split(".", 1)[1] for t in cases(suite(source, name))}


def methods(source):
    return {(cls.name, f.name): ast.dump(f, include_attributes=False)
            for cls in ast.parse(source).body if isinstance(cls, ast.ClassDef)
            for f in cls.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef)) and f.name.startswith("test")}


def added_suite(name):
    return unittest.TestSuite(t for t in cases(suite(current, name)) if t.id().split(".", 1)[1] in added)


def run_transports():
    """Observe real parser errors transported by the added tests, not text tokens."""
    kind = parser.MultilineContinuationError
    original_read = parser.RawConfigParser._read
    originals = copy.copy, copy.deepcopy, pickle.dumps, pickle.loads
    raised, observations = [], {}
    def observe_read(self, *args, **kwargs):
        try:
            return original_read(self, *args, **kwargs)
        except kind as error:
            raised.append(error)
            observations[id(error)] = dict(newline=error.line.endswith("\n"), modes=set())
            raise
    def mark(error, mode):
        if id(error) in observations and any(error is e for e in raised):
            observations[id(error)]["modes"].add(mode)
    def shallow(error, *args, **kwargs):
        restored = originals[0](error, *args, **kwargs)
        mark(error, "copy")
        return restored
    def deep(error, *args, **kwargs):
        restored = originals[1](error, *args, **kwargs)
        mark(error, "deepcopy")
        return restored
    pending = {}
    def dumps(error, protocol=None, *args, **kwargs):
        raw = originals[2](error, protocol, *args, **kwargs)
        if id(error) in observations:
            proto = pickle.DEFAULT_PROTOCOL if protocol is None else protocol
            if proto < 0:
                proto = pickle.HIGHEST_PROTOCOL
            pending[raw] = (error, proto)
        return raw
    def loads(raw, *args, **kwargs):
        restored = originals[3](raw, *args, **kwargs)
        if raw in pending:
            error, proto = pending[raw]
            mark(error, "pickle:" + str(proto))
        return restored
    parser.RawConfigParser._read = observe_read
    copy.copy, copy.deepcopy, pickle.dumps, pickle.loads = shallow, deep, dumps, loads
    try:
        result = run_suite(added_suite("transport_tests"))
    finally:
        parser.RawConfigParser._read = original_read
        copy.copy, copy.deepcopy, pickle.dumps, pickle.loads = originals
    needed = {"copy", "deepcopy", *("pickle:" + str(p) for p in range(pickle.HIGHEST_PROTOCOL + 1))}
    # Tests can split transport modes across independently raised examples.
    by_newline = {flag: set().union(*(r["modes"] for r in observations.values() if r["newline"] == flag))
                  for flag in (False, True)}
    result["observed_modes"] = {str(k): sorted(v) for k, v in by_newline.items()}
    result["required_modes"] = sorted(needed)
    result["complete"] = all(needed <= modes for modes in by_newline.values())
    return result


def mutation_results():
    kind = parser.MultilineContinuationError
    results = {}
    for name, reduce in (
        ("changed_source", lambda e: (type(e), (str(e.source) + ".wrong", e.lineno, e.line))),
        ("changed_line_number", lambda e: (type(e), (e.source, e.lineno + 1, e.line))),
        ("stripped_raw_line", lambda e: (type(e), (e.source, e.lineno, e.line.strip()))),
        ("lost_errors", lambda e: (type(e), e.args, {"errors": []})),
    ):
        previous = kind.__dict__.get("__reduce__")
        kind.__reduce__ = reduce
        try:
            results[name] = run_suite(added_suite("mutant_" + name))
        finally:
            if previous is None:
                del kind.__reduce__
            else:
                kind.__reduce__ = previous
    return results


old_ids = ids(baseline, "saved_test_inventory")
added = ids(current, "current_test_inventory") - old_ids
old_methods, new_methods = methods(baseline), methods(current)
preserved = all(Path(p).read_bytes() == raw.encode() for p, raw in _BASELINE_FILES.items() if p != target)
preserved = preserved and all(new_methods.get(k) == v for k, v in old_methods.items())
result = dict(existing_work_preserved=preserved, added_tests=sorted(added),
              saved_suite=run_suite(suite(baseline, "saved_tests")),
              edited_suite=run_suite(suite(current, "edited_tests")),
              contract=run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(helper["ContinuationContract"])))
result["transports"] = run_transports()
result["restoration_faults"] = mutation_results()
passed = (preserved and bool(added) and all(result[n]["successful"] for n in ("saved_suite", "edited_suite", "contract", "transports"))
          and result["transports"]["complete"]
          and all(r["tests"] > 0 and not r["successful"] for r in result["restoration_faults"].values()))
result["passed"] = passed
# Keep verdicts and scopes; detailed failures remain bounded actual diagnostics.
parts = [result[n] for n in ("saved_suite", "edited_suite", "contract", "transports")]
parts += list(result["restoration_faults"].values())
for part in parts:
    details = part["details"]
    part["detail_entries_omitted"] = max(0, len(details) - 1)
    part["details"] = [dict(test=r["test"], trace=r["trace"][-500:]) for r in details[:1]]
encode = lambda: json.dumps(result, ensure_ascii=True, separators=(",", ":"))
if len(encode().encode()) > 6500:
    for part in parts:
        part["detail_entries_omitted"] += len(part["details"])
        part["details"] = []
    result["diagnostic_examples_omitted_for_size"] = True
assert len(encode().encode()) <= 6500
print(encode())
raise SystemExit(0 if passed else 1)
