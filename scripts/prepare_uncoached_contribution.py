"""Native full-loop qualification with scripted replies; zero model inference."""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
from types import SimpleNamespace

import parser_roundtrip as task
from run_uncoached_contribution import Adapter, Loop, RunLog
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.working_session import INPUT_LIMIT


class ScriptedLog(RunLog):
    def append(self, kind, payload, artifacts):
        payload = {**payload, "qualification_only": True}
        if kind in ("invocation_started", "response_received", "response_extracted", "invocation_completed"):
            payload.update(scripted_response_not_model_output=True, completion_sent=False)
        return super().append(kind, payload, artifacts)


def scripted_reply(session, mode, number):
    """Fixed qualification program; none of this policy enters live inputs."""
    prefix = ([dict(action="tree", path=".", offset=0, limit=8),
               dict(action="search", path="Lib", query="MultilineContinuationError", offset=0, limit=8),
               dict(action="read", path="Lib/configparser.py", start_line=594, end_line=622)] if mode == "compact" else
              [dict(action="read", path="Lib/configparser.py", start_line=1, end_line=0),
               dict(action="read", path="Lib/test/test_configparser.py", start_line=1, end_line=605),
               dict(action="check", check_id="public", expected_candidate_id=session.candidate.candidate_id)])
    group = dict(action="work_on", sources=[dict(path=p, start_line=a, end_line=b) for p, a, b in (
        ("Lib/configparser.py", 299, 341), ("Lib/configparser.py", 594, 622),
        ("Lib/test/test_configparser.py", 1812, 1870))], results=[])
    anchor = "class InlineCommentStrippingTestCase(unittest.TestCase):"
    reference = (task.AREA / "REFERENCE_TEST.py").read_text(encoding="utf-8")
    if number <= 3:
        operation = prefix[number-1]
    elif number == 4:
        operation = group
    elif number == 5:
        operation = dict(action="check", check_id="public", expected_candidate_id=session.candidate.candidate_id)
    elif number == 6:
        operation = dict(action="patch", path="Lib/test/test_configparser.py", old=anchor,
            new=reference.replace("range(pickle.HIGHEST_PROTOCOL + 1)", "(pickle.DEFAULT_PROTOCOL,)") + "\n\n" + anchor,
            expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256("Lib/test/test_configparser.py"))
    elif number == 7:
        operation = dict(action="patch", path="Lib/test/test_configparser.py", old="(pickle.DEFAULT_PROTOCOL,)",
            new="range(pickle.HIGHEST_PROTOCOL + 1)", expected_candidate_id=session.candidate.candidate_id,
            expected_file_sha256=session.candidate.file_sha256("Lib/test/test_configparser.py"))
    elif number == 8:
        operation = dict(action="patch", path="Lib/test/test_configparser.py", old=anchor, new=anchor + "\n    pass",
            expected_candidate_id=task.STARTING_ID,
            expected_file_sha256=task.starting_work()[0].file_sha256("Lib/test/test_configparser.py"))
    elif number == 9:
        operation = dict(action="submit", expected_candidate_id=session.candidate.candidate_id)
    else:
        raise AssertionError("scripted route overran its planned closure")
    reply = dict(discussion="OFFLINE SCRIPT; no Qwen inference or reviewer message.",
                 operation=json.loads(canonical_json_bytes(operation)))
    if number in (6, 7, 8):
        reply["check_after"] = "public"
    return reply


def qualify_case(output, url, mode, source_identities):
    output.mkdir()
    session, adapter = task.initial_session(), Adapter(task)
    store, log = ArtifactStore(output), ScriptedLog(output / "records.jsonl", "scripted-" + mode)
    # Do not send the intercepted completion route to the native endpoint.
    def post(url, route, wire, timeout):
        task.require(route == "/v1/chat/completions", "unexpected scripted route")
        request = json.loads(wire)
        task.require(wire == completion_request_bytes(adapter.request_for(session.view())), "actual wire differs")
        state = json.loads(request["messages"][1]["content"])
        task.require(set(state) == {"workspace", "preceding_operation_feedback"}, "coaching channel present")
        row = loop.cache[sha256_bytes(canonical_json_bytes(request))]
        number = loop.sent
        if number in (7, 8):
            edit = state["preceding_operation_feedback"][0]["result"]
            check = state["workspace"]["latest_feedback"]["result"]
            task.require(edit["candidate_id"] == check["checked_candidate_id"], "bundle receipt binding differs")
            task.require(check["passed"] == (number == 8), "actual failed/corrected check differs")
        reply = scripted_reply(session, mode, number)
        # The one output token is a mock accounting placeholder, not a measurement.
        return canonical_json_bytes(dict(choices=[dict(finish_reason="stop", message=dict(
            reasoning_content="", content=json.dumps(reply, ensure_ascii=False, separators=(",", ":"))))],
            usage=dict(prompt_tokens=row["prompt_tokens"], completion_tokens=1, total_tokens=row["prompt_tokens"] + 1,
                       prompt_tokens_details=dict(cached_tokens=0)), timings=dict(cache_n=0)))
    loop = Loop(output, store, log, url=url, task_module=adapter, post=post,
                source_check=lambda: task.verify_sources(source_identities), health=lambda: task.base.pilot.health(output.parent.parent))
    initial_count = loop.measure(session.view())
    initial = next(iter(loop.cache.values()))
    outcome = loop.execute(session)
    task.require(outcome["disposition"] == "checked_submission" and outcome["sent_requests"] == 9 and
                 outcome["actual_operations"] == 11, "scripted route did not finish as expected")
    task.require(all(session.candidate.file_map[p] == data for p, data in task.starting_work()[0].files
                     if p != "Lib/test/test_configparser.py"), "prior work changed")
    task.require(not task.read(output / "calls/C08-host-result.json")["operations"][0]["result"]["accepted"], "stale guard accepted")
    records = verify_records(output / "records.jsonl", output)
    admitted = [r["payload"]["prompt_tokens"] for r in records if r["record_type"] == "invocation_started"]
    admitted += [r["payload"]["feedback_input_tokens"] for r in records if r["record_type"] == "reply_processed"]
    peak = max(admitted)
    task.require(peak <= INPUT_LIMIT, "qualification admitted input exceeded hard ceiling")
    task.require(all(not r["payload"].get("completion_sent") for r in records), "qualification claims a completion send")
    result = dict(mode=mode, status="scripted_complete_contribution", completion_requests=0,
        scripted_replies=loop.sent, mock_output_tokens_are_not_inference=True, actual_operations=session.calls_used,
        initial={k: initial[k] for k in ("prompt_tokens", "request_sha256", "native_sha256", "wire_request_sha256")},
        peak_input=peak, peak_sizing_trial=max(row["prompt_tokens"] for row in loop.cache.values()),
        native_inputs=len(loop.cache), outcome=outcome,
        no_reviewer_messages=True, script_is_not_model_selection=True)
    task.save(output, "QUALIFICATION.json", result)
    return result


