"""Short offline task screen, before any full execution package or model calls."""
from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path

import prepare_incident_pressure as prior
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.ecological_pilot_v2 import EcologicalFixture
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file

ROOT = prior.ROOT
AREA = ROOT / "development/compiler_incident"
BAD = "        if isinstance(node.op, (ast.UAdd, ast.USub)):\n"
GOOD = "        if isinstance(node.op, ast.UAdd) and isinstance(node.operand, ast.Constant) and type(node.operand.value) in (int, float):\n"


def captures():
    completed = subprocess.run([sys.executable, "-I", "-S", "-c",
        "import runpy,sys;sys.path.insert(0,'.');runpy.run_path(" + repr(str(AREA / "CAPTURE.py")) + ",run_name='__main__')"],
        input=(AREA / "donor/calculation.py").read_bytes(), cwd=AREA / "source", capture_output=True, timeout=30)
    if completed.returncode:
        raise RuntimeError(completed.stderr.decode())
    return load_json_strict(completed.stdout)


def fixture(checker=b"print('screening only; not behavioral acceptance')\n"):
    candidate = Candidate.create({p.relative_to(AREA / "source").as_posix(): p.read_bytes()
                                  for p in (AREA / "source").rglob("*") if p.is_file()})
    bodies = tuple((f"OBS-{i:04d}", canonical_json_bytes(record)) for i, record in enumerate(captures(), 1))
    labels = ("input calculation module", "BUILD-A emitted module", "BUILD-B emitted module")
    observations = tuple(dict(handle=handle, sequence=i, action="capture", target=target,
                             candidate_id=candidate.candidate_id, size_bytes=len(raw), sha256=sha256_bytes(raw))
                         for i, ((handle, raw), target) in enumerate(zip(bodies, labels), 1))
    return EcologicalFixture("COMPILER-INCIDENT", "captured_compiler_investigation", (AREA / "TASK.txt").read_text(encoding="utf-8"),
                             candidate, checker, b"", observations, bodies, {"authored_compiler_fault":True}, ())


def minimum_route(selected):
    value = new_state("compiler-screen", selected)
    reference = prior.pilot.tool_reference(prior.pilot.grammar_for(value))
    requests = [("initial", prior.request_for(value, reference))]
    for handle, _ in selected.observation_bodies:
        result = value.execute(dict(action="reopen_observation", handle=handle))
        prior.require(result["accepted"], "capture is not exactly retrievable")
        requests.append(("after-"+handle, prior.request_for(value, reference)))
    for path in ("compiler/unary.py", "reports/incident.json"):
        result = value.execute(dict(action="read", path=path, start_line=1))
        prior.require(result["accepted"], "source not readable")
        requests.append(("after-read-"+path.replace("/","-"), prior.request_for(value, reference)))
    return value, requests


def screen(args):
    selected = fixture()
    value, requests = minimum_route(selected)
    args.output.mkdir(parents=True, exist_ok=False)
    store = ArtifactStore(args.output)
    log = prior.pilot.PilotLog(args.output / "records.jsonl", "compiler-task-screen")
    sources = {p.relative_to(ROOT).as_posix():sha256_file(p) for p in [Path(__file__).resolve(),
        ROOT / "scripts/prepare_incident_pressure.py", AREA / "CAPTURE.py", AREA / "TASK.txt",
        *sorted(p for p in (AREA / "source").rglob("*") if p.is_file()),
        *sorted(p for p in (AREA / "donor").rglob("*") if p.is_file())]}
    log.append("screen_started", {"completion_calls":0,"source_sha256":sources},
               [store.put("candidate.json", prior.pilot.reference.candidate_bytes(selected.initial)),
                store.put("captures.json", canonical_json_bytes(captures())),
                store.put("actions-results.json",canonical_json_bytes(value.pairs))])
    rows, failure = [], None
    try:
        with prior.base.owned_runtime(args,store,log) as url:
            for name, request in requests:
                prior.pilot.health(args.output)
                template,native,tokens,count = prior.pilot.render_only(url,request)
                row={"name":name,"prompt_tokens":count,"fits_16000":count<=prior.WORKING_SET,"fits_23808":count<=prior.RESIDENT_CEILING}
                refs=[store.put(name+suffix,raw) for suffix,raw in (("-request.json",canonical_json_bytes(request)),
                    ("-native.txt",native),("-template.json",template),("-tokens.json",tokens))]
                log.append("screen_input",{**row,"completion_sent":False},refs)
                rows.append(row)
        log.append("screen_completed",{"completion_calls":0,"behavioral_acceptance_qualified":False,"rows":rows},[])
    except BaseException as error:
        failure=error
        log.append("screen_failed",{"type":type(error).__name__,"error":str(error),"completion_calls":0},[])
    records=verify_records(args.output/'records.jsonl',args.output)
    files=prior.base.file_inventory(args.output)
    prior.base.write_json(args.output/'SCREEN_SEAL.json',{"completion_calls":0,"source_sha256":sources,"rows":rows,
        "files":files,"aggregate_sha256":sha256_bytes(canonical_json_bytes(files)),"record_count":len(records),
        "memory":prior.base.memory_stats(args.output/'memory.csv'),"completed":failure is None})
    if failure:
        raise failure
    print(rows)


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--model',type=Path,required=True)
    parser.add_argument('--server',type=Path,required=True)
    parser.add_argument('--output',type=Path,default=AREA/'screen-001')
    screen(parser.parse_args())
