"""Qualify, freeze, execute and verify one declared recovery continuation."""
import argparse
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import continuation_task as study
import qualify
from saved_states import stored
from working_set_exp.accounted_contribution import process_reply
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def setup():
    folder = study.AREA / "setup-001"
    folder.mkdir(exist_ok=False)
    store, log = ArtifactStore(folder), RecordLog(folder / "records.jsonl", "corrected-rejection-setup")
    bound = study.source_identities()
    state = stored(study.SOURCE_RUN, "after/C03-O01-state.json")
    session, adapter = study.original.initial_session(), study.runner.Adapter(study.Task())
    for key in ("pairs", "ranges", "saved", "last", "requests_used", "delivered_sources"):
        setattr(session, key, copy.deepcopy(state[key]))
    reply = stored(study.SOURCE_RUN, "calls/C04-reply.json")
    server, model, _ = study.runtime_paths()
    failure, report = None, None
    try:
        with qualify.RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            loop = study.runner.Loop(folder, store, log, url=url, task_module=adapter,
                source_check=lambda: study.verify_sources(bound), health=lambda: study.pilot.health(folder))
            # Replay the previously dispatched proposal; no new model receives
            # this pre-rejection state under the changed reference.
            session.begin_request()
            result = process_reply(session, reply, loop.measure, adapter.preceding_feedback)
            assert len(result["operations"]) == 1 and not result["operations"][0]["result"]["accepted"]
            assert session.ranges == state["ranges"] and session.saved == state["saved"]
            assert session.candidate.candidate_id == state["candidate_id"]
            study.save(folder, "recorded-proposal.json", reply)
            study.save(folder, "actual-rejection.json", result)
            study.save(folder, "after-reexecution-state.json", study.snapshot(session))
            # New explicitly declared allowance. Historical actions remain exact.
            session.starting_archive_length = len(session.pairs)
            session.requests_used = 0
            session.call_limit, session.request_limit = study.MAX_OPERATIONS, study.MAX_REQUESTS
            assert session._fits_feedback(loop.measure)
            count = loop.measure(session.view())
            assert session.calls_used == 0 and session.working_account() is None and count <= 23808
            study.save(folder, "continuation-state.json", study.snapshot(session))
            study.save(folder, "continuation-input.json", adapter.request_for(session.view()))
            report = dict(initial_tokens=count, recent_rows=len(session.view()["recent_activity"]),
                initial_selection="actual prior broad selection; no researcher narrowing",
                initial_account=None, initial_candidate=session.candidate.candidate_id,
                historical_operations=4, new_requests_used=0, new_operations_used=0,
                actual_reexecution_accepted=False, model_completion_requests=0)
    except BaseException as error:
        failure = error
        study.save(folder, "FAILED.json", dict(type=type(error).__name__, message=str(error)))
    study.save(folder, "RESULTS.json", dict(status="failed_preserved" if failure else "qualified_setup",
        report=report, source_sha256=bound, model_completion_requests=0,
        memory=qualify.RUNTIME.memory_stats(folder / "memory.csv")))
    files = qualify.RUNTIME.file_inventory(folder)
    study.save(folder, "SEAL.json", dict(files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))
    if failure:
        raise failure
    study.save(study.AREA, "SETUP.json", study.snapshot(session))
    print(json.dumps(report), flush=True)


def scripted_reply(module, session, number):
    def reply(action, account):
        return dict(discussion="Researcher-scripted qualification; not actor evidence.", account=account, operation=action)
    def patch(path, old, new, account):
        return reply(dict(action="patch", path=path, old=old, new=new,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256(path)), account)
    if number == 1:
        return reply(dict(action="work_on", sources=[
            dict(path="Lib/urllib/parse.py", start_line=170, end_line=195),
            dict(path=study.TEST, start_line=1, end_line=35),
            dict(path=study.TEST, start_line=1445, end_line=0)], results=[]),
            "Researcher qualification: port behavior is governed by the inspected implementation. "
            "Tests and documentation remain unwritten and unchecked. Preserve the question while replacing broad sources.")
    if number == 2:
        text = (study.original.AREA / "REFERENCE_TEST.py").read_text(encoding="utf-8")
        if module.scenario == "correction":
            text = text.replace("('Port out of range 0-65535'", "('WRONG RANGE MESSAGE'")
        return patch(study.TEST, qualify.TEST_ANCHOR, text + "\n\n" + qualify.TEST_ANCHOR,
                     "Proposed tests need actual execution; documentation is still unfinished.")
    if module.scenario == "correction":
        if number == 3:
            return patch(study.TEST, "('WRONG RANGE MESSAGE'", "('Port out of range 0-65535'",
                         "The failed tests report the actual range message. Correct the expectation, keeping the library unchanged.")
        number -= 1
    if number == 3:
        return reply(dict(action="work_on", sources=[dict(path=study.DOC, start_line=1, end_line=55)], results=[]),
                     "The tests scope passed. Saved tests persist as source selection changes; documentation is not yet verified.")
    if number == 4:
        return patch(study.DOC, qualify.DOC_ANCHOR,
            (study.original.AREA / "REFERENCE_DOC.txt").read_text(encoding="utf-8") + "\n" + qualify.DOC_ANCHOR,
            "Document the established behavior; this documentation edit and its examples still need the public check.")
    if number == 5:
        return reply(dict(action="submit", expected_candidate_id=session.candidate.candidate_id),
                     "The actual public check passed on this candidate. Tests and examples are checked; prose still receives review.")
    raise AssertionError("undeclared qualification route")


def publish():
    module = study.Task()
    report = study.read(module.PACKAGE / "QUALIFICATION.json")
    correction = study.Task("correction").PACKAGE
    assert study.read(correction / "SEAL.json")["status"] == "qualified_no_model_inference"
    study.save(study.AREA, module.MANIFEST.name, dict(actor=study.ACTOR, seed=study.SEED,
        maximum_requests=study.MAX_REQUESTS, maximum_operations=study.MAX_OPERATIONS,
        source_sha256=study.source_identities(), preparation_seal_sha256=sha256_file(module.PACKAGE / "SEAL.json"),
        correction_seal_sha256=sha256_file(correction / "SEAL.json"), initial=report["initial"],
        starting_candidate=study.starting_candidate().candidate_id, checkpoint_sha256=sha256_file(study.SETUP),
        prior_attempt_closed=True, inherited_operations=4, no_live_coaching=True, initial_account=None,
        initial_selection="recorded broad selection", automatic_retry=False,
        owner_direction="Proceed with the reviewed account/group boundary qualification and one uncoached recorded-state recovery continuation."))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("setup", "route", "publish", "run", "verify"))
    parser.add_argument("--scenario", default="complete", choices=("complete", "correction"))
    args = parser.parse_args()
    module = study.Task(args.scenario)
    if args.mode == "setup":
        setup()
    elif args.mode == "route":
        qualify.manage.prepare_one(module, scripted_reply,
            [True, True] if args.scenario == "complete" else [False, True, True])
    elif args.mode == "publish":
        publish()
    elif args.mode == "run":
        manifest = study.read(module.MANIFEST)
        assert sha256_file(study.Task("correction").PACKAGE / "SEAL.json") == manifest["correction_seal_sha256"]
        study.runner.run_once(SimpleNamespace(owner_direction=manifest["owner_direction"],
            manifest_sha256=sha256_file(module.MANIFEST)), module)
    else:
        result = qualify.manage.verify(module, module.RUN)
        study.save(study.AREA / "review", "VERIFICATION.json", result)
        print(json.dumps(result, indent=2))
