"""Offline checker portability: preserved legacy acceptance plus declared obligations."""
import argparse
import json

import interpolation_task as task
from working_set_exp.candidate import Candidate
from working_set_exp.observations import ObservationStore
from manage import legacy as custody


def candidate(test=None, doc=None):
    original, _ = task.legacy.starting_work()
    files = dict(original.files)
    if test is not None:
        files[task.TEST] += b'\n\n' + test.encode()
    if doc is not None:
        files[task.DOC] += b'\n\n' + doc.encode()
    return Candidate.create(files, max_file_bytes=original.max_file_bytes)


def main(name):
    folder = task.AREA/name
    folder.mkdir(exist_ok=False)
    sources = task.source_identities()
    test = (task.legacy.AREA/'REFERENCE_TEST.py').read_text(encoding='utf-8')
    doc = (task.legacy.AREA/'REFERENCE_DOC.txt').read_text(encoding='utf-8')
    cases = [('baseline', candidate(), False), ('reference', candidate(test,doc), True),
        ('missing_class', candidate(test.replace('self.assertIs(type(result), type(error))',
                                                'self.assertIsInstance(result, type(error))'),doc), False),
        ('missing_diagnostic', candidate(test.replace('self.assertEqual(str(result), str(error))', 'pass')
            .replace('self.assertEqual(result.message, error.message)', 'pass'),doc),False)]
    results, error = [], None
    try:
        for name, value, expected in cases:
            store = ObservationStore(folder/name)
            actual = store.execute(value, task.checker(), 'public', 'CHK-0001')
            assert actual['executed'] and actual['capture_complete'], actual
            full = json.loads((store.directory('CHK-0001')/'stdout.bin').read_bytes())
            assessment = task.reporting.assessment(store,'CHK-0001')
            task.save(folder,name+'-assessment.json',assessment)
            task.save(folder,name+'-overview.json',task.reporting.overview(assessment))
            assert actual['passed'] is expected, (name, actual, full)
            old_store = ObservationStore(folder/(name+'-legacy'))
            old = old_store.execute(value,task.legacy.checker(),'public','CHK-0001')
            assert old['passed'] == full['legacy_public_passed'], name
            if name == 'reference':
                assert len(full['fault_sensitivity']['restored_class']['targets']) == 16
                assert full['examples']['successful']
            if name.startswith('missing_'):
                fault = 'restored_class' if name == 'missing_class' else 'restored_diagnostic'
                assert full['legacy_public_passed'], 'Original checker must retain its historical behavior'
                assert not full['fault_sensitivity'][fault]['all_targets_detected']
            row = dict(case=name,passed=actual['passed'],legacy_passed=old['passed'],
                bytes=actual['streams']['stdout']['captured_bytes'],failed=assessment['failed_criteria'])
            results.append(row)
            print(json.dumps(row),flush=True)
    except BaseException as exc:
        error=exc
        task.save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        task.save(folder,'RESULTS.json',dict(cases=results,completion_requests=0))
        custody.seal(folder,'failed_preserved' if error else 'qualified_no_model_inference',sources,completion_requests=0)
    if error:
        raise error


if __name__ == '__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--output',default='checker-qualification-001')
    main(parser.parse_args().output)

