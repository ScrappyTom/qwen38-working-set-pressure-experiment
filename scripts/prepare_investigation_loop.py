"""Prepare the two ordinary multi-turn runs; this entry point never requests generation."""
from __future__ import annotations

import argparse
from pathlib import Path

import prepare_interface_comparison as reference
import prepare_interface_wording as wording
from working_set_exp.candidate import Candidate, MAX_FILE_BYTES
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.ecological_pilot_v2 import EcologicalFixture, admitted_donor_candidate, build_request
from working_set_exp.interface_consultation import endpoint_request, new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunities

ROOT = Path(__file__).resolve().parents[1]
AREA = ROOT / "development/investigation_loop"
PACKAGE = AREA / "preparation-001"
SPEC = AREA / "SPEC.md"
ACTOR = dict(reference.ACTOR)
INPUT_CEILING = ACTOR["context"] - ACTOR["generation_reserve"]
CALL_LIMIT = 20
SEEDS = (104729, 130363)
base, cont, require = reference.base, reference.cont, reference.require
TARGET = "src/addressable_information_layer/patching.py"
BAD = "    new_map = address_map\n"
GOOD = "    new_map = build_address_map(new_artifact)\n"
WRONG = "    new_map = build_address_map(artifact)\n"


def schedule():
    return [{"id": f"L{index:02d}", "seed": seed, "call_limit": CALL_LIMIT}
            for index, seed in enumerate(SEEDS, 1)]


def source_identities():
    names = ("prepare_investigation_loop.py", "run_investigation_loop.py", "prepare_interface_comparison.py",
             "prepare_interface_wording.py", "prepare_interface_design.py", "run_interface_consultation.py",
             "run_interface_follow_on.py", "continue_interface_follow_on.py", "run_interface_comparison.py")
    paths = [*sorted((ROOT / "src").rglob("*.py")), *(ROOT / "scripts" / name for name in names),
             ROOT / "tests/test_investigation_loop.py",
             ROOT / "maintenance/result_return_boundaries/RETURN_CONTRACT.md"]
    return {p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}


def fixture(candidate, task, checker):
    return EcologicalFixture("LOOP-TASK", "ordinary_loop_development", task, candidate, checker,
                             b"", (), (), {"development_only": True}, ())


def constructed_fixture():
    candidate = admitted_donor_candidate(ROOT / "experiments/020_owner_controlled_ecological_pilot_v2/fresh_bank")
    files = candidate.file_map
    require(files[TARGET].count(GOOD.encode()) == 1, "fixture injection target differs")
    files[TARGET] = files[TARGET].replace(GOOD.encode(), BAD.encode())
    result = fixture(Candidate.create(files), (AREA / "TASK.txt").read_text(encoding="utf-8"),
                     (AREA / "PUBLIC_CHECK.py").read_bytes())
    previous = load_json_strict((AREA / "OFFLINE_FEASIBILITY.json").read_bytes())
    require(result.initial.candidate_id == previous["initial_candidate_id"], "offline source binding differs")
    require(sha256_bytes(result.public_checker) == previous["public_check_sha256"], "public check differs")
    require(sha256_bytes(result.task.encode()) == previous["task_sha256"], "task differs")
    return result


def load_fixture(folder):
    value = load_json_strict((folder / "candidate.json").read_bytes())
    candidate = Candidate.create({row["path"]: row["content_utf8"].encode() for row in value["files"]})
    require(reference.candidate_bytes(candidate) == (folder / "candidate.json").read_bytes(), "candidate artifact differs")
    return fixture(candidate, (folder / "TASK.txt").read_text(encoding="utf-8"), (folder / "PUBLIC_CHECK.py").read_bytes())


