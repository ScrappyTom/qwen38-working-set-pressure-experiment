import copy
from pathlib import Path
import sys

import inspect
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import saved_work_continuation as work
import prepare_saved_work_continuation as prep
import run_saved_work_continuation as run
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes


def initial():
    value = work.starting_state()
    group = work.assemble(value, 1)
    request = work.request_for(value, phase=1, phase_used=0, total_used=0,
        externalized=0, setup_ranges=[[1,3],[4,7]])
    return value, group, request


def test_saved_candidate_and_historical_capture_bindings():
    value, group, request = initial()
    assert value.state.candidate.candidate_id == work.SUCCESSOR
    assert work.delivered(request, value, group)
    assert all(row["candidate_id"] == value.fixture.initial.candidate_id for row in value.fixture.observations)
    assert value.pairs[2]["result"]["checked_candidate_id"] == work.SUCCESSOR
    assert "25/26 contract cases passed" in value.pairs[2]["result"]["stdout"]
    state = work.read_bytes(request["messages"][1]["content"].encode())
    assert state["resource_state"]["calls_used"] == 0
    assert state["resource_state"]["phase_calls_remaining"] == 8
    assert request["chat_template_kwargs"] == {"enable_thinking":True, "reasoning_effort":"xhigh"}
    assert all(request[k] == -1 for k in ("max_tokens","n_predict","thinking_budget_tokens","reasoning_budget_tokens"))
    assert request["response_format"] == work.pilot.grammar_for(value)


def test_prefix_admission_is_monotonic_and_does_not_protect_or_restore_groups():
    value, group, _ = initial()
    tried = []
    def render(request, prefix):
        tried.append(prefix)
        return {"prompt_tokens":work.INPUT_CEILING+1 if prefix < 6 else work.INPUT_CEILING}
    selected = work.select_input(value, previous=4, phase=1, phase_used=0, total_used=0,
        setup_ranges=[[1,3],[4,7]], render=render)
    assert tried == [4,5,6]
    assert selected["externalized"] == 6
    assert not work.delivered(selected["request"], value, group)
    assert work.delivered(selected["request"], value, [7])


def test_rejected_report_edit_preserves_source_and_current_guards():
    value, _, _ = initial()
    before = value.state.candidate
    action = prep.report_action(value, prep.report_text({"builds":prep.oracle_report()["builds"][:1]}))
    action["expected_candidate_id"] = value.fixture.initial.candidate_id
    result = value.execute(action)
    assert not result["accepted"] and value.state.candidate == before
    request = work.request_for(value, phase=1, phase_used=1, total_used=1,
        externalized=len(value.pairs), setup_ranges=[[1,3],[4,7]])
    assert work.result_delivered(request, value, len(value.pairs))
    assert not work.delivered(request, value, [len(value.pairs)])  # The rejected patch's old/new are external.


def fake_render(url, request):
    native = ("mock-template:" + sha256_bytes(canonical_json_bytes(request))).encode()
    return canonical_json_bytes({"prompt":native.decode()}), native, canonical_json_bytes({"tokens":[0]*1000}), 1000


def make_loop(tmp_path, mode="direct"):
    _, _, request = initial()
    native = fake_render("offline",request)[1]
    plan = dict(initial_request_sha256=sha256_bytes(canonical_json_bytes(request)),
        initial_native_sha256=sha256_bytes(native), initial_prompt_tokens=1000)
    store, log = ArtifactStore(tmp_path), run.RunLog(tmp_path/"records.jsonl", "mock-saved-work")
    requests = []
    def post(url, route, raw, timeout):
        assert route == "/v1/chat/completions"
        request = work.read_bytes(raw)
        state = work.read_bytes(request["messages"][1]["content"].encode())
        requests.append(state)
        phase = int(state["active_user_authored_step"]["id"][-1])
        used = state["resource_state"]["phase_calls_used"]
        if mode == "exhaust" or used == 1:
            action = dict(action="check", check_id="public", expected_candidate_id=state["candidate_id"])
        elif used == 0:
            # The mock chooses a known oracle action, never an input to Qwen.
            events = state["active_phase_event_frame"]["events"]
            exact = next(e["result_body"]["fields"]["content"] for e in reversed(events)
                if e["action"].get("path") == work.REPORT and e["action"]["action"] == "read" and e["result_body"]["fields"])
            file_hash = next(e["result"]["file_sha256"] for e in reversed(events)
                if e["action"].get("path") == work.REPORT and e["action"]["action"] == "read")
            expected = prep.oracle_report()
            if phase == 1:
                expected["builds"] = expected["builds"][:1]
                if mode == "wrong_partial":
                    expected["builds"][0]["changed_functions"] = []
            action = dict(action="patch", path=work.REPORT, old=exact, new=prep.report_text(expected),
                expected_candidate_id=state["candidate_id"], expected_file_sha256=file_hash)
        else:
            action = dict(action="submit", expected_candidate_id=state["candidate_id"])
        return canonical_json_bytes(dict(choices=[dict(finish_reason="length" if mode == "incomplete" else "stop",
            message=dict(reasoning_content="mock reasoning", content=canonical_json_bytes(action).decode()))],
            usage=dict(prompt_tokens=1000, completion_tokens=100, total_tokens=1100, prompt_tokens_details=dict(cached_tokens=0)),
            timings=dict(cache_n=0)))
    loop = run.Loop(plan,tmp_path,store,log,post=post,render=fake_render,health=lambda:{},source_check=lambda:None)
    return loop, requests


