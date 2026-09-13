"""Derive review measurements from the closed run; no inference or mutation."""
from __future__ import annotations

import json
import argparse
from collections import Counter
from pathlib import Path


def report() -> dict:
    root = Path(__file__).resolve().parents[1]
    folder = root / "development/configparser_backport/run-001"
    read = lambda path: json.loads(path.read_bytes())
    records = [json.loads(line) for line in (folder / "records.jsonl").read_bytes().splitlines()]
    completed = [r["payload"] for r in records if r["record_type"] == "invocation_completed"]
    started = [r["payload"] for r in records if r["record_type"] == "invocation_started"]
    prepared = [r["payload"] for r in records if r["record_type"] == "native_input_prepared"]
    loop = next(r["payload"] for r in records if r["record_type"] == "task_loop_completed")
    closed = next(r["payload"] for r in records if r["record_type"] == "runtime_closed")
    initial, final = (read(folder / name) for name in ("starting-candidate.json", "final-candidate.json"))
    maps = [{f["path"]: f["content_utf8"] for f in c["files"]} for c in (initial, final)]
    turns = []
    for row in completed:
        tag, prefix = row["id"], row["externalized_through"]
        request = read(folder / f"admission/{tag}-x{prefix:03d}-endpoint-request.json")
        state = json.loads(request["messages"][1]["content"])
        events = state["active_phase_event_frame"]["events"]
        result = row["host_result"]["result"]
        action = row["host_result"]["action"]
        turns.append(dict(
            id=tag, action=action["action"], path=action.get("path"),
            input_tokens=row["usage"]["prompt_tokens"], generated_tokens=row["usage"]["completion_tokens"],
            model_request_seconds=row["elapsed_seconds"], externalized_through=prefix,
            resident_result_sequences=[e["sequence"] for e in events if e["result_body"]["residency"] == "resident"],
            resident_patch_sequences=[e["sequence"] for e in events if e["action_payload"]["residency"] == "resident"],
            returned_lines=[result.get("returned_start_line"), result.get("returned_end_line")]
                if action["action"] == "read" else None,
        ))
    total_request_seconds = sum(t["model_request_seconds"] for t in turns)
    # The final two counterfactual inputs were rendered/tokenized but never sent.
    terminal = [r for r in prepared if r["id"] == "C33"]
    assert len(completed) == len(started) == 32 and terminal[-1]["externalized_through"] == 32
    assert [r["prompt_tokens"] for r in terminal[-2:]] == [23928, 18941]
    last = read(folder / "calls/C32-host-result.json")["result"]
    delivered = read(folder / "admission/C32-x025-endpoint-request.json")
    assert json.loads(delivered["messages"][1]["content"])["active_phase_event_frame"]["events"][-1]["result_body"]["residency"] == "resident"
    groups = {}
    for label, lo, hi in (("through_final_library_patch", 1, 18), ("after_final_library_patch", 19, 32),
                           ("before_first_externalization", 1, 10)):
        subset = turns[lo-1:hi]
        groups[label] = dict(generated_tokens=sum(t["generated_tokens"] for t in subset),
                            model_request_seconds=sum(t["model_request_seconds"] for t in subset))
    return dict(
        scope="post-run descriptive measurements; no new model calls or scores",
        action_counts=dict(Counter(t["action"] for t in turns)),
        changed_paths=[path for path in maps[0] if maps[0][path] != maps[1][path]],
        initial_source_bytes=sum(len(s.encode()) for s in maps[0].values()),
        final_source_bytes=sum(len(s.encode()) for s in maps[1].values()),
        input_tokens=sum(t["input_tokens"] for t in turns),
        generated_tokens=sum(t["generated_tokens"] for t in turns),
        peak_input_tokens=max(t["input_tokens"] for t in turns),
        peak_generated_tokens=max(t["generated_tokens"] for t in turns),
        model_request_seconds=total_request_seconds,
        task_loop_seconds=loop["task_loop_seconds"],
        non_request_task_loop_seconds=loop["task_loop_seconds"]-total_request_seconds,
        response_processing_seconds=sum(r["payload"]["response_processing_seconds"] for r in records
                                        if r["record_type"] == "action_feedback_recorded"),
        memory=closed["memory"], effective_runtime=closed["effective_runtime"],
        check_opportunities=loop["check_opportunities"],
        terminal_admission=[dict(prefix=r["externalized_through"], input_tokens=r["prompt_tokens"],
                                 physical_generation_space=r["physical_generation_space"])
                            for r in terminal],
        latest_result_stored_but_not_delivered=dict(id="C32", path=last["path"],
            start=last["returned_start_line"], end=last["returned_end_line"],
            next=last["next_start_line"], source_bytes=len(last["content"].encode()),
            admission_excess_tokens=120, calls_unused=8),
        groups=groups, turns=turns,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    result = report()
    encoded = json.dumps(result, ensure_ascii=False, indent=2) + "\n"
    if args.output:
        with args.output.open("xb") as stream:
            stream.write(encoded.encode())
        print(f"Saved complete measurements for {len(result['turns'])} turns")
    else:
        print(encoded, end="")