def tool_reference(grammar, *, candidate: Candidate | None = None):
    # Keep the schema-generated requirements. Replace only the obsolete effects
    # with facts earned by the return repair, then include the reviewed addendum.
    text = reference.tool_reference(grammar)
    replacements = {
        "p0_page": reference.EFFECTS["p0_page"] + " Directory counts do not render signatures. A file outline rejects a signature above 240 UTF-8 bytes or unparseable Python; exact source remains accessible through read. These errors return a normal tool rejection.",
        "read": "Returns exact current source from start_line (one-based), as the largest whole-line page fitting 18,000 content bytes, 22,000 complete-result JSON bytes AND 22,000 bytes for its exact saved-result wrapper. Escaping can shorten the page. Includes candidate_id, file_sha256, returned interval and next_start_line; no line_count argument. complete means no later page, not that earlier lines were read. Empty reads beyond EOF add no coverage. Validates the complete return before recording acquisition. Does not edit or check the candidate.",
        "check": "Runs a NEW check on the current candidate; expected_candidate_id must match it. Only public is available in this continuation stage. Returns checked_candidate_id, check_id, passed, returncode, stdout and stderr, with full-stream byte counts/hashes and streams_truncated; each displayed stream is limited to 8,192 bytes and execution has a 30-second timeout. Updates the public-check flag only after complete-result admission. The checker may have executed when its oversized return is rejected; that rejection is not a newly accepted check observation. accepted=true with passed=false is an executed failing check.",
    }
    for name, effect in replacements.items():
        require(text.count(reference.EFFECTS[name]) == 1, "reference effect needs review")
        text = text.replace(reference.EFFECTS[name], effect, 1)
    common = (
        "Every newly saved original result must also fit its complete exact historical-access wrapper within 22,000 JSON bytes. "
        "The host validates complete returns before committing acquisition, mutation or terminal state. "
        "A rejected read or edit is not credited as successful. Stored originals are never silently truncated to fit retrieval; "
        "repeated accesses retain their canonical source. Imported historical bodies must fit their retrieval wrappers. "
        "Recorded reads describe acquisition of the indicated source version; after an edit they do not establish inspection of changed successor content. "
        "An unchanged file can remain applicable across a candidate change.\n"
    )
    text = text.replace(reference.INTRO.rstrip(), reference.INTRO.rstrip() + "\n\n" + common, 1)
    if candidate is not None:
        original = f"at most {MAX_FILE_BYTES:,} bytes\nper file"
        require(text.count(original) == 1, "reference file limit needs review")
        text = text.replace(original, f"at most {candidate.max_file_bytes:,} bytes\nper file", 1)
    return text


def request_for(value, seed, visible_reference):
    require(seed in SEEDS, "seed outside pilot")
    used = len(value.pairs)
    require(used < CALL_LIMIT and not value.state.submitted, "terminal path has no next request")
    state = load_json_strict(build_request(value.fixture, candidate=value.state.candidate, pairs=value.pairs,
                                         externalized_payload_count=0, calls_used=used, fork_binding=None))
    require(state["resource_state"].pop(wording.RESOURCE_KEY) == wording.RESOURCE_EXAMPLE, "resource wording changed")
    state["resource_state"].update(call_limit=CALL_LIMIT, calls_remaining=CALL_LIMIT-used, reasoning_budget_tokens=-1)
    value.request = canonical_json_bytes(state)
    request = endpoint_request(value, seed=42, mode="action")
    request["model"], request["seed"] = base.ALIAS, seed
    system = request["messages"][0]["content"]
    require(system.count(wording.OLD_NAVIGATION) == 1, "navigation source changed")
    request["messages"][0]["content"] = system.replace(wording.OLD_NAVIGATION, wording.NEW_NAVIGATION) + "\n\n" + visible_reference
    return request


def grammar_for(value):
    return endpoint_request(value, seed=42, mode="action")["response_format"]


