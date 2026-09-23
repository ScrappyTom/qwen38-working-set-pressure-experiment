"""CPU qualification draft. Never invokes a model or native runtime.

Run only after the active model attempt closes. Each version is one preserved
attempt; this does not qualify native input fit or authorize calling a draft done.
"""
import argparse
import ast
import json
from pathlib import Path

import bootstrap
import parser_roundtrip as historical
import transport_capture
import transport_reports as reports
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

AREA = Path(__file__).resolve().parent
REFERENCE_SEAL = '95335757c598d456359689897a6454376f9253dfdb74872259bfac8b28400912'
TARGET = 'Lib/test/test_configparser.py'


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def candidates():
    start, _ = historical.starting_work()
    folder = historical.RUN
    assert sha256_file(folder/'RESPONSE_SEAL.json') == REFERENCE_SEAL
    seal = load_json_strict((folder/'RESPONSE_SEAL.json').read_bytes())
    row = next(r for r in seal['files'] if r['path'] == 'final-candidate.json')
    assert sha256_file(folder/'final-candidate.json') == row['sha256']
    raw = load_json_strict((folder/'final-candidate.json').read_bytes())
    reference = Candidate.create({r['path']:r['content_utf8'].encode() for r in raw['files']},
                                 max_file_bytes=raw['max_file_bytes'])
    assert reference.candidate_id == raw['candidate_id']
    cases = [('unchanged_entry', start, False), ('historical_checked_work', reference, True)]
    files = start.file_map
    files[TARGET] += b'\nclass VacuousNewCoverage(unittest.TestCase):\n    def test_vacuous(self):\n        self.assertTrue(True)\n'
    cases.append(('vacuous_addition', Candidate.create(files, max_file_bytes=start.max_file_bytes), False))

    def altered(name, transform):
        files = reference.file_map
        files[TARGET] = transform(files[TARGET].decode()).encode()
        cases.append((name, Candidate.create(files, max_file_bytes=start.max_file_bytes), False))

    def replace_once(source, old, new):
        assert source.count(old) == 1, old
        return source.replace(old, new, 1)

    altered('missing_deepcopy', lambda s: replace_once(s, 'copied = copy.deepcopy(exc)', 'copied = copy.copy(exc)'))
    altered('missing_protocols', lambda s: replace_once(s, 'for proto in range(pickle.HIGHEST_PROTOCOL + 1):\n                pickled = pickle.dumps(exc, proto)',
                                                      'for proto in (pickle.HIGHEST_PROTOCOL,):\n                pickled = pickle.dumps(exc, proto)'))
    newline_case = "            ('test.cfg', '[section]\\noption\\n    continuation\\n',\n             '    continuation\\n', 3),\n"
    def no_newline(source):
        assert source.count(newline_case) == 3
        return source.replace(newline_case, '')
    altered('missing_newline_case', no_newline)
    altered('wrong_current_expectation', lambda s: replace_once(s, 'copied = copy.copy(exc)',
        'copied = copy.copy(exc)\n            self.assertEqual(copied.source, source + ".wrong")'))
    # Remove every assertion of restored errors in the new methods, leaving all
    # other contracts intact: only the lost_errors injection should escape.
    def no_errors(source):
        for line in ('            self.assertEqual(copied.errors, [(lineno, line)])\n',
                     '                self.assertEqual(restored.errors, [(lineno, line)])\n'):
            assert line in source
            source = source.replace(line, '')
        return source
    altered('undetected_errors_fault', no_errors)
    # An executable no-op inside an OLD test preserves behavior but changes its
    # recorded AST. This isolates the existing-work criterion from new coverage.
    baseline_tree = ast.parse(start.file_map[TARGET].decode())
    old_method = next(method for cls in baseline_tree.body if isinstance(cls, ast.ClassDef)
                      for method in cls.body if isinstance(method, ast.FunctionDef)
                      and method.name.startswith('test'))
    def old_test_changed(source):
        tree = ast.parse(source)
        current_method = next(method for cls in tree.body if isinstance(cls, ast.ClassDef)
                              for method in cls.body if isinstance(method, ast.FunctionDef)
                              and method.name == old_method.name and method.lineno == old_method.lineno)
        lines = source.splitlines(True)
        lines.insert(current_method.body[0].lineno-1, ' '*(current_method.col_offset+4)+'pass\n')
        return ''.join(lines)
    altered('prior_test_ast_changed', old_test_changed)
    files = reference.file_map
    files['Doc/library/configparser.rst'] += b'\nUnrequested change.\n'
    cases.append(('prior_work_changed', Candidate.create(files, max_file_bytes=start.max_file_bytes), False))
    return cases


