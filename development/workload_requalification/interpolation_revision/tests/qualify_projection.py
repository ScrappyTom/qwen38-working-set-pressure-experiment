"""CPU-only qualification of reporting changes against exact checker observations.

The sole new checker execution removes ExtendedInterpolation from the existing
researcher reference. It is partial-path engineering evidence, never model work.
No generation, tokenizer, model server or GPU operation is performed here.
"""
import argparse
import copy
import difflib
import importlib.util
import json
from pathlib import Path
import traceback

import interpolation_task as task
import report_projection as revised
import reporting as original
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file, sha256_bytes
from working_set_exp.observations import ObservationStore

AREA = Path(__file__).resolve().parents[1]
ROOT = task.ROOT
CAPTURES = task.AREA / 'checker-qualification-002'


def save(path, value):
    path.write_bytes(canonical_json_bytes(value))


def inventory(folder):
    return {p.relative_to(ROOT).as_posix(): sha256_file(p)
            for p in folder.rglob('*') if p.is_file()}


def record_case(folder, name, store):
    full = json.loads((store.directory('CHK-0001') / 'stdout.bin').read_bytes())
    before = original.assessment(store, 'CHK-0001')
    after = revised.assessment(store, 'CHK-0001')
    # Preserve every assessment fact except the declared required-path rendering.
    old_rows = {row['criterion']: row for row in before['criteria']}
    new_rows = {row['criterion']: row for row in after['criteria']}
    assert set(old_rows) == set(new_rows)
    assert {k:v for k,v in before.items() if k!='criteria'} == {k:v for k,v in after.items() if k!='criteria'}
    for key in old_rows:
        if key != 'required_paths':
            assert old_rows[key] == new_rows[key], (name, key)
    row = new_rows['required_paths']
    assert (row['met'], row['meaning']) == (old_rows['required_paths']['met'], old_rows['required_paths']['meaning'])
    expected = [(entry['policy'], entry['operation']) for entry in full['observed_paths']['missing_paths']]
    shown = [(group['policy'], operation) for group in row['missing_groups'] for operation in group['missing_operations']]
    assert shown == expected, (name, shown, expected)
    assert row['all_missing_groups_shown'] is True
    assert row['missing_operation_total'] == len(expected)
    assert all(group['missing_operation_count'] == len(group['missing_operations']) for group in row['missing_groups'])
    assert not any(k.startswith('missing_paths') or k == 'additional_missing_paths' for k in row)
    for group in row['missing_groups']:
        # Failed lookup describes transported exception origin; not raw/resolved outcomes.
        assert 'transport_source' in group and 'lookup' not in group, group
        assert 'copy' in group['transport_source'] and 'pickle' in group['transport_source']
        if group['policy'] == 'BasicInterpolation':
            assert 'ExtendedInterpolation' not in group['transport_source']
            assert 'cross-section' not in group['transport_source']
        else:
            assert 'cross-section' in group['transport_source']
    assert 'raw=True' in row['operation_meanings']['raw_bypass']
    assert 'supplying' in row['operation_meanings']['resolved']
    saved = copy.deepcopy(after)
    overview = revised.overview(after)
    assert after == saved, 'overview mutated its input'
    overview_rows = {r['criterion']:r for r in overview['criteria']}
    if expected:
        assert overview_rows['required_paths'] == row, 'standing view lost complete operation groups'
    else:
        assert 'required_paths' not in overview_rows, 'satisfied path criterion remains incorrectly outstanding'
    pages, offset, entries = [], 0, []
    while True:
        page = revised.inspect_check(store, 'CHK-0001', offset)
        assert page['offset'] == offset and page['records_complete'] is True
        assert page['total_records'] == len(after['criteria'])
        assert page['all_records_shown'] == (offset == 0 and len(page['entries']) == page['total_records'])
        entries.extend(page['entries']); pages.append(page)
        if page['next_offset'] is None:
            break
        assert page['next_offset'] == offset + len(page['entries'])
        offset = page['next_offset']
    assert entries == after['criteria'], 'inspection loses, duplicates or changes records'
    save(folder/(name+'-assessment.json'), after)
    save(folder/(name+'-overview.json'), overview)
    save(folder/(name+'-inspection-pages.json'), pages)
    return dict(case=name, missing_paths=len(expected), groups=len(row['missing_groups']),
                passed=after['passed'], failed_criteria=after['failed_criteria'],
                criteria=len(after['criteria']), inspected_pages=len(pages),
                raw_stdout_sha256=sha256_file(store.directory('CHK-0001')/'stdout.bin'))


