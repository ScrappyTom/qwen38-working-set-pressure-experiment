"""Post-run descriptive audit; no inference, task operations or artifact repair."""
import collections
import datetime
import difflib
import hashlib
import json
from pathlib import Path

AREA = Path(__file__).resolve().parent.parent
RUN = AREA / "run-001"
OUT = AREA / "review"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def save(name, value):
    path = OUT / name
    if path.exists():
        raise FileExistsError(path)
    text = value if isinstance(value, str) else json.dumps(value, indent=2, ensure_ascii=False) + "\n"
    path.write_bytes(text.encode("utf-8"))


def main():
    rows = [json.loads(line) for line in (RUN / "records.jsonl").read_text().splitlines()]
    closed = [r["payload"] for r in rows if r["record_type"] == "task_loop_completed"]
    stopped = [r["payload"] for r in rows if r["record_type"] == "attempt_stopped"]
    assert (closed or stopped) and (RUN / "RESPONSE_SEAL.json").exists(), "audit requires a closed attempt"
    starts = {r["payload"]["id"]: r["payload"] for r in rows if r["record_type"] == "invocation_started"}
    calls, inputs, actions, deliveries, checks, accounts = [], [], [], [], [], []
    completed = [r["payload"] for r in rows if r["record_type"] == "response_received"]
    for r in completed:
        name = r["id"]
        response = read(RUN / "calls" / (name + "-endpoint-response.json"))
        r = {**r, "usage": response["usage"]}
        wire = read(RUN / "calls" / (name + "-wire-request.json"))
        shown = json.loads(wire["messages"][1]["content"])
        inputs.append(shown)
        reply_path = RUN / "calls" / (name + "-reply.json")
        reply = read(reply_path) if reply_path.exists() else {}
        result_path = RUN / "calls" / (name + "-host-result.json")
        result = read(result_path) if result_path.exists() else dict(operations=[])
        calls.append(dict(id=name, input_tokens=r["usage"]["prompt_tokens"],
            generated_tokens=r["usage"]["completion_tokens"],
            cached_tokens=r["usage"].get("prompt_tokens_details", {}).get("cached_tokens", 0),
            input_plus_generation=r["usage"]["total_tokens"],
            seconds=r["elapsed_seconds"], actual_operations=len(result["operations"]),
            thinking_characters=len((RUN / "calls" / (name + "-assistant-reasoning.txt")).read_text(encoding="utf-8")),
            final_characters=len((RUN / "calls" / (name + "-assistant-content.txt")).read_text(encoding="utf-8")),
            account_in_reply="account" in reply, host_processing_completed=result_path.exists(),
            reply_selected=reply_path.exists(), finish_reason=response["choices"][0]["finish_reason"]))
        if "account" in reply:
            accounts.append(dict(id=name, input_candidate=shown["workspace"]["candidate_id"], text=reply["account"]))
        for i, op in enumerate(result["operations"], 1):
            summary = dict(id=name, operation=i, origin=op["origin"], action=op["action"]["action"],
                accepted=op["result"].get("accepted"))
            for key in ("path", "check_id", "start_line", "end_line", "query"):
                if key in op["action"]:
                    summary[key] = op["action"][key]
            actions.append(summary)
            if op["action"]["action"] == "check":
                checks.append(dict(**summary, result=op["result"]))
    for previous, current, info in zip(completed, inputs[1:], completed[1:]):
        operations = read(RUN / "calls" / (previous["id"] + "-host-result.json"))["operations"]
        receipts = [*current["preceding_operation_feedback"], current["workspace"]["latest_feedback"]]
        assert [x["result"] for x in receipts] == [x["result"] for x in operations], previous["id"]
        deliveries.append(dict(produced_by=previous["id"], delivered_to=info["id"],
                               complete_exact_receipts=len(operations)))
    processing = [r["payload"]["processing_seconds"] for r in rows if r["record_type"] == "reply_processed"]
    memory = [int(line.split(",")[-1]) for line in (RUN / "memory.csv").read_text().splitlines() if line.strip()]
    first = next(r for r in rows if r["record_type"] == "invocation_started")
    end = next(r for r in rows if r["record_type"] in ("attempt_stopped", "task_loop_completed"))
    interval = (datetime.datetime.fromisoformat(end["created_at_utc"]) - datetime.datetime.fromisoformat(first["created_at_utc"])).total_seconds()
    metrics = dict(classification="one uncoached recorded-state development continuation; no matched causal comparison",
        closure=(closed or stopped)[-1], first_dispatch_to_closure_seconds=interval,
        calls=calls, operations=actions, operation_counts=dict(collections.Counter(x["action"] for x in actions)),
        complete_next_input_delivery=deliveries, input_tokens=sum(x["input_tokens"] for x in calls),
        generated_tokens=sum(x["generated_tokens"] for x in calls),
        cached_tokens=sum(x["cached_tokens"] for x in calls),
        model_request_seconds=sum(x["seconds"] for x in calls), response_processing_seconds=sum(processing),
        peak_sent_input=max(x["input_tokens"] for x in calls),
        peak_input_plus_generation=max(x["input_plus_generation"] for x in calls), minimum_free_mib=min(memory))
    save("METRICS.json", metrics)
    save("ACCOUNTS.json", accounts)
    save("CHECKS.json", checks)
    initial = read(RUN / "starting-candidate.json")
    last_candidate = RUN / ("stopped-candidate.json" if stopped else "final-candidate.json")
    final = read(last_candidate)
    old = {f["path"]: f["content_utf8"] for f in initial["files"]}
    new = {f["path"]: f["content_utf8"] for f in final["files"]}
    assert old.keys() == new.keys()
    for record in final["files"]:
        assert hashlib.sha256(record["content_utf8"].encode()).hexdigest() == record["sha256"]
    changed = [path for path in old if old[path] != new[path]]
    save("FINAL_DIFF.patch", "".join("".join(difflib.unified_diff(old[p].splitlines(True), new[p].splitlines(True),
            fromfile="original/" + p, tofile="saved/" + p)) for p in changed))
    save("ARTIFACT_IDENTITIES.json", dict(starting_candidate=initial["candidate_id"],
        final_candidate=final["candidate_id"], final_snapshot=str(last_candidate.relative_to(AREA)),
        changed_paths=changed, unchanged_paths=[p for p in old if p not in changed],
        files=[{k:v for k,v in f.items() if k != "content_utf8"} for f in final["files"]]))
    print(json.dumps({k:v for k,v in metrics.items() if k not in ("calls", "operations", "complete_next_input_delivery")}, indent=2))


if __name__ == "__main__":
    main()
