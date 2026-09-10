"""Independent post-seal byte, native-count and treatment-isolation checks."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes


def digest(path):
    with path.open("rb") as handle:
        return hashlib.file_digest(handle, "sha256").hexdigest()


def read(path):
    return json.loads(path.read_bytes())


def neutral(value, label):
    if isinstance(value, dict):
        return {key: label if key == "fixture_id" else neutral(item, label) for key, item in value.items()}
    if isinstance(value, list):
        return [neutral(item, label) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    args = parser.parse_args()
    folder = Path(__file__).parent / "preparation-001"
    seal = read(folder / "PREPARATION_SEAL.json")
    manifest = read(folder / "PACKAGE_MANIFEST.json")
    assert digest(args.model) == manifest["actor"]["model_sha256"]
    assert digest(args.tokenizer) == "d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c"
    assert seal["disposition"] == "prepared_without_completion"
    assert seal["completion_calls"] == manifest["completion_calls"] == 0
    assert seal["prepared_requests"] == len(manifest["rows"]) == 16
    assert manifest["comparison_live_authorized"] is False
    for row in seal["files"]:
        path = folder / row["path"]
        assert path.stat().st_size == row["size_bytes"] and digest(path) == row["sha256"]
    assert hashlib.sha256(canonical_json_bytes(seal["files"])).hexdigest() == seal["aggregate_sha256"]
    for name, value in seal["private_runtime_files_local_only"].items():
        assert digest(folder / "private-runtime" / name) == value
    for path, value in manifest["source_sha256"].items():
        assert digest(ROOT / path) == value
    records = verify_records(folder / "records.jsonl", folder)
    assert len(records) == seal["record_count"]
    prepared = [r for r in records if r["record_type"] == "request_prepared"]
    assert len(prepared) == 16
    assert all(r["payload"]["completion_sent"] is False and r["payload"]["routes"] == ["/apply-template", "/tokenize"] for r in prepared)
    assert not any(r["record_type"] in {"invocation_started", "invocation_completed", "response_received"} for r in records)
    closed = [r for r in records if r["record_type"] == "runtime_closed"]
    assert len(closed) == 1 and closed[0]["payload"]["owned_server_shutdown_verified"] and closed[0]["payload"]["dedicated_port_free"]
    runtime = seal["effective_runtime"]
    assert all(runtime[k] for k in ("full_offload", "context_matches", "q4_k_and_v", "mtp_disabled"))
    assert not runtime["truncation_observed"] and not runtime["cuda_failure_observed"]
    stderr = (folder / "private-runtime/server.stderr.log").read_text(encoding="utf-8", errors="replace")
    assert not re.search(r'POST /(v1/chat/completions|completion)\b', stderr)
    reference = (folder / "TOOL_REFERENCE.txt").read_text(encoding="utf-8")
    common_grammar = read(folder / "RESPONSE_FORMAT.json")
    design_package = ROOT / "development/qwen_interface_consultation/follow-on/package"
    for number in range(1, 5):
        for name in ("original-request.json", "candidate.json", "session.json", "provenance.json"):
            assert (folder / f"states/I{number}" / name).read_bytes() == (design_package / f"states/D{number}" / name).read_bytes()
    request_map, token_rows, system = {}, [], None
    for row in manifest["rows"]:
        raw = (folder / row["request_path"]).read_bytes()
        request = json.loads(raw)
        rendered = (folder / row["rendered_path"]).read_bytes()
        assert hashlib.sha256(raw).hexdigest() == row["request_sha256"]
        assert hashlib.sha256(rendered).hexdigest() == row["rendered_sha256"]
        template = read(folder / f"requests/{row['id']}-template-response.json")
        assert template["prompt"].encode("utf-8") == rendered
        assert len(read(folder / f"requests/{row['id']}-tokenization.json")["tokens"]) == row["prompt_tokens"]
        assert [m["role"] for m in request["messages"]] == ["system", "user"]
        assert request["response_format"] == common_grammar
        assert request["seed"] == row["seed"] and request["model"] == "qwen38-iq3-interface-follow-on"
        assert all(request[k] == -1 for k in ("max_tokens", "n_predict", "thinking_budget_tokens", "reasoning_budget_tokens"))
        assert request["chat_template_kwargs"] == {"enable_thinking": True, "reasoning_effort": "xhigh"}
        assert request["cache_prompt"] is False and request["stream"] is False
        original = read(folder / f"states/{row['state']}/original-request.json")
        assert request["messages"][1]["content"].encode("utf-8") == canonical_json_bytes(neutral(original, row["state"]))
        actual_system = request["messages"][0]["content"]
        legacy_system = actual_system.removesuffix("\n\n" + reference) if row["condition"] == "visible_reference" else actual_system
        system = legacy_system if system is None else system
        assert legacy_system == system
        expected_system = system + ("\n\n" + reference if row["condition"] == "visible_reference" else "")
        assert actual_system == expected_system
        # The pinned native template trims the message's trailing newline.
        # Directly inspected native bytes establish this; input words persist.
        displayed_system = actual_system.strip().encode("utf-8")
        assert rendered.count(displayed_system) == 1
        assert rendered.count(request["messages"][1]["content"].encode("utf-8")) == 1
        assert rendered.index(displayed_system) < rendered.index(request["messages"][1]["content"].encode("utf-8"))
        with tempfile.TemporaryDirectory(prefix="interface-comparison-token-audit-") as temporary:
            path = Path(temporary) / "prompt.bin"
            path.write_bytes(rendered)
            proc = subprocess.run([str(args.tokenizer), "--offline", "--model", str(args.model), "--file", str(path),
                                   "--show-count", "--no-bos", "--no-escape"],
                                  env={**os.environ, "LLAMA_ARG_OFFLINE": "1"}, capture_output=True,
                                  text=True, encoding="utf-8", errors="replace", check=True)
        found = re.findall(r"Total number of tokens:\s*(\d+)", proc.stdout + "\n" + proc.stderr)
        assert len(found) == 1 and int(found[0]) == row["prompt_tokens"] <= 23808
        token_rows.append({"id": row["id"], "offline_prompt_tokens": int(found[0]), "native_match": True})
        request_map[row["id"]] = request
    pairs = []
    rows = manifest["rows"]
    for index in range(0, 16, 2):
        a, b = rows[index:index + 2]
        assert a["state"] == b["state"] and a["seed"] == b["seed"]
        assert {a["condition"], b["condition"]} == {"legacy", "visible_reference"}
        legacy, variant = (a, b) if a["condition"] == "legacy" else (b, a)
        left, right = request_map[legacy["id"]], request_map[variant["id"]]
        assert {k: v for k, v in left.items() if k != "messages"} == {k: v for k, v in right.items() if k != "messages"}
        assert left["messages"][1] == right["messages"][1]
        left_rendered = (folder / legacy["rendered_path"]).read_bytes()
        right_rendered = (folder / variant["rendered_path"]).read_bytes()
        assert left_rendered == right_rendered.replace(("\n\n" + reference.rstrip()).encode("utf-8"), b"", 1)
        pairs.append({"state": a["state"], "seed": a["seed"], "first": a["condition"],
                      "added_input_tokens": variant["prompt_tokens"] - legacy["prompt_tokens"]})
    for index in range(0, 8, 2):
        assert pairs[index]["state"] == pairs[index + 1]["state"]
        assert {pairs[index]["seed"], pairs[index + 1]["seed"]} == {42, 314159}
        assert pairs[index]["first"] != pairs[index + 1]["first"]
    report = {"all_checks_passed": True, "preparation_seal_sha256": digest(folder / "PREPARATION_SEAL.json"),
              "package_sha256": digest(folder / "PACKAGE_MANIFEST.json"), "verifier_sha256": digest(Path(__file__)),
              "tokenizer_sha256": digest(args.tokenizer), "verified_public_files": len(seal["files"]),
              "verified_private_files": len(seal["private_runtime_files_local_only"]), "verified_chain_records": len(records),
              "verified_execution_sources": len(manifest["source_sha256"]), "completion_calls": 0,
              "four_state_snapshots_identical_to_reviewed_design_package": True,
              "only_visible_system_reference_differs_within_pairs": True,
              "native_template_trims_system_trailing_newline": True, "token_rows": token_rows, "pairs": pairs}
    target = Path(__file__).parent / "VERIFICATION.json"
    with target.open("x", encoding="utf-8", newline="\n") as handle:
        json.dump(report, handle, indent=2)
        handle.write("\n")
    print(json.dumps({k: v for k, v in report.items() if k not in {"token_rows", "pairs"}}, indent=2))


if __name__ == "__main__":
    main()
