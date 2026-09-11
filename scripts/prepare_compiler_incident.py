"""Offline compiler-incident qualification; no model-completion endpoint."""
from __future__ import annotations

import argparse
import ast
import copy
import subprocess
import sys
import tempfile
from pathlib import Path

import prepare_incident_pressure as prior
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.ecological_pilot_v2 import EcologicalFixture
from working_set_exp.event_frame_v3 import resident_pair_v3
from working_set_exp.interface_consultation import new_state
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunities

ROOT = prior.ROOT
AREA = ROOT / "development/compiler_incident"
TARGET = "compiler/unary.py"
REPORT = "reports/incident.json"
BAD = "        if isinstance(node.op, (ast.UAdd, ast.USub)):\n"
PARTIAL = "        if isinstance(node.op, ast.UAdd):\n"
GOOD = "        if isinstance(node.op, ast.UAdd) and isinstance(node.operand, ast.Constant) and type(node.operand.value) in (int, float):\n"
ROUTES = ("schema_informed_minimum", "evidence_first", "source_first", "report_incremental", "check_first", "correction")
require = prior.require


def candidate_files():
    # The preliminary subprocess wrote bytecode after its candidate snapshot.
    # Bytecode and incidental files cannot enter a future authored candidate.
    files = [p for p in (AREA / "source").rglob("*")
             if p.is_file() and "__pycache__" not in p.parts and p.suffix in {".py", ".md", ".json"}]
    require(len(files) == 6, "candidate text inventory changed")
    return sorted(files)


def capture_records(source=None, *, candidate=None):
    with tempfile.TemporaryDirectory(prefix="compiler-capture-") as folder:
        files = candidate.files if candidate is not None else [
            (path.relative_to(AREA / "source").as_posix(), path.read_bytes()) for path in candidate_files()]
        for name, raw in files:
            destination = Path(folder) / name
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(raw)
        completed = subprocess.run([sys.executable, "-I", "-S", "-B", "-c",
            "import runpy,sys;sys.path.insert(0,'.');runpy.run_path(" + repr(str(AREA / "CAPTURE.py")) + ",run_name='__main__')"],
            input=(AREA / "donor/calculation.py").read_bytes() if source is None else source,
            cwd=folder, capture_output=True, timeout=30)
    require(completed.returncode == 0, "capture failed: " + completed.stderr.decode(errors="replace"))
    return load_json_strict(completed.stdout)


def decode_dump(text):
    """Decode our captured ast.dump notation without evaluating Python code."""
    def decode(node):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            cls = getattr(ast, node.func.id, None)
            require(isinstance(cls, type) and issubclass(cls, ast.AST) and not node.args, "non-AST constructor")
            require(all(k.arg in cls._fields for k in node.keywords), "unexpected AST field")
            require(len({k.arg for k in node.keywords}) == len(node.keywords), "duplicate AST field")
            return cls(**{k.arg: decode(k.value) for k in node.keywords})
        if isinstance(node, ast.List):
            return [decode(item) for item in node.elts]
        if isinstance(node, ast.Tuple):
            return tuple(decode(item) for item in node.elts)
        # ast.literal_eval accepts constants and signed numeric literals only
        # here; calls, attributes and comprehensions cannot execute.
        return ast.literal_eval(node)
    result = decode(ast.parse(text, mode="eval").body)
    require(isinstance(result, ast.Module) and ast.dump(result) == text, "AST dump round trip differs")
    return result


def first_expression_change(before, after):
    if isinstance(before, ast.expr) and isinstance(after, ast.expr) and type(before) is not type(after):
        return dict(before=ast.unparse(before), after=ast.unparse(after))
    if isinstance(before, ast.AST) and type(before) is type(after):
        for field in before._fields:
            found = first_expression_change(getattr(before, field, None), getattr(after, field, None))
            if found:
                return found
    elif isinstance(before, list) and isinstance(after, list):
        require(len(before) == len(after), "capture changed list cardinality; review comparison definition")
        for left, right in zip(before, after):
            found = first_expression_change(left, right)
            if found:
                return found
    return None


def expected_report(records):
    original = decode_dump(records[0]["ast_dump"])
    originals = [node for node in original.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))]
    rows = []
    for number, record in enumerate(records[1:], 2):
        emitted = decode_dump(record["ast_dump"])
        by_name = {node.name: node for node in emitted.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))}
        changed = [node for node in originals if ast.dump(node) != ast.dump(by_name[node.name])]
        require(changed, "expected a changed captured build")
        first = next(({"function": node.name, **found} for node in changed
                      if (found := first_expression_change(node, by_name[node.name]))), None)
        require(first is not None, "no changed expression in capture")
        rows.append(dict(capture=f"OBS-{number:04d}", changed_functions=[node.name for node in changed], first_change=first))
    return {"builds": rows}


