"""Prepare only the sixteen matched ordinary-action requests; never complete one.

The only model-facing treatment is an appended, source-checked tool reference.
The consumed runners, action schema, executor and development states are reused
without modification. A later execution decision is required for model exposure.
"""
from __future__ import annotations

import argparse
from pathlib import Path

import continue_interface_follow_on as cont
import run_interface_follow_on as base
from prepare_interface_design import neutral_ids
from run_interface_consultation import candidate_bytes, session_bytes
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.interface_consultation import development_states, endpoint_request
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


ROOT = base.ROOT
COMPARISON = ROOT / "development/qwen_interface_consultation/comparison"
DESIGN = cont.CONT / "design-001"
REVIEW = cont.CONT / "design-review/DECISION.json"
ACTOR = {**cont.ACTOR, "generation_reserve": 32768}
INPUT_CEILING = ACTOR["context"] - ACTOR["generation_reserve"]
CONDITIONS = ("legacy", "visible_reference")
SEEDS = (42, 314159)
require = base.require

# These effect descriptions are checked against the pinned executor, candidate,
# and P0 implementations. Argument forms below are rendered from the schema.
EFFECTS = {
    "p0_page": "Returns current repository structure, Python function/class signatures and line ranges, not exact source. path may identify a file or directory; '.' is the root. offset counts rows from zero. At most 24 rows and 12,000 JSON bytes; next_offset continues the page or is null.",
    "tree": "Returns a shallow page of current directory entries. path identifies a directory; '.' is the root. offset counts entries from zero; next_offset continues the page or is null.",
    "search": "Returns literal case-folded matches in current source under path (file or directory; '.' is the root), with path, line number and at most 320 characters of line text. query also has a host limit of 128 UTF-8 bytes. offset counts matching lines from zero; next_offset continues the page or is null.",
    "read": "Returns exact current source from start_line (one-based), as the largest whole-line page within 18,000 content bytes, with candidate_id, file_sha256, returned interval and next_start_line. There is no line_count argument. complete means no later page, not that all earlier lines were read; an empty read beyond EOF also has complete=true without new coverage. Records reading; does not edit or check the candidate.",
    "patch": "Changes one existing file by replacing old exactly once with new. expected_candidate_id and expected_file_sha256 must equal the current PRE-EDIT candidate ID and target file fingerprint, not the desired output IDs. old must occur exactly once, old and new must differ, and each fragment is also limited to 2,000 UTF-8 bytes. The successor must satisfy candidate limits and change identity; the effective diff must fit 6,000 UTF-8 bytes. Returns previous/current candidate IDs, the new file fingerprint and diff. An accepted patch clears both current check flags; historical results remain saved.",
    "check": "Runs a NEW check on the current candidate; expected_candidate_id must match that current candidate. Although the common grammar includes prefork, only public is available in this continuation stage. Returns checked_candidate_id, check_id, passed, returncode, stdout and stderr, with full-stream byte counts/hashes and streams_truncated; each displayed stream is limited to 8,192 bytes and execution has a 30-second timeout. Sets the current public-check flag from the outcome. accepted=true with passed=false is an executed failing check.",
    "submit": "Submits the current candidate in this continuation stage; expected_candidate_id must match it. Sets submitted and returns submitted_candidate_id and the current public-check flag. The tool does not require a passing check to accept submission; task instructions still apply. Submission ends the work path.",
    "reopen_observation": "Requires an available saved observation handle, not merely a string of the right form. Returns the saved result JSON as exact_result_utf8, with handle, exact_result_sha256, size_bytes and accepted. It does not execute the original operation again.",
    "reopen_result": "Requires an available saved result handle. Returns the FULL original saved result JSON as exact_result_utf8, including its original bindings and result fields, with handle, exact_result_sha256, size_bytes and accepted. It does not return only an extracted-field object or execute the original operation again.",
    "reopen_event": "Requires an actually saved action payload for the event; an EVT address alone does not establish that one exists. Returns action_payload (the saved old/new fields for a patch), handle, action_payload_sha256, size_bytes and accepted. Original path and version guards remain in the historical event signal; they are not added to this returned payload. It does not replay the edit.",
}
GROUPS = (
    ("Current repository access", ("p0_page", "tree", "search", "read")),
    ("Candidate operations", ("patch", "check", "submit")),
    ("Saved information access", ("reopen_observation", "reopen_result", "reopen_event")),
)
INTRO = """Visible tool reference
Each final action is one strict JSON object. All listed keys are required;
additional keys are forbidden. Include the action discriminator with its exact
listed value. Integer arguments cannot be booleans. The entire final action
must fit 5,000 UTF-8 bytes; each canonical JSON result must fit 22,000 bytes.
String lengths below are character limits imposed by the output grammar;
separate UTF-8 byte limits imposed by the host also apply.

Paths are canonical candidate-relative paths, with forward slashes: no absolute
path, backslash, NUL, redundant slash, or '.'/'..' segment; no trailing slash.
The special path '.' is accepted only for p0_page/tree/search. A path is limited
to 160 UTF-8 bytes in addition to the grammar's character limit. Read and patch
require an existing file. Candidate files must remain UTF-8, at most 24,000 bytes
per file and 512 bytes per source line, within 256 files and 8,000,000 total bytes.

Use exact current IDs for version guards and actually available saved handles
for retrieval. These operation contracts describe forms and effects; the task
and operating instructions remain part of the input. Saved-information access
records an ordered retrieval, but does not mutate source, perform a new check,
or add current-source read coverage. Retrieval can return historical versions.
"""


