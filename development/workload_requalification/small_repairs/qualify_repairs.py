"""Checker/report compatibility; does not send a model request."""
import argparse
import json

import repair_task as task
from manage import legacy
from working_set_exp.candidate import Candidate
from working_set_exp.observations import ObservationStore


def main(output):
    folder=task.AREA/output;folder.mkdir(exist_ok=False)
    sources={};results=[];error=None
    try:
        for case in task.MODULES:
            module=task.Task(case);sources.update(module.implementation_identities())
            original=module.legacy.constructed_fixture()
            files=original.initial.file_map
            assert files[module.legacy.TARGET].count(module.legacy.BAD.encode())==1
            files[module.legacy.TARGET]=files[module.legacy.TARGET].replace(module.legacy.BAD.encode(),module.legacy.GOOD.encode())
            corrected=Candidate.create(files,max_file_bytes=original.initial.max_file_bytes)
            for label,candidate,expected in [('original',original.initial,False),('reference',corrected,True)]:
                store=ObservationStore(folder/case/label)
                result=store.execute(candidate,original.public_checker,'public','CHK-0001')
                assert result['executed'] and result['capture_complete'] and result['passed'] is expected,result
                assessment=task.case_reports.assessment(store,'CHK-0001')
                task.save(folder/case,label+'-assessment.json',assessment)
                task.save(folder/case,label+'-overview.json',task.case_reports.overview(assessment))
                assert bool(assessment['failed_criteria']) is not expected
                results.append(dict(case=case,entry=label,candidate_id=candidate.candidate_id,
                    passed=result['passed'],criteria=len(assessment['criteria']),failed=assessment['failed_criteria']))
                print(json.dumps(results[-1]),flush=True)
    except BaseException as exc:
        error=exc;task.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        task.save(folder,'RESULTS.json',dict(cases=results,completion_requests=0))
        legacy.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',sources,completion_requests=0)
    if error:raise error


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='checker-qualification-005')
    main(parser.parse_args().output)
