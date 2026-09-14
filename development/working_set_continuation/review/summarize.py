"""Descriptive accounting from exact requests and recorded operation receipts."""
import json
from datetime import datetime
from pathlib import Path

import interpolation_contribution as task
from working_set_exp.custody import verify_records
from working_set_exp.working_session import WorkingSession


def source_rows(view):
    return view["working_set"]["sources"] + WorkingSession.feedback_sources(view["latest_feedback"])


def span_ids(rows):
    return {(s["path"], s["file_sha256"], i) for s in rows
            for i in range(s["returned_start_line"], s["returned_end_line"] + 1)}


def summarize(folder):
    records = verify_records(folder / "records.jsonl", folder)
    completed = {r["payload"]["id"]: r["payload"] for r in records if r["record_type"] == "invocation_completed"}
    received = {r["payload"]["id"]: r["payload"] for r in records if r["record_type"] == "response_received"}
    seen, rows = set(), []
    for tag, timing in received.items():
        response = task.read(folder / f"calls/{tag}-endpoint-response.json")
        value = dict(id=tag, usage=response["usage"], elapsed_seconds=timing["elapsed_seconds"],
            finish_reason=response["choices"][0]["finish_reason"], processed=tag in completed,
            within_generation_reserve=response["usage"]["completion_tokens"] <= task.ACTOR["generation_reserve"])
        request = task.read(folder / f"calls/{tag}-wire-request.json")
        view = json.loads(request["messages"][1]["content"])["workspace"]
        visible = span_ids(source_rows(view))
        seen |= visible
        host_path = folder / f"calls/{tag}-host-result.json"
        host = task.read(host_path) if host_path.exists() else dict(operations=[])
        received = []
        for operation in host["operations"]:
            result = operation["result"]
            acquired = [result["source"]] if "source" in result else result.get("sources", [])
            ids = span_ids(acquired)
            received.append(dict(action=operation["action"], accepted=result.get("accepted"), passed=result.get("passed"),
                new_source_lines=len(ids - seen), reacquired_absent_lines=len((ids & seen) - visible),
                already_visible_lines=len(ids & visible), source_ranges=[{k: s[k] for k in
                    ("path", "returned_start_line", "returned_end_line", "next_start_line")} for s in acquired]))
            seen |= ids
        source_list = source_rows(view)
        duplicate_lines = sum(max(0, s["returned_end_line"]-s["returned_start_line"]+1) for s in source_list) - len(visible)
        rows.append(dict(**value, allowance=view["allowance"], operations=received,
            visible_source_lines=len(visible), duplicate_current_source_lines=duplicate_lines,
            selected_ranges=[{k:s[k] for k in ("path", "returned_start_line", "returned_end_line")} for s in source_list]))
    usage = dict(input_tokens=sum(r["usage"]["prompt_tokens"] for r in rows),
        generated_tokens=sum(r["usage"]["completion_tokens"] for r in rows),
        model_request_seconds=sum(r["elapsed_seconds"] for r in rows),
        max_input_tokens=max((r["usage"]["prompt_tokens"] for r in rows), default=0),
        max_input_plus_generation=max((r["usage"]["total_tokens"] for r in rows), default=0))
    outcome = next((r["payload"] for r in records if r["record_type"] == "task_loop_completed"), None)
    artifact = next((folder / n for n in ("final-candidate.json", "stopped-candidate.json") if (folder / n).exists()), None)
    first = next((r for r in records if r["record_type"] == "invocation_started"), None)
    stop = next((r for r in records if r["record_type"] in ("task_loop_completed", "attempt_stopped")), None)
    return dict(calls=rows, totals=usage, outcome=outcome,
        stop_record=stop["payload"] if stop else None,
        first_dispatch_to_closure_record_seconds=(datetime.fromisoformat(stop["created_at_utc"])-
            datetime.fromisoformat(first["created_at_utc"])).total_seconds() if first and stop else None,
        source_line_count_method="path/file-SHA/line identities; a changed file hash does not imply every line contains new information",
        exact_prior_artifact_preserved=artifact.read_bytes() == (folder / "starting-candidate.json").read_bytes() if artifact else None,
        reviewer_time_and_inference_separately_metered=False)


if __name__ == "__main__":
    print(json.dumps(summarize(task.RUN), indent=2))
