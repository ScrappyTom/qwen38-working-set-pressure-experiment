"""Prepare the earned resource/navigation wording candidate; never complete it.

Keep the consumed source closure intact. Reuse its states, native preparation,
visible reference and custody helpers, with only two declared wording edits.
"""
from __future__ import annotations

import argparse
import copy
from pathlib import Path

import prepare_interface_comparison as reference
import run_interface_comparison as previous
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


ROOT = reference.ROOT
AREA = ROOT / "development/qwen_interface_consultation/wording"
REVIEW = reference.COMPARISON / "review/DECISION.json"
DECISION_SHA = "bd258a23ac2b210c24f8ebe2acb1f96f6a27d7fe61709ec43021c8f06d578966"
REFERENCE_SHA = "75f774a6335da7a8d98dcbae4e4b025f2ab81a0421f74dd06503813fda4fba0f"
ACTOR = reference.ACTOR
SEEDS = (1729, 271828)
CONDITIONS = ("reference", "wording")
RESOURCE_KEY = "correction_cycle_reserved_by_fixture_design"
RESOURCE_EXAMPLE = "check -> patch -> recheck -> submit fits within the prospective ideal path"
OLD_NAVIGATION = "If its contract says the repository view is incomplete, use p0_page to expand exact readable structure."
NEW_NAVIGATION = (
    "The P0 root lists all top-level entries; complete_for_repository=false describes its scope, not unfinished work. "
    "Use p0_page when you need directory structure or a file outline. "
    "A page's next_offset continues rows for that same path; null ends that scoped listing. "
    "Paging does not change the root's completeness flags."
)
require = reference.require


def wording_variant(request: dict) -> dict:
    """A prospective presentation adapter, not a change to stored host state."""
    require([m["role"] for m in request["messages"]] == ["system", "user"], "expected fresh ordinary input")
    system = request["messages"][0]["content"]
    require(system.count(OLD_NAVIGATION) == 1, "navigation wording needs review")
    expected_reference = reference.tool_reference(request["response_format"])
    require(sha256_bytes(expected_reference.encode("utf-8")) == REFERENCE_SHA,
            "tool schema or reference needs review")
    require(system.endswith("\n\n" + expected_reference), "complete tested reference is missing")
    state = load_json_strict(request["messages"][1]["content"].encode("utf-8"))
    require(state["schema_version"] == "experiment-020-ecological-event-frame-request-v1", "state schema needs review")
    require(state["resource_state"].get(RESOURCE_KEY) == RESOURCE_EXAMPLE, "resource wording needs review")
    require(state["current_p0"]["complete_for_top_level"] is True
            and state["current_p0"]["complete_for_repository"] is False, "P0 scope needs review")
    del state["resource_state"][RESOURCE_KEY]
    result = copy.deepcopy(request)
    result["messages"][0]["content"] = system.replace(OLD_NAVIGATION, NEW_NAVIGATION, 1)
    result["messages"][1]["content"] = canonical_json_bytes(state).decode("utf-8")
    return result


def schedule() -> list[dict]:
    rows = []
    # Two directly affected states, two new seeds, four counterbalanced pairs.
    for index, state_index in enumerate((2, 3)):
        for seed_index, seed in enumerate(SEEDS):
            order = CONDITIONS if (index + seed_index) % 2 == 0 else CONDITIONS[::-1]
            for condition in order:
                rows.append({"id": f"W{len(rows) + 1:02d}", "state": f"I{state_index + 1}",
                             "state_index": state_index, "seed": seed, "condition": condition,
                             "purpose": "proposed_comparison"})
    return rows


def preparation_rows() -> list[dict]:
    rows = schedule()
    # Input/capacity regressions only. These four IDs are excluded from exposure.
    for state_index in (0, 1):
        for condition in CONDITIONS:
            rows.append({"id": f"E{len(rows) - 7:02d}", "state": f"I{state_index + 1}",
                         "state_index": state_index, "seed": SEEDS[0], "condition": condition,
                         "purpose": "offline_input_regression"})
    return rows


def request_for(value, row: dict, tool_reference: str) -> dict:
    require(row["condition"] in CONDITIONS and row["seed"] in SEEDS, "unprepared condition or seed")
    # The consumed helper restricts seeds to its old scope. Build its exact
    # reference input, then select this separately declared prospective seed.
    request = reference.request_for(value, {**row, "seed": reference.SEEDS[0], "condition": "visible_reference"}, tool_reference)
    request["seed"] = row["seed"]
    return wording_variant(request) if row["condition"] == "wording" else request