def partial_capture(folder):
    test = (task.legacy.AREA/'REFERENCE_TEST.py').read_text(encoding='utf-8')
    removed = "            (configparser.ExtendedInterpolation(), '${other:missing}', 'other:missing'),\n"
    assert test.count(removed) == 1
    partial = test.replace(removed, '')
    doc = (task.legacy.AREA/'REFERENCE_DOC.txt').read_text(encoding='utf-8')
    original, _ = task.legacy.starting_work()
    files = dict(original.files)
    files[task.TEST] += b'\n\n' + partial.encode()
    files[task.DOC] += b'\n\n' + doc.encode()
    candidate = Candidate.create(files, max_file_bytes=original.max_file_bytes)
    (folder/'partial-reference-test.py').write_text(partial, encoding='utf-8', newline='\n')
    (folder/'partial-fixture.patch').write_text(''.join(difflib.unified_diff(test.splitlines(True),
        partial.splitlines(True), fromfile='researcher-reference.py', tofile='basic-only-reference.py')),
        encoding='utf-8', newline='\n')
    save(folder/'PARTIAL_FIXTURE.json', dict(classification='researcher-authored CPU qualification; no model work',
        starting_candidate_id=original.candidate_id, candidate_id=candidate.candidate_id,
        checker_sha256=sha256_bytes(task.checker()), scope='public',
        exact_alteration='Remove only ExtendedInterpolation tuple from the reference test mode loop.',
        reference_test_sha256=sha256_file(task.legacy.AREA/'REFERENCE_TEST.py'),
        reference_doc_sha256=sha256_file(task.legacy.AREA/'REFERENCE_DOC.txt'),
        files={path:sha256_bytes(data) for path,data in candidate.files}))
    store = ObservationStore(folder/'partial-basic-only')
    result = store.execute(candidate, task.checker(), 'public', 'CHK-0001')
    assert result['executed'] and result['capture_complete'] and not result['passed'], result
    full = json.loads((store.directory('CHK-0001')/'stdout.bin').read_bytes())
    assert len(full['observed_paths']['missing_paths']) == 10
    assert {r['policy'] for r in full['observed_paths']['missing_paths']} == {'ExtendedInterpolation'}
    return store


def label_cases(folder):
    spec = importlib.util.spec_from_file_location('qualified_interpolation_receipts', AREA/'session.py')
    module = importlib.util.module_from_spec(spec); spec.loader.exec_module(module)
    old = task.Task(replay_folder=folder/'unused-replay').initial_session()
    session = old.clone(); session.__class__ = module.Session
    frozen = canonical_json_bytes(dict(pairs=session.pairs, last=session.last))
    prior = session.view()
    assert prior['latest_feedback']['episode'] == 'prior_work'
    expected = old.view()
    assert prior['latest_feedback']['sequence'] == session.starting_archive_length
    prior_without_label = copy.deepcopy(prior)
    prior_without_label['latest_feedback'].pop('episode')
    assert prior_without_label == expected, 'entry label changes more than display episode'
    assert canonical_json_bytes(dict(pairs=session.pairs, last=session.last)) == frozen
    save(folder/'prior-work-view.json', prior)
    # Pure archive read with a mocked ample capacity result; does not qualify native fit.
    result = session.execute(dict(action='history', before=0, path=task.TEST), lambda _: 0)
    assert result['accepted']
    before_current = canonical_json_bytes(dict(pairs=session.pairs, last=session.last))
    current = session.view()
    assert current['latest_feedback']['episode'] == 'this_contribution'
    assert current['latest_feedback']['sequence'] == session.starting_archive_length + 1
    assert current['recent_activity'][-1]['episode'] == 'this_contribution'
    assert canonical_json_bytes(dict(pairs=session.pairs, last=session.last)) == before_current
    assert 'episode' not in session.last
    assert canonical_json_bytes(session.pairs[:old.starting_archive_length]) == canonical_json_bytes(old.pairs)
    session.mark_delivered(current)
    save(folder/'current-contribution-view.json', current)
    none = session.clone(); none.last = None
    assert none.view()['latest_feedback'] is None
    return dict(prior_receipt_sequence=prior['latest_feedback']['sequence'],
                current_receipt_sequence=current['latest_feedback']['sequence'],
                archived_receipts_unchanged=True, native_sizing_qualified=False)


def main(output, reuse_partial=None):
    folder = AREA/output; folder.mkdir(exist_ok=False)
    watched = inventory(CAPTURES)
    sources = {p.relative_to(ROOT).as_posix():sha256_file(p) for p in
        (AREA/'report_projection.py', AREA/'session.py', Path(__file__).resolve())}
    save(folder/'INPUTS.json', dict(source_identities=sources, preserved_captures=watched,
        checker_sha256=sha256_bytes(task.checker()), completion_requests=0, native_requests=0))
    cases, labels, error = [], None, None
    try:
        if reuse_partial:
            partial_store = ObservationStore(AREA/reuse_partial/'partial-basic-only', replay=True)
            save(folder/'PARTIAL_REUSE.json', dict(source=reuse_partial,
                preserved_files=inventory(AREA/reuse_partial/'partial-basic-only')))
        else:
            partial_store = partial_capture(folder)
        for name in ('baseline','reference','missing_class','missing_diagnostic'):
            cases.append(record_case(folder, name, ObservationStore(CAPTURES/name, replay=True)))
        cases.append(record_case(folder,'partial-basic-only',partial_store))
        labels = label_cases(folder)
    except BaseException as exc:
        error = exc
        save(folder/'FAILED.json', dict(type=type(exc).__name__, message=str(exc), traceback=traceback.format_exc()))
    finally:
        unchanged = watched == inventory(CAPTURES)
        save(folder/'RESULTS.json', dict(cases=cases, receipt_labels=labels,
            historical_captures_unchanged=unchanged,
            completion_requests=0, native_requests=0, checker_executions=0 if reuse_partial else 1,
            status='failed_preserved' if error else 'qualified_cpu_only'))
        save(folder/'SEAL.json', dict(status='failed_preserved' if error else 'qualified_cpu_only',
            source_identities=sources, files={p.relative_to(folder).as_posix():sha256_file(p)
                for p in folder.rglob('*') if p.is_file()}))
    if not unchanged:
        raise AssertionError('Preserved historical captures changed')
    if error:
        raise error
    print(json.dumps(dict(output=str(folder), cases=cases, labels=labels)))


if __name__ == '__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--output', default='cpu-qualification-001')
    parser.add_argument('--reuse-partial')
    args=parser.parse_args(); main(args.output,args.reuse_partial)
