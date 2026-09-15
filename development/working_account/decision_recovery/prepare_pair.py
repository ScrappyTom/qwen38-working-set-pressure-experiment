"""Native recovery qualification and the conditional frozen comparison."""
import argparse
import copy
import json
from types import SimpleNamespace

import recovery_task as study
import qualify
from working_set_exp.accounted_contribution import process_reply
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

ANCHOR = '    def test_attributes_bad_port(self):\n        """Check handling of invalid ports."""\n'


class ReferenceAdapter(study.runner.Adapter):
    def __init__(self, module, legacy=False):
        super().__init__(module)
        self.legacy = legacy

    def request_for(self, view):
        request = super().request_for(view)
        if self.legacy:
            request["messages"][0]["content"] = study.read(study.SOURCE / "calls/C02-wire-request.json")["messages"][0]["content"]
        return request


def boundary(folder):
    folder.mkdir(parents=True, exist_ok=False)
    bound = study.source_identities()
    store, log = ArtifactStore(folder), RecordLog(folder / "records.jsonl", "recovery-coordinate-boundary")
    server, model, _ = study.runtime_paths()
    rows, failure = [], None
    try:
        with qualify.RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            loop = study.runner.Loop(folder, store, log, url=url, task_module=ReferenceAdapter(study.Task()),
                source_check=lambda: study.verify_sources(bound), health=lambda: study.pilot.health(folder))
            for condition, legacy in (("ordinary", True), ("ordinary", False), ("focused", False)):
                for recent in (1, 0):
                    session = study.initial_session(condition, recent=recent)
                    adapter = ReferenceAdapter(study.Task(condition), legacy)
                    loop.task = adapter
                    count = loop.measure(session.view())
                    name = f"{'legacy' if legacy else condition}-recent-{recent}"
                    study.save(folder, name + "-input.json", adapter.request_for(session.view()))
                    rows.append(dict(name=name, input_tokens=count, admitted=count <= 23808))
            for condition in ("ordinary", "focused"):
                session = study.initial_session(condition)
                adapter = ReferenceAdapter(study.Task(condition))
                loop.task = adapter
                before = copy.deepcopy(session.ranges)
                session.mark_delivered(session.view())
                session.begin_request()
                reply = dict(discussion="Researcher qualification of existing coordinate discovery.",
                    operation=dict(action="search", path=study.TEST,
                                   query="def test_attributes_bad_port", offset=0, limit=1))
                host = process_reply(session, reply, loop.measure, adapter.preceding_feedback)
                study.save(folder, condition + "-search-result.json", host)
                study.save(folder, condition + "-search-state.json", study.snapshot(session))
                result = host["operations"][0]["result"]
                study.require(result.get("accepted") and result.get("matches") and result["matches"][0]["line"] == 716,
                              "exact coordinate search was not returned")
                study.require(session.ranges == before and session.last["result"] == result,
                              "search displaced selection or lost its complete result")
                count = loop.measure(session.view())
                study.require(count <= 23808, "search feedback does not fit")
                rows.append(dict(name=condition + "-coordinate-search", returned_line=716,
                                 input_tokens=count, selected_source_unchanged=True,
                                 complete_result_in_next_input=True))
                session.mark_delivered(session.view())
                session.begin_request()
                action = dict(action="work_on", sources=[
                    dict(path=study.TEST, start_line=result["matches"][0]["line"], end_line=result["matches"][0]["line"]+3),
                    dict(path=study.TEST, start_line=1, end_line=20),
                    dict(path="Lib/urllib/parse.py", start_line=170, end_line=250)], results=[])
                selected = process_reply(session, dict(discussion="Use the actual returned coordinate.",
                    account="The implementation governs expectations; tests and documentation are not yet saved or checked.",
                    operation=action), loop.measure, adapter.preceding_feedback)
                study.require(all(op["result"].get("accepted") for op in selected["operations"]), "coordinate group failed")
                study.save(folder, condition + "-group-result.json", selected)
                study.save(folder, condition + "-group-state.json", study.snapshot(session))
                rows.append(dict(name=condition + "-coordinate-group", input_tokens=loop.measure(session.view()),
                                 author="researcher", model_completion_requests=0))
    except BaseException as error:
        failure = error
        study.save(folder, "FAILED.json", dict(type=type(error).__name__, message=str(error)))
    study.save(folder, "RESULTS.json", dict(status="failed_preserved" if failure else "qualified",
        cases=rows, source_sha256=bound, model_completion_requests=0,
        memory=qualify.RUNTIME.memory_stats(folder / "memory.csv")))
    files = qualify.RUNTIME.file_inventory(folder)
    study.save(folder, "SEAL.json", dict(files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))
    if failure:
        raise failure
    print(json.dumps(rows, indent=2), flush=True)


