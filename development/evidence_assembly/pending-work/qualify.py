"""Exact saved-proposal route from the real rejection; no model inference."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import study
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import completion_request_bytes, process_reply
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

AREA = Path(__file__).resolve().parent
TASK = study.Task("assembled")
SOURCE = TASK.RUN
RUNTIME = study.prior.base.base
TEST = "Lib/test/test_configparser.py"
DOC = "Doc/library/configparser.rst"
PROPOSAL = "EVT-0071"
PROPOSED_ID = "017b4b8b2216a6cf18531662b939cf357caa595d7bdee27a168ee1f40bb20cf6"
GROUP = [s for s in study.GROUPS["assembled"]
         if s["path"] != TEST or s["start_line"] in (1, 2200)]
_spec = importlib.util.spec_from_file_location("pending_qualification_legacy",
    study.ROOT / "development/working_set_continuation/manage.py")
legacy = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(legacy)


def identities():
    paths = [Path(__file__), AREA / "SPEC.md", SOURCE / "RESPONSE_SEAL.json"]
    return {**TASK.source_identities(),
            **{p.relative_to(study.ROOT).as_posix(): sha256_file(p) for p in paths}}


def verify_inventory(folder, seal_name):
    seal = study.read(folder / seal_name)
    study.require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"],
                  "seal inventory differs")
    for row in seal["files"]:
        p = folder / row["path"]
        study.require(p.stat().st_size == row["size_bytes"] and sha256_file(p) == row["sha256"],
                      "changed evidence: " + str(p))
    study.prior.verify_sources(seal["source_sha256"])
    return seal


def measurements(folder):
    counts = {}
    for record in verify_records(folder / "records.jsonl", folder):
        if record["record_type"] != "native_input_prepared":
            continue
        row = record["payload"]
        stem = row["stem"]
        request = study.read(folder / (stem + "-endpoint-request.json"))
        native = (folder / (stem + "-native.txt")).read_bytes()
        study.require(native == TASK.expected_native(request) ==
                      study.read(folder / (stem + "-template.json"))["prompt"].encode(),
                      "native rendering differs")
        study.require((folder / (stem + "-wire-request.json")).read_bytes() ==
                      completion_request_bytes(request), "wire differs")
        study.require(len(study.read(folder / (stem + "-tokens.json"))["tokens"]) == row["prompt_tokens"],
                      "native token count differs")
        counts[sha256_bytes(canonical_json_bytes(request))] = row["prompt_tokens"]
    return counts


def checkpoint():
    verify_inventory(SOURCE, "RESPONSE_SEAL.json")
    counts = measurements(SOURCE)
    session, adapter = TASK.initial_session(), runner.Adapter(TASK)
    def measure(view):
        return counts[sha256_bytes(canonical_json_bytes(adapter.request_for(view)))]
    for i in range(1, 5):
        tag = f"C{i:02d}"
        study.require(completion_request_bytes(adapter.request_for(session.view())) ==
                      (SOURCE / f"calls/{tag}-wire-request.json").read_bytes(), "prefix input differs")
        session.mark_delivered(session.view())
        session.begin_request()
        result = process_reply(session, study.read(SOURCE / f"calls/{tag}-reply.json"),
                               measure, adapter.preceding_feedback)
        study.require(result == study.read(SOURCE / f"calls/{tag}-host-result.json"), "prefix result differs")
    study.require(canonical_json_bytes(TASK.snapshot(session)) ==
                  (SOURCE / "after/C04-O01-state.json").read_bytes(), "rejection checkpoint differs")
    study.require(session.candidate.candidate_id == study.STARTING_ID and
                  session.requests_used == session.calls_used == 4, "checkpoint allowance differs")
    return session, adapter


def reply(session, index):
    response = dict(discussion="Researcher-selected offline feasibility; no model response.")
    if index == 1:
        response["operation"] = dict(action="work_on", sources=copy.deepcopy(GROUP), results=[])
    elif index == 2:
        response["operation"] = dict(action="reopen_event", handle=PROPOSAL, offset=0)
    elif index == 3:
        page = session.saved[PROPOSAL]
        study.require(page["offset"] == 0 and page["next_offset"] is None, "proposal incomplete")
        response["operation"] = json.loads(page["exact_utf8"])
    elif index == 4:
        old = ".. exception:: InterpolationSyntaxError\n"
        response["operation"] = dict(action="patch", path=DOC, old=old,
            new=(study.AREA / "REFERENCE_DOC.txt").read_text(encoding="utf-8") + "\n" + old,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256(DOC))
        response["check_after"] = "public"
    else:
        raise AssertionError("undeclared route step")
    return response


def visible_requirements(session, original_action, require_proposal):
    view = session.view()
    visible = session._verified_source_ranges(view["working_set"]["sources"] +
                                              session.feedback_sources(view["latest_feedback"]))
    study.require(any(s["path"] == "Lib/configparser.py" and s["start_line"] <= 170 and
                      s["end_line"] >= 180 for s in visible), "base formatter left working input")
    if not require_proposal:
        return
    page = session.saved[PROPOSAL]
    study.require(page["offset"] == 0 and page["next_offset"] is None and
                  page["exact_utf8"].encode() == canonical_json_bytes(original_action), "proposal changed")
    pages = view["working_set"]["saved_results"] + (view["latest_feedback"] or {}).get("result", {}).get("saved_results", [])
    if (view["latest_feedback"] or {}).get("result", {}).get("kind") == "saved_bytes":
        pages.append(view["latest_feedback"]["result"])
    study.require(page in pages, "proposal not present in next input")


def route(session, adapter, measure, save_step):
    original_action = study.read(SOURCE / "calls/C04-operation-01.json")["action"]
    initial_candidate = session.candidate
    saved_tests = None
    rows = []
    for index in range(1, 5):
        before = measure(session.view())
        study.require(before <= 23808, "next input exceeds hard limit")
        session.mark_delivered(session.view())
        session.begin_request()
        proposed = reply(session, index)
        actual = process_reply(session, proposed, measure, adapter.preceding_feedback)
        after = measure(session.view())
        study.require(after <= 23808 and not session.delivery_blocked and
                      all(op["result"]["accepted"] for op in actual["operations"]), "route operation failed")
        visible_requirements(session, original_action, index >= 2)
        if index == 1:
            study.require(session.candidate == initial_candidate and session.ranges ==
                          sorted(GROUP, key=lambda s: (s["path"], s["start_line"])), "group altered source or was shortened")
        if index == 3:
            study.require(proposed["operation"] == original_action and
                          session.candidate.candidate_id == PROPOSED_ID, "not the exact previously rejected proposal")
            saved_tests = session.candidate.file_map[TEST]
        if index == 4:
            study.require(session.candidate.file_map[TEST] == saved_tests, "saved tests changed during documentation/closure")
            study.require(session.check_state()["passed"] and session.check_state()["applies_to_current"],
                          "actual current check did not pass")
        rows.append(dict(step=index, input_tokens=before, next_input_tokens=after,
                         requests_used=session.requests_used, operations_used=session.calls_used,
                         operation_count=len(actual["operations"]), candidate=session.candidate.candidate_id))
        save_step(index, proposed, actual, session)
    study.require(not session.submitted and session.requests_used == 8 and session.calls_used == 9,
                  "route changed the original remaining allowance")
    try:
        session.begin_request()
    except ValueError:
        pass
    else:
        raise AssertionError("submission request should be unavailable")
    changed = [p for p in initial_candidate.file_map if
               initial_candidate.file_map[p] != session.candidate.file_map[p]]
    study.require(sorted(changed) == sorted([TEST, DOC]), "unrelated work changed")
    return rows


def qualify(folder):
    study.require(not folder.exists(), "preserve existing qualification, including failures")
    folder.mkdir(parents=True)
    bound = identities()
    session, adapter = checkpoint()
    store = ArtifactStore(folder)
    log = legacy.QualificationLog(folder / "records.jsonl", "pending-work-qualification", task_module=TASK)
    server, model, _ = TASK.runtime_paths()
    rows, error = [], None
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            def deny_completion(*args, **kwargs):
                raise AssertionError("completion forbidden in offline qualification")
            loop = runner.Loop(folder, store, log, url=url, task_module=adapter, post=deny_completion,
                               source_check=lambda: TASK.verify_sources(bound))
            loop.snapshot(session, "starting")
            def save_step(index, proposed, actual, current):
                tag = f"Q{index}"
                log.append("scripted_step", dict(id=tag, no_model_response=True),
                    [store.put(f"steps/{tag}-reply.json", canonical_json_bytes(proposed)),
                     store.put(f"steps/{tag}-result.json", canonical_json_bytes(actual))])
                loop.snapshot(current, f"after/{tag}")
                store.put(f"after/{tag}-wire-request.json", completion_request_bytes(adapter.request_for(current.view())))
                print(tag, "accepted; next input", loop.measure(current.view()), flush=True)
            rows = route(session, adapter, loop.measure, save_step)
            study.require(not loop.sent, "inference occurred")
            loop.snapshot(session, "final")
    except BaseException as problem:
        error = problem
        study.save(folder, "FAILED.json", dict(type=type(problem).__name__, message=str(problem)))
    finally:
        study.save(folder, "QUALIFICATION.json", dict(status="failed_preserved" if error else "qualified_offline",
            starting_at="assembled after C04 rejection", source_seal_sha256=sha256_file(SOURCE / "RESPONSE_SEAL.json"),
            researcher_selected=True, model_completion_requests=0, original_requests_remaining=4,
            original_operations_remaining=8, rows=rows, submitted=session.submitted,
            exact_proposal_handle=PROPOSAL, memory=RUNTIME.memory_stats(folder / "memory.csv"),
            port_free=RUNTIME.port_free(RUNTIME.PORT)))
        legacy.seal(folder, "failed_preserved" if error else "qualified_no_model_inference", bound, completion_requests=0)
    if error:
        raise error


def verify(folder):
    seal = verify_inventory(folder, "SEAL.json")
    study.require(seal["completion_requests"] == 0, "qualification sent inference")
    records = verify_records(folder / "records.jsonl", folder)
    closed = [r["payload"] for r in records if r["record_type"] == "runtime_closed"]
    study.require(len(closed) == 1 and closed[0]["owned_server_shutdown_verified"] and
                  closed[0]["dedicated_port_free"], "runtime closure incomplete")
    study.require(all(r["payload"].get("completion_sent") is not True for r in records), "completion was sent")
    for name, digest in seal["private_runtime_files_local_only"].items():
        study.require(sha256_file(folder / "private-runtime" / name) == digest, "private custody differs")
    counts = measurements(folder)
    session, adapter = checkpoint()
    def measure(view):
        return counts[sha256_bytes(canonical_json_bytes(adapter.request_for(view)))]
    def exact(index, proposed, actual, current):
        tag = f"Q{index}"
        study.require(proposed == study.read(folder / f"steps/{tag}-reply.json") and
                      actual == study.read(folder / f"steps/{tag}-result.json"), "step differs")
        study.require(canonical_json_bytes(TASK.snapshot(current)) ==
                      (folder / f"after/{tag}-state.json").read_bytes(), "state differs")
        study.require(TASK.candidate_bytes(current.candidate) ==
                      (folder / f"after/{tag}-candidate.json").read_bytes(), "saved work differs")
        study.require(completion_request_bytes(adapter.request_for(current.view())) ==
                      (folder / f"after/{tag}-wire-request.json").read_bytes(), "next input differs")
    rows = route(session, adapter, measure, exact)
    study.require(rows == study.read(folder / "QUALIFICATION.json")["rows"], "measurements differ")
    return dict(status="replayed_exactly", new_model_requests=0, scripted_requests=4,
                scripted_operations=5, native_inputs=len(counts), custody_records=len(records),
                source_files=len(seal["source_sha256"]), submitted=session.submitted,
                closure="checked contribution; no request remains for submission",
                original_allowances_preserved=True, complete_proposal_and_base_source_present=True,
                saved_tests_preserved=True, actual_current_check_passes=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("qualify", "verify"))
    parser.add_argument("--folder", default="qualification-001")
    args = parser.parse_args()
    folder = AREA / args.folder
    if args.mode == "qualify":
        qualify(folder)
    else:
        result = verify(folder)
        study.save(AREA, f"VERIFICATION-{folder.name}.json", result)
        print(json.dumps(result, indent=2))