def prepare(output):
    task.require(not output.exists(), "preserve existing preparation")
    output.mkdir(parents=True)
    store, log = ArtifactStore(output), ScriptedLog(output / "records.jsonl", "uncoached-preparation")
    source_identities = task.source_identities()
    status, error = "incomplete", None
    server, model, _ = task.runtime_paths()
    args = SimpleNamespace(output=output, server=server, model=model)
    original_post = task.base.base.post
    def rendering_only(url, route, raw, timeout):
        task.require(route in ("/apply-template", "/tokenize"), "native preparation cannot send completions")
        return original_post(url, route, raw, timeout)
    try:
        # Both owned startup and model settings are the actual selected runtime.
        # Only /apply-template and /tokenize POSTs are permitted inside it.
        with task.base.base.owned_runtime(args, store, log) as url:
            task.base.base.post = rendering_only
            try:
                (output / "cases").mkdir()
                results = [qualify_case(output / "cases" / mode, url, mode, source_identities) for mode in ("compact", "broad")]
            finally:
                task.base.base.post = original_post
        session, adapter = task.initial_session(), Adapter(task)
        task.save(output, "starting-candidate.json", task.candidate_bytes(session.candidate))
        task.save(output, "starting-state.json", task.snapshot(session))
        task.save(output, "initial-wire-request.json", completion_request_bytes(adapter.request_for(session.view())))
        task.save(output, "initial-request.json", adapter.request_for(session.view()))
        spec = importlib.util.spec_from_file_location("pinned_converter", task.base.AREA / "parser-documentation/grammar-review/json_schema_to_grammar.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        converter = module.SchemaConverter(prop_order={}, allow_fetch=False, dotall=False, raw_pattern=False)
        converter.visit(json.loads(completion_request_bytes(adapter.request_for(session.view())))["response_format"]["json_schema"]["schema"], "")
        grammar = converter.format_grammar().encode()
        proof = task.base.AREA / "parser-documentation/wire-qualification-001/implemented_combined.gbnf"
        task.require(grammar == proof.read_bytes(), "schema differs from qualified native grammar")
        task.save(output, "qualified-native-grammar.gbnf", grammar)
        task.save(output, "NATIVE_CONSTRAINT_BINDING.json", dict(grammar_sha256=sha256_bytes(grammar),
            existing_native_proof_sha256=sha256_file(proof.parent / "RESULTS.json"), exact_grammar_unchanged=True))
        result = dict(status="qualified_no_model_inference", completion_requests=0, actor=task.ACTOR,
            source_sha256=source_identities, initial=results[0]["initial"], cases=results,
            peak_input=max(r["peak_input"] for r in results), native_inputs=sum(r["native_inputs"] for r in results),
            memory=task.base.base.memory_stats(output / "memory.csv"), runtime=task.base.base.runtime_evidence(output / "private-runtime/server.stderr.log"),
            port_free=task.base.base.port_free(task.base.base.PORT))
        task.save(output, "QUALIFICATION.json", result)
        status = "qualified_no_model_inference"
    except BaseException as problem:
        error = problem
        task.save(output, "FAILED.json", dict(error_type=type(problem).__name__, error=str(problem)))
    finally:
        task.base.base.post = original_post
        files = task.base.base.file_inventory(output)
        task.save(output, "SEAL.json", dict(status=status, files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),
            source_sha256=source_identities, completion_requests=0,
            private_runtime_files_local_only={p.name: sha256_file(p) for p in (output/"private-runtime").glob("*") if p.is_file()}))
    if error:
        raise error
    task.save(task.AREA, "EXECUTION_MANIFEST.json", dict(status="prepared_not_executed", actor=task.ACTOR,
        maximum_requests=task.MAX_REQUESTS, maximum_operations=task.MAX_OPERATIONS, input_ceiling=INPUT_LIMIT,
        initial=result["initial"], source_sha256=source_identities, preparation_seal_sha256=sha256_file(output/"SEAL.json"),
        prior_work_seal_sha256=task.SOURCE_SEAL, no_live_coaching=True, automatic_retry=False))
    print("Qualified with zero Qwen requests:", result["native_inputs"], "native inputs; peak", result["peak_input"], flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=task.PACKAGE)
    prepare(parser.parse_args().output)
