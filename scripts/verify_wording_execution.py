"""Verify the sealed W01-W08 attempt and replay saved actions without model calls."""
from __future__ import annotations

import argparse
from collections import Counter
import copy
from datetime import datetime
from pathlib import Path
import subprocess
from types import SimpleNamespace

import run_interface_wording as run
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count
from working_set_exp.tools import strict_action


MANIFEST_SHA = "6e763ce033deb5cbe2cd2c429b688e6d5c430efc3c30ac72bb89372caec3dd2a"
TOKENIZER_SHA = "d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c"
require = run.require


def verify(args):
    # Verify the terminal seal before reading any model response body.
    seal = run.prep.reference.cont.verified_seal(run.RUN)
    require(seal["disposition"] == "completed_matched_comparison", "this verifier requires the completed attempt")
    require(sha256_file(run.MANIFEST) == MANIFEST_SHA, "execution manifest differs")
    plan = run.load_manifest()
    require((run.RUN / "EXECUTION_MANIFEST.json").read_bytes() == run.MANIFEST.read_bytes(), "run manifest differs")
    require((run.RUN / "SPEC.md").read_bytes() == run.SPEC.read_bytes(), "run specification differs")
    require(seal["execution_manifest_sha256"] == MANIFEST_SHA and seal["actor"] == plan["actor"], "seal binding differs")
    require(seal["memory_policy"] == plan["memory_policy"], "memory policy differs")
    require(all(seal[k] == 8 for k in ("sent_requests", "received_responses", "completed_responses")), "counts differ")
    records = verify_records(run.RUN / "records.jsonl", run.RUN)
    require(records[0]["record_type"] == "stage_prepared" and records[0]["payload"]["owner_approval"] == "I approve", "owner direction differs")
    ids = [r["id"] for r in plan["rows"]]
    kinds = ("invocation_prepared", "invocation_started", "response_received", "response_extracted",
             "post_response_runtime_check", "action_selected", "host_decision", "invocation_completed")
    for kind in kinds:
        require([r["payload"]["id"] for r in records if r["record_type"] == kind] == ids, kind + " schedule differs")
    expected_types = ["stage_prepared", "runtime_prepared", "runtime_ready"] + ["invocation_prepared"] * 8
    expected_types += list(kinds[1:]) * 8 + ["runtime_closed", "stage_closed"]
    require([r["record_type"] for r in records] == expected_types, "record order or once-only scope differs")
    require(all(r["payload"]["completion_sent"] is False for r in records if r["record_type"] == "invocation_prepared"), "preflight sent a completion")
    for r in records[-2:]:
        require(r["payload"]["owned_server_shutdown_verified"] and r["payload"]["dedicated_port_free"], "runtime closure differs")
    health_expected = {"full_offload": True, "context_matches": True, "q4_k_and_v": True,
                       "mtp_disabled": True, "truncation_observed": False, "cuda_failure_observed": False}
    require(seal["effective_runtime"] == health_expected, "effective runtime differs")
    for r in records:
        if r["record_type"] in ("invocation_started", "post_response_runtime_check"):
            require(r["payload"]["effective_runtime"] == health_expected, "invocation health differs")
            require(r["payload"]["memory"]["reference_is_advisory"] is True, "memory policy was not advisory")
    require(sha256_file(args.model) == plan["actor"]["model_sha256"], "offline model differs")
    require(sha256_file(args.tokenizer) == TOKENIZER_SHA, "offline tokenizer differs")
    version = subprocess.run([str(args.tokenizer), "--version"], capture_output=True, check=True)
    profile = SimpleNamespace(model_path=args.model, tokenizer_path=args.tokenizer)
    cache = {}

    def count(raw):
        if not raw:
            return 0
        if raw not in cache:
            cache[raw] = tokenizer_count(profile, raw)
        return cache[raw]

    completed = {r["payload"]["id"]: r["payload"] for r in records if r["record_type"] == "invocation_completed"}
    requests, checked, native_hashes = {}, [], set()
    reference = (run.PACKAGE / "TOOL_REFERENCE.txt").read_text(encoding="utf-8")
    for row in plan["rows"]:
        tag = row["id"]
        path = lambda tail: run.RUN / "calls" / (tag + "-" + tail)
        raw_request, rendered = path("endpoint-request.json").read_bytes(), path("rendered-prompt.txt").read_bytes()
        require(raw_request == (run.PACKAGE / row["request_path"]).read_bytes(), "actual API input differs: " + tag)
        require(rendered == (run.PACKAGE / row["rendered_path"]).read_bytes(), "actual native input differs: " + tag)
        require(sha256_bytes(rendered) == row["rendered_sha256"], "native hash differs: " + tag)
        request = load_json_strict(raw_request)
        require(request["seed"] == row["seed"] and [m["role"] for m in request["messages"]] == ["system", "user"], "fresh request or seed differs")
        require(request["messages"][0]["content"].endswith(reference), "complete reference differs")
        requests[(row["state"], row["seed"], row["condition"])] = request
        native_hashes.add(sha256_bytes(rendered))
        response = load_json_strict(path("endpoint-response.json").read_bytes())
        require(len(response["choices"]) == 1, "choice count differs")
        choice = response["choices"][0]
        message, usage, timings = choice["message"], response["usage"], response["timings"]
        require(choice["finish_reason"] == "stop" and message["role"] == "assistant", "incomplete output")
        require(set(message) == {"role", "content", "reasoning_content"}, "unexpected response channel")
        reasoning, final = path("assistant-reasoning.txt").read_bytes(), path("assistant-content.txt").read_bytes()
        require(reasoning == message["reasoning_content"].encode("utf-8") and final == message["content"].encode("utf-8"), "saved fields differ")
        n = count(rendered)
        require(n == usage["prompt_tokens"] == timings["prompt_n"] == row["prompt_tokens"], "native/offline/usage disagreement")
        require(usage["prompt_tokens_details"]["cached_tokens"] == timings["cache_n"] == 0, "cache reuse")
        require(usage["completion_tokens"] == timings["predicted_n"] > 0, "generation accounting differs")
        require(usage["total_tokens"] == n + usage["completion_tokens"], "total accounting differs")
        action = strict_action(final)
        require(canonical_json_bytes(action) == path("action.json").read_bytes(), "final/action differs")
        value, rebuilt = run.fresh_state(row)
        require(rebuilt == raw_request, "fresh-state input differs")
        require(run.prep.reference.candidate_bytes(value.state.candidate) == path("candidate-before.json").read_bytes(), "before candidate differs")
        require(run.prep.reference.session_bytes(value.state) == path("state-before.json").read_bytes(), "before session differs")
        before_pairs = len(value.pairs)
        result = value.execute(action)
        require(len(value.pairs) == before_pairs + 1, "replay did not append one ordered action/result")
        host = {"action": action, "executed": True, "execution_attempted": True, "finish_reason": "stop", "result": result}
        require(canonical_json_bytes(host) == path("host-result.json").read_bytes(), "replayed host result differs")
        require(run.prep.reference.candidate_bytes(value.state.candidate) == path("candidate-after.json").read_bytes(), "after candidate differs")
        require(run.prep.reference.session_bytes(value.state) == path("state-after.json").read_bytes(), "after session differs")
        done = completed[tag]
        require(all(done[k] == v for k, v in row.items()), "completed row differs")
        require(done["host_result"] == host and done["usage"] == usage and done["timings"] == timings, "record/artifact disagreement")
        remaining = plan["actor"]["context"] - usage["total_tokens"]
        require(remaining == done["physical_tokens_remaining"] >= 0, "physical accounting differs")
        a, b = count(reasoning), count(final)
        checked.append({"id": tag, "state": row["state"], "seed": row["seed"], "condition": row["condition"],
                        "input_tokens": n, "output_tokens": usage["completion_tokens"],
                        "retokenized_reasoning_text_tokens": a, "retokenized_final_text_tokens": b,
                        "endpoint_minus_retokenized_fields": usage["completion_tokens"] - a - b,
                        "elapsed_seconds": round(done["elapsed_seconds"], 6),
                        "physical_tokens_remaining": remaining, "action": action, "accepted": result.get("accepted"),
                        "submitted": value.state.submitted, "exact_fresh_state_replay": True,
                        "input_sha256": sha256_bytes(rendered), "response_sha256": sha256_file(path("endpoint-response.json"))})

    # Independently reverse just the declared two-edit package on each actual pair.
    change = load_json_strict((run.PACKAGE / "WORDING_CHANGE.json").read_bytes())
    sentence, field = change["replace_system_sentence"], change["remove_user_field"]
    for state in ("I3", "I4"):
        for seed in (1729, 271828):
            candidate = copy.deepcopy(requests[(state, seed, "wording")])
            system = candidate["messages"][0]["content"]
            require(system.count(sentence["after"]) == 1, "candidate sentence differs")
            candidate["messages"][0]["content"] = system.replace(sentence["after"], sentence["before"], 1)
            user = load_json_strict(candidate["messages"][1]["content"].encode("utf-8"))
            require("correction_cycle_reserved_by_fixture_design" not in user["resource_state"], "resource example remains")
            user["resource_state"]["correction_cycle_reserved_by_fixture_design"] = field["old_value"]
            candidate["messages"][1]["content"] = canonical_json_bytes(user).decode("utf-8")
            require(candidate == requests[(state, seed, "reference")], "undeclared paired-input difference")
    telemetry = [line.split(",") for line in (run.RUN / "memory.csv").read_text().splitlines()]
    stamps = [datetime.strptime(row[0].strip(), "%Y/%m/%d %H:%M:%S.%f") for row in telemetry]
    frees = [int(row[-1]) for row in telemetry]
    require(seal["memory"] == {"samples": len(frees), "min_free_mib": min(frees), "max_free_mib": max(frees)}, "memory summary differs")
    totals = {}
    metrics = ("input_tokens", "output_tokens", "retokenized_reasoning_text_tokens", "retokenized_final_text_tokens", "elapsed_seconds")
    for condition in ("reference", "wording"):
        selected = [r for r in checked if r["condition"] == condition]
        totals[condition] = {key: sum(r[key] for r in selected) for key in metrics}
        totals[condition]["actions"] = dict(Counter(r["action"]["action"] for r in selected))
    return {"status": "sealed_execution_verified_and_replayed", "scope": "offline verification; zero model completions; does not certify direct review",
            "verifier_sha256": sha256_file(Path(__file__)), "execution_manifest_sha256": MANIFEST_SHA,
            "response_seal_sha256": sha256_file(run.RUN / "RESPONSE_SEAL.json"), "package_sha256": run.PACKAGE_SHA,
            "public_files_verified": len(seal["files"]), "private_files_verified_local_only": len(seal["private_runtime_files_local_only"]),
            "record_count": len(records), "execution_source_identities": len(plan["execution_source_sha256"]),
            "completed_requests": len(checked), "unique_native_inputs": len(native_hashes), "replayed_actions": len(checked),
            "actor": plan["actor"], "model_sha256": plan["actor"]["model_sha256"], "tokenizer_sha256": TOKENIZER_SHA,
            "tokenizer_version": (version.stdout + version.stderr).decode("utf-8", errors="replace").strip(),
            "text_tokenization_note": "Pinned CLI, no BOS or escapes. Separate saved-text counts are not original generation segmentation; residuals are not asserted special-token overhead.",
            "owner_approval": records[0]["payload"]["owner_approval"], "first_record_utc": records[0]["created_at_utc"],
            "last_record_utc": records[-1]["created_at_utc"], "memory": seal["memory"],
            "maximum_telemetry_sample_gap_seconds": max((b-a).total_seconds() for a, b in zip(stamps, stamps[1:])),
            "excluded_offline_inputs_not_exposed": plan["excluded_input_ids"], "undocumented_pair_changes": False,
            "prior_closures_unchanged": True, "totals": totals, "calls": checked}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "verification output already exists")
    result = verify(args)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_bytes(canonical_json_bytes(result))
    print(canonical_json_bytes({key: result[key] for key in ("status", "public_files_verified", "record_count", "replayed_actions", "totals")}).decode("utf-8"))


if __name__ == "__main__":
    main()