def scripted_reply(module, session, number):
    def reply(action, account=None):
        result = dict(discussion="Researcher-scripted qualification; not Qwen work.")
        if account is not None:
            result["account"] = account
        result["operation"] = action
        return result
    def patch(path, old, new, account):
        return reply(dict(action="patch", path=path, old=old, new=new,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256(path)), account)
    if number == 1:
        return reply(dict(action="search", path=study.TEST, query="def test_attributes_bad_port", offset=0, limit=1))
    if number == 2:
        result = session.pairs[-1]["result"]
        study.require(result["accepted"] and len(result["matches"]) == 1, "use actual coordinate feedback")
        line = result["matches"][0]["line"]
        return reply(dict(action="work_on", sources=[
            dict(path=study.TEST, start_line=line, end_line=line+3),
            dict(path=study.TEST, start_line=1, end_line=20),
            dict(path="Lib/urllib/parse.py", start_line=170, end_line=250)], results=[]),
            "The implementation governs expectations; tests and documentation are not yet saved or checked.")
    if number == 3:
        text = (study.original.AREA / "REFERENCE_TEST.py").read_text(encoding="utf-8")
        study.require(text.startswith("class PortAccessContractTests(unittest.TestCase):\n"), "reference class differs")
        method = text.split("\n", 1)[1]
        if module.scenario == "correction":
            method = method.replace("Port out of range 0-65535", "WRONG RANGE MESSAGE")
        return patch(study.TEST, ANCHOR, method + "\n" + ANCHOR,
                     "These saved expectations need the actual tests result. Documentation is still unfinished.")
    if module.scenario == "correction":
        if number == 4:
            return patch(study.TEST, "WRONG RANGE MESSAGE", "Port out of range 0-65535",
                         "The failed test reports the actual message. Correct the expectation without changing the library.")
        number -= 1
    if number == 4:
        return reply(dict(action="work_on", sources=[dict(path=study.DOC, start_line=1, end_line=55)], results=[]),
                     "Tests passed in their scope. Saved tests remain; documentation and its examples still need completion.")
    if number == 5:
        return patch(study.DOC, qualify.DOC_ANCHOR,
            (study.original.AREA / "REFERENCE_DOC.txt").read_text(encoding="utf-8") + "\n" + qualify.DOC_ANCHOR,
            "The documentation is a proposal until the actual public check; prose also receives independent review.")
    if number == 6:
        return reply(dict(action="submit", expected_candidate_id=session.candidate.candidate_id))
    raise AssertionError("undeclared scripted route")


def publish():
    decision = study.read(study.AREA / "DECISION.json")
    study.require(decision["compare_framing"] is True and decision["frame_sha256"] == sha256_file(study.FRAME_PATH),
                  "framing comparison not selected")
    for condition in ("focused", "ordinary"):
        module = study.Task(condition)
        initial = study.read(module.PACKAGE / "QUALIFICATION.json")["initial"]
        correction = study.Task(condition, "correction").PACKAGE
        study.require(study.read(correction / "SEAL.json")["status"] == "qualified_no_model_inference", "correction not qualified")
        study.save(study.AREA, module.MANIFEST.name, dict(actor=study.ACTOR, seed=study.SEED,
            maximum_requests=study.MAX_REQUESTS, maximum_operations=study.MAX_OPERATIONS,
            source_sha256=study.source_identities(), preparation_seal_sha256=sha256_file(module.PACKAGE / "SEAL.json"),
            correction_seal_sha256=sha256_file(correction / "SEAL.json"), initial=initial,
            condition=condition, order=["focused", "ordinary"], starting_candidate=study.starting_candidate().candidate_id,
            decision_sha256=sha256_file(study.AREA / "DECISION.json"), initial_account=None,
            initial_selection="same actual broad selection; common zero recent rows; complete latest rejection",
            owner_direction="Proceed as recommended with the declared recovery framing comparison and actual-result continuation.",
            no_live_coaching=True, automatic_retry=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("boundary", "route", "publish", "run", "verify"))
    parser.add_argument("--condition", default="ordinary", choices=("ordinary", "focused"))
    parser.add_argument("--scenario", default="complete", choices=("complete", "correction"))
    parser.add_argument("--version", default="001")
    args = parser.parse_args()
    module = study.Task(args.condition, args.scenario, args.version)
    if args.mode == "boundary":
        boundary(study.AREA / ("boundary-" + args.version))
    elif args.mode == "route":
        qualify.manage.prepare_one(module, scripted_reply, [True, True] if args.scenario == "complete" else [False, True, True])
    elif args.mode == "publish":
        publish()
    elif args.mode == "run":
        manifest = study.read(module.MANIFEST)
        study.require(sha256_file(study.AREA / "DECISION.json") == manifest["decision_sha256"], "decision changed")
        study.require(sha256_file(study.Task(args.condition, "correction").PACKAGE / "SEAL.json") == manifest["correction_seal_sha256"], "correction changed")
        if args.condition == "ordinary":
            study.require((study.Task("focused").RUN / "RESPONSE_SEAL.json").is_file(), "frozen order requires focused closure")
        study.runner.run_once(SimpleNamespace(owner_direction=manifest["owner_direction"], manifest_sha256=sha256_file(module.MANIFEST)), module)
    else:
        result = qualify.manage.verify(module, module.RUN)
        study.save(study.AREA / "review", f"VERIFICATION-{args.condition}.json", result)
        print(json.dumps(result, indent=2))
