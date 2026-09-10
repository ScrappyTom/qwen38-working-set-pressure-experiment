"""Verify sealed development custody and replay actions; does not certify direct review."""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from working_set_exp.custody import verify_records
from working_set_exp.interface_consultation import development_states, endpoint_request, patch, toy
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.tools import strict_action


ROOT = Path(__file__).resolve().parents[1]


def require(condition: bool, detail: str) -> None:
    if not condition:
        raise ValueError(detail)


def check_candidate(path: Path, candidate) -> None:
    saved = load_json_strict(path.read_bytes())
    require(saved["candidate_id"] == candidate.candidate_id, f"candidate identity: {path}")
    require([row["path"] for row in saved["files"]] == [name for name, _ in candidate.files], f"candidate paths: {path}")
    for row, (_, data) in zip(saved["files"], candidate.files):
        require(row["content_utf8"].encode("utf-8") == data and row["sha256"] == sha256_bytes(data), f"candidate bytes: {path}")


def check_session(path: Path, state) -> None:
    expected = {"candidate_id": state.candidate.candidate_id, "complete_reads": sorted(state.complete_reads),
                "read_coverage": state.read_coverage, "public_check_passed": state.public_check_passed,
                "submitted": state.submitted}
    require(path.read_bytes() == canonical_json_bytes(expected), f"session state: {path}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), "output already exists")
    seal = load_json_strict((args.run / "RESPONSE_SEAL.json").read_bytes())
    require(seal["disposition"] == "completed_development_consultation" and seal["completed_responses"] == 16,
            "this verifier requires the closed initial sixteen-response run")
    files = [{"path": p.relative_to(args.run).as_posix(), "size_bytes": p.stat().st_size, "sha256": sha256_file(p)}
             for p in sorted(args.run.rglob("*")) if p.is_file() and "private-runtime" not in p.parts and p.name != "RESPONSE_SEAL.json"]
    require(files == seal["files"] and sha256_bytes(canonical_json_bytes(files)) == seal["aggregate_sha256"], "response seal inventory")
    private_status = {}
    for name, digest in seal["private_runtime_files_local_only"].items():
        path = args.run / "private-runtime" / name
        private_status[name] = "verified" if path.exists() and sha256_file(path) == digest else "unavailable_or_different"
        if path.exists():
            require(private_status[name] == "verified", f"private runtime file: {name}")
    records = verify_records(args.run / "records.jsonl", args.run)
    require(len(records) == seal["record_count"], "record count")
    first, closed = records[0]["payload"], records[-1]["payload"]
    require(closed["owned_server_shutdown_verified"] and closed["dedicated_port_free"], "recorded shutdown")
    for relative, digest in first["execution_code_sha256"].items():
        require(sha256_file(ROOT / relative) == digest, f"execution code changed: {relative}")
    manifest = load_json_strict((args.package / "PACKAGE_MANIFEST.json").read_bytes())
    require(sha256_file(args.package / "PACKAGE_MANIFEST.json") == first["package_sha256"], "prepared package identity")
    for row in manifest["files"]:
        path = args.package / row["path"]
        require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"], f"package file: {path}")
    schedule = load_json_strict((args.package / "SCHEDULE.json").read_bytes())
    groups = {kind: [r for r in records if r["record_type"] == kind] for kind in
              ("invocation_prepared", "invocation_started", "response_received", "invocation_completed")}
    require(all(len(rows) == 16 for rows in groups.values()), "invocation accounting")
    require(groups["invocation_prepared"][-1]["sequence"] < groups["invocation_started"][0]["sequence"], "preflight ordering")
    rows = []
    replayed = 0
    for index, planned in enumerate(schedule):
        ordinal = planned["ordinal"]
        stem = args.run / "calls" / f"{ordinal:02d}"
        artifact = lambda suffix: Path(str(stem) + suffix)
        for group in groups.values():
            require(all(group[index]["payload"][key] == value for key, value in planned.items()), "saved schedule order")
        request_raw = artifact("-endpoint-request.json").read_bytes()
        require(request_raw == (args.package / planned["request_path"]).read_bytes(), "exact endpoint request")
        value = {v.name: v for v in development_states(ROOT)}[planned["state"]]
        require(request_raw == canonical_json_bytes(endpoint_request(value, seed=planned["seed"], mode=planned["mode"])), "fresh request reconstruction")
        check_candidate(artifact("-candidate-before.json"), value.state.candidate)
        check_session(artifact("-state-before.json"), value.state)
        rendered = artifact("-rendered-prompt.txt").read_bytes()
        require(rendered == load_json_strict(artifact("-template-response.json").read_bytes())["prompt"].encode("utf-8"), "rendered native bytes")
        response = load_json_strict(artifact("-endpoint-response.json").read_bytes())
        require(len(response["choices"]) == 1, "one response")
        choice, usage = response["choices"][0], response["usage"]
        content = (choice["message"].get("content") or "").encode("utf-8")
        reasoning = (choice["message"].get("reasoning_content") or "").encode("utf-8")
        require(content == artifact("-assistant-content.txt").read_bytes() and reasoning == artifact("-assistant-reasoning.txt").read_bytes(), "exact raw final/reasoning separation")
        prepared = groups["invocation_prepared"][index]["payload"]
        completed = groups["invocation_completed"][index]["payload"]
        require(usage == completed["usage"] and usage["prompt_tokens"] == prepared["prompt_tokens"], "native prompt/usage accounting")
        require(choice["finish_reason"] == completed["finish_reason"], "finish accounting")
        host = load_json_strict(artifact("-host-result.json").read_bytes())
        require(host == completed["host_result"], "recorded host result")
        if host["executed"]:
            require(planned["mode"] == "action" and choice["finish_reason"] == "stop", "action admission")
            action = strict_action(content)
            require(action == host["action"] and value.execute(action) == host["result"], "exact tool replay")
            replayed += 1
        check_candidate(artifact("-candidate-after.json"), value.state.candidate)
        check_session(artifact("-state-after.json"), value.state)
        rows.append({**planned, "prompt_tokens": usage["prompt_tokens"], "completion_tokens": usage["completion_tokens"],
                     "cached_tokens": usage.get("prompt_tokens_details", {}).get("cached_tokens"),
                     "reasoning_utf8_bytes": len(reasoning), "final_utf8_bytes": len(content),
                     "elapsed_seconds": completed["elapsed_seconds"], "finish_reason": choice["finish_reason"],
                     "executed": host["executed"], "action": host.get("action"),
                     "accepted": host.get("result", {}).get("accepted"), "check_passed": host.get("result", {}).get("passed"),
                     "rendered_prompt_sha256": sha256_bytes(rendered)})
    for start in (0, 8):
        require(all(rows[start+i]["rendered_prompt_sha256"] == rows[start+i+4]["rendered_prompt_sha256"] for i in range(4)), "repeated seed prompt identity")
    probe_path = args.run.parent / "HOST_PROBES.json"
    probes = load_json_strict(probe_path.read_bytes())
    old_check = {v.name: v for v in development_states(ROOT)}["02-old-check"]
    before = old_check.state.candidate.candidate_id
    recovered = old_check.execute({"action": "reopen_result", "handle": "RES-0002"})
    require(recovered == probes["old_check_retrieval"]["actual_tool_result"], "offline old-result probe replay")
    require(old_check.state.candidate.candidate_id == before and not old_check.state.public_check_passed, "offline recovery effects")
    uninspected = toy("offline-rejection-contract-probe", b"def value():\n    return 1\n", "offline host probe", b"")
    guarded_edit = uninspected.execute(patch(uninspected, "return 1", "return 2"))
    require(guarded_edit == probes["patch_without_recorded_read"]["actual_tool_result"] and not uninspected.state.complete_reads,
            "offline inspection-enforcement probe replay")
    memory = [int(line.split(",")[-1].strip()) for line in (args.run / "memory.csv").read_text().splitlines() if line.strip()]
    output = {"mechanical_verification_only_not_direct_transcript_review": True,
              "response_seal_sha256": sha256_file(args.run / "RESPONSE_SEAL.json"), "record_count": len(records),
              "sealed_file_count": len(files), "replayed_actions": replayed, "private_runtime": private_status,
              "independent_offline_host_probes_reproduced": 2, "host_probes_sha256": sha256_file(probe_path),
              "started_at_utc": records[0]["created_at_utc"], "closed_at_utc": records[-1]["created_at_utc"],
              "sampled_free_gpu_mib": {"min": min(memory), "max": max(memory), "samples": len(memory)},
              "total_prompt_tokens": sum(r["prompt_tokens"] for r in rows),
              "total_completion_tokens": sum(r["completion_tokens"] for r in rows),
              "total_completion_wall_seconds": round(sum(r["elapsed_seconds"] for r in rows), 3),
              "maximum_input_plus_output_tokens": max(r["prompt_tokens"]+r["completion_tokens"] for r in rows),
              "verification_script_sha256": sha256_file(Path(__file__)), "calls": rows}
    args.output.write_bytes(canonical_json_bytes(output))
    print(json.dumps({key: value for key, value in output.items() if key != "calls"}, indent=2))


if __name__ == "__main__":
    main()
