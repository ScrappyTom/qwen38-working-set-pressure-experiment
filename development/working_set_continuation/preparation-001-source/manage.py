"""Qualification and execution using the existing uncoached runner; no retry."""
import argparse
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import interpolation_contribution as task
import parser_roundtrip as old_task
import run_uncoached_contribution as runner
from test_working_continuation import TEST_PATH, DOC_PATH, TEST_ANCHOR, DOC_ANCHOR
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_session import ContributionSession
from working_set_exp.contribution_reply import completion_request_bytes, process_reply
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.working_session import INPUT_LIMIT

RUNTIME = task.base.base


class QualificationLog(runner.RunLog):
    def append(self, kind, payload, artifacts):
        payload = {**payload, "qualification_only": True, "completion_sent": False}
        if kind in ("invocation_started", "response_received", "response_extracted", "invocation_completed"):
            payload["scripted_response_not_model_output"] = True
        return super().append(kind, payload, artifacts)


def seal(folder, status, bound, **values):
    files = RUNTIME.file_inventory(folder)
    task.save(folder, "SEAL.json", dict(status=status, source_sha256=bound, files=files,
        aggregate_sha256=sha256_bytes(canonical_json_bytes(files)), **values,
        private_runtime_files_local_only={p.name: sha256_file(p) for p in (folder / "private-runtime").glob("*") if p.is_file()}))


def source_union(s, view):
    return s._verified_source_ranges(view["working_set"]["sources"] + s.feedback_sources(view["latest_feedback"]))


def broad_states(folder, loop):
    report = []
    for attempt, call, prior in (("A02", 13, 12), ("A03", 6, 5)):
        origin = task.ROOT / "development/reasoning_allocation/run-001" / attempt
        old_request = task.read(origin / f"calls/C{call:02d}-wire-request.json")
        old_view = json.loads(old_request["messages"][1]["content"])["workspace"]
        state = task.read(origin / f"after/C{prior:02d}-O01-state.json")
        data = task.read(origin / f"after/C{prior:02d}-O01-candidate.json")
        candidate = Candidate.create({r["path"]: r["content_utf8"].encode() for r in data["files"]}, max_file_bytes=data["max_file_bytes"])
        s = ContributionSession(candidate, old_task.checker(), old_view["task"], pairs=state["pairs"], call_limit=state["call_limit"])
        for key in ("ranges", "saved", "last", "starting_archive_length", "delivered_sources"):
            setattr(s, key, copy.deepcopy(state[key]))
        s.diffs = {int(k): v for k, v in state["diffs"].items()}
        corrected = s.view()
        task.require(old_view["latest_feedback"] == corrected["latest_feedback"], "feedback changed")
        task.require(source_union(s, old_view) == source_union(s, corrected), "visible source union changed")
        expected = copy.deepcopy(old_view)
        expected["working_set"]["sources"] = corrected["working_set"]["sources"]
        task.require(expected == corrected, "correction changes state beyond source duplication")
        counts = {}
        for label, view in (("original", old_view), ("corrected", corrected)):
            request = copy.deepcopy(old_request)
            body = json.loads(request["messages"][1]["content"])
            body["workspace"] = view
            request["messages"][1]["content"] = canonical_json_bytes(body).decode()
            stem = f"broad/{attempt}-C{call:02d}-{label}"
            template, native, tokens, count = loop.native_render(request, stem)
            loop.store.put(stem + "-wire-request.json", completion_request_bytes(request))
            loop.store.put(stem + "-native.txt", native)
            if label == "original":
                # Exact saved prompt, rather than a text-length approximation.
                original_record = next(r for r in verify_records(origin / "records.jsonl", origin)
                    if r["record_type"] == "invocation_started" and r["payload"]["id"] == f"C{call:02d}")
                old_native = origin / (original_record["payload"]["input_stem"] + "-native.txt")
                task.require(native == old_native.read_bytes() and count == original_record["payload"]["prompt_tokens"], "saved native reproduction differs")
            counts[label] = count
        s.mark_delivered(corrected)
        # Cross a newly displayed fragment boundary in the actual source, without
        # committing the probe's deliberately non-task change to the model start.
        latest = s.feedback_sources(s.last)[0]
        start = max(1, latest["returned_start_line"] - 1)
        end = latest["returned_start_line"] + 1
        fragment = s.source(dict(path=latest["path"], start_line=start, end_line=end))["content"]
        task.require(candidate.file_map[latest["path"]].decode().count(fragment) == 1, "probe anchor not unique")
        result = s.execute(dict(action="patch", path=latest["path"], old=fragment, new=fragment + "# offline boundary probe\n",
            expected_candidate_id=candidate.candidate_id, expected_file_sha256=candidate.file_sha256(latest["path"])), lambda view: 500)
        task.require(result["accepted"], "visible cross-fragment source rejected")
        report.append(dict(attempt=attempt, call=call, native_tokens=counts,
            removed_native_tokens=counts["original"]-counts["corrected"], feedback_unchanged=True,
            source_union_unchanged=True, cross_fragment_edit_accepted=True))
    return report


