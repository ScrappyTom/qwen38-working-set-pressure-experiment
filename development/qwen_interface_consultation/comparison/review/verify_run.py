"""Post-seal independent custody, native-count and actual-tool replay audit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from working_set_exp.custody import verify_records
from working_set_exp.interface_consultation import development_states
from working_set_exp.jsonutil import canonical_json_bytes
from working_set_exp.tools import strict_action
from run_interface_consultation import candidate_bytes, session_bytes


def read(path):
    return json.loads(path.read_bytes())


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    args = parser.parse_args()
    area = Path(__file__).parent.parent
    run, package = area / "run-001", area / "preparation-001"
    # Nothing generated is read before the terminal response seal exists.
    seal = read(run / "RESPONSE_SEAL.json")
    plan = read(run / "EXECUTION_MANIFEST.json")
    prepared = read(package / "PACKAGE_MANIFEST.json")
    assert digest(run / "EXECUTION_MANIFEST.json") == seal["execution_manifest_sha256"]
    assert (run / "EXECUTION_MANIFEST.json").read_bytes() == (area / "EXECUTION_MANIFEST.json").read_bytes()
    assert digest(run / "SPEC.md") == plan["execution_spec_sha256"]
    assert digest(package / "PACKAGE_MANIFEST.json") == seal["package_sha256"] == plan["package_sha256"]
    assert digest(package / "PREPARATION_SEAL.json") == seal["preparation_seal_sha256"]
    assert plan["rows"] == prepared["rows"] and plan["owner_authorized_completion_calls"] == 16
    assert plan["actor"] == seal["actor"] == prepared["actor"]
    assert plan["memory_policy"] == seal["memory_policy"] == prepared["memory_policy"]
    assert digest(args.model) == plan["actor"]["model_sha256"]
    assert digest(args.tokenizer) == "d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c"
    for relative, value in plan["execution_source_sha256"].items():
        assert digest(ROOT / relative) == value
    for row in seal["files"]:
        path = run / row["path"]
        assert path.stat().st_size == row["size_bytes"] and digest(path) == row["sha256"]
    assert hashlib.sha256(canonical_json_bytes(seal["files"])).hexdigest() == seal["aggregate_sha256"]
    for name, value in seal["private_runtime_files_local_only"].items():
        assert digest(run / "private-runtime" / name) == value
    records = verify_records(run / "records.jsonl", run)
    assert len(records) == seal["record_count"]
    by_type = lambda kind: [r for r in records if r["record_type"] == kind]
    starts, received, completed = by_type("invocation_started"), by_type("response_received"), by_type("invocation_completed")
    assert len(starts) == seal["sent_requests"] <= 16
    assert len(received) == seal["received_responses"] <= len(starts)
    assert len(completed) == seal["completed_responses"] <= len(received)
    assert [r["payload"]["id"] for r in starts] == [r["id"] for r in plan["rows"][:len(starts)]]
    assert len({r["payload"]["id"] for r in starts}) == len(starts)
    if seal["disposition"] == "completed_matched_comparison":
        assert len(starts) == len(received) == len(completed) == 16
    assert records[-1]["record_type"] == "stage_closed"
    assert records[-1]["payload"]["owned_server_shutdown_verified"] and records[-1]["payload"]["dedicated_port_free"]
    launch = read(run / "private-runtime/launch.json")
    for flag, value in {"--ctx-size":"56576", "--parallel":"1", "--gpu-layers":"all", "--fit":"off",
                        "--cache-type-k":"q4_0", "--cache-type-v":"q4_0", "--reasoning":"on",
                        "--reasoning-budget":"-1", "--reasoning-effort":"xhigh", "--n-predict":"-1"}.items():
        assert launch[launch.index(flag)+1] == value
    assert "--no-context-shift" in launch
    assert digest(Path(launch[0])) == plan["actor"]["server_sha256"]
    assert digest(Path(launch[launch.index("--model")+1])) == plan["actor"]["model_sha256"]

    def tokens(raw):
        if not raw:
            return 0  # No BOS is requested for these separate text fields.
        with tempfile.TemporaryDirectory(prefix="interface-comparison-text-audit-") as temporary:
            path = Path(temporary) / "text.bin"
            path.write_bytes(raw)
            proc = subprocess.run([str(args.tokenizer), "--offline", "--model", str(args.model), "--file", str(path),
                                   "--show-count", "--no-bos", "--no-escape"],
                                  env={**os.environ, "LLAMA_ARG_OFFLINE":"1"}, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", check=True)
        found = re.findall(r"Total number of tokens:\s*(\d+)", proc.stdout + "\n" + proc.stderr)
        assert len(found) == 1
        return int(found[0])

    rows = {r["id"]:r for r in plan["rows"]}
    calls = []
    for record in completed:
        outcome = record["payload"]
        row = rows[outcome["id"]]
        stem = run / "calls" / row["id"]
        named = lambda suffix: Path(str(stem) + suffix)
        assert named("-endpoint-request.json").read_bytes() == (package / row["request_path"]).read_bytes()
        prompt = named("-rendered-prompt.txt").read_bytes()
        assert prompt == (package / row["rendered_path"]).read_bytes()
        request, response = read(named("-endpoint-request.json")), read(named("-endpoint-response.json"))
        assert response["usage"] == outcome["usage"]
        assert tokens(prompt) == row["prompt_tokens"] == response["usage"]["prompt_tokens"]
        assert response["usage"]["prompt_tokens_details"]["cached_tokens"] == response["timings"]["cache_n"] == 0
        assert response["timings"]["prompt_n"] == row["prompt_tokens"]
        assert response["timings"]["predicted_n"] == response["usage"]["completion_tokens"]
        assert len(response["choices"]) == 1 and response["choices"][0]["finish_reason"] == "stop"
        message = response["choices"][0]["message"]
        assert not message.get("tool_calls") and not message.get("function_call")
        reasoning, content = (message.get("reasoning_content") or "").encode("utf-8"), message["content"].encode("utf-8")
        assert reasoning == named("-assistant-reasoning.txt").read_bytes()
        assert content == named("-assistant-content.txt").read_bytes()
        assert [m["role"] for m in request["messages"]] == ["system","user"]
        assert all(request[k] == -1 for k in ("max_tokens","n_predict","thinking_budget_tokens","reasoning_budget_tokens"))
        assert request["chat_template_kwargs"] == {"enable_thinking":True,"reasoning_effort":"xhigh"}
        assert request["seed"] == row["seed"] and request["cache_prompt"] is False
        assert request["response_format"] == read(package / "RESPONSE_FORMAT.json")
        action = strict_action(content)
        assert action == read(named("-action.json"))
        host = read(named("-host-result.json"))
        assert host == outcome["host_result"] and host["execution_attempted"] and host["executed"]
        assert host["action"] == action
        actual = development_states(ROOT)[row["state_index"]]
        original_folder = package / "states" / row["state"]
        assert actual.request == (original_folder / "original-request.json").read_bytes()
        assert candidate_bytes(actual.state.candidate) == named("-candidate-before.json").read_bytes() == (original_folder / "candidate.json").read_bytes()
        assert session_bytes(actual.state) == named("-state-before.json").read_bytes() == (original_folder / "session.json").read_bytes()
        candidate_before = actual.state.candidate.candidate_id
        replay_result = actual.execute(action)
        assert replay_result == host["result"]
        assert candidate_bytes(actual.state.candidate) == named("-candidate-after.json").read_bytes()
        assert session_bytes(actual.state) == named("-state-after.json").read_bytes()
        assert outcome["physical_tokens_remaining"] == 56576-response["usage"]["prompt_tokens"]-response["usage"]["completion_tokens"] >= 0
        assert outcome["within_proposed_generation_reserve"] == (response["usage"]["completion_tokens"] <= 32768)
        call = {"id":row["id"], "state":row["state"], "seed":row["seed"], "condition":row["condition"],
                "prompt_tokens":row["prompt_tokens"], "output_tokens":response["usage"]["completion_tokens"],
                "offline_reasoning_text_tokens":tokens(reasoning), "offline_final_text_tokens":tokens(content),
                "reasoning_chars":len(reasoning.decode("utf-8")), "final_chars":len(content.decode("utf-8")),
                "elapsed_seconds":outcome["elapsed_seconds"], "timings":response["timings"], "action":action,
                "accepted":replay_result["accepted"], "check_passed":replay_result.get("passed"),
                "candidate_before":candidate_before, "candidate_after":actual.state.candidate.candidate_id,
                "physical_tokens_remaining":outcome["physical_tokens_remaining"],
                "within_proposed_generation_reserve":outcome["within_proposed_generation_reserve"],
                "exact_replay_verified":True}
        calls.append(call)
        print(f"Verified {row['id']}: input, exact output, action and candidate/session replay", flush=True)
    call_map = {r["id"]:r for r in calls}
    pairs = []
    for index in range(0,16,2):
        pair = plan["rows"][index:index+2]
        if not all(r["id"] in call_map for r in pair):
            continue
        a,b = [call_map[r["id"]] for r in pair]
        assert a["state"] == b["state"] and a["seed"] == b["seed"]
        legacy,variant = (a,b) if a["condition"] == "legacy" else (b,a)
        pairs.append({"state":a["state"],"seed":a["seed"],"legacy_id":legacy["id"],"reference_id":variant["id"],
                      "same_action_object":legacy["action"]==variant["action"],
                      "reference_minus_legacy":{key:variant[key]-legacy[key] for key in
                                                ("prompt_tokens","output_tokens","offline_reasoning_text_tokens","elapsed_seconds")}})
    totals = {condition:{"completed_calls":sum(r["condition"]==condition for r in calls),
                        **{key:sum(r[key] for r in calls if r["condition"]==condition) for key in
                           ("prompt_tokens","output_tokens","offline_reasoning_text_tokens","offline_final_text_tokens","elapsed_seconds")}}
              for condition in ("legacy","visible_reference")}
    report = {"custody_and_replay_checks_passed":True,"all_sixteen_completed":len(calls)==16,
              "seal_sha256":digest(run/"RESPONSE_SEAL.json"),"verifier_sha256":digest(Path(__file__)),
              "tokenizer_sha256":digest(args.tokenizer),"verified_public_files":len(seal["files"]),
              "verified_private_files":len(seal["private_runtime_files_local_only"]),"verified_chain_records":len(records),
              "verified_sources":len(plan["execution_source_sha256"]),"memory":seal["memory"],
              "effective_runtime":seal["effective_runtime"],"disposition":seal["disposition"],
              "received_but_not_completed_ids":[r["payload"]["id"] for r in received if r["payload"]["id"] not in call_map],
              "calls":calls,"pairs":pairs,"totals":totals,
              "qualification":"Offline thinking/final text counts are not original generated-token segmentation; action agreement is descriptive, not a quality criterion. No direct behavioral audit is inferred by this verifier."}
    target = Path(__file__).parent / "VERIFICATION.json"
    with target.open("x",encoding="utf-8",newline="\n") as handle:
        json.dump(report,handle,indent=2)
        handle.write("\n")
    print(json.dumps({k:v for k,v in report.items() if k not in {"calls","pairs"}},indent=2))


if __name__ == "__main__":
    main()