def constructed_fixture(records=None):
    records = capture_records() if records is None else records
    candidate = Candidate.create({p.relative_to(AREA / "source").as_posix(): p.read_bytes() for p in candidate_files()})
    bodies = tuple((f"OBS-{number:04d}", canonical_json_bytes(record)) for number, record in enumerate(records, 1))
    labels = ("input calculation module", "BUILD-A emitted module", "BUILD-B emitted module")
    observations = tuple(dict(handle=handle, sequence=i, action="capture", target=label,
                              candidate_id=candidate.candidate_id, size_bytes=len(raw), sha256=sha256_bytes(raw))
                         for i, ((handle, raw), label) in enumerate(zip(bodies, labels), 1))
    report = expected_report(records)
    checker = ("import json\nEXPECTED_REPORT=json.loads(" + repr(canonical_json_bytes(report).decode()) + ")\n").encode()
    checker += (AREA / "PUBLIC_CHECK.py").read_bytes()
    return EcologicalFixture("COMPILER-INCIDENT", "captured_compiler_investigation", (AREA / "TASK.txt").read_text(encoding="utf-8"),
                             candidate, checker, b"", observations, bodies,
                             {"authored_compiler_fault": True, "upstream_calculation_not_faulty": True}, ())


def patch_action(value, path, old, new):
    return dict(action="patch", path=path, old=old, new=new,
                expected_candidate_id=value.state.candidate.candidate_id,
                expected_file_sha256=value.state.candidate.file_sha256(path))


def report_text(report):
    return canonical_json_bytes(report).decode() + "\n"


def qualification_actions(fixture, kind):
    """Generate a short scripted path through actual tools, not an actor trace."""
    require(kind in ROUTES, "unknown qualification path")
    value = new_state(kind, fixture)
    reference = prior.pilot.tool_reference(prior.pilot.grammar_for(value))
    report = expected_report([load_json_strict(raw) for _, raw in fixture.observation_bodies])
    snapshots = []

    def act(action):
        before = prior.request_for(value, reference)
        result = value.execute(action)
        require(result.get("accepted") is True, "qualification action rejected: " + str(result))
        snapshots.append(dict(before_request=before, action=action, result=result,
                              candidate_after=value.state.candidate.candidate_id))
        return result

    def read(path):
        result = act(dict(action="read", path=path, start_line=1))
        require(result["next_start_line"] is None, "unexpected multipage candidate file")

    def check(passed):
        result = act(dict(action="check", check_id="public", expected_candidate_id=value.state.candidate.candidate_id))
        require(result["passed"] is passed, "wrong behavioral qualification outcome")

    def write_report(rows):
        old = value.state.candidate.file_map[REPORT].decode("utf-8")
        act(patch_action(value, REPORT, old, report_text({"builds": rows})))

    if kind == "check_first":
        check(False)
    if kind != "schema_informed_minimum":
        read("README.md")
    if kind in {"schema_informed_minimum", "source_first", "check_first"}:
        if kind == "source_first":
            act(dict(action="p0_page", path="compiler", offset=0))
            read("compiler/api.py")
            read("compiler/selection.py")
        read(TARGET)
        if kind != "schema_informed_minimum":
            act(patch_action(value, TARGET, BAD, GOOD))
        read(REPORT)
    if kind == "report_incremental":
        read(REPORT)
    for number, (handle, _) in enumerate(fixture.observation_bodies):
        act(dict(action="reopen_observation", handle=handle))
        if kind == "report_incremental" and number > 0:
            write_report(report["builds"][:number])
    if kind in {"evidence_first", "correction", "report_incremental"}:
        read(TARGET)
        if kind != "report_incremental":
            read(REPORT)
    if kind not in {"source_first", "check_first"}:
        act(patch_action(value, TARGET, BAD, PARTIAL if kind == "correction" else GOOD))
    if kind != "report_incremental":
        write_report(report["builds"])
    if kind == "correction":
        check(False)
        act(patch_action(value, TARGET, PARTIAL, GOOD))
    check(True)
    act(dict(action="submit", expected_candidate_id=value.state.candidate.candidate_id))
    return value, snapshots


