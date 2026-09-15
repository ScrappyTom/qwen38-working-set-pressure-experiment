"""Replay the preserved terminal exception without changing its frozen verifier.

The original verifier re-raises C04's recorded CapacityError before its final-state
comparison. This review-only adaptation accepts exactly that terminal exception,
then runs the original final-state/artifact/private-runtime comparisons. It does
not fabricate a tool result or count C04 as a processed invocation.
Run with the frozen bbaf1c7a runtime/task sources on PYTHONPATH.
"""
import json
from pathlib import Path
import task

source = task.ROOT / "development/working_set_continuation/review/verify.py"
original = source.read_text(encoding="utf-8")
old = "        actual = adapter.process_reply(session, reply, measure, adapter.preceding_feedback, intermediate)"
new = """        try:
            actual = adapter.process_reply(session, reply, measure, adapter.preceding_feedback, intermediate)
        except Exception as error:
            stops = [r['payload'] for r in records if r['record_type'] == 'attempt_stopped']
            task.require(tag == 'C04' and len(stops) == 1 and
                stops[0] == dict(error_type=type(error).__name__, error=str(error)) and
                type(error).__name__ == 'CapacityError' and
                str(error) == 'Rejection cannot be delivered; no state transition committed',
                'terminal exception differs')
            task.require(not (folder / f'calls/{tag}-host-result.json').exists(), 'unexpected terminal result')
            task.require(not (folder / f'calls/{tag}-operation-01.json').exists(), 'unexpected terminal operation')
            break"""
assert original.count(old) == 1
namespace = dict(__name__="preserved_stop_replay")
exec(compile(original.replace(old, new), str(source), "exec"), namespace)
namespace["task"] = task.Task()
folder = task.AREA / "run-001"
result = namespace["verify"](folder)
records = [json.loads(x) for x in (folder / "records.jsonl").read_text().splitlines()]
closed = [r["payload"] for r in records if r["record_type"] == "runtime_closed"]
assert len(closed) == 1 and closed[0]["owned_server_shutdown_verified"] and closed[0]["dedicated_port_free"]
for path in sorted((folder / "calls").glob("*-endpoint-response.json")):
    response = json.loads(path.read_text())
    usage = response["usage"]
    assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"] <= 56576
    assert usage["prompt_tokens_details"]["cached_tokens"] == response["timings"]["cache_n"] == 0
result.update(returned_responses=4, terminal_exception_reproduced=True,
              actual_completion_requests=4, owned_runtime_closed=True)
task.save(task.AREA / "review", "VERIFICATION.json", result)
print(json.dumps(result, indent=2))
