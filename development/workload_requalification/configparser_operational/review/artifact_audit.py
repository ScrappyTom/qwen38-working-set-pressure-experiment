"""Post-run artifact verification; this check is not fed to the closed actor."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import bootstrap
import operational_task as study
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file
from working_set_exp.observations import ObservationStore


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def main():
    run = study.AREA / 'run-001'
    assert (run / 'RESPONSE_SEAL.json').exists()
    output = Path(__file__).with_name('artifact-check-001')
    output.mkdir(exist_ok=False)
    start = study.original.starting_candidate()
    final = read(run / 'final-candidate.json')
    files = {f['path']: f['content_utf8'].encode() for f in final['files']}
    candidate = Candidate.create(files, max_file_bytes=study.original.FILE_LIMIT)
    assert candidate.candidate_id == final['candidate_id']
    changed = [p for p in files if files[p] != start.file_map[p]]
    assert set(changed) == {'Lib/configparser.py', 'Lib/test/test_configparser.py', 'Doc/library/configparser.rst'}
    # Remove only the exact inserted test class: the old module must be intact.
    tests = files['Lib/test/test_configparser.py']
    begin = tests.index(b'class MultilineContinuationErrorTests(')
    end = tests.index(b'class MiscTestCase(', begin)
    assert tests[:begin] + tests[end:] == start.file_map['Lib/test/test_configparser.py']
    before = read(run / 'observations/CHK-0054/stdout.bin')
    assert before['upstream']['successful'] and before['contract']['successful']
    store = ObservationStore(output / 'observations')
    outcome = store.execute(candidate, study.original.checker(), 'public', 'CHK-0001')
    assert outcome['executed'] and outcome['capture_complete']
    actual = read(store.directory('CHK-0001') / 'stdout.bin')
    assert not actual['passed'] and not actual['contract']['successful']
    summary = dict(
        classification='Independent post-run execution; no new model-performance evidence',
        final_candidate=candidate.candidate_id, changed_files=changed,
        existing_test_bytes_preserved=True, checker_executions=1, model_requests=0,
        before_final_edit={k:before[k] for k in ('passed', 'upstream', 'contract', 'candidate_tests')},
        final_outcome=outcome,
        final_suites={k:actual[k] for k in ('upstream', 'contract', 'candidate_tests', 'new_tests_on_original')},
        documentation_directive_present=actual['documentation_directive_present'],
        documentation_semantics='Require direct review; directive presence is insufficient',
        audit_source_sha256=sha256_file(Path(__file__)),
        sealed_run_sha256=sha256_file(run / 'RESPONSE_SEAL.json'))
    (output / 'RESULTS.json').write_bytes(canonical_json_bytes(summary))
    print(json.dumps(dict(candidate=candidate.candidate_id, passed=actual['passed'],
        counts={k:{n:actual[k][n] for n in ('tests','failures','errors','successful')}
                for k in ('upstream','contract','candidate_tests')},
        diagnostics={k:actual[k]['details'] for k in ('contract','candidate_tests')}), indent=2))


if __name__ == '__main__':
    main()
