"""Verify and replay the mock rehearsal from saved records; no model endpoint."""
from __future__ import annotations

import copy
from pathlib import Path

import run_compiler_incident as run
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


def verify():
    folder = run.AREA / "execution-rehearsal-001"
    seal_path = folder / "MOCK_REHEARSAL_SEAL.json"
    seal = load_json_strict(seal_path.read_bytes())
    plan = run.load_manifest()
    assert seal["actual_model_completion_requests"] == 0 and seal["runtime_launched"] is False
    assert seal["execution_manifest_sha256"] == sha256_file(run.MANIFEST)
    assert seal["test_source_sha256"] == sha256_file(run.TEST)
    assert sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"]
    assert [r for r in run.base.file_inventory(folder) if r["path"] != seal_path.name] == seal["files"]
    records = verify_records(folder / "records.jsonl",folder)
    assert len(records) == seal["record_count"]

    def normalized(request):
        request = dict(request)
        request["seed"] = run.task.SEEDS[0]
        return canonical_json_bytes(request)

    # Match the whole endpoint request, not merely the token count or task text.
    native_sources = {}
    for path in run.PACKAGE.rglob("*-request.json"):
        stem = str(path).removesuffix("-request.json")
        native_sources[normalized(load_json_strict(path.read_bytes()))] = stem
    fixture = run.load_fixture()
    reference = run.pilot.tool_reference(run.pilot.grammar_for(run.new_state("reference",fixture)))
    cells = {c["id"]:c for c in plan["schedule"]}
    states, admitted, completed = {}, {}, []
    native_count = 0
    for record in records:
        kind,payload = record["record_type"],record["payload"]
        if kind == "cell_started":
            states[payload["id"],"SHARED"] = run.new_state(payload["id"],fixture)
        elif kind == "authentic_fork":
            parent = states[payload["cell_id"],"SHARED"]
            assert (folder / ("forks/"+payload["cell_id"]+".json")).read_bytes() == canonical_json_bytes(run.snapshot(parent))
            assert len(parent.pairs) == payload["prefix_actions"] == 6
            assert payload["input_tokens"] == 17753
        elif kind == "branch_started":
            states[payload["cell_id"],payload["condition"]] = copy.deepcopy(states[payload["cell_id"],"SHARED"])
        elif kind == "native_input_prepared":
            cell,segment = payload["cell_id"],payload["segment"]
            value = run.new_state("preflight",fixture) if segment == "PREFLIGHT" else states[cell,segment]
            stem = folder / payload["admission_stem"]
            raw = Path(str(stem)+"-endpoint-request.json").read_bytes()
            request = load_json_strict(raw)
            assert raw == canonical_json_bytes(run.task.request_for(value,reference,
                externalized=payload["externalized_through"],seed=cells[cell]["seed"]))
            assert b"PRIVATE_REASONING_SENTINEL" not in raw
            assert Path(str(stem)+"-candidate.json").read_bytes() == run.pilot.reference.candidate_bytes(value.state.candidate)
            assert Path(str(stem)+"-session.json").read_bytes() == run.pilot.reference.session_bytes(value.state)
            source = native_sources[normalized(request)]
            for suffix in ("-native.txt","-template.json","-tokens.json"):
                assert Path(str(stem)+suffix).read_bytes() == Path(source+suffix).read_bytes()
            native = Path(str(stem)+"-native.txt").read_bytes()
            assert sha256_bytes(raw) == payload["endpoint_request_sha256"]
            assert sha256_bytes(native) == payload["native_input_sha256"]
            assert len(load_json_strict(Path(str(stem)+"-tokens.json").read_bytes())["tokens"]) == payload["prompt_tokens"]
            native_count += 1
            admitted[payload["id"]] = payload
        elif kind == "invocation_started":
            assert payload["admission_stem"] == admitted[payload["id"]]["admission_stem"]
            assert payload["prompt_tokens"] <= (23808 if payload["segment"] == "R23808" else 16000)
        elif kind == "invocation_completed":
            value = states[payload["cell_id"],payload["segment"]]
            stem = folder / ("calls/"+payload["id"])
            response = load_json_strict(Path(str(stem)+"-endpoint-response.json").read_bytes())
            message = response["choices"][0]["message"]
            assert response["choices"][0]["finish_reason"] == "stop"
            assert message["reasoning_content"] == Path(str(stem)+"-assistant-reasoning.txt").read_text() == "PRIVATE_REASONING_SENTINEL"
            assert message["content"].encode() == Path(str(stem)+"-assistant-content.txt").read_bytes()
            action = load_json_strict(message["content"].encode())
            assert canonical_json_bytes(action) == Path(str(stem)+"-action.json").read_bytes()
            host = load_json_strict(Path(str(stem)+"-host-result.json").read_bytes())
            assert host == payload["host_result"] and host["executed"]
            assert value.execute(action) == host["result"]
            assert Path(str(stem)+"-candidate-after.json").read_bytes() == run.pilot.reference.candidate_bytes(value.state.candidate)
            assert Path(str(stem)+"-state-after.json").read_bytes() == run.pilot.reference.session_bytes(value.state)
            completed.append(payload["id"])
        elif kind == "segment_completed":
            value = states[payload["cell_id"],payload["segment"]]
            saved = folder / ("segments/"+payload["cell_id"]+"-"+payload["segment"]+"-pairs.json")
            assert saved.read_bytes() == canonical_json_bytes(value.pairs)
            assert len(value.pairs) == payload["actions_total"]
            assert value.state.public_check_passed == payload["public_check_passed"]
            assert value.state.submitted == payload["submitted"]
    assert len(completed) == len(set(completed)) == seal["mocked_completion_responses"] == 34
    assert sum(r["record_type"] == "invocation_started" for r in records) == 34
    assert [r["payload"] for r in records if r["record_type"] == "cell_completed"] == seal["cells"]
    assert all(states[cell,condition].state.submitted and states[cell,condition].state.public_check_passed
               for cell in cells for condition in run.CONDITIONS)
    result = dict(verified=True,actual_model_completion_requests=0,mocked_actions_independently_replayed=34,
        checked_submissions=4,shared_prefix_actions_per_cell=6,native_inputs_verified=native_count,
        custody_records_verified=len(records),public_files_verified=len(seal["files"]),
        execution_manifest_sha256=sha256_file(run.MANIFEST),mock_rehearsal_seal_sha256=sha256_file(seal_path),
        verifier_sha256=sha256_file(Path(__file__)),
        scope="Offline exact-input and real-tool replay of mocked replies; no new model or tokenizer evidence.")
    run.base.write_json(run.AREA / "execution-checks-001/REHEARSAL_VERIFICATION.json",result)
    print(result)


if __name__ == "__main__":
    verify()
