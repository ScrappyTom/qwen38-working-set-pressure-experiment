"""Count saved output text separately without inferring original generated token IDs."""
from __future__ import annotations

import argparse
import subprocess
from pathlib import Path
from types import SimpleNamespace

from working_set_exp.interface_consultation import MODEL_SHA256
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_file
from working_set_exp.runtime import tokenizer_count


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise FileExistsError(args.output)
    seal = load_json_strict((args.run / "RESPONSE_SEAL.json").read_bytes())
    if seal["completed_responses"] != 16 or sha256_file(args.model) != MODEL_SHA256:
        raise ValueError("closed response count or selected model differs")
    profile = SimpleNamespace(model_path=args.model, tokenizer_path=args.tokenizer)
    version_reply = subprocess.run([str(args.tokenizer), "--version"], capture_output=True, check=True)
    version = (version_reply.stdout + version_reply.stderr).decode("utf-8", errors="replace")
    cache = {}
    def count(path):
        raw = path.read_bytes()
        if not raw:
            return 0
        if raw not in cache:
            cache[raw] = tokenizer_count(profile, raw)
        return cache[raw]
    rows = []
    for ordinal in range(1, 17):
        prefix = args.run / "calls" / f"{ordinal:02d}"
        path = lambda suffix: Path(str(prefix) + suffix)
        response = load_json_strict(path("-endpoint-response.json").read_bytes())
        usage = response["usage"]
        native_input = count(path("-rendered-prompt.txt"))
        if native_input != usage["prompt_tokens"]:
            raise ValueError(f"offline/native input token counts differ: {ordinal}")
        reasoning = count(path("-assistant-reasoning.txt"))
        final = count(path("-assistant-content.txt"))
        rows.append({"ordinal": ordinal, "endpoint_prompt_tokens": native_input,
                     "endpoint_completion_tokens": usage["completion_tokens"],
                     "retokenized_reasoning_text_tokens": reasoning, "retokenized_final_text_tokens": final,
                     "endpoint_minus_separately_retokenized_texts": usage["completion_tokens"]-reasoning-final})
    output = {"scope": "offline text tokenization; zero model completions; does not certify direct review",
              "qualification": "all sixteen rendered inputs match actual endpoint prompt usage",
              "interpretation": "The endpoint supplies combined generated output counts, not separate reasoning/final counts. These are counts from retokenizing saved text with the same vocabulary. Their residual is not asserted to equal special-token overhead: generation segmentation and field boundaries can differ.",
              "model_sha256": MODEL_SHA256, "tokenizer_sha256": sha256_file(args.tokenizer), "tokenizer_version": version,
              "tokenization": "existing offline tokenizer_count: no BOS, no escape processing, special tokens parsed",
              "source_sha256": sha256_file(Path(__file__)), "response_seal_sha256": sha256_file(args.run / "RESPONSE_SEAL.json"),
              "totals": {name: sum(row[name] for row in rows) for name in
                         ("endpoint_prompt_tokens", "endpoint_completion_tokens", "retokenized_reasoning_text_tokens", "retokenized_final_text_tokens")},
              "calls": rows}
    args.output.write_bytes(canonical_json_bytes(output))
    print(output["totals"])


if __name__ == "__main__":
    main()
