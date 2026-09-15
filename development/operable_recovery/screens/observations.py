"""Native check-to-exact-inspection paths; synthetic outputs, zero inference."""
import argparse
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import operable_task as study
import run_uncoached_contribution as runner
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

RUNTIME=study.base.base


def run(folder):
    folder.mkdir(parents=True,exist_ok=False)
    store,log=ArtifactStore(folder),RecordLog(folder/'records.jsonl','native-observation-boundaries')
    bound={**study.source_identities(),Path(__file__).resolve().relative_to(study.ROOT).as_posix():sha256_file(Path(__file__))}
    rows=[];error=None
    server,model,_=study.runtime_paths()
    try:
        with RUNTIME.owned_runtime(SimpleNamespace(server=server,model=model,output=folder),store,log) as url:
            for name,code,body in (
                ('long_tail',b"import sys;sys.stdout.write('A'*9000+'REAL FAILURE');sys.exit(1)",b'A'*9000+b'REAL FAILURE'),
                ('escaping',b"import sys;sys.stdout.write(chr(34)*7500);sys.exit(1)",b'"'*7500)):
                target=folder/name;target.mkdir()
                local=ArtifactStore(target);journal=RecordLog(target/'records.jsonl',name)
                session,adapter=study.initial_session(),runner.Adapter(study.Task())
                session.task='Synthetic capture/inspection qualification only. Do not infer application correctness.'
                session.checkers={scope:code for scope in study.DESCRIPTIONS}
                study.attach_observations(session,target,journal)
                local.put('checker.py',code)
                loop=runner.Loop(target,local,journal,url=url,task_module=adapter,
                    source_check=lambda:study.verify_sources(bound),health=lambda:study.pilot.health(folder))
                ranges=copy.deepcopy(session.ranges)
                session.mark_delivered(session.view())
                result=session.execute(dict(action='check',check_id='public',expected_candidate_id=session.candidate.candidate_id),loop.measure)
                assert result['accepted'] and result['executed'] and not result['passed'] and result['capture_complete']
                view=session.view()
                assert view['latest_feedback']['result']==result
                if name=='long_tail':
                    assert 'REAL FAILURE' in canonical_json_bytes(view).decode()
                local.put('executed-check.json',canonical_json_bytes(result))
                pieces=[];offset=0;pages=[]
                while True:
                    page=session.execute(dict(action='inspect_observation',observation=result['observation'],stream='stdout',offset=offset),loop.measure)
                    view=session.view()
                    assert view['latest_feedback']['result']==page and page['encoding']=='utf-8'
                    assert session.ranges==ranges
                    session.mark_delivered(view)
                    assert session.delivered_sources==[]
                    pieces.append(page['content'].encode())
                    pages.append(dict(offset=offset,next_offset=page['next_offset'],native_input=loop.measure(view)))
                    local.put(f'page-{offset}.json',canonical_json_bytes(page))
                    if page['next_offset'] is None:break
                    offset=page['next_offset']
                assert b''.join(pieces)==body
                observed=session.observations.read(result['observation'])
                assert observed['streams']['stdout']['sha256']==sha256_bytes(body)
                local.put('final-state.json',canonical_json_bytes(study.snapshot(session)))
                rows.append(dict(case=name,captured_bytes=len(body),pages=pages,exact_reconstruction=True,
                    primary_diagnostic_delivered=name=='long_tail',selection_unchanged=True,
                    inspections_supplied_no_source_authority=True,custody_records=len(verify_records(target/'records.jsonl',target))))
    except BaseException as problem:
        error=problem
        study.save(folder,'FAILED.json',dict(type=type(problem).__name__,message=str(problem)))
    study.save(folder,'RESULTS.json',dict(status='failed_preserved' if error else 'qualified',cases=rows,
        source_sha256=bound,model_inference_calls=0,memory=RUNTIME.memory_stats(folder/'memory.csv'),port_free=RUNTIME.port_free(RUNTIME.PORT)))
    files=RUNTIME.file_inventory(folder)
    study.save(folder,'SEAL.json',dict(files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))
    if error:raise error
    print(json.dumps(rows),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--folder',default='observation-native-001')
    run(study.AREA/parser.parse_args().folder)
