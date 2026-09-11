"""Qualify incident dependence and proposed working-set limits; no completions."""
from __future__ import annotations

import argparse
import copy
from pathlib import Path

import prepare_investigation_loop as pilot
from prepare_episode_framing import annotate
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.ecological_pilot_v2 import EcologicalFixture
from working_set_exp.interface_consultation import new_state
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunities

ROOT = pilot.ROOT
AREA = ROOT / "development/incident_pressure"
PACKAGE = AREA / "preparation-001"
WORKING_SET = 16_000
RESIDENT_CEILING = pilot.INPUT_CEILING
ACTOR = pilot.ACTOR
CALL_LIMIT = 32
SEEDS = (49979687, 67867967)
WORLDS = ("north-export", "south-export")
TARGET = "config/jobs.json"
CSV = "entry_id,amount\na,0.335\nb,0.335\nc,0.335\n"
base, require = pilot.base, pilot.require


def source_identities():
    files = [AREA / "SPEC.md", AREA / "TASK.txt", AREA / "PUBLIC_CHECK.py",
             *sorted(p for p in (AREA / "source").rglob("*") if p.is_file()),
             ROOT / "scripts/prepare_incident_pressure.py", ROOT / "scripts/prepare_episode_framing.py",
             ROOT / "tests/test_incident_pressure.py"]
    return {**pilot.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in files}}


def fragment(job, policy):
    return '"' + job + '": {"policy": "' + policy + '"}'


def constructed_fixture(world):
    require(world in WORLDS, "unknown counterfactual world")
    candidate = Candidate.create({p.relative_to(AREA / "source").as_posix(): p.read_bytes()
                                  for p in (AREA / "source").rglob("*") if p.is_file()})
    # Capture an actual execution of this checkout's fixture. These are authored
    # preparation worlds, not logs attributed to a production incident.
    probe = ("import json\nfrom posting.api import export\nprint(json.dumps(export("
             + repr(world) + "," + repr(CSV) + "), sort_keys=True))\n").encode()
    observed = run_checker(candidate, probe)
    require(observed["passed"] and not observed["streams_truncated"], "capture failed")
    trace = load_json_strict(observed["stdout"].encode())
    capture = dict(incident_id="INC-042", job_id=world, input_csv=CSV,
                   input_sha256=sha256_bytes(CSV.encode()), configuration_sha256=candidate.file_sha256(TARGET),
                   normalized_records=trace["records"], captured_execution=trace)
    negative = "entry_id,amount\na,-0.335\nb,-0.335\nc,-0.335\n"
    small = "entry_id,amount\na,0.004\nb,0.004\n"
    agreements = {"record_kind": "receiving-account agreements", "jobs": {}}
    for job in WORLDS:
        line = job == world
        agreements["jobs"][job] = {
            "calculation": ("Round each signed line to a minor unit before summing." if line
                            else "Sum signed exact amounts, then round the statement once."),
            "rounding": "nearest minor unit; exact halves away from zero",
            "examples": [dict(input_csv=text, expected_minor_units=amount) for text, amount in
                         ((CSV, 102 if line else 101), (negative, -102 if line else -101), (small, 0 if line else 1))],
        }
    bodies = (("OBS-0001", canonical_json_bytes(capture)), ("OBS-0002", canonical_json_bytes(agreements)))
    rows = tuple(dict(handle=handle, sequence=i, action="capture", target=target,
                      candidate_id=candidate.candidate_id, size_bytes=len(body), sha256=sha256_bytes(body))
                 for i, ((handle, body), target) in enumerate(zip(bodies, ("INC-042 export capture", "receiving-account agreements")), 1))
    checker = ("import json\nCAPTURE = json.loads(" + repr(bodies[0][1].decode())
               + ")\nAGREEMENTS = json.loads(" + repr(bodies[1][1].decode()) + ")\n").encode() + (AREA / "PUBLIC_CHECK.py").read_bytes()
    return EcologicalFixture("INCIDENT-POLICY", "incident_dependent_development", (AREA / "TASK.txt").read_text(encoding="utf-8"),
                             candidate, checker, b"", rows, bodies,
                             {"authored": True, "world": world, "production_incident": False}, ())


