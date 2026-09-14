"""Replay the corrected C03 acquisition using already-recorded native counts."""
import json
from pathlib import Path

import interpolation_contribution as task
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import completion_request_bytes, process_reply
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def main():
    area = task.AREA / "review/page-search-correction-001"
    expected = task.read(task.RUN / "RESPONSE_SEAL.json")["source_sha256"]
    changed = [name for name, digest in expected.items() if sha256_file(task.ROOT/name) != digest]
    task.require(changed == ["src/working_set_exp/working_session.py"], "unexpected frozen-source changes")
    adapter, counts, natives = runner.Adapter(task), {}, {}
    for folder, seal_name in ((task.RUN, "RESPONSE_SEAL.json"),
                              (task.AREA/"review/page-search-probe-001", "SEAL.json")):
        seal = task.read(folder/seal_name)
        task.require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "seal inventory differs")
        for row in seal["files"]:
            task.require(sha256_file(folder/row["path"]) == row["sha256"], "sealed input differs")
        for record in verify_records(folder/"records.jsonl", folder):
            if record["record_type"] != "native_input_prepared":
                continue
            row, stem = record["payload"], record["payload"]["stem"]
            request = task.read(folder/(stem+"-endpoint-request.json"))
            native = (folder/(stem+"-native.txt")).read_bytes()
            task.require(native == adapter.expected_native(request), "native envelope differs")
            task.require(len(task.read(folder/(stem+"-tokens.json"))["tokens"]) == row["prompt_tokens"], "count differs")
            key = sha256_bytes(canonical_json_bytes(request))
            counts[key], natives[key] = row["prompt_tokens"], sha256_bytes(native)
    measured = []
    def measure(view):
        key = sha256_bytes(canonical_json_bytes(adapter.request_for(view)))
        measured.append(dict(request_sha256=key, native_sha256=natives[key], prompt_tokens=counts[key]))
        return counts[key]
    session = task.initial_session()
    for tag in ("C01", "C02"):
        task.require(completion_request_bytes(adapter.request_for(session.view())) ==
                     (task.RUN/f"calls/{tag}-wire-request.json").read_bytes(), "unchanged prefix differs")
        session.mark_delivered(session.view())
        session.begin_request()
        result = process_reply(session, task.read(task.RUN/f"calls/{tag}-reply.json"), measure, adapter.preceding_feedback)
        task.require(result == task.read(task.RUN/f"calls/{tag}-host-result.json"), "unchanged prefix feedback differs")
    task.require(canonical_json_bytes(task.snapshot(session)) ==
                 (task.RUN/"after/C02-O01-state.json").read_bytes(), "unchanged prefix state differs")
    before = session.candidate
    ranges = session.sources()
    session.mark_delivered(session.view())
    session.begin_request()
    result = process_reply(session, task.read(task.RUN/"calls/C03-reply.json"), measure, adapter.preceding_feedback)
    returned = result["operations"][0]["result"]
    task.require(returned["accepted"] and returned["source"]["returned_end_line"] == 1864, "fitting overlap page not returned")
    next_count = measure(session.view())
    task.require(next_count == 23762 and session.candidate == before, "corrected state differs")
    visible = session._verified_source_ranges(session.view()["working_set"]["sources"] +
                                              session.feedback_sources(session.view()["latest_feedback"]))
    for original in ranges:
        task.require(any(row["path"] == original["path"] and row["start_line"] <= original["returned_start_line"]
                         and row["end_line"] >= original["returned_end_line"] for row in visible), "selected evidence lost")
    task.save(area, "QUALIFICATION.json", dict(status="corrected_acquisition_qualified_offline",
        frozen_run_revision="f74466d8", changed_frozen_sources=changed,
        host_sha256=sha256_file(task.ROOT/changed[0]), qualifier_sha256=sha256_file(Path(__file__)),
        tests_sha256=sha256_file(task.ROOT/"tests/test_page_layout_capacity.py"),
        original_outcome="rejected_capacity", corrected_result=returned, corrected_next_input_tokens=next_count,
        native_trials_reused=measured, selected_source_preserved=True, candidate_unchanged=True,
        requests_used=session.requests_used, actual_operations=session.calls_used,
        no_new_native_or_completion_requests=True, no_model_counterfactual_outcome_claimed=True))
    print("Actual C03 now returns lines 1855–1864 at 23,762 native tokens; no selected source lost and no new inference.")


if __name__ == "__main__":
    main()
