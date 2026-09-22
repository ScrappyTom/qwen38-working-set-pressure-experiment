"""Save offline initial-input and custody validation; forbid runtime/checker calls."""
import argparse
import json
from pathlib import Path
from unittest.mock import patch

import execution_task as task
import run_uncoached_contribution as runner
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes,sha256_bytes,sha256_file


def write(folder,name,value):
    data=value if isinstance(value,bytes) else canonical_json_bytes(value)
    with (folder/name).open('xb') as output:output.write(data)


def main(name):
    if Path(name).name!=name or name in ('','.','..') or '/' in name or '\\' in name:
        raise ValueError('Output must be one new local folder name')
    folder=task.AREA/name;folder.mkdir(exist_ok=False)
    bound=None;error=None
    try:
        with (patch('subprocess.Popen',side_effect=AssertionError('CPU qualification forbids subprocesses')),
              patch.object(task.host.base.base,'post',side_effect=AssertionError('CPU qualification forbids endpoints'))):
            bound=task.qualification_sources()
            module=task.Task();session=module.initial_session();adapter=runner.Adapter(module)
            view=session.view();request=adapter.request_for(view)
            expected=task.expected_native(request)
            wire=completion_request_bytes(request)
            write(folder,'initial-view.json',view)
            write(folder,'initial-wire-request.json',wire)
            write(folder,'expected-template-LOCAL-ONLY.txt',expected)
            write(folder,'starting-candidate.json',module.candidate_bytes(session.candidate))
            write(folder,'starting-state.json',module.snapshot(session))
            write(folder,'reply.gbnf',task.response_constraints()['grammar'].encode())
            write(folder,'RESULTS.json',dict(status='qualified_adapter_cpu_only',
                classification='Offline adapter/custody check; local template expectation is not an actual native input',
                completion_requests=0,native_requests=0,new_checker_processes=0,
                starting_candidate=session.candidate.candidate_id,task_sha256=sha256_bytes(session.task.encode()),
                adapted_checker_sha256=sha256_bytes(session.checkers['public']),
                maximum_requests=session.request_limit,maximum_operations=session.call_limit,
                candidate_file_limit=session.candidate.max_file_bytes,
                reference_material_in_initial_input=False,
                existing_checker_qualification='configparser_original/checker-qualification-005',
                decoder_proof_reused='small_repairs/native-005',
                grammar_sha256=sha256_bytes(request['grammar'].encode()),
                wire_sha256=sha256_bytes(wire),local_expected_template_bytes=len(expected),
                native_fit_qualified=False,live_ready=False))
    except BaseException as exc:
        error=exc;write(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        files=[dict(path=p.relative_to(folder).as_posix(),size_bytes=p.stat().st_size,sha256=sha256_file(p))
               for p in sorted(folder.rglob('*')) if p.is_file()]
        write(folder,'SEAL.json',dict(status='failed_preserved' if error else 'qualified_adapter_cpu_only',
            completion_requests=0,native_requests=0,new_checker_processes=0,
            source_sha256=bound,files=files,aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))
    if error:raise error
    print(json.dumps(dict(status='qualified_adapter_cpu_only',folder=str(folder),source_entries=len(bound))),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',required=True)
    main(parser.parse_args().output)
