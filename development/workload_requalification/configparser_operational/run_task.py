"""Qualify the unchanged task path and run only a separately frozen preparation."""
import argparse
import json
from types import SimpleNamespace
from unittest.mock import patch

import bootstrap  # noqa: F401
import operational_task as study
from manage import load_helper
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import load_json_strict,sha256_file

# Isolated module namespaces preserve the earlier adapter and its preparation.
native=load_helper('operational_configparser_native','development/workload_requalification/configparser_execution/qualify_native.py')
execution=load_helper('operational_configparser_execution','development/workload_requalification/configparser_execution/run_configparser.py')
native.task=study
execution.study=study


def preflight():
    with (patch('subprocess.Popen',side_effect=AssertionError('Preflight forbids subprocesses')),
          patch.object(study.host.base.base,'post',side_effect=AssertionError('Preflight forbids endpoints'))):
        bound=study.qualification_sources()
        module=study.Task();session=module.initial_session();adapter=native.runner.Adapter(module)
        request=adapter.request_for(session.view())
        assert session.candidate.candidate_id==study.original.STARTING_ID
        assert session.candidate.max_file_bytes==study.original.FILE_LIMIT
        assert session.edit_checks=={} and not session.pairs and not session.ranges and not session.saved
        assert session.working_account() is None
        assert load_json_strict(request['messages'][1]['content'].encode())==dict(workspace=session.view(),preceding_operation_feedback=[])
        assert all('REFERENCE_EDITS' not in m['content'] and 'reference-candidate' not in m['content'] for m in request['messages'])
        old=load_json_strict((study.DECODER/'wire-request.json').read_bytes())
        assert {k:v for k,v in request.items() if k!='messages'}=={k:v for k,v in old.items() if k!='messages'}
        files=session.candidate.file_map
        for row in native.reference_rows():
            old,new=row['old'].encode(),row['new'].encode()
            assert files[row['path']].count(old)==1
            files[row['path']]=files[row['path']].replace(old,new,1)
        reference=Candidate.create(files,max_file_bytes=study.original.FILE_LIMIT)
        proof=load_json_strict((study.CPU_QUALIFIED/'RESULTS.json').read_bytes())
        assert reference.candidate_id==next(r['candidate_id'] for r in proof['cases'] if r['case']=='correct_reference')
        return bound,reference.candidate_id


native.preflight=preflight


if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('mode',choices=('preflight','native','prepare','run'))
    parser.add_argument('--version',default='001')
    args=parser.parse_args();module=study.Task(args.version)
    if args.mode=='preflight':
        bound,reference=preflight()
        print(json.dumps(dict(status='passed',sources=len(bound),reference_candidate=reference,
                              completion_requests=0,native_requests=0,checker_executions=0)),flush=True)
    elif args.mode=='native':native.qualify(study.NATIVE_QUALIFIED)
    elif args.mode=='prepare':execution.prepare(module)
    else:
        execution.runner.run_once(SimpleNamespace(owner_direction=study.OWNER_DIRECTION,
            manifest_sha256=sha256_file(module.MANIFEST)),module)