def source_identities() -> dict:
    return {**reference.source_identities(),
            Path(previous.__file__).relative_to(ROOT).as_posix(): sha256_file(Path(previous.__file__)),
            Path(__file__).relative_to(ROOT).as_posix(): sha256_file(Path(__file__))}


def prior_binding() -> dict:
    previous.load_manifest()  # Read-only: the original execution closure still verifies.
    require(sha256_file(REVIEW) == DECISION_SHA, "completed comparison decision differs")
    decision = load_json_strict(REVIEW.read_bytes())
    for name, digest in decision["audit_sha256"].items():
        require(sha256_file(REVIEW.parent / name) == digest, "completed comparison audit differs")
    require(sha256_file(previous.RUN / "RESPONSE_SEAL.json") == decision["response_seal_sha256"], "completed response seal differs")
    reference.cont.verified_seal(previous.RUN)
    require(sha256_file(previous.PACKAGE / "TOOL_REFERENCE.txt") == REFERENCE_SHA, "tested reference differs")
    return {"comparison_decision_sha256": DECISION_SHA, "reference_sha256": REFERENCE_SHA,
            "comparison_response_seal_sha256": decision["response_seal_sha256"]}


def prepare(args) -> dict:
    binding, sources = prior_binding(), source_identities()
    values = reference.development_states(ROOT)
    grammar = reference.endpoint_request(values[0], seed=42, mode="action")["response_format"]
    tool_reference = reference.tool_reference(grammar)
    args.output.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(args.output)
    log = reference.PreparationLog(args.output / "records.jsonl", "interface-wording-preparation-001")
    artifacts = [store.put("SPEC.md", (AREA / "SPEC.md").read_bytes()),
                 store.put("TOOL_REFERENCE.txt", tool_reference.encode("utf-8")),
                 store.put("RESPONSE_FORMAT.json", canonical_json_bytes(grammar)),
                 store.put("WORDING_CHANGE.json", canonical_json_bytes({
                     "replace_system_sentence": {"before": OLD_NAVIGATION, "after": NEW_NAVIGATION},
                     "remove_user_field": {"path": "/resource_state/" + RESOURCE_KEY, "old_value": RESOURCE_EXAMPLE}}))]
    for index, value in enumerate(values, 1):
        for name, raw in (("original-request.json", value.request),
                          ("candidate.json", reference.candidate_bytes(value.state.candidate)),
                          ("session.json", reference.session_bytes(value.state)),
                          ("provenance.json", canonical_json_bytes(value.provenance))):
            artifacts.append(store.put(f"states/I{index}/" + name, raw))
    log.append("preparation_started", {**binding, "actor": ACTOR, "memory_policy": reference.cont.POLICY,
               "source_sha256": sources, "completion_calls": 0, "rows": preparation_rows()}, artifacts)
    rows, failure = [], None
    try:
        with reference.base.owned_runtime(args, store, log) as url:
            for row in preparation_rows():
                reference.cont.monitoring(args.output / "memory.csv")
                request = request_for(values[row["state_index"]], row, tool_reference)
                template, rendered, tokenized, count = reference.render_only(url, request)
                reference.cont.healthy_runtime(args.output / "private-runtime/server.stderr.log")
                raw, stem = canonical_json_bytes(request), "requests/" + row["id"]
                artifacts = [store.put(stem + "-request.json", raw), store.put(stem + "-rendered-prompt.txt", rendered),
                             store.put(stem + "-template-response.json", template), store.put(stem + "-tokenization.json", tokenized)]
                prepared = {**row, "request_path": stem + "-request.json", "request_sha256": sha256_bytes(raw),
                            "rendered_path": stem + "-rendered-prompt.txt", "rendered_sha256": sha256_bytes(rendered),
                            "prompt_tokens": count, "physical_generation_space": ACTOR["context"] - count}
                rows.append(prepared)
                log.append("request_prepared", {**prepared, "completion_sent": False,
                           "routes": ["/apply-template", "/tokenize"]}, artifacts)
                print(f"Prepared {row['id']} {row['purpose']} {row['condition']}: {count} input tokens", flush=True)
            require(source_identities() == sources, "preparation source changed")
            require(prior_binding() == binding, "historical binding changed")
            reference.cont.monitoring(args.output / "memory.csv")
        closed = verify_records(args.output / "records.jsonl", args.output)[-1]
        require(closed["record_type"] == "runtime_closed" and closed["payload"]["owned_server_shutdown_verified"]
                and closed["payload"]["dedicated_port_free"], "preparation runtime lifecycle incomplete")
        manifest = {**binding, "actor": ACTOR, "memory_policy": reference.cont.POLICY, "source_sha256": sources,
                    "input_ceiling": reference.INPUT_CEILING, "generation_uncapped": True, "rows": rows,
                    "completion_calls": 0, "proposed_comparison_calls": 8, "comparison_live_authorized": False,
                    "proposed_completion_ids": [r["id"] for r in schedule()],
                    "files": [r for r in reference.base.file_inventory(args.output)
                              if r["path"].startswith(("requests/", "states/")) or r["path"] in
                              {"SPEC.md", "TOOL_REFERENCE.txt", "RESPONSE_FORMAT.json", "WORDING_CHANGE.json"}]}
        log.append("preparation_completed", {"completion_calls": 0, "prepared_requests": len(rows)},
                   [store.put("PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))])
        validate_package(args.output)
    except Exception as error:
        failure = error
        log.append("preparation_stopped", {"error": type(error).__name__ + ": " + str(error), "completion_calls": 0}, [])
    records = verify_records(args.output / "records.jsonl", args.output)
    files = reference.base.file_inventory(args.output)
    seal = {"stage": "wording_preparation", "disposition": "stopped_without_completion" if failure else "prepared_without_completion",
            "completion_calls": 0, "prepared_requests": len(rows), "record_count": len(records), "files": files,
            "aggregate_sha256": sha256_bytes(canonical_json_bytes(files)),
            "memory": reference.base.memory_stats(args.output / "memory.csv"),
            "effective_runtime": reference.base.runtime_evidence(args.output / "private-runtime/server.stderr.log"),
            "private_runtime_files_local_only": {p.name: sha256_file(p) for p in sorted((args.output / "private-runtime").glob("*")) if p.is_file()}}
    reference.base.write_json(args.output / "PREPARATION_SEAL.json", seal)
    if failure:
        raise failure
    return seal


def validate_package(folder: Path) -> dict:
    manifest = load_json_strict((folder / "PACKAGE_MANIFEST.json").read_bytes())
    require(manifest["actor"] == ACTOR and manifest["memory_policy"] == reference.cont.POLICY, "wording policy differs")
    require(manifest["input_ceiling"] == reference.INPUT_CEILING and manifest["generation_uncapped"] is True, "admission differs")
    require(manifest["completion_calls"] == 0 and manifest["comparison_live_authorized"] is False, "not unexposed preparation")
    require(manifest["proposed_comparison_calls"] == 8
            and manifest["proposed_completion_ids"] == [r["id"] for r in schedule()], "proposed exposure scope differs")
    require((folder / "SPEC.md").read_bytes() == (AREA / "SPEC.md").read_bytes(), "wording specification differs")
    require(manifest["source_sha256"] == source_identities(), "preparation source closure differs")
    for key, value in prior_binding().items():
        require(manifest[key] == value, "historical provenance differs")
    for row in manifest["files"]:
        raw = (folder / row["path"]).read_bytes()
        require(len(raw) == row["size_bytes"] and sha256_bytes(raw) == row["sha256"], "prepared artifact differs: " + row["path"])
    values = reference.development_states(ROOT)
    grammar = reference.endpoint_request(values[0], seed=42, mode="action")["response_format"]
    tool_reference = reference.tool_reference(grammar)
    require((folder / "TOOL_REFERENCE.txt").read_bytes() == tool_reference.encode("utf-8"), "reference differs")
    require(len(manifest["rows"]) == len(preparation_rows()), "preparation count differs")
    for row, expected in zip(manifest["rows"], preparation_rows()):
        require(all(row[k] == v for k, v in expected.items()), "schedule differs")
        raw = (folder / row["request_path"]).read_bytes()
        require(raw == canonical_json_bytes(request_for(values[row["state_index"]], row, tool_reference)), "request transformation differs")
        require(sha256_bytes(raw) == row["request_sha256"], "request identity differs")
        rendered = (folder / row["rendered_path"]).read_bytes()
        require(sha256_bytes(rendered) == row["rendered_sha256"], "render identity differs")
        tokens = load_json_strict((folder / ("requests/" + row["id"] + "-tokenization.json")).read_bytes())["tokens"]
        require(len(tokens) == row["prompt_tokens"] and 0 < len(tokens) <= reference.INPUT_CEILING, "native admission differs")
        require(row["physical_generation_space"] == ACTOR["context"] - len(tokens), "capacity accounting differs")
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    seal = prepare(args)
    print(canonical_json_bytes({k: seal[k] for k in ("disposition", "completion_calls", "prepared_requests", "memory")}).decode("utf-8"))


if __name__ == "__main__":
    main()