def repaired_candidate(fixture, *, replacement=GOOD, report=None):
    candidate = fixture.initial
    if replacement is not None:
        candidate, _ = candidate.patch(path=TARGET, old=BAD, new=replacement,
            expected_candidate_id=candidate.candidate_id, expected_file_sha256=candidate.file_sha256(TARGET))
    if report is not None:
        candidate, _ = candidate.patch(path=REPORT, old=candidate.file_map[REPORT].decode("utf-8"), new=report_text(report),
            expected_candidate_id=candidate.candidate_id, expected_file_sha256=candidate.file_sha256(REPORT))
    return candidate


def behavior_matrix(fixture):
    report = expected_report([load_json_strict(raw) for _, raw in fixture.observation_bodies])
    bad_report = copy.deepcopy(report)
    bad_report["builds"][1]["changed_functions"] = ["weibullvariate"]
    variants = (("original", None, None, False), ("repair_only", GOOD, None, False),
                ("report_only", None, report, False), ("incomplete_repair", PARTIAL, report, False),
                ("disabled_optimization", "        if False:\n", report, False),
                ("wrong_scope_report", GOOD, bad_report, False), ("complete", GOOD, report, True))
    rows = []
    for name, replacement, work, passed in variants:
        candidate = repaired_candidate(fixture, replacement=replacement, report=work)
        result = run_checker(candidate, fixture.public_checker)
        require(result["stdout"].rstrip().endswith("/26 contract cases passed"), "checker did not finish: " + str(result))
        require(not result["streams_truncated"] and result["passed"] is passed, "behavior matrix differs: " + name)
        rows.append(dict(variant=name, candidate_id=candidate.candidate_id, result=result))
    return rows


def counterfactual_checks(records):
    # The original cannot be reconstructed uniquely by combining the two lossy
    # emitted trees: an original plus around the negative call disappears in both.
    donor = (AREA / "donor/calculation.py").read_bytes()
    require(donor.count(b"sqrt(-log(r))") == 1, "counterfactual anchor changed")
    other_original = capture_records(donor.replace(b"sqrt(-log(r))", b"sqrt(+-log(r))"))
    require(other_original[1:] == records[1:], "lossy emissions unexpectedly identify original expression")
    require(other_original[0]["reference_calls"] == records[0]["reference_calls"], "original behavior changed")
    require(expected_report(other_original) != expected_report(records), "original report did not differ")
    # A second possible build B selects only Weibull. Its complex symptom is the
    # same, but inverse-normal was not transformed. Original and A alone cannot
    # establish B's observed function scope. This is evaluator-only ablation.
    other_b = copy.deepcopy(records)
    original = decode_dump(records[0]["ast_dump"])
    emitted = decode_dump(records[2]["ast_dump"])
    originals = {node.name: node for node in original.body if isinstance(node, ast.FunctionDef)}
    emitted.body = [copy.deepcopy(originals[node.name]) if isinstance(node, ast.FunctionDef)
                    and node.name == "_normal_dist_inv_cdf" else node for node in emitted.body]
    other_b[2]["ast_dump"] = ast.dump(emitted)
    other_b[2]["compile_request"]["functions"] = ["weibullvariate"]
    require(expected_report(other_b)["builds"][1]["changed_functions"] == ["weibullvariate"], "B ablation failed")
    # A may select both without changing its invoked arithmetic-error symptom.
    other_a = copy.deepcopy(records)
    other_a[1]["ast_dump"] = records[2]["ast_dump"]
    other_a[1]["compile_request"]["functions"] = records[2]["compile_request"]["functions"]
    require(expected_report(other_a)["builds"][0]["changed_functions"] !=
            expected_report(records)["builds"][0]["changed_functions"], "A ablation failed")
    # Execute the alternative selection against this actual candidate too, so
    # the spliced B tree above is not accepted solely on a hand-built expectation.
    probe = ("import ast,hashlib\nfrom compiler.api import optimize\nsource=" + repr(donor.decode()) +
             "\nprint(hashlib.sha256(ast.dump(optimize(source,['weibullvariate'])).encode()).hexdigest())\n").encode()
    scope_execution = run_checker(constructed_fixture(records).initial, probe)
    require(scope_execution["passed"] and not scope_execution["streams_truncated"] and
            scope_execution["stdout"].strip() == sha256_bytes(other_b[2]["ast_dump"].encode()), "alternative build scope not reproduced")
    return {"original_not_reconstructible_from_emissions": True, "same_original_reference_calls": True,
            "original_variant_records": other_original, "build_a_variant_records": other_a,
            "build_b_variant_records": other_b, "reports": [expected_report(x) for x in (records, other_original, other_a, other_b)],
            "alternative_build_b_execution": scope_execution,
            "scope": "report facts depend on captures; optimizer repair alone remains source-led"}


