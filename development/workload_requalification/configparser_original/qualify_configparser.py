"""Preserved CPU qualification only; no model/runtime/network entry point."""
import argparse
import copy
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'src'))

import configparser_task as task
import configparser_reports as reports
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore


def save(folder, name, value):
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def variants():
    original = task.starting_candidate()
    refroot = task.ORIGINAL / 'reference-qualification-002/reference-candidate'
    files = {p.relative_to(refroot).as_posix():p.read_bytes() for p in refroot.rglob('*') if p.is_file()}
    reference = Candidate.create(files, max_file_bytes=task.FILE_LIMIT)
    result = [('original', original, False), ('correct_reference', reference, True)]

    def change(name, path, old, new):
        values = reference.file_map
        assert values[path].count(old.encode()) == 1, name
        values[path] = values[path].replace(old.encode(), new.encode(), 1)
        result.append((name, Candidate.create(values, max_file_bytes=task.FILE_LIMIT), False))

    source = 'Lib/configparser.py'
    guard = '                    if cursect[optname] is None:\n                        raise MultilineContinuationError(fpname, lineno, line)\n'
    change('exception_api_without_behavior', source, guard, '')
    change('rejects_valid_continuations', source, '                    if cursect[optname] is None:\n', '                    if True:\n')
    change('wrong_line_number', source, '        self.source = source\n        self.lineno = lineno\n        self.line = line\n',
        '        self.source = source\n        self.lineno = lineno + 1\n        self.line = line\n')
    edits = load_json_strict((task.ORIGINAL / 'REFERENCE_EDITS.json').read_bytes())['rows']
    change('vacuous_added_test', 'Lib/test/test_configparser.py', edits[3]['new'],
        'class MultilineContinuationBackportTest(unittest.TestCase):\n    def test_nothing(self):\n        self.assertTrue(True)\n\n\n' + edits[3]['old'])
    files = reference.file_map
    files['Doc/library/configparser.rst'] = original.file_map['Doc/library/configparser.rst']
    result.append(('documentation_unchanged', Candidate.create(files, max_file_bytes=task.FILE_LIMIT), False))
    expected = {r['name']:r for r in load_json_strict((task.ORIGINAL / 'reference-qualification-002/RESULTS.json').read_bytes())['outcomes']}
    assert set(expected) == {r[0] for r in result}
    for name, candidate, passed in result:
        assert candidate.candidate_id == expected[name]['candidate_id'] and passed is expected[name]['passed'], name
    return result


def comparable(report):
    value = {name:{k:report[name][k] for k in (*reports.COUNTS, 'successful')} for name in reports.SUITES}
    value.update({k:report[k] for k in ('passed','regression_detects_original','documentation_directive_present',
                                     'documentation_semantics_require_direct_review')})
    # The old formatter sometimes replaces the list with its exact count.
    value['added_test_count'] = report.get('added_test_count', len(report['added_tests']))
    return value


def exact_raw_recovery(store):
    for stream in ('stdout','stderr','outcome'):
        expected = (store.directory('CHK-0001') / ('outcome.json' if stream == 'outcome' else stream + '.bin')).read_bytes()
        collected, offset = bytearray(), 0
        while True:
            page = store.inspect('CHK-0001', stream, offset)
            assert page['encoding'] == 'utf-8'
            collected.extend(page['content'].encode('utf-8'))
            if page['next_offset'] is None:
                break
            offset = page['next_offset']
        assert bytes(collected) == expected


def projected_session(folder, candidate, checker):
    session = task.Session(candidate, {'public':checker}, task.task_text(), edit_checks={},
        call_limit=task.MAX_OPERATIONS, request_limit=task.MAX_REQUESTS,
        observations=ObservationStore(folder, replay=True),
        check_contracts={'public': {'checker_sha256':sha256_bytes(checker)}})
    # CPU transition/view qualification, explicitly not a native token count.
    result = session.execute(dict(action='check',check_id='public',expected_candidate_id=candidate.candidate_id), lambda view:1)
    assert result['accepted'] and result['executed']
    immediate = session.view()
    save(folder.parent, 'immediate-view.json', immediate)
    status = immediate['verification']['checks']['public']
    assert immediate['latest_feedback']['result']['report'] == status['assessment']
    assert status['applies_to_current'] and status['passed'] is result['passed']
    session.execute(dict(action='search',path='Lib/configparser.py',query='ParsingError',offset=0,limit=1), lambda view:1)
    standing = session.view()
    save(folder.parent, 'standing-view.json', standing)
    assert standing['verification']['checks']['public']['assessment'] == status['assessment']
    assert session.candidate.candidate_id == candidate.candidate_id and session.candidate.max_file_bytes == task.FILE_LIMIT
    return dict(assessment_in_immediate_and_standing_view=True, native_input_fit_qualified=False,
                public_submission_eligible=standing['verification']['submission']['eligible'])


