"""Offline actual-state recovery through checked work; zero model completions."""
import copy
from pathlib import Path
from types import SimpleNamespace

import qualify
import task
from saved_states import stored
from working_set_exp.accounted_contribution import process_reply
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

AREA = Path(__file__).resolve().parent
RUN = task.AREA / "run-001"


def main():
    folder = AREA / "recovery-001"
    folder.mkdir(exist_ok=False)
    store, log = ArtifactStore(folder), RecordLog(folder / "records.jsonl", "feedback-history-offline-recovery")
    bound = {**task.source_identities(), Path(__file__).relative_to(task.ROOT).as_posix(): sha256_file(Path(__file__)),
             "tests/test_feedback_history.py": sha256_file(task.ROOT / "tests/test_feedback_history.py")}
    state = stored(RUN, "after/C03-O01-state.json")
    session, adapter = task.initial_session(), task.runner.Adapter(task.Task())
    for key in ("pairs", "ranges", "saved", "last", "requests_used", "delivered_sources"):
        setattr(session, key, copy.deepcopy(state[key]))
    old_wire = stored(RUN, "calls/C04-wire-request.json")
    assert adapter.request_for(session.view()) == old_wire
    original_ranges = copy.deepcopy(session.ranges)
    server, model, _ = task.runtime_paths()
    rows, error = [], None
    try:
        with qualify.RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            loop = task.runner.Loop(folder, store, log, url=url, task_module=adapter,
                source_check=lambda: task.verify_sources(bound), health=lambda: task.pilot.health(folder))
            initial = loop.measure(session.view())
            assert initial == 23802
            def run(reply, expected):
                session.mark_delivered(session.view())
                session.begin_request()
                result = process_reply(session, reply, loop.measure, adapter.preceding_feedback)
                number = len(rows) + 1
                task.save(folder, f"step-{number:02d}-reply.json", reply)
                task.save(folder, f"step-{number:02d}-result.json", result)
                task.save(folder, f"step-{number:02d}-state.json", task.snapshot(session))
                task.save(folder, f"step-{number:02d}-candidate.json", task.candidate_bytes(session.candidate))
                count = loop.measure(session.view())
                assert count <= 23808 and not session.delivery_blocked
                assert [op["result"].get("accepted") for op in result["operations"]] == expected
                # Exact receipts coexist in the next complete proposed input.
                shown = adapter.request_for(session.view())
                import json
                body = json.loads(shown["messages"][1]["content"])
                receipts = body["preceding_operation_feedback"] + [body["workspace"]["latest_feedback"]]
                assert [r["result"] for r in receipts] == [r["result"] for r in result["operations"]]
                rows.append(dict(step=number, input_tokens=count, recent_activity_rows=len(session.view()["recent_activity"]),
                    accepted=expected, checks=[op["result"]["passed"] for op in result["operations"] if op["action"]["action"] == "check"]))
                print(rows[-1], flush=True)
                return result
            run(stored(RUN, "calls/C04-reply.json"), [False])
            assert session.ranges == original_ranges and session.candidate.candidate_id == task.starting_candidate().candidate_id
            assert session.last["recent_activity_limit"] < 4
            assert task.read(RUN / "stopped-candidate.json") == task.read(folder / "step-01-candidate.json")
            run(dict(discussion="Researcher-selected recovery; not Qwen behavior.", operation=dict(action="work_on", sources=[
                dict(path="Lib/urllib/parse.py", start_line=170, end_line=195),
                dict(path=task.TEST, start_line=1, end_line=35),
                dict(path=task.TEST, start_line=1445, end_line=0)], results=[])), [True])
            def patch(path, old, new, account):
                return dict(discussion="Researcher-scripted feasibility after the preserved stop.", account=account,
                    operation=dict(action="patch", path=path, old=old, new=new,
                        expected_candidate_id=session.candidate.candidate_id,
                        expected_file_sha256=session.candidate.file_sha256(path)))
            run(patch(task.TEST, qualify.TEST_ANCHOR,
                (task.AREA / "REFERENCE_TEST.py").read_text(encoding="utf-8") + "\n\n" + qualify.TEST_ANCHOR,
                "Researcher-authored offline account: proposed tests need their actual successor check; documentation remains."), [True, True, True])
            assert rows[-1]["checks"] == [True]
            run(dict(discussion="Researcher changes supporting material after checked tests.", operation=dict(action="work_on",
                sources=[dict(path=task.DOC, start_line=1, end_line=55)], results=[])), [True])
            run(patch(task.DOC, qualify.DOC_ANCHOR,
                (task.AREA / "REFERENCE_DOC.txt").read_text(encoding="utf-8") + "\n" + qualify.DOC_ANCHOR,
                "Researcher-authored offline account: tests passed; examples and the full contribution require actual verification."), [True, True, True])
            assert rows[-1]["checks"] == [True]
            run(dict(discussion="Researcher-scripted closure using current actual public pass.",
                account="Researcher-authored offline account: the current public check passed; prose still needs separate review.",
                operation=dict(action="submit", expected_candidate_id=session.candidate.candidate_id)), [True, True])
            assert session.submitted
    except BaseException as problem:
        error = problem
        task.save(folder, "FAILED.json", dict(type=type(problem).__name__, message=str(problem)))
    task.save(folder, "RESULTS.json", dict(status="failed_preserved" if error else "qualified_offline_recovery",
        source_sha256=bound, source_run="9e95a08d:run-001", initial_tokens=initial, steps=rows,
        model_completion_requests=0, submitted=session.submitted,
        limitation="Only the first proposal is the actual saved Qwen action. Later selection, account and edits are researcher-scripted feasibility, not rescued model work.",
        memory=qualify.RUNTIME.memory_stats(folder / "memory.csv"), port_free=qualify.RUNTIME.port_free(qualify.RUNTIME.PORT)))
    records = verify_records(folder / "records.jsonl", folder)
    assert not any(r["record_type"] == "invocation_started" for r in records)
    assert [r["payload"] for r in records if r["record_type"] == "runtime_closed"][-1]["dedicated_port_free"]
    files = qualify.RUNTIME.file_inventory(folder)
    task.save(folder, "SEAL.json", dict(files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))
    if error:
        raise error


if __name__ == "__main__":
    main()