def request_for(value, reference, *, externalized=0, seed=SEEDS[0]):
    require(seed in SEEDS and 0 <= externalized <= len(value.pairs), "unprepared request parameters")
    used = len(value.pairs)
    require(used < CALL_LIMIT and not value.state.submitted, "terminal path has no next request")
    state = load_json_strict(pilot.build_request(value.fixture, candidate=value.state.candidate,
        pairs=value.pairs, externalized_payload_count=externalized, calls_used=used, fork_binding=None))
    require(state["resource_state"].pop(pilot.wording.RESOURCE_KEY) == pilot.wording.RESOURCE_EXAMPLE, "resource wording changed")
    state["resource_state"].update(call_limit=CALL_LIMIT, calls_remaining=CALL_LIMIT-used, reasoning_budget_tokens=-1)
    value.request = canonical_json_bytes(state)
    request = pilot.endpoint_request(value, seed=42, mode="action")
    request["model"], request["seed"] = base.ALIAS, seed
    system = request["messages"][0]["content"]
    require(system.count(pilot.wording.OLD_NAVIGATION) == 1, "navigation source changed")
    request["messages"][0]["content"] = system.replace(pilot.wording.OLD_NAVIGATION, pilot.wording.NEW_NAVIGATION) + "\n\n" + reference
    return annotate(request, report_precedes_session=True)


def choose_externalization(value, reference, count, *, previous=0):
    """Preparation-only admission probe. count renders the complete native input.

    All signals, task, source identity and schema stay intact. Existing V3 moves
    the oldest prefix of payloads. Failure is returned, never repaired by dropping
    further fields, changing the target or changing reasoning settings.
    """
    for externalized in range(previous, len(value.pairs) + 1):
        request = request_for(value, reference, externalized=externalized)
        tokens = count(request)
        if tokens <= WORKING_SET:
            return dict(externalized=externalized, prompt_tokens=tokens, request=request)
    return None


def patch(value, job, *, old="statement", new="line"):
    return dict(action="patch", path=TARGET, old=fragment(job, old), new=fragment(job, new),
                expected_candidate_id=value.state.candidate.candidate_id,
                expected_file_sha256=value.state.candidate.file_sha256(TARGET))


def qualification_path(fixture, kind):
    require(kind in {"check_shortcut", "observation_shortcut", "source_investigation"}, "unknown route")
    value, snapshots = new_state(kind, fixture), []
    reference = pilot.tool_reference(pilot.grammar_for(value))

    def act(action):
        before = request_for(value, reference)
        result = value.execute(action)
        require(result.get("accepted") is True, "qualification action rejected: " + str(result))
        snapshots.append(dict(before_request=before, action=action, result=result,
                              candidate_after=value.state.candidate.candidate_id))
        return result

    def read(path):
        next_line = 1
        while next_line is not None:
            next_line = act(dict(action="read", path=path, start_line=next_line))["next_start_line"]

    def check():
        return act(dict(action="check", check_id="public", expected_candidate_id=value.state.candidate.candidate_id))

    if kind == "check_shortcut":
        require(check()["passed"] is False, "baseline unexpectedly passes")
    if kind != "check_shortcut":
        act(dict(action="reopen_observation", handle="OBS-0001"))
        act(dict(action="reopen_observation", handle="OBS-0002"))
    read("README.md")
    if kind == "source_investigation":
        act(dict(action="p0_page", path="posting", offset=0))
        for name in ("api.py", "decode.py", "policies.py", "configuration.py"):
            read("posting/" + name)
        require(check()["passed"] is False, "baseline unexpectedly passes")
    act(dict(action="p0_page", path="config", offset=0))
    read(TARGET)
    act(patch(value, fixture.provenance["world"]))
    require(check()["passed"] is True, "repair does not satisfy agreements")
    act(dict(action="submit", expected_candidate_id=value.state.candidate.candidate_id))
    return value, snapshots, check_opportunities(value.pairs, call_limit=CALL_LIMIT)


