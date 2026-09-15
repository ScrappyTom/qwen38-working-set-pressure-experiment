"""Native account/group boundary measurements; no model completion requests."""
import argparse
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import qualify
import task
from working_set_exp.accounted_contribution import process_reply
from working_set_exp.custody import ArtifactStore, RecordLog
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

AREA = Path(__file__).resolve().parent
RECOVERY = task.AREA / "review/recovery-001"
GROUP = [dict(path="Lib/urllib/parse.py", start_line=170, end_line=195),
         dict(path=task.TEST, start_line=1, end_line=35),
         dict(path=task.TEST, start_line=1445, end_line=0)]
SHORT = "Port behavior is governed by the visible implementation. Tests and documentation remain unwritten and unchecked."
SCOPED = (
    "Current contribution: add exact port boundary/error regressions and documentation without changing the library. "
    "The inspected port property checks digit/ASCII form before integer range; the host-info path maps an absent or empty port to None. "
    "The public functions return a parsed object before its port is accessed. Proposed tests must exercise both public functions, "
    "text and ASCII bytes, accepted endpoints, range errors and noninteger values. Their exact class, args and str remain to be "
    "confirmed by actual execution; saving expected values will not establish them. Non-ASCII decimal digits belong in text cases. "
    "Keep the implementation, test imports and insertion location together for the test contribution, then select documentation "
    "support. No new tests or documentation are saved yet; no current check establishes this contribution."
)


def sealed_state():
    seal = task.read(RECOVERY / "SEAL.json")
    assert sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"]
    name = "step-01-state.json"
    row, = [r for r in seal["files"] if r["path"] == name]
    assert sha256_file(RECOVERY / name) == row["sha256"]
    return task.read(RECOVERY / name)


def restore():
    state = sealed_state()
    session = task.initial_session()
    for key in ("pairs", "ranges", "saved", "last", "requests_used", "delivered_sources"):
        setattr(session, key, copy.deepcopy(state[key]))
    return session


def run(folder):
    folder.mkdir(parents=True, exist_ok=False)
    store, log = ArtifactStore(folder), RecordLog(folder / "records.jsonl", "account-group-boundary")
    extra = [Path(__file__), AREA / "PLAN.md", RECOVERY / "SEAL.json", RECOVERY / "step-01-state.json"]
    bound = {**task.source_identities(), **{p.relative_to(task.ROOT).as_posix(): sha256_file(p) for p in extra}}
    adapter = task.runner.Adapter(task.Task())
    server, model, _ = task.runtime_paths()
    rows, failure = [], None
    try:
        with qualify.RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            loop = task.runner.Loop(folder, store, log, url=url, task_module=adapter,
                source_check=lambda: task.verify_sources(bound), health=lambda: task.pilot.health(folder))
            for name, account in (("short", SHORT), ("scoped", SCOPED), ("clear", "")):
                session = restore()
                adapter.preceding_feedback.clear()
                initial = loop.measure(session.view())
                reply = dict(discussion="Researcher-authored offline boundary probe.", account=account,
                    operation=dict(action="work_on", sources=GROUP, results=[]))
                task.save(folder, name + "-reply.json", reply)
                session.mark_delivered(session.view())
                session.begin_request()
                try:
                    host = process_reply(session, reply, loop.measure, adapter.preceding_feedback)
                except Exception as error:
                    host = dict(error_type=type(error).__name__, error=str(error))
                task.save(folder, name + "-result.json", host)
                task.save(folder, name + "-state.json", task.snapshot(session))
                actual_count = loop.measure(session.view())
                # Construct the desired final state on a separate clone. This
                # bypasses only intermediate account admission, not final sizing.
                # It is feasibility evidence, never an executed model result.
                proposed = restore()
                proposed.mark_delivered(proposed.view())
                proposed.begin_request()
                update = dict(action="record_account", text=account)
                proposed._record(update, proposed._ordinary(update))
                adapter.preceding_feedback[:] = [copy.deepcopy(proposed.last)]
                selected = proposed.execute(reply["operation"], loop.measure)
                final_count = loop.measure(proposed.view())
                task.save(folder, name + "-prospective-state.json", task.snapshot(proposed))
                task.save(folder, name + "-prospective-feedback.json", adapter.preceding_feedback)
                rows.append(dict(name=name, account_utf8_bytes=len(account.encode()), initial_tokens=initial,
                    actual_accepted=[op["result"].get("accepted") for op in host.get("operations", [])],
                    associated_operation_skipped=host.get("associated_operation_skipped"),
                    actual_final_tokens=actual_count, prospective_group_accepted=selected["accepted"],
                    prospective_final_tokens=final_count))
                print(json.dumps(rows[-1]), flush=True)
    except BaseException as error:
        failure = error
        task.save(folder, "FAILED.json", dict(type=type(error).__name__, message=str(error)))
    task.save(folder, "RESULTS.json", dict(cases=rows, source_sha256=bound, model_completion_requests=0,
        status="failed_preserved" if failure else "measured", memory=qualify.RUNTIME.memory_stats(folder / "memory.csv")))
    files = qualify.RUNTIME.file_inventory(folder)
    task.save(folder, "SEAL.json", dict(files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))
    if failure:
        raise failure


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="001")
    run(AREA / ("boundary-" + parser.parse_args().version))
