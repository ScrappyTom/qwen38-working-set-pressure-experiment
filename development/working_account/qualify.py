"""Task checks, declared scripted routes and native grammar; no model inference."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import sys
from types import SimpleNamespace

import task as study
from working_set_exp.candidate import Candidate
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

AREA, TASK = study.PARENT, study.Task()
RUNTIME = study.base.base
SOURCE = study.ROOT / "development/evidence_assembly/recovery-run/run-001"
TEST_ANCHOR = 'if __name__ == "__main__":\n    unittest.main()\n'
DOC_ANCHOR = "URL Parsing\n-----------\n"


def module_at(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    value = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(value)
    return value


sys.path.append(str(study.ROOT / "development/evidence_assembly"))
manage = module_at("accounted_existing_manage", study.ROOT / "development/evidence_assembly/manage.py")


def identities():
    return study.source_identities()


def reference_candidate(*, wrong=False, docs=True):
    files = dict(study.starting_candidate().files)
    test = (study.AREA / "REFERENCE_TEST.py").read_text(encoding="utf-8")
    if wrong:
        test = test.replace("('Port out of range 0-65535'", "('WRONG RANGE MESSAGE'")
    original = files[study.TEST].decode()
    study.require(original.count(TEST_ANCHOR) == 1, "test insertion anchor differs")
    files[study.TEST] = original.replace(TEST_ANCHOR, test + "\n\n" + TEST_ANCHOR).encode()
    if docs:
        original = files[study.DOC].decode()
        study.require(original.count(DOC_ANCHOR) == 1, "documentation anchor differs")
        files[study.DOC] = original.replace(DOC_ANCHOR,
            (study.AREA / "REFERENCE_DOC.txt").read_text(encoding="utf-8") + "\n" + DOC_ANCHOR).encode()
    return Candidate.create(files, max_file_bytes=1048576)


def checker_screen(folder):
    folder.mkdir(parents=True, exist_ok=False)
    rows = []
    scenarios = [("original", study.starting_candidate(), "public", False),
                 ("wrong_expectation", reference_candidate(wrong=True, docs=False), "tests", False),
                 ("tests_before_documentation", reference_candidate(docs=False), "tests", True),
                 ("incomplete_public", reference_candidate(docs=False), "public", False),
                 ("complete_public", reference_candidate(), "public", True),
                 ("complete_examples", reference_candidate(), "examples", True)]
    files = dict(reference_candidate().files)
    files[study.DOC] = files[study.DOC].replace(b"ValueError: Port out of range 0-65535", b"ValueError: WRONG RANGE MESSAGE")
    scenarios.append(("wrong_documentation", Candidate.create(files, max_file_bytes=1048576), "examples", False))
    error = None
    try:
        for name, candidate, scope, expected in scenarios:
            result = run_checker(candidate, study.checker(scope))
            study.save(folder, name + "-candidate.json", study.candidate_bytes(candidate))
            study.save(folder, name + "-result.json", result)
            report = json.loads(result["stdout"])
            study.require("assessment_error" not in report and report["scope"] == scope,
                          name + ": checker failed before behavioral assessment")
            rows.append(dict(name=name, scope=scope, passed=result["passed"], expected=expected,
                             streams_truncated=result["streams_truncated"]))
            study.require(result["passed"] == expected and not result["streams_truncated"], name + ": " + result["stdout"] + result["stderr"])
    except BaseException as problem:
        error = problem
        study.save(folder, "FAILED.json", dict(type=type(problem).__name__, message=str(problem)))
    study.save(folder, "RESULTS.json", dict(status="failed_preserved" if error else "passed",
        source_sha256=identities(), cases=rows, model_completion_requests=0))
    files = RUNTIME.file_inventory(folder)
    study.save(folder, "SEAL.json", dict(files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))
    if error:
        raise error
    print("Seven real-checker scenarios passed; no inference", flush=True)


def scripted_reply(module, session, number):
    def reply(action, account=None):
        value = dict(discussion="Researcher-scripted offline qualification; not model behavior.")
        if account is not None:
            value["account"] = account
        value["operation"] = action
        return value
    def patch(path, old, new, account):
        return reply(dict(action="patch", path=path, old=old, new=new,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256(path)), account)
    if number == 1:
        return reply(dict(action="search", path="Lib/urllib/parse.py", query="def port", offset=0, limit=4))
    if number == 2:
        return reply(dict(action="work_on", sources=[
            dict(path="Lib/urllib/parse.py", start_line=170, end_line=195),
            dict(path=study.TEST, start_line=1, end_line=35),
            dict(path=study.TEST, start_line=1445, end_line=0)], results=[]),
            "Establish exact port behavior from implementation and execution. Documentation remains to be written.")
    if number == 3:
        text = (study.AREA / "REFERENCE_TEST.py").read_text(encoding="utf-8")
        if module.scenario == "correction":
            text = text.replace("('Port out of range 0-65535'", "('WRONG RANGE MESSAGE'")
        return patch(study.TEST, TEST_ANCHOR, text + "\n\n" + TEST_ANCHOR,
                     "These proposed expectations must be checked; no execution result for this edit exists yet.")
    if module.scenario == "correction":
        if number == 4:
            return patch(study.TEST, "('WRONG RANGE MESSAGE'", "('Port out of range 0-65535'",
                         "The actual test failure reports the range message; correct the test, keeping the library unchanged.")
        number -= 1
    if number == 4:
        return reply(dict(action="work_on", sources=[dict(path=study.DOC, start_line=1, end_line=55)], results=[]),
                     "The tests scope passed. Saved tests persist while source selection changes. Documentation remains unchecked.")
    if number == 5:
        return patch(study.DOC, DOC_ANCHOR, (study.AREA / "REFERENCE_DOC.txt").read_text(encoding="utf-8") + "\n" + DOC_ANCHOR,
                     "Document the observed boundaries; the added examples and full contribution still need their actual check.")
    if number == 6:
        return reply(dict(action="submit", expected_candidate_id=session.candidate.candidate_id),
                     "The public check passed on this current candidate. Tests and examples are checked; prose remains subject to direct review.")
    raise AssertionError("undeclared reference route")


def checkpoint():
    return TASK.initial_session(), study.runner.Adapter(TASK)


def grammar(folder):
    native = module_at("accounted_native_probe", study.ROOT / "development/evidence_assembly/grouped-actions/native.py")
    native.AREA, native.TASK, native.study = AREA, TASK, study
    native.qualify = sys.modules[__name__]
    def cases(schema, old_schema):
        session, _ = checkpoint()
        operation = json.loads(canonical_json_bytes(dict(action="check", check_id="tests",
                    expected_candidate_id=session.candidate.candidate_id)))
        both = dict(discussion="Use actual feedback.", account="Question: \"port\".\nExpected value is provisional.", operation=operation)
        bad = copy.deepcopy(both); bad["operation"]["check_id"] = "invented"
        wrong_order = dict(operation=operation, discussion="Wrong emitted order", account="Question")
        return [("account_and_check", schema, both, True),
                ("ordinary_scoped_check", schema, dict(discussion="Check", operation=operation), True),
                ("account_only", schema, dict(discussion="Update", account="Question unresolved"), True),
                ("clear_account", schema, dict(discussion="Clear", account=""), True),
                ("discussion_only", schema, dict(discussion="Stop"), True),
                ("unknown_scope", schema, bad, False),
                ("wrong_property_order", schema, wrong_order, False),
                ("legacy_rejects_account", old_schema, both, False),
                ("wrong_account_type", schema, dict(discussion="Bad", account=["Question"]), False)]
    native.cases = cases
    native.run(folder)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("checks", "grammar", "route", "publish", "run", "verify"))
    parser.add_argument("--version", default="003")
    parser.add_argument("--scenario", default="complete", choices=("complete", "correction"))
    args = parser.parse_args()
    if args.mode == "checks":
        checker_screen(AREA / ("checker-" + args.version))
    elif args.mode == "grammar":
        grammar(AREA / ("native-" + args.version))
    elif args.mode == "route":
        module = study.Task(args.scenario, args.version)
        manage.prepare_one(module, scripted_reply, [True, True] if args.scenario == "complete" else [False, True, True])
    else:
        module = study.Task(version=args.version)
        if args.mode == "publish":
            qualification = study.read(module.PACKAGE / "QUALIFICATION.json")
            correction = study.Task("correction", args.version).PACKAGE
            study.require(study.read(correction / "SEAL.json")["status"] == "qualified_no_model_inference", "correction unqualified")
            study.save(study.AREA, module.MANIFEST.name, dict(actor=study.ACTOR, seed=study.SEED,
                maximum_requests=study.MAX_REQUESTS, maximum_operations=study.MAX_OPERATIONS,
                source_sha256=study.source_identities(), preparation_seal_sha256=sha256_file(module.PACKAGE / "SEAL.json"),
                correction_seal_sha256=sha256_file(correction / "SEAL.json"), initial=qualification["initial"],
                starting_candidate=study.starting_candidate().candidate_id, no_live_coaching=True, initial_selection="empty",
                initial_account=None, automatic_retry=False,
                owner_direction="Proceed with the reviewed working-account and declared-verification recommendation."))
        elif args.mode == "run":
            manifest = study.read(module.MANIFEST)
            study.require(sha256_file(study.Task("correction", args.version).PACKAGE / "SEAL.json") == manifest["correction_seal_sha256"], "correction qualification differs")
            study.runner.run_once(SimpleNamespace(owner_direction=manifest["owner_direction"], manifest_sha256=sha256_file(module.MANIFEST)), module)
        else:
            value = manage.verify(module, module.RUN)
            study.save(study.AREA / "review", "VERIFICATION.json", value)
            print(value)
