"""Behavioral acceptance for extending saved transport coverage and documentation."""
import ast
import copy
import difflib
import json
from pathlib import Path
import pickle
import sys
import unittest

helper = {"__name__": "frozen_backport_harness"}
exec(compile(_BACKPORT_HARNESS, "frozen_backport_harness.py", "exec"), helper)
module_from_source, cases, run_suite = (helper[n] for n in ("module_from_source", "cases", "run_suite"))
parser = sys.modules["configparser"]
target, doc_path = "Lib/test/test_configparser.py", "Doc/library/configparser.rst"
current, baseline = Path(target).read_text(encoding="utf-8"), _SAVED_FILES[target]


def suite(source, name):
    return unittest.defaultTestLoader.loadTestsFromModule(module_from_source(name, source, target))


def ids(source, name):
    return {t.id().split(".", 1)[1] for t in cases(suite(source, name))}


def methods(source):
    return {(cls.name, f.name): ast.dump(f, include_attributes=False)
            for cls in ast.parse(source).body if isinstance(cls, ast.ClassDef)
            for f in cls.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}


def added_suite(name):
    return unittest.TestSuite(t for t in cases(suite(current, name)) if t.id().split(".", 1)[1] in added)


def observe_paths():
    kind = parser.InterpolationMissingOptionError
    originals = copy.copy, copy.deepcopy, pickle.dumps, pickle.loads, parser.RawConfigParser.get
    policies = (parser.BasicInterpolation, parser.ExtendedInterpolation)
    before = {p: p.before_get for p in policies}
    raised, events, pending = [], {}, {}
    raw_success, resolved, raw_calls = set(), set(), []
    active = 0
    def wrap(policy):
        def get(self, obj, section, option, value, defaults):
            nonlocal active
            active += 1
            try:
                result = before[policy](self, obj, section, option, value, defaults)
            except kind as error:
                raised.append(error)
                events[id(error)] = dict(policy=policy.__name__, reference=error.reference, modes=set(),
                                         parser=obj, section=section, option=option, value=value)
                raise
            finally:
                active -= 1
            if result != value:
                resolved.add(policy.__name__)
            return result
        return get
    def raw_get(self, section, option, *, raw=False, **kwargs):
        result = originals[4](self, section, option, raw=raw, **kwargs)
        if raw and not active:
            raw_calls.append((self, section, option, result))
        return result
    def mark(error, mode):
        if id(error) in events and any(error is old for old in raised):
            events[id(error)]["modes"].add(mode)
    def shallow(error, *args, **kwargs):
        result = originals[0](error, *args, **kwargs)
        mark(error, "copy")
        return result
    def deep(error, *args, **kwargs):
        result = originals[1](error, *args, **kwargs)
        mark(error, "deepcopy")
        return result
    def dumps(error, protocol=None, *args, **kwargs):
        result = originals[2](error, protocol, *args, **kwargs)
        if id(error) in events:
            protocol = pickle.DEFAULT_PROTOCOL if protocol is None else protocol
            pending[result] = (error, pickle.HIGHEST_PROTOCOL if protocol < 0 else protocol)
        return result
    def loads(raw, *args, **kwargs):
        result = originals[3](raw, *args, **kwargs)
        if raw in pending:
            error, protocol = pending[raw]
            mark(error, f"pickle:{protocol}")
        return result
    for policy in policies:
        policy.before_get = wrap(policy)
    parser.RawConfigParser.get = raw_get
    copy.copy, copy.deepcopy, pickle.dumps, pickle.loads = shallow, deep, dumps, loads
    try:
        result = run_suite(added_suite("observed_interpolation"))
    finally:
        for policy in policies:
            policy.before_get = before[policy]
        copy.copy, copy.deepcopy, pickle.dumps, pickle.loads, parser.RawConfigParser.get = originals
    needed = {"copy", "deepcopy", *(f"pickle:{p}" for p in range(pickle.HIGHEST_PROTOCOL + 1))}
    for event in events.values():
        if any(obj is event["parser"] and section == event["section"] and option == event["option"]
               and value == event["value"] for obj, section, option, value in raw_calls):
            raw_success.add(event["policy"])
    modes = {p.__name__: set().union(*(e["modes"] for e in events.values()
             if e["policy"] == p.__name__ and (p is parser.BasicInterpolation or ":" in e["reference"]))) for p in policies}
    result.update(modes={k: sorted(v) for k, v in modes.items()}, raw_bypass=sorted(raw_success), resolved=sorted(resolved))
    result["complete"] = all(needed <= modes[p.__name__] and p.__name__ in raw_success and p.__name__ in resolved for p in policies)
    return result


def mutations():
    kind, results = parser.InterpolationMissingOptionError, {}
    for index, name in enumerate(("option", "section", "raw_value", "reference")):
        def reduce(error, index=index):
            args = list(error.args)
            args[index] += ".wrong"
            return type(error), tuple(args)
        previous = kind.__dict__.get("__reduce__")
        kind.__reduce__ = reduce
        try:
            results[name] = run_suite(added_suite("restoration_fault_" + name))
        finally:
            if previous is None:
                del kind.__reduce__
            else:
                kind.__reduce__ = previous
    return results


old_ids = ids(baseline, "saved_inventory")
added = ids(current, "new_inventory") - old_ids
old_methods, new_methods = methods(baseline), methods(current)
preserved = all(Path(p).read_bytes() == b.encode() for p, b in _SAVED_FILES.items() if p not in (target, doc_path))
preserved = preserved and all(new_methods.get(k) == v for k, v in old_methods.items())
doc = Path(doc_path).read_text(encoding="utf-8")
doc_change = difflib.SequenceMatcher(None, _SAVED_FILES[doc_path].splitlines(True), doc.splitlines(True), autojunk=False)
doc_added = doc != _SAVED_FILES[doc_path] and all(op[0] in ("equal", "insert") for op in doc_change.get_opcodes())
report = dict(existing_work_preserved=preserved, documentation_added_preserving_existing=doc_added,
    documentation_accuracy_requires_direct_review=True, added_tests=sorted(added),
    saved_suite=run_suite(suite(baseline, "saved_tests")), edited_suite=run_suite(suite(current, "edited_tests")),
    backport_contract=run_suite(unittest.defaultTestLoader.loadTestsFromTestCase(helper["ContinuationContract"])),
    observed_paths=observe_paths(), restoration_faults=mutations())
parts = [report[n] for n in ("saved_suite", "edited_suite", "backport_contract", "observed_paths")]
passed = (preserved and doc_added and bool(added) and all(p["successful"] for p in parts)
          and report["observed_paths"]["complete"]
          and all(r["tests"] > 0 and not r["successful"] for r in report["restoration_faults"].values()))
report["passed"] = passed
for part in parts + list(report["restoration_faults"].values()):
    details = part["details"]
    part["detail_entries_omitted"] = max(0, len(details) - 1)
    part["details"] = [dict(test=r["test"], trace=r["trace"][-600:]) for r in details[:1]]
encode = lambda: json.dumps(report, ensure_ascii=True, separators=(",", ":"))
if len(encode().encode()) > 6500:
    for part in parts + list(report["restoration_faults"].values()):
        part["detail_entries_omitted"] += len(part["details"])
        part["details"] = []
    report["diagnostic_examples_omitted_for_size"] = True
assert len(encode().encode()) <= 6500
print(encode())
raise SystemExit(0 if passed else 1)
