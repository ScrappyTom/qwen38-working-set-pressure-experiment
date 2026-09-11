"""Independently replay the saved offline package; never launches a model."""
from __future__ import annotations

import re
from pathlib import Path

import prepare_compiler_incident as prep
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


def action_form(action, request):
    forms = request["response_format"]["json_schema"]["schema"]["oneOf"]
    form = next(f for f in forms if f["properties"]["action"].get("const") == action["action"])
    assert form["additionalProperties"] is False
    assert set(action) == set(form["required"]) == set(form["properties"])
    for key, value in action.items():
        spec = form["properties"][key]
        assert set(spec) <= {"type", "const", "enum", "pattern", "minimum", "maximum", "minLength", "maxLength"}
        assert type(value) is (str if spec["type"] == "string" else int)
        if "const" in spec:
            assert value == spec["const"]
        if "enum" in spec:
            assert value in spec["enum"]
        if "pattern" in spec:
            assert re.fullmatch(spec["pattern"], value)
        for bound, fn, op in (("minLength", len, lambda a,b:a>=b), ("maxLength", len, lambda a,b:a<=b),
                              ("minimum", lambda x:x, lambda a,b:a>=b), ("maximum", lambda x:x, lambda a,b:a<=b)):
            if bound in spec:
                assert op(fn(value), spec[bound])
    assert len(canonical_json_bytes(action)) <= 5000


def verify():
    folder = prep.AREA / "preparation-001"
    seal = load_json_strict((folder / "PREPARATION_SEAL.json").read_bytes())
    manifest = load_json_strict((folder / "PACKAGE_MANIFEST.json").read_bytes())
    for row in seal["files"]:
        path = folder / row["path"]
        assert path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"]
    assert sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"]
    for name, expected in manifest["source_sha256"].items():
        assert sha256_file(prep.ROOT / name) == expected, name
    records = verify_records(folder / "records.jsonl", folder)
    assert len(records) == seal["record_count"] and records[-1]["record_type"] == "preparation_completed"
    assert manifest["completion_calls"] == seal["completion_calls"] == 0
    assert manifest["execution_authorized"] is False
    fixture = prep.constructed_fixture(load_json_strict((folder / "captures.json").read_bytes()))
    assert fixture.public_checker == (folder / "PUBLIC_CHECK.py").read_bytes()
    assert prep.prior.pilot.reference.candidate_bytes(fixture.initial) == (folder / "candidate.json").read_bytes()
    request_count = 0
    for record in records:
        if record["record_type"] != "input_prepared":
            continue
        payload = record["payload"]
        stem = folder / payload["stem"]
        request = load_json_strict(Path(str(stem)+"-request.json").read_bytes())
        native = Path(str(stem)+"-native.txt").read_bytes()
        template = load_json_strict(Path(str(stem)+"-template.json").read_bytes())
        tokens = load_json_strict(Path(str(stem)+"-tokens.json").read_bytes())["tokens"]
        assert native == template["prompt"].encode("utf-8")
        assert len(tokens) == payload["prompt_tokens"]
        assert payload["completion_sent"] is False
        assert request["chat_template_kwargs"] == {"enable_thinking":True, "reasoning_effort":"xhigh"}
        assert all(request[key] == -1 for key in ("max_tokens", "n_predict", "thinking_budget_tokens", "reasoning_budget_tokens"))
        assert payload["physical_generation_space"] == 56576 - len(tokens)
        request_count += 1

    replayed, states = 0, {}
    for route in manifest["qualification_paths"]:
        name = route["route"]
        value = prep.new_state(name, fixture)
        reference = prep.prior.pilot.tool_reference(prep.prior.pilot.grammar_for(value))
        for number in range(1, route["actions"]+1):
            stem = folder / "resident" / name / f"{number:03d}"
            request = load_json_strict(Path(str(stem)+"-request.json").read_bytes())
            oracle = load_json_strict(Path(str(stem)+"-oracle.json").read_bytes())
            assert prep.prior.request_for(value, reference) == request
            action_form(oracle["action"], request)
            assert value.execute(oracle["action"]) == oracle["result"]
            assert value.state.candidate.candidate_id == oracle["candidate_after"]
            replayed += 1
        assert value.state.submitted and value.state.public_check_passed
        states[name] = value

    # Replay the external branch in actual custody order, including the extra
    # retrieval and its next prepared input, independently of its oracle builder.
    prefix = manifest["external_continuation"]["prefix_actions"]
    value = prep.new_state("external-replay", fixture)
    for pair in states["report_incremental"].pairs[:prefix]:
        assert value.execute(pair["response"]) == pair["result"]
    reference = prep.prior.pilot.tool_reference(prep.prior.pilot.grammar_for(value))
    latest = None
    branch_actions = 0
    for record in records:
        if record["record_type"] == "input_prepared" and record["payload"]["stem"].startswith("external/"):
            payload = record["payload"]
            latest = load_json_strict((folder / (payload["stem"]+"-request.json")).read_bytes())
            frame = load_json_strict(latest["messages"][1]["content"].encode())["active_phase_event_frame"]
            assert prep.prior.request_for(value, reference, externalized=frame["externalized_payload_through_sequence"]) == latest
        if record["record_type"] == "external_oracle" and record["payload"]["stem"] != "fork":
            saved = load_json_strict((folder / ("external/"+record["payload"]["stem"]+".json")).read_bytes())
            assert latest is not None and payload["prompt_tokens"] <= 16000
            action_form(saved["action"], latest)
            assert value.execute(saved["action"]) == saved["result"]
            branch_actions += 1
    assert value.state.submitted and value.state.public_check_passed
    assert value.state.candidate == states["report_incremental"].state.candidate
    assert len(value.pairs) == manifest["external_continuation"]["total_actions"]
    assert branch_actions + prefix == len(value.pairs)
    # Original recovery rows are reproducible from a real pre-submit history.
    _, recovery = prep.prior.recovery_probe(states["report_incremental"])
    assert recovery == manifest["exact_recovery"]
    evidence = {"verified":True, "completion_calls":0,
        "verifier_sha256":sha256_file(Path(__file__)),
        "preparation_seal_sha256":sha256_file(folder / "PREPARATION_SEAL.json"),
        "aggregate_sha256":seal["aggregate_sha256"], "public_files_verified":len(seal["files"]),
        "source_files_verified":len(manifest["source_sha256"]), "custody_records_verified":len(records),
        "native_inputs_verified":request_count, "resident_actions_replayed":replayed,
        "external_prefix_actions":prefix, "external_continuation_actions_replayed":branch_actions,
        "exact_recovery_bodies_verified":len(recovery),
        "all_replayed_actions_fit_saved_grammar":True,
        "scope":"Offline custody, template/count consistency and real-tool replay; not model performance or an independent tokenization rerun."}
    prep.prior.base.write_json(prep.AREA / "VERIFICATION.json", evidence)
    print(evidence)


if __name__ == "__main__":
    verify()