def argument_form(prop: dict) -> str:
    require(set(prop) <= {"type", "const", "enum", "minLength", "maxLength", "pattern", "minimum", "maximum"},
            "unhandled argument constraint; reference must be reviewed")
    kind = prop["type"]
    require(kind in {"string", "integer"}, "unhandled argument type")
    parts = [kind]
    for key, label in (("const", "exactly"), ("enum", "one of"), ("minLength", "min characters"),
                       ("maxLength", "max characters"), ("pattern", "pattern"),
                       ("minimum", "minimum"), ("maximum", "maximum")):
        if key in prop:
            parts.append(label + " " + canonical_json_bytes(prop[key]).decode("utf-8"))
    return "; ".join(parts)


def tool_reference(response_format: dict) -> str:
    schema = response_format["json_schema"]["schema"]
    require(set(schema) == {"oneOf"}, "unhandled action grammar structure")
    options = {}
    for option in schema["oneOf"]:
        require(set(option) == {"type", "properties", "required", "additionalProperties"}, "unhandled action constraint")
        require(option["type"] == "object" and option["additionalProperties"] is False, "action shape differs")
        require(set(option["required"]) == set(option["properties"]), "optional or missing argument needs review")
        name = option["properties"]["action"]["const"]
        require(name not in options, "duplicate action")
        options[name] = option
    require(set(options) == set(EFFECTS), "operation/effect coverage differs")
    lines = [INTRO.rstrip()]
    for title, names in GROUPS:
        lines.extend(["", title])
        for name in names:
            option = options[name]
            lines.append("\n" + name + " — required keys:")
            for key in option["required"]:
                lines.append("  " + key + ": " + argument_form(option["properties"][key]))
            lines.append("Effect and host requirements: " + EFFECTS[name])
    return "\n".join(lines) + "\n"


def schedule() -> list[dict]:
    rows = []
    for state_index in range(4):
        for seed_index, seed in enumerate(SEEDS):
            order = CONDITIONS if (state_index + seed_index) % 2 == 0 else CONDITIONS[::-1]
            for condition in order:
                rows.append({"id": f"C{len(rows) + 1:02d}", "state": f"I{state_index + 1}",
                             "state_index": state_index, "seed": seed, "condition": condition})
    return rows


def request_for(value, row: dict, reference: str) -> dict:
    request = endpoint_request(value, seed=row["seed"], mode="action")
    request["model"] = base.ALIAS
    request["messages"][1]["content"] = canonical_json_bytes(
        neutral_ids(load_json_strict(value.request), row["state"])).decode("utf-8")
    require(row["condition"] in CONDITIONS, "unknown condition")
    if row["condition"] == "visible_reference":
        request["messages"][0]["content"] += "\n\n" + reference
    return request


def render_only(url: str, request: dict, post=base.post) -> tuple[bytes, bytes, bytes, int]:
    # This entry point has no completion route or live-action execution path.
    template = post(url, "/apply-template", canonical_json_bytes(request), 60)
    rendered = load_json_strict(template)["prompt"].encode("utf-8")
    tokenized = post(url, "/tokenize", canonical_json_bytes({"content": rendered.decode("utf-8"), "add_special": False}), 60)
    count = len(load_json_strict(tokenized)["tokens"])
    require(0 < count <= INPUT_CEILING, "native input exceeds prospective generation admission margin")
    return template, rendered, tokenized, count


