"""Recount and replay the sealed task preparation without model inference."""
from __future__ import annotations

import argparse
from pathlib import Path
from types import SimpleNamespace

import run_correction_investigation as run
from working_set_exp.custody import verify_records
from working_set_exp.event_frame_v3 import resident_pair_v3
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes,load_json_strict,sha256_file
from working_set_exp.runtime import tokenizer_count

prep,require=run.prep,run.require
TOKENIZER_SHA="d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c"


def verify(args):
    require(not args.output.exists(), "verification already exists")
    folder=prep.PACKAGE
    manifest_sha=sha256_file(folder / "PACKAGE_MANIFEST.json")
    plan=run.validate_package(folder,manifest_sha)
    seal=load_json_strict((folder / "PREPARATION_SEAL.json").read_bytes())
    require(sha256_file(args.model)==prep.ACTOR["model_sha256"],"model identity differs")
    require(sha256_file(args.tokenizer)==TOKENIZER_SHA,"tokenizer identity differs")
    for name,digest in seal["private_runtime_files_local_only"].items():
        require(sha256_file(folder / "private-runtime" / name)==digest,"private runtime differs")
    launch=load_json_strict((folder / "private-runtime/launch.json").read_bytes())
    require(launch==prep.base.launch_args(Path(launch[0]),args.model),"actual launch differs")
    require(sha256_file(Path(launch[0]))==prep.ACTOR["server_sha256"],"server identity differs")
    records=verify_records(folder / "records.jsonl",folder)
    require(not any(r["record_type"] in {"invocation_started","response_received","invocation_completed"} for r in records),"completion exposure in preparation")
    closed=[r["payload"] for r in records if r["record_type"]=="runtime_closed"]
    require(len(closed)==1 and closed[0]["owned_server_shutdown_verified"] and closed[0]["dedicated_port_free"],"runtime not closed")
    expected_health=dict(full_offload=True,context_matches=True,q4_k_and_v=True,mtp_disabled=True,truncation_observed=False,cuda_failure_observed=False)
    require(seal["effective_runtime"]==expected_health,"runtime differs")
    require(seal["memory"]==prep.base.memory_stats(folder / "memory.csv"),"memory summary differs")
    selected=prep.load_fixture(folder)
    reference=(folder / "TOOL_REFERENCE.txt").read_text(encoding="utf-8")
    require(reference==prep.pilot.tool_reference(prep.pilot.grammar_for(new_state("verify",selected))),"reference differs")
    counts,inputs={},[]
    profile=SimpleNamespace(model_path=args.model,tokenizer_path=args.tokenizer)

    def inspect(row,value):
        stem=folder / row["stem"]
        raw=Path(str(stem)+"-request.json").read_bytes()
        require(raw==canonical_json_bytes(prep.request_for(value,reference)),"reconstructed input differs")
        request=load_json_strict(raw)
        state=load_json_strict(request["messages"][1]["content"].encode())
        require(state["active_user_authored_step"]["episode_annotation"]==prep.EPISODE_ANNOTATION,"annotation differs")
        require([resident_pair_v3(e) for e in state["active_phase_event_frame"]["events"]]==value.pairs,"resident feedback differs")
        native=Path(str(stem)+"-rendered-prompt.txt").read_bytes()
        require(load_json_strict(Path(str(stem)+"-template-response.json").read_bytes())["prompt"].encode()==native,"native rendering differs")
        require(request["messages"][1]["content"].encode() in native,"user state absent from native input")
        require(sha256_file(Path(str(stem)+"-rendered-prompt.txt"))==row["rendered_sha256"],"native hash differs")
        if native not in counts:counts[native]=tokenizer_count(profile,native)
        n=counts[native]
        require(n==len(load_json_strict(Path(str(stem)+"-tokenization.json").read_bytes())["tokens"])==row["prompt_tokens"]<=prep.INPUT_CEILING,"input count differs")
        inputs.append(dict(stem=row["stem"],native_tokens=n,resident_events=len(value.pairs),annotation_present=True))

    inspect(plan["initial"],new_state("R01",selected))
    paths=[]
    for route in plan["qualification_paths"]:
        value=new_state(route["path"],selected)
        checks=[]
        for index,row in enumerate(route["inputs"],1):
            inspect(row,value)
            oracle=load_json_strict((folder / (row["stem"]+"-oracle.json")).read_bytes())
            result=value.execute(oracle["action"])
            require(result==oracle["result"] and value.state.candidate.candidate_id==oracle["candidate_after"],"replayed result/successor differs")
            if oracle["action"]["action"]=="check":checks.append(dict(sequence=index,passed=result["passed"],calls_remaining_after=prep.CALL_LIMIT-index))
        require(value.state.submitted and value.state.public_check_passed,"oracle does not close")
        require(len(value.pairs)==route["scripted_actions"] and route["calls_remaining"]==prep.CALL_LIMIT-len(value.pairs),"oracle allowance differs")
        paths.append(dict(path=route["path"],actions=len(value.pairs),checks=checks,peak_input_tokens=max(r["prompt_tokens"] for r in route["inputs"]),exact_replay=True))
    output=dict(manifest_sha256=manifest_sha,preparation_seal_sha256=sha256_file(folder / "PREPARATION_SEAL.json"),
                verification_source_sha256=sha256_file(Path(__file__)),public_files=len(seal["files"]),records=len(records),
                source_identities=len(plan["source_sha256"]),private_runtime_files=len(seal["private_runtime_files_local_only"]),
                completion_calls=0,prepared_inputs=len(inputs),distinct_cli_recounts=len(counts),oracle_actions=sum(p["actions"] for p in paths),
                candidate_files=len(selected.initial.files),candidate_bytes=sum(len(b) for _,b in selected.initial.files),
                actor=prep.ACTOR,memory=seal["memory"],paths=paths,inputs=inputs,
                limits="Replay uses the actual executor through a separate verification path; preparation is not model behavior or pressure evidence.")
    args.output.write_bytes(canonical_json_bytes(output))
    print(canonical_json_bytes({k:v for k,v in output.items() if k not in {"inputs","actor"}}).decode())


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",type=Path,required=True)
    parser.add_argument("--tokenizer",type=Path,required=True)
    parser.add_argument("--output",type=Path,default=prep.AREA / "VERIFICATION.json")
    verify(parser.parse_args())
