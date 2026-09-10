from __future__ import annotations

import argparse
from pathlib import Path

from working_set_exp.interface_consultation import (
    MODEL_SHA256, RUNTIME_REVISION, SERVER_SHA256, consultation_schedule, development_states, endpoint_request,
)
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


ROOT = Path(__file__).resolve().parents[1]


def main() -> None:
    parser = argparse.ArgumentParser(description="Prepare the bounded 16-response Qwen interface consultation without model exposure.")
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    values = {value.name: value for value in development_states(ROOT)}
    for name, value in values.items():
        folder = args.output / "states" / name
        folder.mkdir(parents=True)
        (folder / "request.json").write_bytes(value.request)
        (folder / "history.json").write_bytes(canonical_json_bytes(value.pairs))
        (folder / "provenance.json").write_bytes(canonical_json_bytes(value.provenance))
        (folder / "diagnostic.txt").write_text(value.questions, encoding="utf-8")
    schedule = consultation_schedule()
    requests = args.output / "requests"
    requests.mkdir()
    for row in schedule:
        path = requests / f"{row['ordinal']:02d}-{row['mode']}.json"
        path.write_bytes(canonical_json_bytes(endpoint_request(values[row["state"]], seed=row["seed"], mode=row["mode"])))
        row["request_path"] = path.relative_to(args.output).as_posix()
        row["request_sha256"] = sha256_file(path)
    (args.output / "SCHEDULE.json").write_bytes(canonical_json_bytes(schedule))
    manifest = {
        "purpose": "development-only interface interpretation; no preferred replacement is supplied",
        "maximum_completion_calls": 16, "attempts_per_request": 1, "retries": 0,
        "model_sha256": MODEL_SHA256, "server_sha256": SERVER_SHA256, "runtime_revision": RUNTIME_REVISION,
        "physical_context": 32768, "kv_k": "q8_0", "kv_v": "q8_0", "mtp": False,
        "reasoning": {"enabled": True, "effort": "xhigh", "budget": -1, "carried_into_later_history": False},
        "files": [{"path": path.relative_to(args.output).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
                  for path in sorted(args.output.rglob("*")) if path.is_file()],
        "preparation_code_sha256": {path.relative_to(ROOT).as_posix(): sha256_file(path)
                                    for path in (Path(__file__), ROOT / "src/working_set_exp/interface_consultation.py")},
        "runtime_template_and_token_qualification": "required before completions; no inference performed by this preparation script",
    }
    (args.output / "PACKAGE_MANIFEST.json").write_bytes(canonical_json_bytes(manifest))
    print(f"Prepared {len(schedule)} exact requests in {args.output}")


if __name__ == "__main__":
    main()
