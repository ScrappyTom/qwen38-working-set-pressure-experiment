"""Prepare and execute the declared pair through the existing contribution runner."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import study
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

RUNTIME = study.prior.base.base
TEST_PATH, DOC_PATH = "Lib/test/test_configparser.py", "Doc/library/configparser.rst"
TEST_ANCHOR = "if __name__ == '__main__':\n    unittest.main()\n"
DOC_ANCHOR = ".. exception:: InterpolationSyntaxError\n"
GOOD_ARGS = "expected_args = ('value', 'main', raw, reference)"
BAD_ARGS = "expected_args = ('wrong-option', 'main', raw, reference)"


def load_helper(name, relative):
    spec = importlib.util.spec_from_file_location(name, study.ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


legacy = load_helper("continuation_qualification", "development/working_set_continuation/manage.py")


def reference_reply(module, session, request_number):
    index = request_number - 1
    action = lambda value: dict(discussion="Offline qualification only; no model produced this response.", operation=value)
    if module.condition == "broad":
        if index == 0:
            return action(dict(action="work_on", sources=copy.deepcopy(study.GROUPS["assembled"]), results=[]))
        index -= 1
    def patch(path, old, new, check=False):
        result = action(dict(action="patch", path=path, old=old, new=new,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=sha256_bytes(session.candidate.file_map[path])))
        if check:
            result["check_after"] = "public"
        return result
    test = (study.AREA / "REFERENCE_TEST.py").read_text(encoding="utf-8")
    if index == 0:
        if module.scenario == "correction":
            study.require(test.count(GOOD_ARGS) == 1, "reference correction anchor differs")
            test = test.replace(GOOD_ARGS, BAD_ARGS)
        return patch(TEST_PATH, TEST_ANCHOR, test + "\n\n" + TEST_ANCHOR)
    if module.scenario == "complete":
        if index == 1:
            return action(dict(action="work_on", sources=[r for r in study.GROUPS["assembled"] if r["path"] == DOC_PATH], results=[]))
        if index == 2:
            return patch(DOC_PATH, DOC_ANCHOR, (study.AREA / "REFERENCE_DOC.txt").read_text(encoding="utf-8") + "\n" + DOC_ANCHOR, True)
        if index == 3:
            return action(dict(action="submit", expected_candidate_id=session.candidate.candidate_id))
    else:
        if index == 1:
            return patch(DOC_PATH, DOC_ANCHOR, (study.AREA / "REFERENCE_DOC.txt").read_text(encoding="utf-8") + "\n" + DOC_ANCHOR, True)
        if index == 2:
            return action(dict(action="work_on", sources=[dict(path=TEST_PATH, start_line=2200, end_line=0),
                dict(path="Lib/configparser.py", start_line=256, end_line=275)], results=[]))
        if index == 3:
            return patch(TEST_PATH, BAD_ARGS, GOOD_ARGS, True)
        if index == 4:
            return action(dict(action="submit", expected_candidate_id=session.candidate.candidate_id))
    raise AssertionError("undeclared scripted response")


def verify(module, folder):
    verifier = load_helper("assembly_replay", "development/working_set_continuation/review/verify.py")
    verifier.task = module
    result = verifier.verify(folder)
    seal_name = "RESPONSE_SEAL.json" if (folder / "RESPONSE_SEAL.json").exists() else "SEAL.json"
    seal = study.read(folder / seal_name)
    records = verify_records(folder / "records.jsonl", folder)
    sent = [r for r in records if r["record_type"] == "invocation_started" and r["payload"].get("completion_sent") is True]
    closed = [r["payload"] for r in records if r["record_type"] == "runtime_closed"]
    study.require(len(closed) == 1 and closed[0]["owned_server_shutdown_verified"] and closed[0]["dedicated_port_free"], "runtime closure incomplete")
    if sent:
        for r in sent:
            tag = r["payload"]["id"]
            response_path = folder / f"calls/{tag}-endpoint-response.json"
            if not response_path.exists():
                continue
            response = study.read(response_path)
            usage = response["usage"]
            study.require(usage["prompt_tokens"] == r["payload"]["prompt_tokens"] and
                usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"] <= 56576,
                "actual generation accounting differs")
            study.require(usage["prompt_tokens_details"]["cached_tokens"] == response["timings"]["cache_n"] == 0, "cache reused")
    else:
        study.require(seal.get("completion_requests") == 0, "qualification sent inference")
    return {**result, "actual_completion_requests":len(sent), "owned_runtime_closed":True}


def prepare_one(module, scripted_reply=None, expected_checks=None):
    folder = module.PACKAGE
    study.require(not folder.exists(), "preserve existing preparation, including failures")
    folder.mkdir(parents=True)
    bound = module.source_identities()
    store = ArtifactStore(folder)
    log = legacy.QualificationLog(folder / "records.jsonl", f"assembly-qualification-{module.condition}-{module.scenario}", task_module=module)
    session, adapter = module.initial_session(), runner.Adapter(module)
    server, model, _ = module.runtime_paths()
    error, initial, outcome, peak = None, None, None, None
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            def scripted(url, route, wire, timeout):
                study.require(route == "/v1/chat/completions", "unexpected intercepted route")
                request = json.loads(wire)
                count = loop.cache[sha256_bytes(canonical_json_bytes(request))]["prompt_tokens"]
                reply = (scripted_reply or reference_reply)(module, session, loop.sent)
                return canonical_json_bytes(dict(choices=[dict(finish_reason="stop", message=dict(reasoning_content="", content=json.dumps(reply)))],
                    usage=dict(prompt_tokens=count, completion_tokens=1, total_tokens=count+1, prompt_tokens_details=dict(cached_tokens=0)), timings=dict(cache_n=0)))
            loop = runner.Loop(folder, store, log, url=url, task_module=adapter, post=scripted,
                               source_check=lambda: module.verify_sources(bound))
            loop.measure(session.view())
            initial = {k:next(iter(loop.cache.values()))[k] for k in ("prompt_tokens", "request_sha256", "native_sha256", "wire_request_sha256")}
            store.put("initial-wire-request.json", completion_request_bytes(adapter.request_for(session.view())))
            outcome = loop.execute(session)
            study.require(outcome["submitted"] and session.check_state()["applies_to_current"], "scripted contribution incomplete")
            checks = [p["result"]["passed"] for p in session.pairs[session.starting_archive_length:] if p["response"]["action"] == "check"]
            expected = expected_checks if expected_checks is not None else ([True] if module.scenario == "complete" else [False, True])
            study.require(checks == expected, "correction feedback path differs")
            peak = max(r["prompt_tokens"] for r in loop.cache.values())
            study.require(all(r["payload"].get("completion_sent") is not True for r in verify_records(folder / "records.jsonl", folder)), "qualification sent inference")
    except BaseException as problem:
        error = problem
        study.save(folder, "FAILED.json", dict(type=type(problem).__name__, message=str(problem)))
    finally:
        qualification = dict(condition=module.condition, scenario=module.scenario, initial=initial,
            scripted_outcome=outcome, peak_native_input=peak, completion_requests=0,
            memory=RUNTIME.memory_stats(folder / "memory.csv"), port_free=RUNTIME.port_free(RUNTIME.PORT))
        study.save(folder, "QUALIFICATION.json", qualification)
        legacy.seal(folder, "failed_preserved" if error else "qualified_no_model_inference", bound, completion_requests=0)
    if error:
        raise error
    checked = verify(module, folder)
    study.save(folder.parent, f"VERIFICATION-{module.scenario}.json", checked)
    print(module.condition, module.scenario, initial["prompt_tokens"], peak, "qualified; zero completions", flush=True)
    return qualification


def prepare():
    reports = []
    for condition in ("broad", "assembled"):
        for scenario in ("complete", "correction"):
            reports.append(prepare_one(study.Task(condition, scenario)))
    for condition in ("broad", "assembled"):
        module = study.Task(condition)
        initial = next(r["initial"] for r in reports if r["condition"] == condition and r["scenario"] == "complete")
        study.save(study.AREA, module.MANIFEST.name, dict(actor=module.ACTOR, seed=module.SEED,
            maximum_requests=module.MAX_REQUESTS, maximum_operations=module.MAX_OPERATIONS,
            source_sha256=module.source_identities(), preparation_seal_sha256=sha256_file(module.PACKAGE / "SEAL.json"),
            initial=initial, starting_candidate=study.STARTING_ID, condition=condition,
            owner_direction="Proceed after the evidence-assembly comparison recommendation",
            initial_selection="researcher_supplied", no_live_coaching=True, automatic_retry=False,
            correction_qualification_sha256=sha256_file(study.Task(condition,"correction").PACKAGE / "SEAL.json")))
    study.save(study.AREA, "QUALIFICATION.json", dict(reports=reports, completion_requests=0))


def execute(condition):
    module = study.Task(condition)
    if condition == "assembled":
        study.require((study.Task("broad").RUN / "RESPONSE_SEAL.json").exists(), "frozen order is broad then assembled")
    manifest = study.read(module.MANIFEST)
    corrected = study.Task(condition, "correction").PACKAGE
    study.require(sha256_file(corrected / "SEAL.json") == manifest["correction_qualification_sha256"], "correction qualification differs")
    runner.run_once(SimpleNamespace(owner_direction=manifest["owner_direction"], manifest_sha256=sha256_file(module.MANIFEST)), module=module)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "execute", "verify"))
    parser.add_argument("--condition", choices=("broad", "assembled"))
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    elif args.mode == "execute":
        study.require(args.condition, "choose a condition")
        execute(args.condition)
    else:
        study.require(args.condition, "choose a condition")
        module = study.Task(args.condition)
        value = verify(module, module.RUN)
        study.save(study.AREA / "review", f"VERIFICATION-{args.condition}.json", value)
        print(value)
