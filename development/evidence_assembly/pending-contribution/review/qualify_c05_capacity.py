"""Post-closure native counterfactual: did the exact pending C02 edit fit at C05?"""
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import pending_task as task
import run_uncoached_contribution as runner
from manage_pending import assembly
from working_set_exp.contribution_reply import completion_request_bytes, process_reply
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

module = task.Task()
task.study.require((module.RUN / "RESPONSE_SEAL.json").exists(), "close the attempt first")
captured = []
original_snapshot = module.snapshot


def capture(session):
    if session.requests_used == 4 and session.calls_used == 4:
        captured.append(copy.deepcopy(session))
    return original_snapshot(session)


module.snapshot = capture
verification = assembly.verify(module, module.RUN)
module.snapshot = original_snapshot
task.study.require(len(captured) == 1, "actual C05 checkpoint not uniquely reconstructed")
session = captured[0]
adapter = runner.Adapter(module)
wire_path = module.RUN / "calls/C05-wire-request.json"
task.study.require(completion_request_bytes(adapter.request_for(session.view())) == wire_path.read_bytes(),
                   "counterfactual does not start from the actual C05 input")
proposed_path = module.RUN / "calls/C02-reply.json"
proposed = task.study.read(proposed_path)
folder = task.AREA / "review/c05-capacity-001"
task.study.require(not folder.exists(), "preserve earlier qualification, including a failed attempt")
folder.mkdir()
bound = {**module.source_identities(), **{p.relative_to(task.study.ROOT).as_posix(): sha256_file(p)
         for p in (Path(__file__), wire_path, proposed_path, module.RUN / "RESPONSE_SEAL.json")}}
store = ArtifactStore(folder)
log = assembly.legacy.QualificationLog(folder / "records.jsonl", "c05-capacity-counterfactual", task_module=module)
error, outcome = None, None
try:
    server, model, _ = module.runtime_paths()
    with assembly.RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
        def no_completion(*args, **kwargs):
            raise AssertionError("completion forbidden in this offline counterfactual")
        loop = runner.Loop(folder, store, log, url=url, task_module=adapter, post=no_completion,
                           source_check=lambda: module.verify_sources(bound))
        loop.snapshot(session, "starting")
        before = loop.measure(session.view())
        session.mark_delivered(session.view())
        session.begin_request()
        actual = process_reply(session, proposed, loop.measure, adapter.preceding_feedback)
        after = loop.measure(session.view())
        task.study.require(all(o["result"]["accepted"] for o in actual["operations"]), "pending edit rejected")
        task.study.require(before == 4765 and after <= 23808, "capacity assertion differs")
        loop.snapshot(session, "counterfactual-after")
        log.append("counterfactual_edit", dict(no_model_response=True, input_tokens=before,
                   next_input_tokens=after), [store.put("proposed-reply.json", canonical_json_bytes(proposed)),
                   store.put("actual-host-result.json", canonical_json_bytes(actual))])
        counts = {k: v["prompt_tokens"] for k, v in loop.cache.items()}
        replay, replay_adapter = copy.deepcopy(captured[0]), runner.Adapter(module)
        replay.mark_delivered(replay.view())
        replay.begin_request()
        def measured(view):
            return counts[sha256_bytes(canonical_json_bytes(replay_adapter.request_for(view)))]
        repeated = process_reply(replay, proposed, measured, replay_adapter.preceding_feedback)
        task.study.require(repeated == actual and module.snapshot(replay) == module.snapshot(session),
                           "counterfactual replay differs")
        task.study.require(loop.sent == 0, "completion sent")
        outcome = dict(classification="reviewer reuses exact C02 proposal at actual C05 selection; no model inference",
            input_tokens=before, next_input_tokens=after, hard_input_limit=23808,
            accepted=True, replayed_exactly=True, original_run_unmodified=True,
            actual_run_verification=verification, native_inputs=len(counts),
            candidate_id=session.candidate.candidate_id,
            limitation="capacity feasibility only; proposal retrieval, semantic support and model action choice are not supplied by this probe")
except BaseException as problem:
    error = problem
    store.put("FAILED.json", canonical_json_bytes(dict(type=type(problem).__name__, message=str(problem))))
finally:
    task.study.save(folder, "QUALIFICATION.json", dict(status="failed_preserved" if error else "qualified_offline",
        model_requests=0, outcome=outcome, memory=assembly.RUNTIME.memory_stats(folder / "memory.csv"),
        port_free=assembly.RUNTIME.port_free(assembly.RUNTIME.PORT)))
    assembly.legacy.seal(folder, "failed_preserved" if error else "qualified_no_model_inference", bound,
                         completion_requests=0)
if error:
    raise error
records = verify_records(folder / "records.jsonl", folder)
closed = [r["payload"] for r in records if r["record_type"] == "runtime_closed"]
task.study.require(len(closed) == 1 and closed[0]["owned_server_shutdown_verified"] and
                   closed[0]["dedicated_port_free"], "runtime did not close normally")
task.study.require(all(r["payload"].get("completion_sent") is not True for r in records), "completion recorded")
print(json.dumps(outcome, indent=2))
