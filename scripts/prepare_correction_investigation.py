"""Prepare one fresh ordinary investigation; never send completion requests."""
from __future__ import annotations

import argparse
from pathlib import Path

import prepare_investigation_loop as pilot
from prepare_episode_framing import annotate, EPISODE_ANNOTATION
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.ecological_pilot_v2 import EcologicalFixture
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunities

ROOT = pilot.ROOT
AREA = ROOT / "development/correction_investigation"
PACKAGE = AREA / "preparation-001"
SPEC = AREA / "SPEC.md"
ACTOR, INPUT_CEILING, CALL_LIMIT = pilot.ACTOR, pilot.INPUT_CEILING, 24
SEED = 32452843
base, require = pilot.base, pilot.require
TARGET = "src/dispatchledger/reporting/totals.py"
BAD = "        destination = bucket(change.after)\n        for receipt, units in contributions(change):\n"
PARTIAL = "        destination = bucket(change.before or change.after)\n        for receipt, units in contributions(change):\n"
GOOD = "        for receipt, units in contributions(change):\n            destination = bucket(receipt)\n"
HISTORY = "all ordered events resident; private thinking omitted; no externalization; declared episode annotation"


def source_identities():
    paths = [SPEC, AREA / "TASK.txt", AREA / "PUBLIC_CHECK.py",
             *(p for p in (AREA / "source").rglob("*") if p.is_file()),
             *(ROOT / "scripts" / name for name in ("prepare_correction_investigation.py", "run_correction_investigation.py", "prepare_episode_framing.py")),
             ROOT / "tests/test_correction_investigation.py"]
    return {**pilot.source_identities(), **{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}


def make_fixture(candidate, task, checker):
    return EcologicalFixture("RECEIPT-CORRECTIONS", "ordinary_evidence_investigation", task, candidate, checker,
                             b"", (), (), {"development_only":True,"authored_fixture":True}, ())


def constructed_fixture():
    files = {p.relative_to(AREA / "source").as_posix():p.read_bytes()
             for p in (AREA / "source").rglob("*") if p.is_file()}
    return make_fixture(Candidate.create(files), (AREA / "TASK.txt").read_text(encoding="utf-8"),
                        (AREA / "PUBLIC_CHECK.py").read_bytes())


def load_fixture(folder):
    saved = load_json_strict((folder / "candidate.json").read_bytes())
    candidate = Candidate.create({r["path"]:r["content_utf8"].encode() for r in saved["files"]})
    require(pilot.reference.candidate_bytes(candidate) == (folder / "candidate.json").read_bytes(), "candidate identity differs")
    return make_fixture(candidate,(folder / "TASK.txt").read_text(encoding="utf-8"),(folder / "PUBLIC_CHECK.py").read_bytes())


def request_for(value, reference):
    # Reuse the same state builder, endpoint schema and wording transforms.
    # Only this new task's prospective numerical allowance and seed differ.
    used = len(value.pairs)
    require(used < CALL_LIMIT and not value.state.submitted, "terminal path has no next request")
    state = load_json_strict(pilot.build_request(value.fixture, candidate=value.state.candidate,
        pairs=value.pairs, externalized_payload_count=0, calls_used=used, fork_binding=None))
    require(state["resource_state"].pop(pilot.wording.RESOURCE_KEY) == pilot.wording.RESOURCE_EXAMPLE, "resource wording changed")
    state["resource_state"].update(call_limit=CALL_LIMIT, calls_remaining=CALL_LIMIT-used, reasoning_budget_tokens=-1)
    value.request = canonical_json_bytes(state)
    request = pilot.endpoint_request(value, seed=42, mode="action")
    request["model"], request["seed"] = base.ALIAS, SEED
    system = request["messages"][0]["content"]
    require(system.count(pilot.wording.OLD_NAVIGATION) == 1, "navigation source changed")
    request["messages"][0]["content"] = system.replace(pilot.wording.OLD_NAVIGATION, pilot.wording.NEW_NAVIGATION) + "\n\n" + reference
    return annotate(request, report_precedes_session=True)


def qualification_paths(selected):
    for kind in ("direct", "correction"):
        value, snapshots = new_state(kind,selected), []
        reference = pilot.tool_reference(pilot.grammar_for(value))

        def act(action):
            request = request_for(value,reference)
            result = value.execute(action)
            require(result.get("accepted") is True, "oracle request rejected: " + str(result))
            snapshots.append(dict(before_request=request,action=action,result=result,candidate_after=value.state.candidate.candidate_id))
            return result

        def read(path):
            start = 1
            while start is not None:
                start = act(dict(action="read",path=path,start_line=start))["next_start_line"]

        def check():
            return act(dict(action="check",check_id="public",expected_candidate_id=value.state.candidate.candidate_id))

        def patch(old,new):
            return act(dict(action="patch",path=TARGET,old=old,new=new,
                            expected_candidate_id=value.state.candidate.candidate_id,
                            expected_file_sha256=value.state.candidate.file_sha256(TARGET)))

        require(check()["passed"] is False, "initial candidate unexpectedly passes")
        read("README.md")
        act(dict(action="p0_page",path="src",offset=0))
        act(dict(action="p0_page",path="src/dispatchledger",offset=0))
        for name in ("api.py", "records.py"):
            read("src/dispatchledger/"+name)
        for directory, names in (("ingest", ("fields.py", "csv_rows.py")),
                                 ("state", ("registry.py",)),
                                 ("reporting", ("entries.py", "totals.py"))):
            act(dict(action="p0_page",path="src/dispatchledger/"+directory,offset=0))
            for name in names:
                read("src/dispatchledger/"+directory+"/"+name)
        if kind == "correction":
            patch(BAD,PARTIAL)
            require(check()["passed"] is False, "partial repair unexpectedly passes")
            read(TARGET)
            patch(PARTIAL,GOOD)
        else:
            patch(BAD,GOOD)
        require(check()["passed"] is True, "complete repair does not pass")
        act(dict(action="submit",expected_candidate_id=value.state.candidate.candidate_id))
        require(value.state.submitted and len(snapshots) <= CALL_LIMIT, "oracle path cannot close")
        yield kind, snapshots, check_opportunities(value.pairs,call_limit=CALL_LIMIT)


def prepare(args):
    selected = constructed_fixture()
    paths = list(qualification_paths(selected))
    sources = source_identities()
    args.output.mkdir(parents=True,exist_ok=False)
    store, log = ArtifactStore(args.output), pilot.PilotLog(args.output / "records.jsonl","correction-preparation-001")
    value = new_state("R01",selected)
    reference = pilot.tool_reference(pilot.grammar_for(value))
    log.append("preparation_started",dict(source_sha256=sources,actor=ACTOR,maximum_completion_calls=CALL_LIMIT,completion_calls=0),
               [store.put(name,raw) for name,raw in (
                   ("SPEC.md",SPEC.read_bytes()),("TASK.txt",selected.task.encode()),("PUBLIC_CHECK.py",selected.public_checker),
                   ("candidate.json",pilot.reference.candidate_bytes(selected.initial)),("TOOL_REFERENCE.txt",reference.encode()),
                   ("RESPONSE_FORMAT.json",canonical_json_bytes(pilot.grammar_for(value))))])
    failure, qualifications, initial = None, [], None
    try:
        with base.owned_runtime(args,store,log) as url:
            def save(stem,request):
                pilot.health(args.output)
                template,native,tokens,count = pilot.render_only(url,request)
                row = dict(stem=stem,prompt_tokens=count,would_admit=count<=INPUT_CEILING,rendered_sha256=sha256_bytes(native))
                log.append("input_prepared",{**row,"completion_sent":False},
                           [store.put(stem+suffix,raw) for suffix,raw in (
                               ("-request.json",canonical_json_bytes(request)),("-rendered-prompt.txt",native),
                               ("-template-response.json",template),("-tokenization.json",tokens))])
                return row
            initial = save("initial/R01",request_for(value,reference))
            require(initial["would_admit"], "initial input exceeds reserve-based capacity")
            for name,snapshots,opportunities in paths:
                rows = []
                for index,snapshot in enumerate(snapshots,1):
                    stem=f"qualification/{name}/{index:03d}"
                    rows.append(save(stem,snapshot["before_request"]))
                    log.append("oracle_action",dict(path=name,sequence=index,model_actor=False),
                               [store.put(stem+"-oracle.json",canonical_json_bytes({k:v for k,v in snapshot.items() if k!="before_request"}))])
                qualifications.append(dict(path=name,scripted_actions=len(snapshots),calls_remaining=CALL_LIMIT-len(snapshots),
                                           check_opportunities=opportunities,inputs=rows,all_inputs_admitted=all(r["would_admit"] for r in rows)))
            require(all(q["all_inputs_admitted"] for q in qualifications), "a required correction path cannot fit")
            require(sources==source_identities(), "source changed during preparation")
            pilot.health(args.output)
        closed=verify_records(args.output / "records.jsonl",args.output)[-1]
        require(closed["record_type"]=="runtime_closed" and closed["payload"]["owned_server_shutdown_verified"]
                and closed["payload"]["dedicated_port_free"], "preparation runtime lifecycle incomplete")
        manifest=dict(schema="correction-investigation-preparation-v1",actor=ACTOR,memory_policy=pilot.cont.POLICY,
                      source_sha256=sources,call_limit=CALL_LIMIT,maximum_completion_calls=CALL_LIMIT,input_ceiling=INPUT_CEILING,
                      run_id="R01",seed=SEED,initial=initial,completion_calls=0,execution_authorized=True,
                      history_policy=HISTORY,episode_annotation=EPISODE_ANNOTATION,qualification_paths=qualifications,
                      files=[r for r in base.file_inventory(args.output) if r["path"]!="records.jsonl"])
        store.put("PACKAGE_MANIFEST.json",canonical_json_bytes(manifest))
        log.append("preparation_completed",dict(completion_calls=0,initial_inputs=1,oracle_paths=len(qualifications)),[])
    except BaseException as error:
        failure=error
        log.append("preparation_stopped",dict(error_type=type(error).__name__,error=str(error),completion_calls=0),[])
    records=verify_records(args.output / "records.jsonl",args.output)
    files=base.file_inventory(args.output)
    base.write_json(args.output / "PREPARATION_SEAL.json",dict(
        disposition="stopped_without_completion" if failure else "prepared_without_completion",completion_calls=0,
        files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),record_count=len(records),
        memory=base.memory_stats(args.output / "memory.csv"),effective_runtime=base.runtime_evidence(args.output / "private-runtime/server.stderr.log"),
        private_runtime_files_local_only={p.name:sha256_file(p) for p in (args.output / "private-runtime").glob("*") if p.is_file()}))
    if failure:
        raise failure
    print({"initial":initial,"oracle_paths":[(q["path"],q["scripted_actions"],max(r["prompt_tokens"] for r in q["inputs"])) for q in qualifications],"completion_calls":0})
    return manifest


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model",type=Path,required=True)
    parser.add_argument("--server",type=Path,required=True)
    parser.add_argument("--output",type=Path,default=PACKAGE)
    prepare(parser.parse_args())
