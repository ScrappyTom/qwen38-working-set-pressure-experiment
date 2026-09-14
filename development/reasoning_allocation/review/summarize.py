"""Read closed comparison evidence; never request inference or modify run files.

Run with PYTHONPATH=src;tests;scripts;development/reasoning_allocation.
Exact operation/checker replay remains compare.py verify. This independent pass
checks source custody, actual input delivery, preserved work and descriptive cost.
"""
import ast
import json
from pathlib import Path

import compare
from working_set_exp.candidate import Candidate
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

AREA = Path(__file__).resolve().parent
read = compare.task.read


def restore(path):
    saved = read(path)
    candidate = Candidate.create({r["path"]: r["content_utf8"].encode() for r in saved["files"]},
                                 max_file_bytes=saved["max_file_bytes"])
    assert candidate.candidate_id == saved["candidate_id"]
    return candidate


def methods(raw):
    return {(cls.name, f.name): ast.dump(f, include_attributes=False)
            for cls in ast.parse(raw).body if isinstance(cls, ast.ClassDef)
            for f in cls.body if isinstance(f, (ast.FunctionDef, ast.AsyncFunctionDef))}


def attempt(condition, manifest):
    folder = compare.RUN / condition["id"]
    seal = compare.verify_seal(folder)
    assert seal["source_sha256"] == manifest["source_sha256"]
    records = verify_records(folder / "records.jsonl", folder)
    assert len(records) == seal["record_count"]
    private = folder / "private-runtime"
    local_verified = all((private / n).exists() for n in seal["private_runtime_files_local_only"])
    if local_verified:
        for name, digest in seal["private_runtime_files_local_only"].items():
            assert sha256_file(private / name) == digest
    before = restore(folder / "starting-candidate.json")
    tail = "final" if (folder / "final-state.json").exists() else "stopped"
    after = restore(folder / (tail + "-candidate.json"))
    final = read(folder / (tail + "-state.json"))
    initial = read(folder / "starting-state.json")
    assert final["pairs"][:39] == initial["pairs"]
    target = "Lib/test/test_configparser.py"
    changed = [p for p, raw in before.files if after.file_map[p] != raw]
    unrelated_preserved = all(after.file_map[p] == raw for p, raw in before.files if p != target)
    try:
        old, new = methods(before.file_map[target]), methods(after.file_map[target])
        preserved_methods = all(new.get(k) == v for k, v in old.items())
        added = sorted(".".join(k) for k in new.keys() - old.keys())
    except SyntaxError:
        preserved_methods, added = False, None

    calls, checks, prior_ops = [], [], None
    current = before
    first_request = None
    for event in records:
        if event["record_type"] != "invocation_started":
            continue
        tag, expected_input = event["payload"]["id"], event["payload"]["prompt_tokens"]
        request = read(folder / f"calls/{tag}-wire-request.json")
        assert [m["role"] for m in request["messages"]] == ["system", "user"]
        if first_request is None:
            first_request = request
        else:
            assert request["messages"][0] == first_request["messages"][0]
            assert {k: v for k, v in request.items() if k != "messages"} == {
                k: v for k, v in first_request.items() if k != "messages"}
        view = json.loads(request["messages"][1]["content"])
        state = view["workspace"]
        if prior_ops:
            assert prior_ops[-1]["result"] == state["latest_feedback"]["result"]
            assert len(prior_ops) - 1 == len(view["preceding_operation_feedback"])
            for operation, feedback in zip(prior_ops[:-1], view["preceding_operation_feedback"]):
                assert operation["result"] == feedback["result"]
        sources = state["working_set"]["sources"] + compare.task.WorkingSession.feedback_sources(state["latest_feedback"])
        seen_lines, repeated_source_bytes = set(), 0
        for source in sources:
            raw = current.file_map[source["path"]]
            assert source["candidate_id"] == current.candidate_id
            assert source["file_sha256"] == sha256_bytes(raw)
            assert source["content"] == "".join(raw.decode().splitlines(keepends=True)[
                source["returned_start_line"] - 1:source["returned_end_line"]])
            for number, line in enumerate(source["content"].splitlines(keepends=True),
                                          source["returned_start_line"]):
                identity = (source["path"], source["file_sha256"], number)
                if identity in seen_lines:
                    repeated_source_bytes += len(line.encode())
                seen_lines.add(identity)
        response_path = folder / f"calls/{tag}-endpoint-response.json"
        row = dict(id=tag, input_tokens=expected_input, response_available=response_path.exists(),
                   repeated_current_source_utf8_bytes=repeated_source_bytes,
                   displayed_actions_remaining=state["allowance"]["actions_remaining"])
        calls.append(row)
        if not response_path.exists():
            break
        response = read(response_path)
        choice = response["choices"][0]
        assert response["usage"]["prompt_tokens"] == expected_input
        assert response["usage"]["total_tokens"] == expected_input + response["usage"]["completion_tokens"]
        assert response["usage"]["total_tokens"] <= manifest["actor"]["context"]
        assert response["usage"].get("prompt_tokens_details", {}).get("cached_tokens") == 0
        assert response.get("timings", {}).get("cache_n") == 0
        for field, suffix in (("content", "content"), ("reasoning_content", "reasoning")):
            assert (choice["message"].get(field) or "").encode() == (folder / f"calls/{tag}-assistant-{suffix}.txt").read_bytes()
        received = next(r for r in records if r["record_type"] == "response_received" and r["payload"]["id"] == tag)
        row.update(generated_tokens=response["usage"]["completion_tokens"],
                   request_seconds=round(received["payload"]["elapsed_seconds"], 3),
                   finish_reason=choice["finish_reason"],
                   thinking_characters=len(choice["message"].get("reasoning_content") or ""),
                   final_characters=len(choice["message"].get("content") or ""))
        result_path = folder / f"calls/{tag}-host-result.json"
        prior_ops = read(result_path)["operations"] if result_path.exists() else []
        row["operations"] = [dict(action=o["action"]["action"], accepted=o["result"].get("accepted")) for o in prior_ops]
        for n, op in enumerate(prior_ops, 1):
            current = restore(folder / f"after/{tag}-O{n:02d}-candidate.json")
            if op["action"]["action"] == "check":
                check = dict(call=tag, result=op["result"])
                if op["result"].get("stdout"):
                    try:
                        check["public"] = json.loads(op["result"]["stdout"])
                    except json.JSONDecodeError:
                        pass
                checks.append(check)
        processed = next((r for r in records if r["record_type"] == "reply_processed" and r["payload"]["id"] == tag), None)
        row["processing_seconds"] = None if processed is None else round(processed["payload"]["processing_seconds"], 3)
    loop = next((r["payload"] for r in records if r["record_type"] == "task_loop_completed"), None)
    returned = [r for r in calls if r["response_available"]]
    metrics = dict(condition=condition, disposition=seal["disposition"], calls=calls,
        sent_requests=len(calls), returned_responses=len(returned), actual_operations=seal["actual_operations"],
        input_tokens=sum(r["input_tokens"] for r in returned),
        generated_tokens=sum(r["generated_tokens"] for r in returned),
        model_request_seconds=round(sum(r["request_seconds"] for r in returned), 3),
        task_loop_seconds=None if loop is None else round(loop["task_loop_seconds"], 3),
        peak_input_tokens=max(r["input_tokens"] for r in calls),
        peak_input_plus_generated_tokens=max((r["input_tokens"] + r["generated_tokens"] for r in returned), default=0),
        check_opportunities=None if loop is None else loop["check_opportunities"], memory=seal["memory"],
        missing_response_cost_not_imputed=len(returned) != len(calls))
    verification = dict(condition=condition, records=len(records), sealed_files=len(seal["files"]),
        private_runtime_hashes_verified=local_verified, source_count=len(seal["source_sha256"]),
        seal_sha256=sha256_file(folder / "SEAL.json"), changed_files=changed,
        unrelated_files_preserved=unrelated_preserved, existing_class_methods_preserved=preserved_methods,
        added_methods=added, candidate_id=after.candidate_id, submitted=final["submitted"],
        sent_next_inputs_contain_actual_feedback=True,
        terminal_feedback_not_sent_due_to_capacity=seal["disposition"] == "feedback_capacity_denied",
        terminal_feedback_not_sent_at_request_limit=bool(prior_ops) and seal["disposition"] == "request_allowance_exhausted",
        exact_current_source_bytes=True, prior_archive_preserved=True,
        checks=checks, runtime_closed=seal["port_free"])
    return verification, metrics