def repaired_capture_probe(fixture, records):
    candidate = repaired_candidate(fixture, report=expected_report(records))
    repaired = capture_records(candidate=candidate)
    require(repaired[0] == records[0], "reference input changed in repair probe")
    for record in repaired[1:]:
        require(record["ast_dump"] == records[0]["ast_dump"], "repair changed this donor's calculation tree")
        require(record["observed_call"] == records[0]["reference_calls"][record["called_function"]],
                "repair did not restore captured call behavior")
    return dict(candidate_id=candidate.candidate_id, repaired_records=repaired,
                trees_equal_original=True, calls_equal_original=True, separate_from_public_score=True)


def exact_clone(value):
    cloned = copy.deepcopy(value)
    require(cloned.state == value.state and cloned.pairs == value.pairs, "fork changed execution state")
    require(cloned.executor.state is cloned.state, "executor did not follow cloned state")
    require(cloned.event_payloads == value.event_payloads and cloned.result_payloads == value.result_payloads,
            "fork changed recovery maps")
    require(cloned.executor.event_reopenable is cloned.event_payloads and
            cloned.executor.result_reopenable is cloned.result_payloads, "executor recovery maps not cloned together")
    return cloned


def source_identities():
    files = [Path(__file__).resolve(), ROOT / "scripts/prepare_incident_pressure.py", ROOT / "scripts/prepare_episode_framing.py",
             AREA / "SPEC.md", AREA / "TASK.txt",
             AREA / "PUBLIC_CHECK.py", AREA / "CAPTURE.py", ROOT / "tests/test_compiler_incident.py",
             *candidate_files(), *sorted((AREA / "donor").glob("*"))]
    return {**prior.pilot.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in files if p.is_file()}}


def original_visible(request, handle, fixture):
    state = load_json_strict(request["messages"][1]["content"].encode())
    raw = dict(fixture.observation_bodies)[handle].decode()
    for event in state["active_phase_event_frame"]["events"]:
        if any(event[field]["present"] and event[field]["residency"] != "resident"
               for field in ("action_payload", "result_body")):
            continue
        pair = resident_pair_v3(event)
        if pair and pair["result"].get("exact_result_utf8") == raw:
            return True
    return False