def run_main_cases(folder):
    results = []
    old_code, new_code = task.original_checker(), task.checker()
    (folder / 'original-checker.py').write_bytes(old_code)
    (folder / 'adapted-checker.py').write_bytes(new_code)
    for name, candidate, expected in variants():
        observations = {}
        for version, code in (('legacy',old_code),('adapted',new_code)):
            store = ObservationStore(folder / name / version / 'observations')
            outcome = store.execute(candidate, code, 'public', 'CHK-0001')
            assert outcome['executed'] and outcome['capture_complete'] and outcome['passed'] is expected, (name,version,outcome)
            value = load_json_strict((store.directory('CHK-0001') / 'stdout.bin').read_bytes())
            observations[version] = value
            exact_raw_recovery(store)
            if version == 'adapted':
                assessment = reports.assessment(store,'CHK-0001', {'checker_sha256':sha256_bytes(code)})
                assert assessment['assessment_available'] and bool(assessment['failed_criteria']) is not expected
                save(folder/name,'assessment.json',assessment)
                save(folder/name,'overview.json',reports.overview(assessment))
                save(folder/name,'page-0.json',reports.inspect_check(store,'CHK-0001',0))
                save(folder/name,'page-4.json',reports.inspect_check(store,'CHK-0001',4))
                projection = projected_session(folder/name/version/'observations',candidate,code)
        old, new = observations['legacy'], observations['adapted']
        assert comparable(old) == comparable(new), name
        if not old.get('diagnostics_omitted_for_byte_limit'):
            assert old['added_tests'] == new['added_tests']
        for suite in reports.SUITES:
            assert len(new[suite]['details']) == new[suite]['failures'] + new[suite]['errors']
            assert new[suite]['runner_output']
        if name in ('exception_api_without_behavior','rejects_valid_continuations','wrong_line_number'):
            assert old['diagnostics_omitted_for_byte_limit']
            assert new['contract']['details']
        results.append(dict(case=name,candidate_id=candidate.candidate_id,expected=expected,passed=new['passed'],
            acceptance_equivalent=True,details_preserved={s:len(new[s]['details']) for s in reports.SUITES},
            legacy_report_reduced=old.get('diagnostics_omitted_for_byte_limit',False),**projection))
        save(folder/name,'qualification-result.json',results[-1])
        print(name, 'equivalent', new['passed'], flush=True)
    return results


def run_boundaries(folder):
    candidate = Candidate.create({'probe.py': b'# Capture qualification only\n'})
    # Use the actual passing reference report; do not relabel a failed variant.
    good = load_json_strict((folder/'correct_reference/adapted/observations/CHK-0001/stdout.bin').read_bytes())
    long = copy.deepcopy(good)
    trace = ('quotes " and slash \\ and control \x01 and Unicode \u03bb\n' * 1200) + 'PRIMARY ASSERTION AT END\n'
    long['contract'].update(successful=False,failures=6,errors=0,
        details=[dict(test=f'long_test_{i}',trace=trace) for i in range(6)], runner_output=trace)
    long['passed'] = False
    assert reports.supported_shape(long)
    def emit(value, ascii_only=False):
        raw = json.dumps(value,ensure_ascii=True).encode('ascii') if ascii_only else canonical_json_bytes(value)
        return ('import sys,time\nsys.stdout.buffer.write('+repr(raw)+')\nsys.stdout.buffer.flush()\n')
    surrogate=copy.deepcopy(good)
    surrogate['contract'].update(successful=False,failures=1,errors=0,
        details=[dict(test='surrogate_failure',trace='invalid scalar: \ud800')])
    surrogate['passed']=False
    cases = [
        ('long_escaping', (emit(long)+'raise SystemExit(1)\n').encode(), {}, True, False),
        ('malformed', b'print("not a supported structured observation")\nraise SystemExit(1)\n', {}, False, False),
        ('crash_after_partial', b'print("ordinary suite was started", flush=True)\nraise RuntimeError("REAL LATER FAILURE")\n', {}, False, False),
        ('timeout_after_complete_looking_report', (emit(good)+'time.sleep(1)\n').encode(), {'timeout':0.15}, True, False),
        ('capture_limit', (emit(long)+'raise SystemExit(1)\n').encode(), {'stream_limit':4096}, False, False),
        ('nonzero_after_passing_report', (emit(good)+'raise SystemExit(2)\n').encode(), {}, True, False),
        ('unknown_success', b'print("unsupported successful output")\n', {}, False, True),
        ('lone_surrogate', (emit(surrogate,ascii_only=True)+'raise SystemExit(1)\n').encode(), {}, False, False),
        ('zero_after_failed_report', emit(long).encode(), {}, True, True),
    ]
    rows=[]
    for name,code,options,known,passed in cases:
        area=folder/'boundaries'/name
        area.mkdir(parents=True)
        (area/'checker.py').write_bytes(code)
        store=ObservationStore(area/'observations',**options)
        outcome=store.execute(candidate,code,'public','CHK-0001')
        assessment=reports.assessment(store,'CHK-0001',{'checker_sha256':sha256_bytes(code)})
        save(area,'assessment.json',assessment);save(area,'overview.json',reports.overview(assessment))
        assert outcome['passed'] is passed and assessment['assessment_available'] is known,(name,outcome,assessment)
        if not outcome['capture_complete']:
            assert 'public_execution' in assessment['failed_criteria']
        if name in ('nonzero_after_passing_report','zero_after_failed_report'):
            assert assessment['report_execution_consistent'] is False
            assert reports.overview(assessment)['report_execution_consistent'] is False
        exact_raw_recovery(store)
        overview=reports.overview(assessment)
        assert len(canonical_json_bytes(overview)) < 16000
        assert len(canonical_json_bytes(reports.inspect_check(store,'CHK-0001',0))) < 22000
        if name=='long_escaping':
            assert 'PRIMARY ASSERTION AT END' in overview['criteria'][0]['diagnostics'][0]['diagnostic']['text']
            assert overview['criteria'][0]['diagnostics_total']==6
            assert overview['criteria'][0]['diagnostics_shown']==1
        rows.append(dict(case=name,passed=outcome['passed'],termination=outcome['termination'],
            assessment_available=known,stdout_captured=outcome['streams']['stdout']['captured_bytes'],
            capture_complete=outcome['capture_complete']))
        save(area,'qualification-result.json',rows[-1])
        print(name,outcome['termination'],flush=True)
    return rows


