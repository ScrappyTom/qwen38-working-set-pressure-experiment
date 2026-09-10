"""Independent post-seal continuation checks; offline tokenization only."""
import argparse
import csv
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import tempfile


HERE = Path(__file__).resolve().parent
FOLLOW = HERE.parent
ROOT = HERE.parents[3]
helpers = runpy.run_path(str(FOLLOW / "qualification-review/verify_evidence.py"))
digest, checked_stage = helpers["digest"], helpers["checked_stage"]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("qualification", "design"), required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    assert not args.output.exists()
    package = FOLLOW / "package"
    plan = json.loads((HERE / "CONTINUATION_MANIFEST.json").read_bytes())
    assert digest(package / "PACKAGE_MANIFEST.json") == plan["original_package_sha256"]
    assert digest(FOLLOW / "qualification-001/RESPONSE_SEAL.json") == plan["prior_q1_seal_sha256"]
    assert digest(FOLLOW / "qualification-review/DECISION.json") == plan["prior_q1_review_sha256"]
    assert digest(HERE / "SPEC.md") == plan["amendment_sha256"]
    for path, expected in plan["execution_source_sha256"].items():
        assert digest(ROOT / path) == expected
    assert digest(args.model) == plan["actor"]["model_sha256"]
    assert digest(args.tokenizer) == "d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c"
    _, _, parent = checked_stage(FOLLOW / "qualification-001")
    run = HERE / (args.stage + "-001")
    seal, records, custody = checked_stage(run)
    assert seal["continuation_manifest_sha256"] == digest(HERE / "CONTINUATION_MANIFEST.json")
    assert seal["memory_policy"] == plan["memory_policy"]
    assert seal["prior_q1_seal_sha256"] == plan["prior_q1_seal_sha256"]

    def tokens(raw):
        with tempfile.TemporaryDirectory(prefix="interface-continuation-token-audit-") as temporary:
            path = Path(temporary) / "text.bin"
            path.write_bytes(raw)
            proc = subprocess.run([str(args.tokenizer), "--offline", "--model", str(args.model),
                "--file", str(path), "--show-count", "--no-bos", "--no-escape"],
                env={**os.environ, "LLAMA_ARG_OFFLINE": "1"}, capture_output=True,
                text=True, encoding="utf-8", errors="replace", check=True)
        found = re.findall(r"Total number of tokens:\s*(\d+)", proc.stdout + "\n" + proc.stderr)
        assert len(found) == 1
        return int(found[0])

    rows = {r["id"]: r for r in plan["rows"] if r["stage"] == args.stage}
    calls = []
    completed = [r["payload"] for r in records if r["record_type"] == "invocation_completed"]
    for done in completed:
        row = rows[done["id"]]
        stem = run / "calls" / row["id"]
        named = lambda suffix: Path(str(stem) + suffix)
        assert named("-endpoint-request.json").read_bytes() == (package / row["request_path"]).read_bytes()
        prompt = named("-rendered-prompt.txt").read_bytes()
        assert prompt == (package / row["rendered_path"]).read_bytes()
        input_tokens = tokens(prompt)
        assert input_tokens == row["prompt_tokens"] == done["usage"]["prompt_tokens"]
        response = json.loads(named("-endpoint-response.json").read_bytes())
        assert done["usage"] == response["usage"]
        assert response["usage"]["prompt_tokens_details"]["cached_tokens"] == response["timings"]["cache_n"] == 0
        message = response["choices"][0]["message"]
        text_counts = {}
        for field, suffix in (("reasoning_content", "reasoning"), ("content", "content")):
            raw = named("-assistant-" + suffix + ".txt").read_bytes()
            assert raw == message[field].encode("utf-8")
            text_counts[suffix + "_text_tokens"] = tokens(raw)
        host = json.loads(named("-host-result.json").read_bytes())
        assert host["executed"] is False and host["candidate_mutated"] is False
        calls.append({"id": row["id"], "usage": done["usage"], "elapsed_seconds": done["elapsed_seconds"],
            "finish_reason": done["finish_reason"], "physical_tokens_remaining": done["physical_tokens_remaining"],
            "within_proposed_generation_reserve": done["within_proposed_generation_reserve"],
            "native_endpoint_offline_input_counts_match": True, "separate_text_retokenization": text_counts,
            "timings": response["timings"], "host": host})
    memory = list(csv.reader((run / "memory.csv").read_text().splitlines()))
    assert len(memory) == seal["memory"]["samples"] and all(len(r) == 5 for r in memory)
    low = [r for r in memory if int(r[-1]) < 350]
    report = {"stage": args.stage, "custody": custody, "original_q1_custody": parent,
        "continuation_manifest_sha256": digest(HERE / "CONTINUATION_MANIFEST.json"),
        "source_identities_verified": len(plan["execution_source_sha256"]),
        "calls": calls, "memory": {**seal["memory"], "below_original_reference_samples": len(low),
            "first_below_reference_local": low[0][0] if low else None,
            "last_below_reference_local": low[-1][0] if low else None},
        "memory_policy": seal["memory_policy"], "effective_runtime": seal["effective_runtime"],
        "verifier_sha256": digest(Path(__file__)),
        "shared_verifier_sha256": digest(FOLLOW / "qualification-review/verify_evidence.py"),
        "limitations": "Mechanical verification does not certify direct reading or content correctness. Text retokenization is not original generated-token segmentation."}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
