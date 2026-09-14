"""After closure: native C03 sizing across the source-fragment boundary; no inference."""
import json
from pathlib import Path
from types import SimpleNamespace

import interpolation_contribution as task
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import completion_request_bytes, process_reply
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.working_session import INPUT_LIMIT


def main():
    task.require((task.RUN / "RESPONSE_SEAL.json").exists(), "live attempt must close before this probe")
    area = task.AREA / "review/page-search-probe-001"
    task.require(not area.exists(), "preserve the original probe; no overwrite")
    area.mkdir()
    bound = task.source_identities()
    task.require(bound == task.read(task.RUN / "EXECUTION_MANIFEST.json")["source_sha256"], "frozen run source inventory differs")
    task.verify_sources(bound)
    rows = verify_records(task.RUN / "records.jsonl", task.RUN)
    counts, known_native = {}, {}
    for row in rows:
        if row["record_type"] != "native_input_prepared":
            continue
        stem = row["payload"]["stem"]
        request = task.read(task.RUN / (stem + "-endpoint-request.json"))
        key = sha256_bytes(canonical_json_bytes(request))
        counts[key] = row["payload"]["prompt_tokens"]
        known_native[key] = (task.RUN / (stem + "-native.txt")).read_bytes()
    session, adapter = task.initial_session(), runner.Adapter(task)
    def recorded_measure(view):
        return counts[sha256_bytes(canonical_json_bytes(adapter.request_for(view)))]
    for tag in ("C01", "C02"):
        task.require(completion_request_bytes(adapter.request_for(session.view())) ==
                     (task.RUN / f"calls/{tag}-wire-request.json").read_bytes(), "prefix input differs")
        session.mark_delivered(session.view())
        session.begin_request()
        result = process_reply(session, task.read(task.RUN / f"calls/{tag}-reply.json"),
                               recorded_measure, adapter.preceding_feedback)
        task.require(result == task.read(task.RUN / f"calls/{tag}-host-result.json"), "prefix replay differs")
    task.require(canonical_json_bytes(task.snapshot(session)) ==
                 (task.RUN / "after/C02-O01-state.json").read_bytes(), "C02 state differs")
    task.require(completion_request_bytes(adapter.request_for(session.view())) ==
                 (task.RUN / "calls/C03-wire-request.json").read_bytes(), "C03 input differs")
    session.mark_delivered(session.view())
    session.begin_request()
    action = task.read(task.RUN / "calls/C03-operation-01.json")["action"]
    task.require(action == dict(action="read", path="Lib/test/test_configparser.py", start_line=1855, end_line=1920),
                 "observed action differs")
    store = ArtifactStore(area)
    log = runner.RunLog(area / "records.jsonl", "closed-run-page-search-probe", task_module=task)
    runtime = task.base.base
    server, model, _ = task.runtime_paths()
    measurements, exact_reproductions, error = [], 0, None
    try:
        with runtime.owned_runtime(SimpleNamespace(server=server, model=model, output=area), store, log) as url:
            def forbid_completion(*args, **kwargs):
                raise AssertionError("this probe cannot send a completion")
            loop = runner.Loop(area, store, log, url=url, task_module=runner.Adapter(task),
                               post=forbid_completion, source_check=lambda: task.verify_sources(bound))
            # Original rejected trials bracket the point where the retained
            # source's trailing fragment disappears. A fitting case suffices to
            # disprove the rejection; this is not a search for an optimal page.
            for end in (1855, 1862, 1863, 1864, 1868, 1869, 1870, 1920):
                proposed = session.clone()
                source = proposed.source(dict(path=action["path"], start_line=action["start_line"], end_line=end))
                proposed.add_source(source)
                proposed._record(action, dict(accepted=True, source=source))
                view = proposed.view()
                count = loop.measure(view)
                key = sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
                measured = loop.cache[key]
                if key in counts:
                    native = (area / (measured["stem"] + "-native.txt")).read_bytes()
                    task.require(count == counts[key] and native == known_native[key], "saved trial reproduction differs")
                    exact_reproductions += 1
                measurements.append(dict(start_line=action["start_line"], end_line=end, native_tokens=count,
                    fits_hard_ceiling=count <= INPUT_LIMIT, exact_saved_trial=key in counts,
                    source_rows=[{k:s[k] for k in ("path", "returned_start_line", "returned_end_line")}
                                 for s in view["working_set"]["sources"]], input_stem=measured["stem"]))
        task.require(exact_reproductions > 0, "no original native trial reproduced")
    except BaseException as problem:
        error = problem
        task.save(area, "FAILED.json", dict(type=type(problem).__name__, message=str(problem)))
    finally:
        report = dict(status="failed_preserved" if error else "measured_no_model_inference",
            original_reply="C03", original_action=action, original_outcome="rejected_capacity",
            exact_saved_trials_reproduced=exact_reproductions, completion_requests=0,
            exhaustive_prefix_search=False, purpose="test feasibility across the changed fragment layout, not maximize page length",
            measurements=measurements, fitting_end_lines=[m["end_line"] for m in measurements if m["fits_hard_ceiling"]],
            memory=runtime.memory_stats(area / "memory.csv"), port_free=runtime.port_free(runtime.PORT))
        task.save(area, "RESULT.json", report)
        records = verify_records(area / "records.jsonl", area)
        task.require(not any(r["record_type"] == "invocation_started" for r in records), "unexpected inference record")
        files = runtime.file_inventory(area)
        task.save(area, "SEAL.json", dict(status=report["status"], files=files, source_sha256=bound,
            probe_source_sha256=sha256_file(Path(__file__)), aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),
            completion_requests=0, private_runtime_files_local_only={p.name:sha256_file(p) for p in
                (area / "private-runtime").glob("*") if p.is_file()}))
    if error:
        raise error
    print(json.dumps({k:v for k,v in report.items() if k != "measurements"}, indent=2))


if __name__ == "__main__":
    main()