def source_identities() -> dict:
    return {**base.source_identities(),
            Path(cont.__file__).relative_to(ROOT).as_posix(): sha256_file(Path(cont.__file__)),
            Path(__file__).relative_to(ROOT).as_posix(): sha256_file(Path(__file__))}


def design_binding() -> dict:
    cont.load_plan()  # Preserve all consumed request/source/owner bindings.
    seal = cont.verified_seal(DESIGN)
    require(seal["completed_responses"] == 4 and seal["disposition"] == "completed_nonexecuting_stage", "design incomplete")
    decision = cont.reviewed_files(REVIEW)
    require(decision["design_seal_sha256"] == sha256_file(DESIGN / "RESPONSE_SEAL.json"), "design review binding differs")
    require(decision["selected_variant"] == "visible_tool_reference" and decision["comparison_live_authorized"] is False,
            "selected preparation differs")
    return {"design_seal_sha256": sha256_file(DESIGN / "RESPONSE_SEAL.json"), "design_decision_sha256": sha256_file(REVIEW)}


class PreparationLog(RecordLog):
    def append(self, record_type, payload, artifacts):
        if record_type == "runtime_prepared":
            payload = dict(payload)
            payload["original_helper_actor"] = payload.pop("actor")
            payload["actor"] = ACTOR
            payload["memory_policy"] = cont.POLICY
            payload["completion_enabled"] = False
        return super().append(record_type, payload, artifacts)


