"""Independent replay and exact-input mock rehearsal; sends no network requests."""
from pathlib import Path

import run_saved_work_continuation as runner
import saved_work_continuation as work
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

require, read = work.require, work.read
OUTPUT = work.AREA / "rehearsal-001"


def main():
    require(not OUTPUT.exists(), "rehearsal exists; preserve it")
    plan = runner.proposed_manifest()
    qualification = runner.verify_package()
    rows = []
    for route in qualification["routes"]:
        folder = work.PACKAGE / "routes" / route["kind"]
        value = new_state("independent-replay", work.compiler.load_fixture())
        pairs = read(folder / "pairs.json")
        for sequence, pair in enumerate(pairs, 1):
            require(value.execute(pair["response"]) == pair["result"], "tool replay differs")
        final = read(folder / "final-candidate.json")
        require(work.pilot.reference.candidate_bytes(value.state.candidate) == canonical_json_bytes(final), "saved final differs")
        require(value.state.public_check_passed and value.state.submitted, "route did not close")
        partial = read(folder / "partial-candidate.json")
        partial_files = {f["path"]:f["content_utf8"].encode() for f in partial["files"]}
        require(Candidate.create(partial_files).candidate_id == partial["candidate_id"], "partial identity differs")
        final_report = read_bytes(value.state.candidate.file_map[work.REPORT])
        partial_report = read_bytes(partial_files[work.REPORT])
        # The full public checker has independently compared both final entries
        # with the captures. Compare the saved partial's actual entry with that
        # accepted final entry, not the preparation's constructed Python variable.
        first_matches = partial_report["builds"] == final_report["builds"][:1]
        require(first_matches == route["partial_entry_correct"], "partial assessment differs")
        for item in route["rows"]:
            request = read(work.PACKAGE / (item["stem"]+"-request.json"))
            state = read_bytes(request["messages"][1]["content"].encode())
            prefix = state["active_phase_event_frame"]["externalized_payload_through_sequence"]
            events = state["active_phase_event_frame"]["events"]
            require(len(events) <= len(pairs), "input history exceeds replay")
            expected = [work.compiler.event_from_pair_v3(p["response"],p["result"],sequence=i,
                payload_residency="external" if i <= prefix else "resident") for i,p in enumerate(pairs[:len(events)],1)]
            require(events == expected, "actual prepared event delivery differs")
            require(sha256_file(work.PACKAGE/(item["stem"]+"-native.txt")) == item["native_sha256"], "native bytes differ")
        rows.append(dict(kind=route["kind"], replayed_actions=len(pairs), saved_partial_entry_matches_checked_final=first_matches,
            prepared_inputs_verified=len(route["rows"]), final_public_passed=True))

    OUTPUT.mkdir()
    store, log = ArtifactStore(OUTPUT), runner.RunLog(OUTPUT/"records.jsonl", "offline-exact-input-rehearsal")
    log.append("mock_rehearsal_only", {"real_completion_requests":0, "native_token_counts_from_frozen_offline_qualification":True}, [])
    direct = qualification["routes"][0]
    pair_list = read(work.PACKAGE/"routes/direct/pairs.json")
    action_indices = [7,8,14,15,16]
    by_request = {}
    for row in direct["rows"]:
        raw = (work.PACKAGE/(row["stem"]+"-request.json")).read_bytes()
        by_request[raw] = row
    sent = []
    def render(url, request):
        row = by_request[canonical_json_bytes(request)]
        native = (work.PACKAGE/(row["stem"]+"-native.txt")).read_bytes()
        count = row["prompt_tokens"]
        return canonical_json_bytes({"prompt":native.decode()}), native, canonical_json_bytes({"tokens":[0]*count}), count
    def post(url, route, raw, timeout):
        require(route == "/v1/chat/completions" and len(sent) < len(action_indices), "unexpected mock request")
        row = by_request[raw]
        pair = pair_list[action_indices[len(sent)]]
        sent.append(row["native_sha256"])
        count = row["prompt_tokens"]
        return canonical_json_bytes(dict(choices=[dict(finish_reason="stop", message=dict(
            reasoning_content="SCRIPTED MOCK: no model generation occurred.", content=canonical_json_bytes(pair["response"]).decode()))],
            usage=dict(prompt_tokens=count, completion_tokens=100, total_tokens=count+100, prompt_tokens_details=dict(cached_tokens=0)),
            timings=dict(cache_n=0)))
    outcome = runner.Loop(plan,OUTPUT,store,log,render=render,post=post,health=lambda:{"mock_runtime":True}).execute()
    require(outcome["submitted"] and outcome["current_public_check_passed"] and len(sent) == 5, "exact-input rehearsal failed")
    records = verify_records(OUTPUT/"records.jsonl",OUTPUT)
    result = dict(status="offline_verified", real_completion_requests=0, replayed_routes=rows,
        exact_input_mock_calls=len(sent), scripted_mock_result=outcome,
        verified_package_seal_sha256=sha256_file(work.PACKAGE/"SEAL.json"),
        verifier_sha256=sha256_file(Path(__file__)), initial_input_sha256=plan["initial_native_sha256"])
    store.put("VERIFICATION.json",canonical_json_bytes(result))
    files = runner.base.file_inventory(OUTPUT)
    store.put("SEAL.json",canonical_json_bytes(dict(status="offline_mock_rehearsal", real_completion_requests=0,
        record_count=len(records), files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files)))))
    print({"status":result["status"], "replayed_routes":rows, "exact_input_mock_calls":len(sent), "real_completion_requests":0})


def read_bytes(raw):
    return work.read_bytes(raw)


if __name__ == "__main__":
    main()
