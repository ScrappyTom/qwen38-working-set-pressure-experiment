"""Offline checks for this stopped qualification; never calls a model server.

Run after sealing. This independently checks bytes/chains and retokenizes text;
it does not certify that a reviewer has read or interpreted a transcript.
"""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile


ROOT = Path(__file__).resolve().parents[4]
FOLLOW = Path(__file__).resolve().parents[1]


def encoded(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(",", ":"), allow_nan=False).encode("utf-8")


def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def checked_files(folder, rows):
    assert len({r["path"] for r in rows}) == len(rows)
    for row in rows:
        path = folder / row["path"]
        assert path.stat().st_size == row["size_bytes"], row["path"]
        assert digest(path) == row["sha256"], row["path"]


def checked_stage(folder):
    seal = json.loads((folder / "RESPONSE_SEAL.json").read_bytes())
    checked_files(folder, seal["files"])
    assert hashlib.sha256(encoded(seal["files"])).hexdigest() == seal["aggregate_sha256"]
    actual = {p.relative_to(folder).as_posix() for p in folder.rglob("*")
              if p.is_file() and "private-runtime" not in p.parts and p.name != "RESPONSE_SEAL.json"}
    assert actual == {r["path"] for r in seal["files"]}
    for name, expected in seal["private_runtime_files_local_only"].items():
        assert digest(folder / "private-runtime" / name) == expected, name
    previous = None
    records = []
    for sequence, line in enumerate((folder / "records.jsonl").read_bytes().splitlines(), 1):
        record = json.loads(line)
        body = {k: v for k, v in record.items() if k != "record_sha256"}
        assert hashlib.sha256(encoded(body)).hexdigest() == record["record_sha256"]
        assert record["sequence"] == sequence and record["previous_record_sha256"] == previous
        assert not records or record["run_id"] == records[0]["run_id"]
        checked_files(folder, record["artifacts"])
        previous = record["record_sha256"]
        records.append(record)
    assert len(records) == seal["record_count"]
    counts = {key: sum(r["record_type"] == kind for r in records) for key, kind in (
        ("sent_requests", "invocation_started"), ("received_responses", "response_received"),
        ("completed_responses", "invocation_completed"))}
    assert all(seal[k] == v for k, v in counts.items())
    return seal, records, {"seal_sha256": digest(folder / "RESPONSE_SEAL.json"),
        "checked_public_files": len(seal["files"]), "checked_private_files": len(seal["private_runtime_files_local_only"]),
        "checked_chain_records": len(records), "aggregate_sha256": seal["aggregate_sha256"], **counts}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists(), "Do not overwrite an analysis artifact"
    package = FOLLOW / "package"
    manifest = json.loads((package / "PACKAGE_MANIFEST.json").read_bytes())
    checked_files(package, manifest["files"])
    assert {p.relative_to(package).as_posix() for p in package.rglob("*") if p.is_file() and p.name != "PACKAGE_MANIFEST.json"} == {r["path"] for r in manifest["files"]}
    for path, expected in manifest["source_sha256"].items():
        assert digest(ROOT / path) == expected, path
    assert digest(args.model) == manifest["actor"]["model_sha256"]
    tokenizer_sha = digest(args.tokenizer)
    assert tokenizer_sha == "d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c"
    stages = {}
    for name in ("preparation-001", "qualification-001"):
        seal, records, stages[name] = checked_stage(FOLLOW / name)
        assert seal["package_sha256"] == digest(package / "PACKAGE_MANIFEST.json")
        assert records[0]["payload"]["execution_code_sha256"] == manifest["source_sha256"]

    def token_count(raw):
        with tempfile.TemporaryDirectory(prefix="follow-on-audit-") as temporary:
            path = Path(temporary) / "text.bin"
            path.write_bytes(raw)
            result = subprocess.run([str(args.tokenizer), "--offline", "--model", str(args.model),
                "--file", str(path), "--show-count", "--no-bos", "--no-escape"],
                capture_output=True, text=True, encoding="utf-8", errors="replace",
                env={**os.environ, "LLAMA_ARG_OFFLINE": "1"}, check=True)
        counts = re.findall(r"Total number of tokens:\s*(\d+)", result.stdout + "\n" + result.stderr)
        assert len(counts) == 1
        return int(counts[0])

    inputs = []
    for row in manifest["rows"]:
        request = json.loads((package / row["request_path"]).read_bytes())
        prompt = (package / row["rendered_path"]).read_bytes()
        count = token_count(prompt)
        assert count == row["prompt_tokens"]
        assert [m["role"] for m in request["messages"]] == ["system", "user"]
        assert not any(k in request for k in ("response_format", "tools", "functions"))
        assert request["cache_prompt"] is False
        assert all(request[k] == -1 for k in ("max_tokens", "n_predict", "thinking_budget_tokens", "reasoning_budget_tokens"))
        if row["stage"] == "qualification":
            assert prompt == (FOLLOW / "qualification-001/calls" / (row["id"] + "-rendered-prompt.txt")).read_bytes()
            assert (package / row["request_path"]).read_bytes() == (FOLLOW / "qualification-001/calls" / (row["id"] + "-endpoint-request.json")).read_bytes()
        inputs.append({"id": row["id"], "offline_tokens": count, "matches_native": True})
    calls = FOLLOW / "qualification-001/calls"
    response = json.loads((calls / "Q1-endpoint-response.json").read_bytes())
    message = response["choices"][0]["message"]
    assert response["choices"][0]["finish_reason"] == "stop"
    assert response["usage"]["prompt_tokens"] == inputs[0]["offline_tokens"]
    assert response["usage"]["prompt_tokens_details"]["cached_tokens"] == 0
    assert response["timings"]["cache_n"] == 0
    output_counts = {}
    for key, suffix in (("reasoning_content", "reasoning"), ("content", "content")):
        raw = (calls / ("Q1-assistant-" + suffix + ".txt")).read_bytes()
        assert raw == message[key].encode("utf-8")
        output_counts[suffix + "_text_tokens"] = token_count(raw)
    answer = json.loads(message["content"])
    expected = json.loads((package / "EXPECTED_RESULTS.json").read_bytes())["Q1"]
    assert answer == expected
    assert list(answer) == ["opening_code", "middle_code", "late_code", "opening_rule"]
    memory = list(csv.reader((FOLLOW / "qualification-001/memory.csv").read_text().splitlines()))
    assert all(len(row) == 5 for row in memory)
    low = [row for row in memory if int(row[-1]) < manifest["actor"]["minimum_free_gpu_mib"]]
    assert min(int(row[-1]) for row in memory) == seal["memory"]["min_free_mib"]
    report = {"analysis_scope": "independent offline byte/chain/accounting verification; direct reading is documented separately",
        "package_sha256": digest(package / "PACKAGE_MANIFEST.json"), "package_files_checked": len(manifest["files"]),
        "source_files_checked": len(manifest["source_sha256"]), "tokenizer_sha256": tokenizer_sha,
        "verifier_sha256": digest(Path(__file__)), "stages": stages, "inputs": inputs,
        "q1": {"correct_fields": 4, "usage": response["usage"], "output_text_retokenization": output_counts,
               "text_count_limitation": "text counts are not original generated token segmentation",
               "timings": response["timings"], "normal_finish": True},
        "memory": {"samples": len(memory), "below_target_samples": len(low), "minimum_free_mib": min(int(r[-1]) for r in memory),
                   "below_target_first_local": low[0][0], "below_target_last_local": low[-1][0]},
        "remaining_unexposed": ["Q2", "Q3", "D1", "D2", "D3", "D4"],
        "continue_to_design": False}
    args.output.write_bytes(encoded(report) + b"\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