def qualification_paths(selected_fixture):
    """Oracle histories only; none of these actions enters a live initial state."""
    direct = load_json_strict((AREA / "OFFLINE_FEASIBILITY.json").read_bytes())["transcript"]
    for kind in ("direct", "focused_correction", "explore_and_correct"):
        value = new_state(kind, selected_fixture)
        snapshots = []

        def act(action):
            request = request_for(value, SEEDS[0], tool_reference(grammar_for(value)))
            result = value.execute(action)
            require(result.get("accepted") is True, "oracle tool rejected: " + str(result))
            snapshots.append({"before_request": request, "action": action, "result": result,
                              "candidate_after": value.state.candidate.candidate_id})
            return result

        def check():
            return act({"action":"check", "check_id":"public", "expected_candidate_id":value.state.candidate.candidate_id})

        def read(name):
            path = "src/addressable_information_layer/" + name
            start = 1
            while start is not None:
                start = act({"action":"read", "path":path, "start_line":start})["next_start_line"]

        def patch(old, new):
            return act({"action":"patch", "path":TARGET, "old":old, "new":new,
                        "expected_candidate_id":value.state.candidate.candidate_id,
                        "expected_file_sha256":value.state.candidate.file_sha256(TARGET)})

        if kind == "direct":
            for row in direct:
                require(act(row["action"]) == row["result"], "known offline path differs")
        else:
            for path in ("src", "src/addressable_information_layer"):
                act({"action":"p0_page", "path":path, "offset":0})
            act({"action":"search", "path":".", "query":"materialize_reopen", "offset":0, "limit":16})
            read("reopen.py")
            act({"action":"p0_page", "path":TARGET, "offset":0})
            read("patching.py")
            act({"action":"p0_page", "path":"src/addressable_information_layer/artifact_units.py", "offset":0})
            read("artifact_units.py")
            read("content_log.py")
            act({"action":"search", "path":"src", "query":"class AddressMap", "offset":0, "limit":16})
            if kind == "explore_and_correct":
                read("records.py")
            require(not check()["passed"], "broken candidate unexpectedly passes")
            patch(BAD, WRONG)
            require(not check()["passed"], "planned incorrect edit did not fail")
            read("patching.py")
            patch(WRONG, GOOD)
            require(check()["passed"], "corrected candidate fails")
            act({"action":"submit", "expected_candidate_id":value.state.candidate.candidate_id})
        require(value.state.submitted and value.state.public_check_passed, "oracle path did not close")
        yield kind, snapshots, check_opportunities(value.pairs, call_limit=CALL_LIMIT)


class PilotLog(RecordLog):
    def append(self, record_type, payload, artifacts):
        if record_type == "runtime_prepared":
            payload = {**payload, "original_helper_actor":payload["actor"], "actor":ACTOR, "memory_policy":cont.POLICY}
        return super().append(record_type, payload, artifacts)


def health(output):
    return {"memory":cont.monitoring(output / "memory.csv"),
            "effective_runtime":cont.healthy_runtime(output / "private-runtime/server.stderr.log")}


def render_only(url, request, post=base.post):
    template = post(url, "/apply-template", canonical_json_bytes(request), 60)
    rendered = load_json_strict(template)["prompt"].encode("utf-8")
    tokenized = post(url, "/tokenize", canonical_json_bytes({"content":rendered.decode(), "add_special":False}), 60)
    count = len(load_json_strict(tokenized)["tokens"])
    require(count > 0, "empty native input")
    return template, rendered, tokenized, count