def external_continuation(fixture, snapshots, resident_rows, save, record):
    """Offline incremental-report path, forked only at its measured boundary.

    The optional original retrieval here is a declared oracle action for checking
    the return path. It is never a semantic action-selection rule for a model.
    """
    boundary = next((i for i, row in enumerate(resident_rows) if not row["fits_working_set"]), None)
    if boundary is None:
        return {"natural_boundary": False, "qualified": False}
    common = new_state("common-prefix", fixture)
    for snapshot in snapshots[:boundary]:
        require(common.execute(snapshot["action"]) == snapshot["result"], "common-prefix replay differs")
    reference = prior.pilot.tool_reference(prior.pilot.grammar_for(common))
    cloned = exact_clone(common)
    require(prior.request_for(common, reference) == prior.request_for(cloned, reference) ==
            snapshots[boundary]["before_request"], "pre-residency fork requests differ")
    record("fork", {"prefix_actions": boundary, "candidate_id": common.state.candidate.candidate_id,
                    "same_full_request": True, "same_session_state": True, "same_recovery_maps": True})
    externalized = 0
    inputs, recovery = [], []
    recovered_original = False

    def admit():
        nonlocal externalized
        trial = 0
        def count(request):
            nonlocal trial
            row = save(f"external/after-{len(cloned.pairs):03d}-trial-{trial:03d}", request)
            trial += 1
            inputs.append(row)
            return row["prompt_tokens"]
        selected = prior.choose_externalization(cloned, reference, count, previous=externalized)
        require(selected is not None, "externalized state cannot fit; preserve this preparation stop")
        externalized = selected["externalized"]
        return selected["request"]

    for snapshot in snapshots[boundary:]:
        before = admit()
        action = snapshot["action"]
        # The first build's comparison is already in the actual partial report.
        # For the second report edit, qualify recovering the absent original
        # while retaining the captured B tree. No hidden synthesis is returned.
        if (action["action"] == "patch" and action["path"] == REPORT and "OBS-0003" in action["new"]
                and not original_visible(before, "OBS-0001", fixture) and not recovered_original):
            pre_state = copy.deepcopy(cloned.state)
            maps = copy.deepcopy((cloned.result_payloads, cloned.event_payloads))
            result = cloned.execute(dict(action="reopen_observation", handle="OBS-0001"))
            require(result["accepted"] and result["exact_result_utf8"].encode() == dict(fixture.observation_bodies)["OBS-0001"],
                    "exact original retrieval differs")
            require(cloned.state == pre_state and (cloned.result_payloads, cloned.event_payloads) == maps,
                    "observation retrieval changed candidate/check or canonical originals")
            record("recovery-action", {"action": cloned.pairs[-1]["response"], "result": result,
                                       "candidate_unchanged": True, "canonical_maps_unchanged": True})
            after = admit()
            require(original_visible(after, "OBS-0001", fixture), "recovered original absent from next prepared input")
            require(original_visible(after, "OBS-0003", fixture), "build B unavailable for recovered comparison")
            recovery.append(dict(handle="OBS-0001", saved_bytes=len(result["exact_result_utf8"].encode()),
                                 returned_bytes=len(canonical_json_bytes(result)), next_input_contains_original_and_b=True))
            recovered_original, before = True, after
        require(len(cloned.pairs) < prior.CALL_LIMIT, "external path consumed the frozen allowance")
        result = cloned.execute(action)
        require(result == snapshot["result"], "continued action changed tool outcome")
        record(f"action-{len(cloned.pairs):03d}", {"action": action, "result": result,
            "externalized_through": externalized,
            "visible_observations_before": [h for h, _ in fixture.observation_bodies if original_visible(before, h, fixture)]})
    require(cloned.state.submitted and cloned.state.public_check_passed, "external path did not finish checked")
    return dict(natural_boundary=True, prefix_actions=boundary, qualified=True, total_actions=len(cloned.pairs),
                recovery=recovery, inputs=inputs, maximum_admitted_input=max(r["prompt_tokens"] for r in inputs if r["fits_working_set"]),
                final_candidate_id=cloned.state.candidate.candidate_id,
                check_opportunities=check_opportunities(cloned.pairs, call_limit=prior.CALL_LIMIT))