def prepare(args) -> dict:
    binding = design_binding()
    sources = source_identities()
    values = development_states(ROOT)
    grammar = endpoint_request(values[0], seed=42, mode="action")["response_format"]
    reference = tool_reference(grammar)
    args.output.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(args.output)
    log = PreparationLog(args.output / "records.jsonl", "interface-comparison-preparation-001")
    artifacts = [store.put("SPEC.md", (COMPARISON / "SPEC.md").read_bytes()),
                 store.put("TOOL_REFERENCE.txt", reference.encode("utf-8")),
                 store.put("RESPONSE_FORMAT.json", canonical_json_bytes(grammar))]
    for i, value in enumerate(values, 1):
        stem = f"states/I{i}/"
        for name, raw in (("original-request.json", value.request), ("candidate.json", candidate_bytes(value.state.candidate)),
                          ("session.json", session_bytes(value.state)), ("provenance.json", canonical_json_bytes(value.provenance))):
            artifacts.append(store.put(stem + name, raw))
    log.append("preparation_started", {**binding, "actor": ACTOR, "memory_policy": cont.POLICY,
               "source_sha256": sources, "completion_calls": 0, "schedule": schedule()}, artifacts)
    rows, failure = [], None
    try:
        with base.owned_runtime(args, store, log) as url:
            for row in schedule():
                cont.monitoring(args.output / "memory.csv")
                request = request_for(values[row["state_index"]], row, reference)
                template, rendered, tokenized, count = render_only(url, request)
                cont.healthy_runtime(args.output / "private-runtime/server.stderr.log")
                raw = canonical_json_bytes(request)
                stem = "requests/" + row["id"]
                artifacts = [store.put(stem + "-request.json", raw), store.put(stem + "-rendered-prompt.txt", rendered),
                             store.put(stem + "-template-response.json", template), store.put(stem + "-tokenization.json", tokenized)]
                completed = {**row, "request_path": stem + "-request.json", "request_sha256": sha256_bytes(raw),
                             "rendered_path": stem + "-rendered-prompt.txt", "rendered_sha256": sha256_bytes(rendered),
                             "prompt_tokens": count, "physical_generation_space": ACTOR["context"] - count}
                rows.append(completed)
                log.append("request_prepared", {**completed, "completion_sent": False,
                           "routes": ["/apply-template", "/tokenize"]}, artifacts)
                print(f"Prepared {row['id']} {row['condition']}: {count} input tokens", flush=True)
            require(source_identities() == sources, "preparation source changed")
            require(design_binding() == binding, "design review changed")
            cont.monitoring(args.output / "memory.csv")
        closed = verify_records(args.output / "records.jsonl", args.output)[-1]
        require(closed["record_type"] == "runtime_closed" and closed["payload"]["owned_server_shutdown_verified"]
                and closed["payload"]["dedicated_port_free"], "preparation runtime lifecycle incomplete")
        manifest = {**binding, "actor": ACTOR, "memory_policy": cont.POLICY, "source_sha256": sources,
                    "input_ceiling": INPUT_CEILING, "generation_uncapped": True, "rows": rows,
                    "completion_calls": 0, "proposed_comparison_calls": 16, "comparison_live_authorized": False,
                    "files": [v for v in base.file_inventory(args.output)
                              if v["path"].startswith(("requests/", "states/")) or v["path"] in {"SPEC.md", "TOOL_REFERENCE.txt", "RESPONSE_FORMAT.json"}]}
        log.append("preparation_completed", {"completion_calls": 0, "prepared_requests": len(rows)},
                   [store.put("PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))])
        validate_package(args.output)
    except Exception as error:
        failure = error
        log.append("preparation_stopped", {"error": type(error).__name__ + ": " + str(error), "completion_calls": 0}, [])
    records = verify_records(args.output / "records.jsonl", args.output)
    files = base.file_inventory(args.output)
    seal = {"stage": "comparison_preparation", "disposition": "stopped_without_completion" if failure else "prepared_without_completion",
            "completion_calls": 0, "prepared_requests": len(rows), "record_count": len(records), "files": files,
            "aggregate_sha256": sha256_bytes(canonical_json_bytes(files)), "memory": base.memory_stats(args.output / "memory.csv"),
            "effective_runtime": base.runtime_evidence(args.output / "private-runtime/server.stderr.log"),
            "private_runtime_files_local_only": {p.name: sha256_file(p) for p in sorted((args.output / "private-runtime").glob("*")) if p.is_file()}}
    base.write_json(args.output / "PREPARATION_SEAL.json", seal)
    if failure:
        raise failure
    return seal


def validate_package(folder: Path) -> dict:
    manifest = load_json_strict((folder / "PACKAGE_MANIFEST.json").read_bytes())
    require(manifest["actor"] == ACTOR and manifest["memory_policy"] == cont.POLICY, "comparison policy differs")
    require(manifest["input_ceiling"] == INPUT_CEILING and manifest["generation_uncapped"] is True, "comparison admission differs")
    require(manifest["completion_calls"] == 0 and manifest["comparison_live_authorized"] is False, "not an unexposed preparation")
    require(manifest["proposed_comparison_calls"] == 16, "comparison scope differs")
    require((folder / "SPEC.md").read_bytes() == (COMPARISON / "SPEC.md").read_bytes(), "comparison specification differs")
    for path, digest in manifest["source_sha256"].items():
        require(sha256_file(ROOT / path) == digest, "prepared execution source differs: " + path)
    require(manifest["source_sha256"] == source_identities(), "source closure differs")
    for key, value in design_binding().items():
        require(manifest[key] == value, "design provenance differs")
    for row in manifest["files"]:
        raw = (folder / row["path"]).read_bytes()
        require(len(raw) == row["size_bytes"] and sha256_bytes(raw) == row["sha256"], "prepared artifact differs: " + row["path"])
    values = development_states(ROOT)
    grammar = endpoint_request(values[0], seed=42, mode="action")["response_format"]
    reference = tool_reference(grammar)
    require((folder / "TOOL_REFERENCE.txt").read_bytes() == reference.encode("utf-8"), "reference differs")
    require(len(manifest["rows"]) == 16, "schedule length differs")
    for row, expected in zip(manifest["rows"], schedule()):
        require(all(row[key] == value for key, value in expected.items()), "schedule differs")
        raw = (folder / row["request_path"]).read_bytes()
        require(raw == canonical_json_bytes(request_for(values[row["state_index"]], row, reference)), "request transformation differs")
        require(sha256_bytes(raw) == row["request_sha256"], "request identity differs")
        rendered = (folder / row["rendered_path"]).read_bytes()
        require(sha256_bytes(rendered) == row["rendered_sha256"], "render identity differs")
        tokens = load_json_strict((folder / ("requests/" + row["id"] + "-tokenization.json")).read_bytes())["tokens"]
        require(len(tokens) == row["prompt_tokens"] and 0 < len(tokens) <= INPUT_CEILING, "native admission differs")
        require(row["physical_generation_space"] == ACTOR["context"] - len(tokens), "physical capacity differs")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    print(canonical_json_bytes(prepare(args)).decode("utf-8"), flush=True)


if __name__ == "__main__":
    main()