def counterfactual_checks(fixtures):
    require(fixtures[0].initial == fixtures[1].initial and fixtures[0].task == fixtures[1].task,
            "worlds must share exact initial source and task")
    matrix = []
    for fixture in fixtures:
        for repaired_job in (None, *WORLDS, "both"):
            candidate = fixture.initial
            jobs = WORLDS if repaired_job == "both" else (() if repaired_job is None else (repaired_job,))
            for job in jobs:
                candidate, _ = candidate.patch(path=TARGET, old=fragment(job,"statement"), new=fragment(job,"line"),
                    expected_candidate_id=candidate.candidate_id, expected_file_sha256=candidate.file_sha256(TARGET))
            result = run_checker(candidate, fixture.public_checker)
            require(not result["streams_truncated"], "checker output is truncated")
            expected = repaired_job == fixture.provenance["world"]
            require(result["passed"] is expected, "counterfactual acceptance does not discriminate")
            matrix.append(dict(world=fixture.provenance["world"], repair=repaired_job,
                               candidate_id=candidate.candidate_id, result=result))
    return matrix


def recovery_probe(value):
    # Explicitly forced offline removal qualifies plumbing, never natural pressure.
    reference = pilot.tool_reference(pilot.grammar_for(value))
    clone = copy.deepcopy(value)
    clone.state.submitted = False
    clone.executor.state = clone.state
    external = request_for(clone, reference, externalized=len(clone.pairs))
    frame = load_json_strict(external["messages"][1]["content"].encode())["active_phase_event_frame"]
    require(all(e["result_body"]["residency"] in {"none", "external"} for e in frame["events"]), "payload removal failed")
    before = copy.deepcopy(clone.state)
    recovered = []
    for action, saved in (("reopen_observation", dict(value.fixture.observation_bodies)),
                          ("reopen_result", value.result_payloads), ("reopen_event", value.event_payloads)):
        for handle, raw in saved.items():
            result = clone.executor.execute(dict(action=action, handle=handle))
            require(result.get("accepted") is True, "historical access rejected")
            exact = canonical_json_bytes(result["action_payload"]) if action == "reopen_event" else result["exact_result_utf8"].encode()
            require(exact == raw and clone.state == before, "retrieval changed data or execution state")
            recovered.append(dict(action=action, handle=handle, saved_bytes=len(raw),
                                  returned_bytes=len(canonical_json_bytes(result)), sha256=sha256_bytes(raw)))
    return external, recovered