def prepare(args):
    selected = constructed_fixture()
    paths = list(qualification_paths(selected))
    sources = source_identities()
    args.output.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(args.output)
    log = PilotLog(args.output / "records.jsonl", "investigation-loop-preparation-001")
    value = new_state("initial", selected)
    grammar = grammar_for(value)
    visible_reference = tool_reference(grammar)
    artifacts = [store.put(name, raw) for name, raw in (
        ("SPEC.md", SPEC.read_bytes()), ("candidate.json", reference.candidate_bytes(selected.initial)),
        ("TASK.txt", selected.task.encode()), ("PUBLIC_CHECK.py", selected.public_checker),
        ("TOOL_REFERENCE.txt", visible_reference.encode()), ("RESPONSE_FORMAT.json", canonical_json_bytes(grammar)))]
    log.append("preparation_started", {"source_sha256":sources,"actor":ACTOR,"schedule":schedule(),
        "completion_calls":0,"maximum_proposed_calls":CALL_LIMIT*len(SEEDS)}, artifacts)
    rows, qualifications, failure = [], [], None
    try:
        with base.owned_runtime(args, store, log) as url:
            def save_input(stem, request):
                health(args.output)
                template, rendered, tokenized, count = render_only(url, request)
                artifacts = [store.put(stem+suffix, raw) for suffix, raw in (
                    ("-request.json",canonical_json_bytes(request)),("-rendered-prompt.txt",rendered),
                    ("-template-response.json",template),("-tokenization.json",tokenized))]
                row = {"stem":stem,"prompt_tokens":count,"would_admit":count<=INPUT_CEILING,
                       "physical_generation_space":ACTOR["context"]-count,"rendered_sha256":sha256_bytes(rendered)}
                log.append("input_prepared", {**row,"completion_sent":False,"routes":["/apply-template","/tokenize"]}, artifacts)
                return row
            for run in schedule():
                row = save_input("initial/"+run["id"], request_for(new_state(run["id"], selected), run["seed"], visible_reference))
                require(row["would_admit"], "initial native input cannot fit")
                rows.append({**run, **row})
            for name, snapshots, opportunities in paths:
                inputs = []
                for index, snapshot in enumerate(snapshots, 1):
                    stem = f"qualification/{name}/{index:03d}"
                    inputs.append(save_input(stem, snapshot["before_request"]))
                    log.append("oracle_action", {"path":name,"sequence":index,"model_actor":False},
                               [store.put(stem+"-oracle.json",canonical_json_bytes({k:v for k,v in snapshot.items() if k != "before_request"}))])
                qualifications.append({"path":name,"required_to_fit":name != "explore_and_correct",
                    "scripted_actions":len(snapshots),"calls_remaining":CALL_LIMIT-len(snapshots),
                    "check_opportunities":opportunities,"inputs":inputs,"all_inputs_admitted":all(r["would_admit"] for r in inputs)})
            require(all(q["all_inputs_admitted"] for q in qualifications if q["required_to_fit"]), "a required qualification path exceeded the native admission ceiling")
            require(any(not q["all_inputs_admitted"] for q in qualifications if not q["required_to_fit"]), "planned capacity-denial example did not exceed the ceiling")
            require(source_identities() == sources, "source changed during preparation")
            health(args.output)
        closed = verify_records(args.output / "records.jsonl", args.output)[-1]
        require(closed["record_type"] == "runtime_closed" and closed["payload"]["owned_server_shutdown_verified"]
                and closed["payload"]["dedicated_port_free"], "preparation runtime lifecycle incomplete")
        manifest = {"schema":"ordinary-investigation-loop-preparation-v1","actor":ACTOR,"memory_policy":cont.POLICY,
                    "source_sha256":sources,"input_ceiling":INPUT_CEILING,"call_limit":CALL_LIMIT,"schedule":rows,
                    "maximum_completion_calls":CALL_LIMIT*len(SEEDS),"completion_calls":0,"execution_authorized":False,
                    "history_policy":"all ordered events resident; private thinking omitted; no externalization",
                    "qualification_paths":qualifications,"files":[r for r in base.file_inventory(args.output) if r["path"] != "records.jsonl"]}
        store.put("PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
        log.append("preparation_completed", {"completion_calls":0,"initial_inputs":len(rows),"qualification_paths":len(qualifications)}, [])
    except BaseException as error:
        failure = error
        log.append("preparation_stopped", {"error_type":type(error).__name__,"error":str(error),"completion_calls":0}, [])
    records = verify_records(args.output / "records.jsonl", args.output)
    files = base.file_inventory(args.output)
    seal = {"disposition":"stopped_without_completion" if failure else "prepared_without_completion",
            "completion_calls":0,"files":files,"aggregate_sha256":sha256_bytes(canonical_json_bytes(files)),
            "record_count":len(records),"memory":base.memory_stats(args.output / "memory.csv"),
            "effective_runtime":base.runtime_evidence(args.output / "private-runtime/server.stderr.log"),
            "private_runtime_files_local_only":{p.name:sha256_file(p) for p in (args.output / "private-runtime").glob("*") if p.is_file()}}
    base.write_json(args.output / "PREPARATION_SEAL.json", seal)
    if failure:
        raise failure
    print({"prepared_initial_inputs":len(rows),"qualification_actions":[len(p[1]) for p in paths],
           "peak_input_tokens":max(r["prompt_tokens"] for q in qualifications for r in q["inputs"]),"completion_calls":0})
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",type=Path,required=True)
    parser.add_argument("--server",type=Path,required=True)
    parser.add_argument("--output",type=Path,default=PACKAGE)
    prepare(parser.parse_args())


if __name__ == "__main__":
    main()