def comparable(report):
    result = {k:report[k] for k in ('passed', 'existing_work_preserved', 'added_tests')}
    result['suites'] = {k:{f:report[k][f] for f in (*reports.COUNTS, 'successful')} for k in reports.SUITES}
    result['transport_modes'] = {k:report['transports'][k] for k in ('complete', 'required_modes', 'observed_modes')}
    result['faults'] = {k:{f:report['restoration_faults'][k][f] for f in (*reports.COUNTS, 'successful')} for k in reports.FAULTS}
    return result


def exact_diagnostics(assessment):
    by_field = {}
    for row in assessment['diagnostic_records']:
        key = row['criterion'], row['diagnostic_index'], row['field']
        raw = by_field.setdefault(key, bytearray())
        assert len(raw) == row['start_byte']
        raw.extend(row['text'].encode())
        assert len(raw) == row['end_byte']
        if row['end_byte'] == row['total_bytes']:
            assert sha256_bytes(bytes(raw)) == row['field_sha256']
    return len(by_field)


def main(version):
    folder = AREA/f'capture-qualification-{version}'
    folder.mkdir(exist_ok=False)
    save(folder/'ATTEMPT.json', dict(model_requests=0, native_requests=0, status='started'))
    start, _ = historical.starting_work()
    old = historical.checker()
    new = transport_capture.preserve_observations(start.file_map, historical.base.task.checker(),
                                                  (historical.AREA/'PUBLIC_CHECK.py').read_bytes())
    (folder/'legacy-checker.py').write_bytes(old)
    (folder/'adapted-checker.py').write_bytes(new)
    results = []
    try:
        for name, candidate, expected in candidates():
            reports_by_kind = {}
            for kind, code in (('legacy', old), ('adapted', new)):
                store = ObservationStore(folder/name/kind/'observations')
                outcome = store.execute(candidate, code, 'public', 'CHK-0001')
                assert outcome['executed'] and outcome['capture_complete']
                report = load_json_strict((store.directory('CHK-0001')/'stdout.bin').read_bytes())
                reports_by_kind[kind] = report
                assert outcome['passed'] is expected and report['passed'] is expected, (name, kind, outcome)
                if kind == 'adapted':
                    assessment = reports.assessment(store, 'CHK-0001', {'checker_sha256':sha256_bytes(code)})
                    assert assessment['assessment_available']
                    assert bool(assessment['failed_criteria']) is not expected
                    fields = exact_diagnostics(assessment)
                    save(folder/name/'assessment.json', assessment)
                    save(folder/name/'overview.json', reports.overview(assessment))
                    offset = 0
                    while True:
                        page = reports.inspect_check(store, 'CHK-0001', offset)
                        save(folder/name/f'page-{offset}.json', page)
                        if page['next_offset'] is None:
                            break
                        offset = page['next_offset']
            assert comparable(reports_by_kind['legacy']) == comparable(reports_by_kind['adapted']), name
            row = dict(case=name, candidate_id=candidate.candidate_id, passed=expected,
                       acceptance_equivalent=True, exact_diagnostic_fields=fields)
            results.append(row)
            save(folder/name/'RESULT.json', row)
            print(name, expected, flush=True)
        save(folder/'RESULTS.json', dict(status='capture_and_report_cpu_qualified', cases=results,
             model_requests=0, native_requests=0, checker_executions=2*len(results),
             native_input_fit_qualified=False, full_boundary_qualification_complete=False))
    except BaseException as error:
        save(folder/'FAILURE.json', dict(type=type(error).__name__, message=str(error), completed=results))
        raise


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--version', required=True)
    main(parser.parse_args().version)
