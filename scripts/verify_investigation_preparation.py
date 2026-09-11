"""Offline seal, native-token, state-delivery and oracle replay verification."""
import argparse
from pathlib import Path
from types import SimpleNamespace

import prepare_investigation_loop as prep
import run_investigation_loop as run
from working_set_exp.custody import verify_records
from working_set_exp.event_frame_v3 import resident_pair_v3
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count

PACKAGE_SHA = "6c4ae13079c093c73b0b29ea7a830e66081e0344a0be088dc1dde3785b48ed93"
SEAL_SHA = "9197f9e3f366f9146c68dbbc0c42969edf3e292af298ddf4f6e911119ce8a080"
TOKENIZER_SHA = "d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",type=Path,required=True)
    parser.add_argument("--tokenizer",type=Path,required=True)
    parser.add_argument("--output",type=Path,required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    folder = prep.PACKAGE
    plan = run.validate_package(folder,PACKAGE_SHA)
    assert sha256_file(folder/"PREPARATION_SEAL.json") == SEAL_SHA
    seal = load_json_strict((folder/"PREPARATION_SEAL.json").read_bytes())
    for name,digest in seal["private_runtime_files_local_only"].items():
        assert sha256_file(folder/"private-runtime"/name) == digest
    assert sha256_file(args.model) == plan["actor"]["model_sha256"]
    assert sha256_file(args.tokenizer) == TOKENIZER_SHA
    profile = SimpleNamespace(model_path=args.model,tokenizer_path=args.tokenizer)
    cache, checks = {}, []
    records = verify_records(folder/"records.jsonl",folder)
    inputs = [r["payload"] for r in records if r["record_type"]=="input_prepared"]
    assert len(inputs) == 47
    assert all(not r["completion_sent"] and r["routes"]==["/apply-template","/tokenize"] for r in inputs)
    closed = [r for r in records if r["record_type"]=="runtime_closed"]
    assert len(closed)==1 and closed[0]["payload"]["owned_server_shutdown_verified"] and closed[0]["payload"]["dedicated_port_free"]
    for row in inputs:
        stem = row["stem"]
        rendered = (folder/(stem+"-rendered-prompt.txt")).read_bytes()
        template = load_json_strict((folder/(stem+"-template-response.json")).read_bytes())
        tokens = load_json_strict((folder/(stem+"-tokenization.json")).read_bytes())["tokens"]
        assert template["prompt"].encode()==rendered and sha256_bytes(rendered)==row["rendered_sha256"]
        if rendered not in cache:
            cache[rendered]=tokenizer_count(profile,rendered)
        assert len(tokens)==cache[rendered]==row["prompt_tokens"]
        assert row["would_admit"] == (len(tokens)<=prep.INPUT_CEILING)
        checks.append({"stem":stem,"native_tokens":len(tokens),"would_admit":row["would_admit"]})
    initial = [load_json_strict((folder/(r["stem"]+"-request.json")).read_bytes()) for r in plan["schedule"]]
    assert initial[0]["messages"] == initial[1]["messages"] and initial[0]["seed"] != initial[1]["seed"]
    for request in initial:
        state=load_json_strict(request["messages"][1]["content"].encode())
        assert not state["active_phase_event_frame"]["events"] and state["resource_state"]["calls_remaining"]==20
        assert not state["observation_directory"]["entries"]
    selected=prep.load_fixture(folder)
    visible=(folder/"TOOL_REFERENCE.txt").read_text(encoding="utf-8")
    replays=[]
    for path in plan["qualification_paths"]:
        value=new_state(path["path"],selected)
        denied=None
        for number,row in enumerate(path["inputs"],1):
            saved=(folder/(row["stem"]+"-request.json")).read_bytes()
            assert canonical_json_bytes(prep.request_for(value,prep.SEEDS[0],visible))==saved
            state=load_json_strict(load_json_strict(saved)["messages"][1]["content"].encode())
            assert [resident_pair_v3(e) for e in state["active_phase_event_frame"]["events"]]==value.pairs
            if not row["would_admit"] and denied is None:
                denied=number
            oracle=load_json_strict((folder/(row["stem"]+"-oracle.json")).read_bytes())
            assert value.execute(oracle["action"])==oracle["result"]
            assert value.state.candidate.candidate_id==oracle["candidate_after"]
        assert value.state.submitted and value.state.public_check_passed
        replays.append({"path":path["path"],"actions":len(value.pairs),"first_denied_input":denied,
                        "later_oracle_states_counterfactual":denied is not None,"final_candidate_id":value.state.candidate.candidate_id})
    report={"scope":"offline independent token recount, exact prepared-history replay and custody verification; not model behavior or proof of direct review",
            "model_completions":0,"package_sha256":PACKAGE_SHA,"seal_sha256":SEAL_SHA,
            "verifier_sha256":sha256_file(Path(__file__)),"source_identities":len(plan["source_sha256"]),
            "public_files_verified":len(seal["files"]),"private_files_verified_local_only":len(seal["private_runtime_files_local_only"]),
            "records_verified":len(records),"native_inputs_verified":len(checks),"distinct_cli_recounts":len(cache),
            "tokenizer_sha256":TOKENIZER_SHA,"input_checks":checks,"oracle_replays":replays,
            "memory_during_render_only_preparation":seal["memory"],"actual_inference_workload_qualified":False}
    args.output.write_bytes(canonical_json_bytes(report))
    print({k:report[k] for k in ("model_completions","public_files_verified","native_inputs_verified","distinct_cli_recounts","oracle_replays")})


if __name__ == "__main__":
    main()