def reference_reply(session, index):
    def action(value, check=False):
        return dict(discussion="Scripted offline feasibility only", operation=value, **({"check_after": "public"} if check else {}))
    def patch(path, old, new, check=False):
        return action(dict(action="patch", path=path, old=old, new=new,
            expected_candidate_id=session.candidate.candidate_id, expected_file_sha256=session.candidate.file_sha256(path)), check)
    if index == 1:
        return action(dict(action="work_on", sources=[dict(path="Lib/configparser.py", start_line=256, end_line=276),
            dict(path="Lib/configparser.py", start_line=365, end_line=505),
            dict(path=TEST_PATH, start_line=2200, end_line=2210)], results=[]))
    if index == 2:
        return patch(TEST_PATH, TEST_ANCHOR, (task.AREA / "REFERENCE_TEST.py").read_text(encoding="utf-8") + "\n\n" + TEST_ANCHOR)
    if index == 3:
        return action(dict(action="work_on", sources=[dict(path=DOC_PATH, start_line=334, end_line=425),
            dict(path=DOC_PATH, start_line=1352, end_line=1385)], results=[]))
    if index == 4:
        return patch(DOC_PATH, DOC_ANCHOR, (task.AREA / "REFERENCE_DOC.txt").read_text(encoding="utf-8") + "\n" + DOC_ANCHOR, True)
    if index == 5:
        return action(dict(action="submit", expected_candidate_id=session.candidate.candidate_id))
    raise AssertionError("undeclared scripted request")


def prepare():
    folder = task.PACKAGE
    task.require(not folder.exists(), "preparation exists; preserve failures separately")
    folder.mkdir()
    bound = task.source_identities()
    store = ArtifactStore(folder)
    log = QualificationLog(folder / "records.jsonl", "continuation-qualification", task_module=task)
    session, adapter = task.initial_session(), runner.Adapter(task)
    server, model, _ = task.runtime_paths()
    error, initial, outcome, broad = None, None, None, []
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            def scripted(url, route, wire, timeout):
                task.require(route == "/v1/chat/completions", "unexpected scripted route")
                request = json.loads(wire)
                count = loop.cache[sha256_bytes(canonical_json_bytes(request))]["prompt_tokens"]
                reply = reference_reply(session, loop.sent)
                return canonical_json_bytes(dict(choices=[dict(finish_reason="stop", message=dict(reasoning_content="", content=json.dumps(reply)))],
                    usage=dict(prompt_tokens=count, completion_tokens=1, total_tokens=count+1, prompt_tokens_details=dict(cached_tokens=0)), timings=dict(cache_n=0)))
            loop = runner.Loop(folder, store, log, url=url, task_module=adapter, post=scripted,
                               source_check=lambda: task.verify_sources(bound))
            loop.measure(session.view())
            initial = {k: next(iter(loop.cache.values()))[k] for k in ("prompt_tokens", "request_sha256", "native_sha256", "wire_request_sha256")}
            store.put("initial-wire-request.json", completion_request_bytes(adapter.request_for(session.view())))
            store.put("starting-candidate.json", task.candidate_bytes(session.candidate))
            broad = broad_states(folder, loop)
            outcome = loop.execute(session)
            task.require(outcome["submitted"] and session.requests_used == 5 and session.calls_used == 6, "scripted contribution failed")
            task.require(session.pairs[-2]["result"]["passed"], "reference check did not pass")
            task.require(all(r["payload"].get("completion_sent") is not True for r in verify_records(folder/"records.jsonl", folder)), "qualification sent inference")
    except BaseException as problem:
        error = problem
        task.save(folder, "FAILED.json", dict(type=type(problem).__name__, message=str(problem)))
    finally:
        qualification = dict(initial=initial, broad_states=broad, scripted_outcome=outcome, completion_requests=0,
            memory=RUNTIME.memory_stats(folder / "memory.csv"), port_free=RUNTIME.port_free(RUNTIME.PORT))
        task.save(folder, "QUALIFICATION.json", qualification)
        seal(folder, "failed_preserved" if error else "qualified_no_model_inference", bound, completion_requests=0)
    if error:
        raise error
    task.save(task.AREA, "EXECUTION_MANIFEST.json", dict(actor=task.ACTOR, seed=task.SEED,
        maximum_requests=task.MAX_REQUESTS, maximum_operations=task.MAX_OPERATIONS,
        source_sha256=bound, preparation_seal_sha256=sha256_file(folder / "SEAL.json"), initial=initial,
        owner_direction="Proceed after the two host corrections and next medium contribution recommendation",
        no_live_coaching=True, automatic_retry=False, starting_candidate=task.STARTING_ID))
    print(json.dumps(qualification, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("prepare", "execute"))
    args = parser.parse_args()
    if args.mode == "prepare":
        prepare()
    else:
        runner.run_once(SimpleNamespace(owner_direction="Proceed with the recommended corrected-host medium contribution",
            manifest_sha256=sha256_file(task.MANIFEST)), module=task)
