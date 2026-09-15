"""Bind C05 recovery preparation and execution to the existing contribution loop."""
import argparse
import copy
import importlib.util
import json
from types import SimpleNamespace
from unittest.mock import patch

import recovery_task as task
import run_uncoached_contribution as runner
from working_set_exp.jsonutil import sha256_file

study = task.study
spec = importlib.util.spec_from_file_location("recovery_assembly_management", task.AREA.parent / "manage.py")
assembly = importlib.util.module_from_spec(spec)
spec.loader.exec_module(assembly)
TEST, DOC = "Lib/test/test_configparser.py", "Doc/library/configparser.rst"
GOOD, BAD = "self.assertEqual(e.option, 'my_dir')", "self.assertEqual(e.option, 'offline-wrong-option')"
SUPPORT = [r for r in study.GROUPS["assembled"]
           if r["path"] == "Lib/configparser.py" or r["path"] == TEST and r["start_line"] in (1, 2200)]
DOCS = [r for r in study.GROUPS["assembled"] if r["path"] == DOC]


def reference_reply(module, session, number):
    reply = dict(discussion="Researcher-scripted preparation only; no model response.")
    if number == 1:
        reply["operation"] = dict(action="work_on", sources=copy.deepcopy(SUPPORT), results=[task.PROPOSAL])
    elif number == 2:
        page = session.saved[task.PROPOSAL]
        study.require(page["offset"] == 0 and page["next_offset"] is None, "proposal is incomplete")
        reply["operation"] = json.loads(page["exact_utf8"])
        if module.scenario == "correction":
            value = reply["operation"]["new"]
            study.require(GOOD in value and BAD not in value, "fault anchor differs")
            reply["operation"]["new"] = value.replace(GOOD, BAD, 1)
    elif number == 3:
        reply["operation"] = dict(action="work_on", sources=copy.deepcopy(DOCS), results=[])
    elif number == 4:
        old = ".. exception:: InterpolationSyntaxError\n"
        reply["operation"] = dict(action="patch", path=DOC, old=old,
            new=(study.AREA / "REFERENCE_DOC.txt").read_text(encoding="utf-8") + "\n" + old,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256(DOC))
        reply["check_after"] = "public"
    elif module.scenario == "correction" and number == 5:
        reply["operation"] = dict(action="work_on", sources=[dict(path=TEST, start_line=2200, end_line=0),
            dict(path="Lib/configparser.py", start_line=256, end_line=275)], results=[])
    elif module.scenario == "correction" and number == 6:
        reply["operation"] = dict(action="patch", path=TEST, old=BAD, new=GOOD,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256(TEST))
        reply["check_after"] = "public"
    elif number == (5 if module.scenario == "complete" else 7):
        reply["operation"] = dict(action="submit", expected_candidate_id=session.candidate.candidate_id)
    else:
        raise AssertionError("undeclared scripted reply")
    return reply


def verify_preparation():
    module = task.Task()
    manifest = runner.verify_package(module)
    corrected = task.Task("correction")
    study.require(sha256_file(corrected.PACKAGE / "SEAL.json") == manifest["correction_qualification_sha256"],
                  "correction qualification differs")
    rows = [assembly.verify(task.Task(s), task.Task(s).PACKAGE) for s in ("complete", "correction")]
    before = module.initial_session().candidate
    finals = [study.read(task.Task(s).PACKAGE / "final-candidate.json") for s in ("complete", "correction")]
    study.require(finals[0] == finals[1], "corrected and complete artifacts differ")
    complete_test = study.read(module.PACKAGE / "after/C02-O01-candidate.json")
    selected_docs = study.read(module.PACKAGE / "after/C03-O01-state.json")
    study.require(selected_docs["saved"] == {} and all(r["path"] == DOC for r in selected_docs["ranges"]),
                  "documentation selection did not release prior support")
    final_map = {r["path"]: r["content_utf8"].encode() for r in finals[0]["files"]}
    saved_tests = next(r["content_utf8"].encode() for r in complete_test["files"] if r["path"] == TEST)
    study.require(final_map[TEST] == saved_tests and
                  sorted(p for p in before.file_map if before.file_map[p] != final_map[p]) == sorted([TEST, DOC]),
                  "saved tests or unrelated source changed")
    study.require(not module.RUN.exists(), "prepared execution already exists")
    return dict(status="ready_not_started", initial=manifest["initial"], actor=module.ACTOR,
        seed=module.SEED, maximum_requests=module.MAX_REQUESTS, maximum_operations=module.MAX_OPERATIONS,
        final_scripted_candidate=finals[0]["candidate_id"], preserved_work_across_selection=True,
        actual_completion_requests=0, routes=rows, manifest_sha256=sha256_file(module.MANIFEST))


def prepare():
    reports = []
    with patch.object(assembly, "reference_reply", reference_reply):
        for scenario in ("complete", "correction"):
            reports.append(assembly.prepare_one(task.Task(scenario)))
    study.require(reports[0]["initial"] == reports[1]["initial"], "initial inputs differ")
    module = task.Task()
    study.save(task.AREA, module.MANIFEST.name, dict(actor=module.ACTOR, seed=module.SEED,
        maximum_requests=module.MAX_REQUESTS, maximum_operations=module.MAX_OPERATIONS,
        source_sha256=module.source_identities(), preparation_seal_sha256=sha256_file(module.PACKAGE / "SEAL.json"),
        initial=reports[0]["initial"], starting_candidate=study.STARTING_ID,
        owner_direction="Proceed to prepare the next uncoached contribution and freeze its starting state and allowance",
        starting_checkpoint="pending-contribution run-001 after C04-O01, before C05",
        initial_selection="actual_model_selected_checkpoint_with_inherited_assembly_assistance",
        no_live_coaching=True, automatic_retry=False, execution_status="prepared_not_started",
        correction_qualification_sha256=sha256_file(task.Task("correction").PACKAGE / "SEAL.json")))
    study.save(task.AREA, "QUALIFICATION.json", dict(reports=reports, completion_requests=0))
    checked = verify_preparation()
    study.save(task.AREA, "PREPARATION_VERIFICATION.json", checked)
    print(json.dumps({k:checked[k] for k in ("status", "initial", "seed", "maximum_requests", "maximum_operations")}, indent=2))


def execute(owner_direction):
    study.require(owner_direction.strip(), "record the direction to execute this prepared attempt")
    verify_preparation()
    module = task.Task()
    runner.run_once(SimpleNamespace(owner_direction=owner_direction,
                    manifest_sha256=sha256_file(module.MANIFEST)), module=module)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "verify-preparation", "execute", "verify-run"))
    parser.add_argument("--owner-direction", default="")
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "verify-preparation":
        print(json.dumps(verify_preparation(), indent=2))
    elif args.mode == "execute":
        execute(args.owner_direction)
    else:
        module = task.Task()
        print(json.dumps(assembly.verify(module, module.RUN), indent=2))