def run_suite_edge(folder):
    reference=next(candidate for name,candidate,_ in variants() if name=='correct_reference')
    files=reference.file_map
    files['Lib/test/test_configparser.py'] += (
        '\n\nclass UnexpectedSuccessProbe(unittest.TestCase):\n'
        '    @unittest.expectedFailure\n'
        '    def test_unexpected_success_probe(self):\n'
        '        self.assertTrue(True)\n').encode()
    candidate=Candidate.create(files,max_file_bytes=task.FILE_LIMIT)
    area=folder/'suite-edges/unexpected_success';area.mkdir(parents=True)
    save(area,'candidate.json',dict(candidate_id=candidate.candidate_id,
        files=[dict(path=p,content_utf8=b.decode()) for p,b in candidate.files],
        qualification_only=True))
    values={}
    for version,code in (('legacy',task.original_checker()),('adapted',task.checker())):
        store=ObservationStore(area/version/'observations')
        outcome=store.execute(candidate,code,'public','CHK-0001')
        assert outcome['capture_complete'] and not outcome['passed']
        values[version]=load_json_strict((store.directory('CHK-0001')/'stdout.bin').read_bytes())
        exact_raw_recovery(store)
        if version=='adapted':
            value=reports.assessment(store,'CHK-0001',{'checker_sha256':sha256_bytes(code)})
            save(area,'assessment.json',value);save(area,'overview.json',reports.overview(value))
            save(area,'page-0.json',reports.inspect_check(store,'CHK-0001',0))
            row=reports.overview(value)['criteria'][0]
            assert row['criterion']=='candidate_tests.execution' and row['met'] is False
            assert row['counts']['failures']==row['counts']['errors']==row['diagnostics_total']==0
            assert 'UNEXPECTED SUCCESS:' in row['runner_diagnostic']['text']
            assert 'test_unexpected_success_probe' in row['runner_diagnostic']['text']
            projection=projected_session(area/version/'observations',candidate,code)
            actual=load_json_strict((area/version/'immediate-view.json').read_bytes())
            assert 'UNEXPECTED SUCCESS:' in actual['latest_feedback']['result']['report']['criteria'][0]['runner_diagnostic']['text']
    assert comparable(values['legacy'])==comparable(values['adapted'])
    row=dict(case='unexpected_success',candidate_id=candidate.candidate_id,passed=False,
        acceptance_equivalent=True,current_test_failures=0,current_test_errors=0,
        actual_runner_diagnostic_delivered=True,**projection)
    save(area,'qualification-result.json',row)
    print('unexpected_success equivalent False; runner diagnostic delivered',flush=True)
    return [row]


def main(name):
    if '/' in name or '\\' in name or name in ('.','..'):
        raise ValueError('output must be one new local directory name')
    folder=task.AREA/name
    folder.mkdir(exist_ok=False)
    sources=task.source_identities();results=[];boundaries=[];suite_edges=[];error=None
    try:
        results=run_main_cases(folder)
        boundaries=run_boundaries(folder)
        suite_edges=run_suite_edge(folder)
    except BaseException as exc:
        error=exc;save(folder,'FAILED.json',dict(type=type(exc).__name__,message=str(exc)))
    finally:
        save(folder,'RESULTS.json',dict(status='failed_preserved' if error else 'qualified_cpu_only',
            cases=results,boundaries=boundaries,suite_edges=suite_edges,completion_requests=0,native_requests=0,
            original_checker_sha256=sha256_bytes(task.original_checker()),adapted_checker_sha256=sha256_bytes(task.checker()),
            native_fit_qualified=False,source_discovery_and_full_contribution_route_qualified=False))
        files=[dict(path=p.relative_to(folder).as_posix(),size_bytes=p.stat().st_size,sha256=sha256_file(p))
               for p in sorted(folder.rglob('*')) if p.is_file()]
        save(folder,'SEAL.json',dict(status='failed_preserved' if error else 'qualified_cpu_only',
            completion_requests=0,native_requests=0,source_sha256=sources,files=files,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))
    if error:
        raise error


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',required=True)
    main(parser.parse_args().output)