def main():
    manifest = compare.verify_package()
    root_seal = compare.verify_seal(compare.RUN)
    results = [attempt(row, manifest) for row in compare.SCHEDULE if (compare.RUN / row["id"]).exists()]
    verification, metrics = map(list, zip(*results))
    for name, value in (("VERIFICATION.json", verification), ("METRICS.json", metrics)):
        (AREA / name).write_bytes(canonical_json_bytes(value))
    pairs = []
    for high, medium in (("A01", "A02"), ("A04", "A03")):
        requests = [read(compare.RUN / a / "calls/C01-wire-request.json") for a in (high, medium)]
        assert [r["chat_template_kwargs"].pop("reasoning_effort") for r in requests] == ["xhigh", "medium"]
        assert requests[0] == requests[1]
        native = [(compare.RUN / a / "admission/I0001-native.txt").read_bytes() for a in (high, medium)]
        head = ("<|im_start|>system\n" + compare.XHIGH + "\n\n").encode()
        assert native[0].startswith(head)
        assert native[1] == b"<|im_start|>system\n" + native[0][len(head):]
        token_counts = [next(m for m in metrics if m["condition"]["id"] == a)["calls"][0]["input_tokens"] for a in (high, medium)]
        assert token_counts[0] - token_counts[1] == 38
        pairs.append(dict(xhigh=high, medium=medium, seed=requests[0]["seed"],
                          only_request_difference="chat_template_kwargs.reasoning_effort",
                          only_native_difference=compare.XHIGH, input_token_difference=38))
    receipt = dict(status=root_seal["status"], source_count=len(manifest["source_sha256"]),
        run_seal_sha256=sha256_file(compare.RUN / "SEAL.json"), pairs=pairs,
        model_requests=sum(m["sent_requests"] for m in metrics),
        actual_operations=sum(m["actual_operations"] for m in metrics),
        unused_requests_closed=64-sum(m["sent_requests"] for m in metrics),
        unused_operations_closed=96-sum(m["actual_operations"] for m in metrics),
        offline_analyzer_completion_requests=0, all_owned_runtimes_closed=all(v["runtime_closed"] for v in verification),
        review_inference_cost_separately_measured=False)
    (AREA / "EXECUTION_RECEIPT.json").write_bytes(canonical_json_bytes(receipt))
    print(json.dumps([dict(condition=r["condition"], submitted=r["submitted"],
                           changed_files=r["changed_files"], added=r["added_methods"]) for r in verification]))
    print(json.dumps([{k: v for k, v in r.items() if k not in ("calls", "memory", "check_opportunities")} for r in metrics]))


if __name__ == "__main__":
    main()
