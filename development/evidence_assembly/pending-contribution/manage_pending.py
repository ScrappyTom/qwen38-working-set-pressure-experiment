"""Bind the new contribution to existing preparation, runner and exact replay."""
import argparse
import json
from types import SimpleNamespace
from unittest.mock import patch

import pending_task as task
import run_uncoached_contribution as runner
from working_set_exp.jsonutil import sha256_file

study, grouped = task.study, task.grouped
# Reuse the existing preparation and replay; no new execution loop.
_spec = task.importlib.util.spec_from_file_location("preceding_assembly_management", task.AREA.parent / "manage.py")
assembly = task.importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(assembly)
GOOD = "self.assertEqual(e.option, 'my_dir')"
BAD = "self.assertEqual(e.option, 'offline-wrong-option')"
OWNER = "Proceed after recommending an uncoached completed contribution with the qualified grouped-action host"


def reference_reply(module, session, number):
    if module.scenario == "complete":
        return grouped.reply(session, number)
    if number <= 3:
        reply = grouped.reply(session, number)
        if number == 2:
            text = reply["operation"]["new"]
            study.require(GOOD in text and BAD not in text, "fault anchor differs")
            reply["operation"]["new"] = text.replace(GOOD, BAD, 1)
        return reply
    response = dict(discussion="Scripted offline correction only; no model response.")
    if number == 4:
        response["operation"] = dict(action="work_on", sources=[
            dict(path=grouped.prior.TEST, start_line=2200, end_line=0),
            dict(path="Lib/configparser.py", start_line=170, end_line=180)], results=[])
    elif number == 5:
        response["operation"] = dict(action="patch", path=grouped.prior.TEST, old=BAD, new=GOOD,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256(grouped.prior.TEST))
        response["check_after"] = "public"
    elif number == 6:
        response["operation"] = dict(action="submit", expected_candidate_id=session.candidate.candidate_id)
    else:
        raise AssertionError("undeclared scripted reply")
    return response


def prepare():
    reports = []
    with patch.object(assembly, "reference_reply", reference_reply):
        for scenario in ("complete", "correction"):
            reports.append(assembly.prepare_one(task.Task(scenario)))
    module = task.Task()
    study.require(reports[0]["initial"] == reports[1]["initial"], "qualification scenarios changed initial input")
    study.save(task.AREA, module.MANIFEST.name, dict(actor=module.ACTOR, seed=module.SEED,
        maximum_requests=module.MAX_REQUESTS, maximum_operations=module.MAX_OPERATIONS,
        source_sha256=module.source_identities(), preparation_seal_sha256=sha256_file(module.PACKAGE / "SEAL.json"),
        initial=reports[0]["initial"], starting_candidate=study.STARTING_ID,
        owner_direction=OWNER, initial_selection="reused_actual_checkpoint_with_prior_assembly_assistance",
        no_live_coaching=True, automatic_retry=False,
        correction_qualification_sha256=sha256_file(task.Task("correction").PACKAGE / "SEAL.json")))
    study.save(task.AREA, "QUALIFICATION.json", dict(reports=reports, completion_requests=0))


def execute():
    module = task.Task()
    manifest = study.read(module.MANIFEST)
    study.require(sha256_file(task.Task("correction").PACKAGE / "SEAL.json") ==
                  manifest["correction_qualification_sha256"], "correction qualification changed")
    runner.run_once(SimpleNamespace(owner_direction=OWNER, manifest_sha256=sha256_file(module.MANIFEST)), module=module)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "execute", "verify"))
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "execute":
        execute()
    else:
        result = assembly.verify(task.Task(), task.Task().RUN)
        study.save(task.AREA / "review", "VERIFICATION.json", result)
        print(json.dumps(result, indent=2))