def prepare(args):
    # Finish all non-model task construction first. Failed checks must be
    # completed behavioral tests, not setup failures accepted as negative cases.
    records = capture_records()
    fixture = constructed_fixture(records)
    matrix, counterfactual = behavior_matrix(fixture), counterfactual_checks(records)
    repaired_captures = repaired_capture_probe(fixture, records)
    routes = [(kind, *qualification_actions(fixture, kind)) for kind in ROUTES]
    sources = source_identities()
    args.output.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(args.output)
    log = prior.pilot.PilotLog(args.output / "records.jsonl", "compiler-incident-preparation")
    artifacts = [store.put("SPEC.md", (AREA / "SPEC.md").read_bytes()),
                 store.put("candidate.json", prior.pilot.reference.candidate_bytes(fixture.initial)),
                 store.put("TASK.txt", fixture.task.encode()), store.put("PUBLIC_CHECK.py", fixture.public_checker),
                 store.put("captures.json", canonical_json_bytes(records)),
                 store.put("observations.json", canonical_json_bytes(list(fixture.observations))),
                 store.put("expected-report.json", canonical_json_bytes(expected_report(records))),
                 store.put("behavior-matrix.json", canonical_json_bytes(matrix)),
                 store.put("repaired-capture-probe.json", canonical_json_bytes(repaired_captures)),
                 store.put("counterfactuals.json", canonical_json_bytes(counterfactual))]
    log.append("preparation_started", dict(source_sha256=sources, actor=prior.ACTOR, completion_calls=0), artifacts)
    failure, qualifications, recovery_rows, external = None, [], [], None
    try:
        with prior.base.owned_runtime(args, store, log) as url:
            def save(stem, request):
                prior.pilot.health(args.output)
                template, native, tokens, count = prior.pilot.render_only(url, request)
                row = dict(stem=stem, prompt_tokens=count, fits_working_set=count <= prior.WORKING_SET,
                           fits_resident=count <= prior.RESIDENT_CEILING,
                           physical_generation_space=prior.ACTOR["context"]-count)
                log.append("input_prepared", {**row, "completion_sent": False}, [store.put(stem+suffix, raw) for suffix, raw in
                    (("-request.json", canonical_json_bytes(request)), ("-native.txt", native),
                     ("-template.json", template), ("-tokens.json", tokens))])
                return row

            for kind, value, snapshots in routes:
                rows = []
                for sequence, snapshot in enumerate(snapshots, 1):
                    stem = f"resident/{kind}/{sequence:03d}"
                    rows.append(save(stem, snapshot["before_request"]))
                    log.append("oracle_action", dict(route=kind, sequence=sequence, model_actor=False),
                        [store.put(stem+"-oracle.json", canonical_json_bytes({k:v for k,v in snapshot.items() if k != "before_request"}))])
                qualifications.append(dict(route=kind, actions=len(rows), maximum_input=max(row["prompt_tokens"] for row in rows),
                    crosses_working_set=any(not row["fits_working_set"] for row in rows),
                    all_fit_resident=all(row["fits_resident"] for row in rows),
                    first_over_limit_action=next((i for i,row in enumerate(rows,1) if not row["fits_working_set"]), None),
                    checked_submission=value.state.submitted and value.state.public_check_passed,
                    check_opportunities=check_opportunities(value.pairs, call_limit=prior.CALL_LIMIT), inputs=rows))
                if kind == "report_incremental":
                    def record(stem, payload):
                        log.append("external_oracle", {"stem": stem, "model_actor": False},
                            [store.put("external/"+stem+".json", canonical_json_bytes(payload))])
                    external = external_continuation(fixture, snapshots, rows, save, record)
                    forced, recovered = prior.recovery_probe(value)
                    recovery_rows = recovered
                    save("exact-recovery/pre-submit-external", forced)
                    log.append("exact_recovery_qualified", {"forced_offline_plumbing_only": True,
                        "terminal_history_removed_by_exact_replay": True},
                        [store.put("exact-recovery/records.json", canonical_json_bytes(recovered))])
            require(source_identities() == sources, "source changed during preparation")
            prior.pilot.health(args.output)
        closed = verify_records(args.output / "records.jsonl", args.output)[-1]
        require(closed["record_type"] == "runtime_closed" and closed["payload"]["owned_server_shutdown_verified"]
                and closed["payload"]["dedicated_port_free"], "runtime lifecycle not closed")
        geometry = all(row["crosses_working_set"] and row["all_fit_resident"] for row in qualifications)
        manifest = dict(schema="compiler-incident-offline-qualification-v1", source_sha256=sources, actor=prior.ACTOR,
            working_set=prior.WORKING_SET, resident_ceiling=prior.RESIDENT_CEILING,
            prospective_call_limit=prior.CALL_LIMIT, prospective_seeds=prior.SEEDS,
            completion_calls=0, execution_authorized=False, task_geometry_qualified=geometry,
            report_incident_dependent=True, repair_alone_source_led=True, qualifies_all_possible_actor_routes=False,
            qualification_paths=qualifications, external_continuation=external, exact_recovery=recovery_rows,
            files=[r for r in prior.base.file_inventory(args.output) if r["path"] != "records.jsonl"])
        store.put("PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
        log.append("preparation_completed", dict(completion_calls=0, task_geometry_qualified=geometry,
                    external_continuation_qualified=bool(external and external["qualified"]), execution_authorized=False), [])
    except BaseException as error:
        failure = error
        log.append("preparation_stopped", dict(error_type=type(error).__name__, error=str(error), completion_calls=0), [])
    saved = verify_records(args.output / "records.jsonl", args.output)
    files = prior.base.file_inventory(args.output)
    prior.base.write_json(args.output / "PREPARATION_SEAL.json", dict(
        disposition="stopped_without_completion" if failure else "qualified_without_completion",
        completion_calls=0, files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files)), record_count=len(saved),
        memory=prior.base.memory_stats(args.output / "memory.csv"),
        effective_runtime=prior.base.runtime_evidence(args.output / "private-runtime/server.stderr.log"),
        private_runtime_files_local_only={p.name:sha256_file(p) for p in (args.output / "private-runtime").glob("*") if p.is_file()}))
    if failure:
        raise failure
    print({"completion_calls":0, "routes":[(r["route"],r["maximum_input"]) for r in qualifications],
           "task_geometry_qualified":geometry, "external_actions":external.get("total_actions") if external else None})
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=AREA / "preparation-001")
    prepare(parser.parse_args())
