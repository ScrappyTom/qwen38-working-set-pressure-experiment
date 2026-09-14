"""Native-sized source/action selection from a frozen real rejection; no inference."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import subprocess
from types import ModuleType, SimpleNamespace
from unittest.mock import patch

import study
import run_uncoached_contribution as runner
from working_set_exp import working_view
from working_set_exp.contribution_reply import completion_request_bytes, process_reply
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

AREA = Path(__file__).resolve().parent
FROZEN = "99052976e2a40ee8aa29247a5bd6f8587007b972"
VIEW = "src/working_set_exp/working_view.py"
_spec = importlib.util.spec_from_file_location("preceding_pending_qualification",
    AREA.parent / "pending-work/qualify.py")
prior = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(prior)
TASK, RUNTIME, SOURCE = prior.TASK, prior.RUNTIME, prior.SOURCE


def frozen_view_bytes():
    return subprocess.run(["git", "show", f"{FROZEN}:{VIEW}"], cwd=study.ROOT,
                          check=True, capture_output=True).stdout


def checkpoint():
    """Replay the old prefix with its exact source, then resume the current host."""
    source = frozen_view_bytes()
    frozen = ModuleType("working_set_exp.frozen_group_qualification_view")
    frozen.__package__ = "working_set_exp"
    exec(compile(source, FROZEN + ":" + VIEW, "exec"), frozen.__dict__)

    def historical_inventory(folder, seal_name):
        seal = study.read(folder / seal_name)
        study.require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"],
                      "historical inventory differs")
        for row in seal["files"]:
            path = folder / row["path"]
            study.require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"],
                          "historical artifact differs: " + row["path"])
        for name, digest in seal["source_sha256"].items():
            actual = sha256_bytes(source) if name == VIEW else sha256_file(study.ROOT / name)
            study.require(actual == digest, "historical source differs: " + name)
        return seal

    with patch.object(working_view, "schema", frozen.schema), \
         patch.object(working_view, "system_prompt", frozen.system_prompt), \
         patch.object(prior, "verify_inventory", historical_inventory):
        session, old_adapter = prior.checkpoint()
    adapter = runner.Adapter(TASK)
    adapter.preceding_feedback = copy.deepcopy(old_adapter.preceding_feedback)
    return session, adapter


def identities():
    paths = [Path(__file__), AREA / "SPEC.md", AREA / "native.py",
             study.ROOT / "tests/test_working_action_groups.py",
             AREA.parent / "pending-work/qualify.py", SOURCE / "RESPONSE_SEAL.json"]
    return {**TASK.source_identities(),
            **{p.relative_to(study.ROOT).as_posix(): sha256_file(p) for p in paths}}


def reply(session, index):
    if index == 1:
        value = prior.reply(session, 1)
        value["operation"]["results"] = [prior.PROPOSAL]
        return value
    if index in (2, 3):
        return prior.reply(session, index + 1)
    if index == 4:
        return dict(discussion="Researcher-scripted offline closure; no model response.",
                    operation=dict(action="submit", expected_candidate_id=session.candidate.candidate_id))
    raise AssertionError("undeclared scripted step")


def route(session, adapter, measure, save_step):
    initial = session.candidate
    original = study.read(SOURCE / "calls/C04-operation-01.json")["action"]
    history = copy.deepcopy(session.pairs)
    rows, saved_tests = [], None
    for index in range(1, 5):
        before = measure(session.view())
        study.require(before <= 23808, "input exceeds declared ceiling")
        session.mark_delivered(session.view())
        session.begin_request()
        proposed = reply(session, index)
        actual = process_reply(session, proposed, measure, adapter.preceding_feedback)
        after = measure(session.view())
        study.require(after <= 23808 and not session.delivery_blocked and
                      all(op["result"]["accepted"] for op in actual["operations"]), "operation failed")
        prior.visible_requirements(session, original, True)
        study.require(session.pairs[:len(history)] == history, "historical record changed")
        if index == 1:
            study.require(session.candidate == initial and session.ranges ==
                          sorted(prior.GROUP, key=lambda s: (s["path"], s["start_line"])),
                          "acquisition changed source or shortened the selected group")
        if index == 2:
            study.require(canonical_json_bytes(proposed["operation"]) == canonical_json_bytes(original) and
                          session.candidate.candidate_id == prior.PROPOSED_ID, "saved proposal differs")
            saved_tests = session.candidate.file_map[prior.TEST]
        if index >= 3:
            study.require(session.candidate.file_map[prior.TEST] == saved_tests, "saved tests changed")
            checked = session.check_state()
            study.require(checked["passed"] and checked["applies_to_current"], "current check did not pass")
        rows.append(dict(step=index, input_tokens=before, next_input_tokens=after,
                         requests_used=session.requests_used, operations_used=session.calls_used,
                         operation_count=len(actual["operations"]), candidate=session.candidate.candidate_id))
        save_step(index, proposed, actual, session)
    study.require(session.submitted and session.requests_used == 8 and session.calls_used == 9 and
                  session.request_limit == 8 and session.call_limit == 12, "original allowance changed")
    study.require(sorted(p for p in initial.file_map if initial.file_map[p] != session.candidate.file_map[p]) ==
                  sorted([prior.TEST, prior.DOC]), "unrelated work changed")
    study.require(TASK.candidate_bytes(session.candidate) ==
                  (prior.AREA / "qualification-002/final-candidate.json").read_bytes(),
                  "artifact differs from preceding qualified work")
    return rows


def qualify(folder):
    study.require(not folder.exists(), "preserve existing qualification, including failures")
    folder.mkdir(parents=True)
    bound, rows, session, error = identities(), [], None, None
    store = ArtifactStore(folder)
    log = prior.legacy.QualificationLog(folder / "records.jsonl", "grouped-actions-qualification", task_module=TASK)
    try:
        session, adapter = checkpoint()
        study.save(folder, "PREFIX.json", dict(replayed_calls=4, frozen_revision=FROZEN,
            frozen_view_sha256=sha256_bytes(frozen_view_bytes()),
            original_seal_sha256=sha256_file(SOURCE / "RESPONSE_SEAL.json"),
            snapshot_sha256=sha256_bytes(canonical_json_bytes(TASK.snapshot(session)))))
        server, model, _ = TASK.runtime_paths()
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
            study.require(not loop.sent, "model inference occurred")
            loop.snapshot(session, "final")
    except BaseException as problem:
        error = problem
        study.save(folder, "FAILED.json", dict(type=type(problem).__name__, message=str(problem)))
    finally:
        study.save(folder, "QUALIFICATION.json", dict(status="failed_preserved" if error else "qualified_offline",
            frozen_prefix_revision=FROZEN, starting_at="assembled after C04 rejection",
            researcher_selected=True, model_completion_requests=0, original_requests_remaining=4,
            original_operations_remaining=8, rows=rows, submitted=bool(session and session.submitted),
            exact_proposal_handle=prior.PROPOSAL, memory=RUNTIME.memory_stats(folder / "memory.csv"),
            port_free=RUNTIME.port_free(RUNTIME.PORT)))
        prior.legacy.seal(folder, "failed_preserved" if error else "qualified_no_model_inference",
                          bound, completion_requests=0)
    if error:
        raise error


def verify(folder):
    seal = prior.verify_inventory(folder, "SEAL.json")
    study.require(seal["completion_requests"] == 0, "qualification sent inference")
    records = verify_records(folder / "records.jsonl", folder)
    closed = [r["payload"] for r in records if r["record_type"] == "runtime_closed"]
    study.require(len(closed) == 1 and closed[0]["owned_server_shutdown_verified"] and
                  closed[0]["dedicated_port_free"], "runtime closure incomplete")
    study.require(all(r["payload"].get("completion_sent") is not True for r in records), "completion sent")
    for name, digest in seal["private_runtime_files_local_only"].items():
        study.require(sha256_file(folder / "private-runtime" / name) == digest, "private custody differs")
    counts = prior.measurements(folder)
    session, adapter = checkpoint()
    prefix = study.read(folder / "PREFIX.json")
    study.require(prefix == dict(replayed_calls=4, frozen_revision=FROZEN,
        frozen_view_sha256=sha256_bytes(frozen_view_bytes()),
        original_seal_sha256=sha256_file(SOURCE / "RESPONSE_SEAL.json"),
        snapshot_sha256=sha256_bytes(canonical_json_bytes(TASK.snapshot(session)))), "prefix receipt differs")
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
                original_allowances_preserved=True, complete_proposal_and_base_source_present=True,
                saved_tests_preserved=True, same_final_artifact_as_prior_qualification=True,
                actual_current_check_passes=True, frozen_prefix_revision=FROZEN)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("qualify", "verify"))
    parser.add_argument("--folder", default="qualification-001")
    args = parser.parse_args()
    target = AREA / args.folder
    if args.mode == "qualify":
        qualify(target)
    else:
        result = verify(target)
        study.save(AREA, f"VERIFICATION-{target.name}.json", result)
        print(json.dumps(result, indent=2))