def prepare(args):
    fixtures = [constructed_fixture(world) for world in WORLDS]
    matrix = counterfactual_checks(fixtures)
    routes = [(fixture, kind, *qualification_path(fixture, kind)) for fixture in fixtures
              for kind in ("check_shortcut", "observation_shortcut", "source_investigation")]
    sources = source_identities()
    args.output.mkdir(parents=True, exist_ok=False)
    store, log = ArtifactStore(args.output), pilot.PilotLog(args.output / "records.jsonl", "incident-pressure-preparation-001")
    artifacts = [store.put("SPEC.md", (AREA / "SPEC.md").read_bytes()),
                 store.put("counterfactual-checks.json", canonical_json_bytes(matrix))]
    for fixture in fixtures:
        name = fixture.provenance["world"]
        for suffix, raw in (("candidate.json", pilot.reference.candidate_bytes(fixture.initial)),
                            ("TASK.txt", fixture.task.encode()), ("PUBLIC_CHECK.py", fixture.public_checker),
                            ("observations.json", canonical_json_bytes(list(fixture.observations))), *fixture.observation_bodies):
            artifacts.append(store.put("worlds/" + name + "/" + suffix, raw))
    log.append("preparation_started", dict(source_sha256=sources, actor=ACTOR, completion_calls=0), artifacts)
    failure, qualifications, recovery = None, [], []
    try:
        with base.owned_runtime(args, store, log) as url:
            def save(stem, request):
                pilot.health(args.output)
                template, native, tokens, count = pilot.render_only(url, request)
                row = dict(stem=stem, prompt_tokens=count, fits_working_set=count<=WORKING_SET,
                           fits_resident=count<=RESIDENT_CEILING, physical_generation_space=ACTOR["context"]-count)
                log.append("input_prepared", {**row,"completion_sent":False}, [store.put(stem + suffix, raw) for suffix,raw in
                    (("-request.json",canonical_json_bytes(request)),("-rendered-prompt.txt",native),
                     ("-template-response.json",template),("-tokenization.json",tokens))])
                return row
            for fixture, kind, value, snapshots, opportunities in routes:
                rows = []
                name = fixture.provenance["world"] + "/" + kind
                for number, snapshot in enumerate(snapshots, 1):
                    stem = f"routes/{name}/{number:03d}"
                    rows.append(save(stem, snapshot["before_request"]))
                    log.append("oracle_action", dict(route=name, sequence=number, model_actor=False),
                        [store.put(stem+"-oracle.json", canonical_json_bytes({k:v for k,v in snapshot.items() if k!="before_request"}))])
                qualifications.append(dict(route=name, scripted_actions=len(rows), maximum_input=max(r["prompt_tokens"] for r in rows),
                    natural_boundary_on_scripted_route=any(not r["fits_working_set"] for r in rows),
                    all_fit_resident=all(r["fits_resident"] for r in rows), check_opportunities=opportunities, inputs=rows))
                if kind == "source_investigation":
                    external, recovered = recovery_probe(value)
                    recovery.append(dict(world=fixture.provenance["world"], forced_offline_only=True, recovered=recovered,
                                         input=save("recovery/"+fixture.provenance["world"], external)))
            require(source_identities() == sources, "source changed during preparation")
            pilot.health(args.output)
        closed = verify_records(args.output / "records.jsonl", args.output)[-1]
        require(closed["record_type"] == "runtime_closed" and closed["payload"]["owned_server_shutdown_verified"]
                and closed["payload"]["dedicated_port_free"], "runtime lifecycle incomplete")
        shortcuts = [q for q in qualifications if "shortcut" in q["route"]]
        pressure_rejected = any(not q["natural_boundary_on_scripted_route"] for q in shortcuts)
        manifest = dict(schema="incident-pressure-offline-qualification-v1", source_sha256=sources, actor=ACTOR,
                        working_set=WORKING_SET, resident_ceiling=RESIDENT_CEILING, prospective_seeds=SEEDS,
                        prospective_call_limit=CALL_LIMIT, completion_calls=0, execution_authorized=False,
                        source_identical_counterfactuals=True, task_has_incident_dependent_correction=True,
                        pressure_rejected_by_shortcut=pressure_rejected, ready_for_live_pressure=False,
                        qualification_paths=qualifications, recovery=recovery,
                        files=[r for r in base.file_inventory(args.output) if r["path"]!="records.jsonl"])
        store.put("PACKAGE_MANIFEST.json", canonical_json_bytes(manifest))
        log.append("preparation_completed", dict(completion_calls=0, pressure_rejected_by_shortcut=pressure_rejected,
                   ready_for_live_pressure=False), [])
    except BaseException as error:
        failure = error
        log.append("preparation_stopped", dict(error_type=type(error).__name__, error=str(error), completion_calls=0), [])
    records = verify_records(args.output / "records.jsonl", args.output)
    files = base.file_inventory(args.output)
    base.write_json(args.output / "PREPARATION_SEAL.json", dict(disposition="stopped_without_completion" if failure else "qualified_without_completion",
        completion_calls=0, files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files)), record_count=len(records),
        memory=base.memory_stats(args.output / "memory.csv"), effective_runtime=base.runtime_evidence(args.output / "private-runtime/server.stderr.log"),
        private_runtime_files_local_only={p.name:sha256_file(p) for p in (args.output / "private-runtime").glob("*") if p.is_file()}))
    if failure:
        raise failure
    print({"completion_calls":0, "routes":[(q["route"], q["maximum_input"]) for q in qualifications],
           "pressure_rejected_by_shortcut":pressure_rejected, "ready_for_live_pressure":False})
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=PACKAGE)
    prepare(parser.parse_args())


if __name__ == "__main__":
    main()
