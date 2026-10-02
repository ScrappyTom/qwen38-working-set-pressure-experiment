"""Independent, saved-record-only accounting for the sealed URL run 002.

This does not import the host, invoke a checker, tokenize, or request a model.
Exact custody and replay are separately qualified by verify_run.py.
"""
from collections import Counter, defaultdict
from hashlib import sha256
import json
from pathlib import Path


HERE = Path(__file__).resolve().parent
RUN = HERE.parent / "run-002"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def digest(path):
    return sha256(path.read_bytes()).hexdigest()


def main():
    seal = read(RUN / "RESPONSE_SEAL.json")
    verification = read(HERE / "VERIFICATION-002.json")
    assert verification["status"] == "replayed_exactly"
    records = [json.loads(line) for line in
               (RUN / "records.jsonl").read_text(encoding="utf-8").splitlines()]
    by_type = defaultdict(list)
    for record in records:
        by_type[record["record_type"]].append(record)
    started = by_type["invocation_started"]
    received = by_type["response_received"]
    completed = by_type["invocation_completed"]
    processed = by_type["reply_processed"]
    assert len(started) == len(received) == len(completed) == len(processed) == 20
    loop = by_type["task_loop_completed"][0]["payload"]
    closed = by_type["runtime_closed"][0]["payload"]
    assert closed["owned_server_shutdown_verified"] and closed["dedicated_port_free"]
    assert loop["disposition"] == "request_allowance_exhausted"
    operations = defaultdict(list)
    for record in by_type["contribution_operation"]:
        operation = read(RUN / record["artifacts"][0]["path"])
        operations[record["payload"]["id"]].append(operation)
    native = {}
    for record in by_type["native_input_prepared"]:
        payload = record["payload"]
        count = read(RUN / next(item["path"] for item in record["artifacts"]
                               if item["path"].endswith("-count.json")))
        assert count["prompt_tokens"] == payload["prompt_tokens"]
        assert count["physical_generation_space"] == payload["physical_generation_space"]
        native[payload["stem"]] = count
    assert len(native) == 94

    rows = []
    previous = []
    cumulative_operations = 0
    source_deliveries = []
    for index, (start, response_record, complete, reply) in enumerate(
            zip(started, received, completed, processed), 1):
        ident = f"C{index:02}"
        assert {start["payload"]["id"], response_record["payload"]["id"],
                complete["payload"]["id"], reply["payload"]["id"]} == {ident}
        wire = read(RUN / start["artifacts"][0]["path"])
        body = json.loads(wire["messages"][-1]["content"])
        view = body["workspace"]
        endpoint = read(RUN / response_record["artifacts"][0]["path"])
        usage = endpoint["usage"]
        assert usage == complete["payload"]["usage"]
        assert usage["prompt_tokens"] == start["payload"]["prompt_tokens"]
        assert native[start["payload"]["input_stem"]]["prompt_tokens"] == usage["prompt_tokens"]
        assert usage["total_tokens"] == usage["prompt_tokens"] + usage["completion_tokens"]
        assert endpoint["choices"][0]["finish_reason"] == "stop"
        assert view["allowance"]["requests_used"] == index - 1
        assert view["allowance"]["requests_remaining"] == 21 - index
        assert view["allowance"]["actions_used"] == cumulative_operations
        if previous:
            latest = view["latest_feedback"]
            assert latest["sequence"] == cumulative_operations
            assert latest["result"]["accepted"] == previous[-1]["result"]["accepted"]
            earlier = body["preceding_operation_feedback"]
            assert len(earlier) == len(previous) - 1
            for receipt, operation in zip(earlier, previous[:-1]):
                assert receipt["result"] == operation["result"]
            result = previous[-1]["result"]
            if "source" not in result and "sources" not in result:
                assert latest["result"] == result
            for source in ([result["source"]] if "source" in result else
                           result.get("sources", [])):
                matches = []
                for shown in view["working_set"]["sources"]:
                    if (shown["path"] == source["path"] and
                        shown["file_sha256"] == source["file_sha256"] and
                        shown["returned_start_line"] <= source["returned_start_line"] and
                        shown["returned_end_line"] >= source["returned_end_line"]):
                        lines = shown["content"].splitlines(keepends=True)
                        first = source["returned_start_line"] - shown["returned_start_line"]
                        last = source["returned_end_line"] - shown["returned_start_line"] + 1
                        matches.append("".join(lines[first:last]) == source["content"])
                assert any(matches), (ident, source["path"], source["returned_start_line"])
                source_deliveries.append({"received_in": ident, "path": source["path"],
                                          "first": source["returned_start_line"],
                                          "last": source["returned_end_line"]})
        assert reply["payload"]["feedback_admitted"] is True
        model_seconds = response_record["payload"]["elapsed_seconds"]
        assert model_seconds == complete["payload"]["elapsed_seconds"]
        rows.append({"id": ident, "input_tokens": usage["prompt_tokens"],
                     "generated_tokens": usage["completion_tokens"],
                     "input_plus_generation": usage["total_tokens"],
                     "cached_input_tokens": usage["prompt_tokens_details"]["cached_tokens"],
                     "model_seconds": model_seconds,
                     "processing_seconds": reply["payload"]["processing_seconds"],
                     "actual_operations": len(operations[ident]),
                     "input_mode": view["presentation"]["mode"],
                     "visible_source_characters": sum(len(s["content"]) for s in
                                                      view["working_set"]["sources"]),
                     "prepared_feedback_input_tokens": reply["payload"]["feedback_input_tokens"],
                     "feedback_sent_to_later_request": index < 20})
        assert len(operations[ident]) == complete["payload"]["actual_operations"]
        cumulative_operations += len(operations[ident])
        previous = operations[ident]

    all_operations = [operation for group in operations.values() for operation in group]
    assert cumulative_operations == len(all_operations) == loop["actual_operations"] == 30
    assert len([op for op in all_operations if not op["result"]["accepted"]]) == 1
    assert len([op for op in all_operations if op["action"]["action"] == "check"]) == 1
    model_seconds = sum(row["model_seconds"] for row in rows)
    processing_seconds = sum(row["processing_seconds"] for row in rows)
    result = {
        "status": "independently_recomputed_from_saved_wires_endpoints_and_receipts",
        "run": "url_port_entry/run-002",
        "response_seal_sha256": digest(RUN / "RESPONSE_SEAL.json"),
        "records_sha256": digest(RUN / "records.jsonl"),
        "verification_sha256": digest(HERE / "VERIFICATION-002.json"),
        "accounting_script_sha256": digest(Path(__file__)),
        "disposition": loop["disposition"],
        "sent_requests": len(started), "completed_responses": len(rows),
        "actual_operations": len(all_operations),
        "operation_types": dict(sorted(Counter(op["action"]["action"] for op in all_operations).items())),
        "operation_origins": dict(sorted(Counter(op["origin"] for op in all_operations).items())),
        "accepted_operations": sum(op["result"]["accepted"] is True for op in all_operations),
        "rejected_operations": sum(op["result"]["accepted"] is False for op in all_operations),
        "sent_input_tokens": sum(row["input_tokens"] for row in rows),
        "generated_tokens": sum(row["generated_tokens"] for row in rows),
        "cached_input_tokens": sum(row["cached_input_tokens"] for row in rows),
        "model_request_seconds": model_seconds,
        "response_processing_seconds": processing_seconds,
        "task_loop_seconds": loop["task_loop_seconds"],
        "task_loop_minus_model_request_seconds": loop["task_loop_seconds"] - model_seconds,
        "task_loop_minus_model_and_response_processing_seconds":
            loop["task_loop_seconds"] - model_seconds - processing_seconds,
        "peak_sent_input_tokens": max(row["input_tokens"] for row in rows),
        "peak_generated_tokens": max(row["generated_tokens"] for row in rows),
        "peak_sent_input_plus_generation": max(row["input_plus_generation"] for row in rows),
        "native_measured_inputs_including_unsent": len(native),
        "peak_native_measured_input_including_unsent": max(c["prompt_tokens"] for c in native.values()),
        "native_measured_inputs_not_sent": len(native) - len(started),
        "feedback_admitted_after_completed_response": len(processed),
        "previous_reply_feedback_received_in_actual_next_request": 19,
        "accepted_source_extents_verified_in_next_actual_input": source_deliveries,
        "last_check_feedback_admitted_but_not_sent": {
            "after": "C20", "observation": "CHK-0030", "passed": False,
            "prepared_feedback_input_tokens": rows[-1]["prepared_feedback_input_tokens"],
            "reason": "No C21 exists; the twenty-request allowance is exhausted.",
            "interpretation_or_correction_after_check": "not exercised"},
        "input_presentation_modes": dict(Counter(row["input_mode"] for row in rows)),
        "final_candidate_id": loop["candidate_id"], "submitted": loop["submitted"],
        "current_public_pass": loop["current_check"],
        "runtime_closure": closed,
        "no_additional_model_checker_or_native_execution": True,
        "limits": [
            "Generated usage includes thinking and final output; it does not identify wasted reasoning.",
            "Processing time includes rendering/admission and native measurements, not just checker execution.",
            "The action allowance remaining after the check does not create another adaptive model request.",
            "Replay and accounting do not establish semantic correctness of the new tests or account.",
            "Recovery-mode inputs can contain new exact inspection excerpts while designated bulk bodies remain omitted."],
        "calls": rows}
    out = HERE / "METRICS-002-INDEPENDENT.json"
    assert not out.exists(), "Preserve earlier accounting attempts before replacing a report."
    out.write_text(json.dumps(result, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(json.dumps({key: result[key] for key in [
        "status", "sent_requests", "actual_operations", "operation_types", "sent_input_tokens",
        "generated_tokens", "model_request_seconds", "response_processing_seconds", "task_loop_seconds",
        "peak_sent_input_tokens", "peak_generated_tokens", "peak_sent_input_plus_generation",
        "peak_native_measured_input_including_unsent", "input_presentation_modes"]}, indent=2))


if __name__ == "__main__":
    main()
