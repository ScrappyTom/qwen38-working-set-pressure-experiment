"""Prepare four informed-design requests; native rendering/tokenization makes no model calls."""
from __future__ import annotations

import argparse
import urllib.request
from pathlib import Path

from working_set_exp.interface_consultation import MODEL_SHA256, SERVER_SHA256, development_states, endpoint_request
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.tools import action_schema


ROOT = Path(__file__).resolve().parents[1]
FACTS = """Implementation facts for informed design, beyond the brief current prompt:
The schema below is the actual final-action grammar. It is currently supplied
to the endpoint as response_format, not displayed as tool instructions in the
ordinary rendered prompt. Available action/check IDs in the state also apply.
Only one action may execute per invocation. All reopen operations take handle.
Candidate identity is a hash of the complete file inventory and content hashes.
Patch guards refer to the existing candidate and existing target file. The tool
requires the exact old fragment to occur once and rejects unchanged bytes. An
accepted patch creates a new candidate and clears current check flags. The
grammar limits old/new to 512 characters each; host limits also apply: 2,000
UTF-8 bytes per fragment, 5,000 action bytes, 6,000 diff bytes, 24,000 bytes per
file, 512 bytes per source line, and 8,000,000 candidate bytes across at most
256 files. Paths are canonical and candidate-relative.
Reading current source before mutation is an instruction to the actor. The
patch tool does not inspect read history or P0 completeness. Reading reports
the exact current file hash and a bounded whole-line page (at most 18,000
content bytes). Its complete flag means this page reaches EOF, not that all
earlier lines were read. Whole-file coverage must account for all source lines.
The P0 root is a top-level directory summary. Its repository-complete flag is
always false; p0_page exposes further directory/file-outline structure without
source. That root flag does not clear after source reads.
Check executes the named available check on the expected current candidate.
Submit binds to the current candidate and ends the task; it reports the current
check flag but does not enforce a passing check. The task's inspection/check
obligations and acceptance evaluation remain distinct from tool validation.
Reopen_result returns a saved exact operation result with its original bindings.
Reopen_event returns saved old/new action fields. Reopen_observation returns a
listed saved observation. Retrieval does not rerun checks, replay edits, make
historical evidence current, or extend current-source read coverage. It creates
a new ordered access event retaining the canonical source address.
Presence describes whether an extracted field payload exists; residency says
whether its fields are included in this input. Payload SHA/size describe the
canonical JSON of the extracted fields, not only the displayed source string.
The complete action/result pair SHA/size include structural fields and bindings.
File hashes/sizes instead describe file bytes. Exact internal custody must be
preserved even when some details are not useful in the model-facing view.
The ideal correction-cycle sentence is a design illustration, not a prescribed
action order or a guarantee of remaining capacity. Calls remaining describe
action allowance, separate from physical context space. No change to budgets,
stopping policy, recovery guarantees or stored evidence is requested here.
"""
QUESTION = """How would you prefer these same available facts and operations to be
presented when choosing your next action? You may retain the current interface.
Show a concrete proposed tool description and state fragment where a change
would help, and explain what existing fact or operation each part represents.
Distinguish what you would show together, leave available on request, or keep
as an internal audit detail. Preserve exact recovery, ordered activity, version
guards, one action per invocation, and the distinction between retrieving a
saved result and executing a new check or edit. Identify any suggestion that
needs new information or behavior rather than a different presentation. Do not
perform the embedded coding task. Give a focused design proposal, not a new
memory architecture or definitions of every field."""


def neutral_ids(value, label):
    if isinstance(value, dict):
        return {key: label if key == "fixture_id" else neutral_ids(item, label) for key, item in value.items()}
    if isinstance(value, list):
        return [neutral_ids(item, label) for item in value]
    return value


def native(route: str, data: bytes) -> bytes:
    request = urllib.request.Request("http://127.0.0.1:18124" + route, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=60) as response:
        return response.read()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    args.output.mkdir(parents=True, exist_ok=False)
    (args.output / "IMPLEMENTATION_FACTS.txt").write_text(FACTS, encoding="utf-8", newline="\n")
    (args.output / "DESIGN_QUESTION.txt").write_text(QUESTION, encoding="utf-8", newline="\n")
    schema = action_schema("continuation", probe_id=None, read_mode="maximal_bounded_page",
                           hierarchical_p0=True, result_reopen=True, event_reopen=True)["json_schema"]["schema"]
    rows = []
    for ordinal, state in enumerate(development_states(ROOT), 1):
        label = f"D{ordinal}"
        original = load_json_strict(state.request)
        projected = neutral_ids(original, label)
        request = endpoint_request(state, seed=42, mode="diagnostic")
        request["messages"][0]["content"] = (
            "You are advising on a coding agent interface. Review the supplied state and implementation facts, "
            "then propose your preferred presentation. Do not perform the embedded task or emit an executable tool action. "
            "Distinguish preferences, implementation facts, and uncertainty."
        )
        request["messages"][1]["content"] = (
            "Current state, with a neutral fixture identifier:\n" + canonical_json_bytes(projected).decode("utf-8") +
            "\n\n" + FACTS + "\nActual accepted final-action grammar:\n" + canonical_json_bytes(schema).decode("utf-8") +
            "\n\nDesign question:\n" + QUESTION
        )
        raw = canonical_json_bytes(request)
        (args.output / f"{ordinal:02d}-request.json").write_bytes(raw)
        template_raw = native("/apply-template", raw)
        rendered = load_json_strict(template_raw)["prompt"].encode("utf-8")
        tokens = load_json_strict(native("/tokenize", canonical_json_bytes({"content": rendered.decode("utf-8"), "add_special": False})))["tokens"]
        (args.output / f"{ordinal:02d}-template-response.json").write_bytes(template_raw)
        (args.output / f"{ordinal:02d}-rendered-prompt.txt").write_bytes(rendered)
        if len(tokens) + 8192 > 32768:
            raise ValueError("design request lacks the stated development generation space")
        rows.append({"ordinal": ordinal, "neutral_id": label, "source_state": state.name, "source_state_sha256": sha256_bytes(state.request),
                     "request_sha256": sha256_bytes(raw), "prompt_tokens": len(tokens), "physical_generation_space": 32768-len(tokens), "seed": 42})
    files = [{"path": path.relative_to(args.output).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
             for path in sorted(args.output.rglob("*")) if path.is_file()]
    manifest = {"purpose": "informed interface design after preserved initial interpretations; not executed",
                "maximum_proposed_completions": 4, "completion_calls_made": 0, "attempts_per_request": 1, "retries": 0,
                "actor": {"model_sha256": MODEL_SHA256, "server_sha256": SERVER_SHA256, "context": 32768,
                          "kv_k": "q8_0", "kv_v": "q8_0", "mtp": False, "thinking": True, "effort": "xhigh", "budget": -1},
                "not_an_authorization_receipt": True, "rows": rows, "files": files,
                "source_sha256": {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in
                                   (Path(__file__), ROOT / "src/working_set_exp/interface_consultation.py", ROOT / "src/working_set_exp/tools.py",
                                    ROOT / "src/working_set_exp/candidate.py", ROOT / "src/working_set_exp/hierarchical_p0.py")}}
    (args.output / "PACKAGE_MANIFEST.json").write_bytes(canonical_json_bytes(manifest))
    print(f"Prepared {len(rows)} informed-design requests; maximum native input {max(row['prompt_tokens'] for row in rows)} tokens; zero completion calls.")


if __name__ == "__main__":
    main()