def test_real_runner_closes_after_restart_without_oracle_transition(tmp_path, mode="direct"):
    loop, requests = make_loop(tmp_path, mode)
    result = loop.execute()
    records = verify_records(tmp_path/"records.jsonl", tmp_path)
    assert result["sent_requests"] == 5 and result["current_public_check_passed"] and result["submitted"]
    restart = [r for r in records if r["record_type"] == "deliberate_working_context_restart"]
    assert len(restart) == 1 and restart[0]["payload"]["semantic_assessment_used"] is False
    assert [s["resource_state"]["phase_calls_used"] for s in requests] == [0,1,0,1,2]
    phase2 = requests[2]
    assert phase2["active_phase_event_frame"]["externalized_payload_through_sequence"] == 9
    assert all(e["result_body"]["fields"] is None for e in phase2["active_phase_event_frame"]["events"][:9])
    assert len([r for r in records if r["record_type"] == "assisted_acquisition"]) == 9
    assert all(r["payload"]["selected_generation_reserve"] == 32768 for r in records if r["record_type"] == "invocation_completed")


def test_phase_budget_does_not_transfer_or_trigger_automatic_restart(tmp_path):
    loop, requests = make_loop(tmp_path, "exhaust")
    result = loop.execute()
    records = verify_records(tmp_path/"records.jsonl", tmp_path)
    assert len(requests) == 8 and result["disposition"] == "phase_allowance_exhausted"
    assert not any(r["record_type"] == "deliberate_working_context_restart" for r in records)


def test_incomplete_response_preserved_without_action_or_retry(tmp_path):
    loop, requests = make_loop(tmp_path, "incomplete")
    with unittest.TestCase().assertRaisesRegex(ValueError, "incomplete output"):
        loop.execute()
    records = verify_records(tmp_path/"records.jsonl", tmp_path)
    assert len(requests) == 1
    assert len([r for r in records if r["record_type"] == "response_extracted"]) == 1
    assert not any(r["record_type"] == "action_selected" for r in records)
    assert work.read(tmp_path/"calls/P1-01-C01-candidate-after.json")["candidate_id"] == work.SUCCESSOR


def test_preparation_and_live_paths_keep_oracle_out_of_inputs():
    import ast
    tree = ast.parse((ROOT/"scripts/run_saved_work_continuation.py").read_text())
    imports = [n.module for n in ast.walk(tree) if isinstance(n, ast.ImportFrom)]
    imports += [a.name for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names]
    assert "prepare_saved_work_continuation" not in imports and "prepare_compiler_incident" not in imports
    _, _, request = initial()
    state = work.read_bytes(request["messages"][1]["content"].encode())
    assert state["development_setup_sequence_ranges"] == [[1,3],[4,7]]
    assert "expected_report" not in canonical_json_bytes(request).decode()


def load_tests(loader, tests, pattern):
    suite = unittest.TestSuite()
    for name, function in list(globals().items()):
        if not name.startswith("test_") or not callable(function):
            continue
        parameters = inspect.signature(function).parameters
        for mode in (("direct", "wrong_partial") if "mode" in parameters else (None,)):
            def invoke(function=function, parameters=parameters, mode=mode):
                with tempfile.TemporaryDirectory(prefix="saved-work-test-") as folder:
                    kwargs = {"tmp_path":Path(folder)} if "tmp_path" in parameters else {}
                    if mode is not None:
                        kwargs["mode"] = mode
                    function(**kwargs)
            suite.addTest(unittest.FunctionTestCase(invoke, description=name+("/"+mode if mode else "")))
    return suite
