"""Separate direct-route/behavior review; never overwrite the conservative screen."""
import argparse
import json
from pathlib import Path

import assess as base


def review(version):
    task = base.study.Task(version)
    run, folder = task.RUN, base.AREA / 'review' / version
    assessed = task.read(folder / 'ASSESSMENT.json')
    verified = task.read(base.AREA / f'review/VERIFICATION-{version}.json')
    assert verified['status'] == 'replayed_exactly'
    assert assessed['exact_replay_sha256'] == base.sha256_file(base.AREA / f'review/VERIFICATION-{version}.json')
    candidate = task.candidate_from_snapshot(task.read(run / 'final-candidate.json'))
    session = task.restore(task.read(run / 'final-state.json'), candidate, replay_folder=run, replay=True)
    wire = task.read(run / 'calls/C09-wire-request.json')
    view = json.loads(wire['messages'][-1]['content'])['workspace']
    search = task.read(run / 'calls/C09-operation-01.json')
    orientation = bool(view['phase']['current'] == 'B'
        and any(r['kind'] == 'directory' and r['path'] == 'policies' for r in view['current_p0']['entries'])
        and search['action']['action'] == 'search' and search['action']['path'] == 'policies'
        and search['action']['query'] == 'active_policy_prefix' and search['result']['accepted']
        and any(r['path'] == 'policies/current.py' and r['line'] == 4 for r in search['result']['matches']))
    # The original assignment preserves output behavior, not source-byte identity.
    # Check that behavior independently at the completed B and C boundaries and final.
    program = '''import json
from api.name import normalize_name
values=['',' a ',' MiX ',' Stra\u00dfe ',' \u00c5\u00df ','\\tNAME\\n',' \u0130 ',' \u03a3\u03c2\u03c3 ']
actual=[normalize_name(value) for value in values]
expected=['orbit-'+value.strip().casefold() for value in values]
assert actual==expected, (actual,expected)
print(json.dumps(actual,ensure_ascii=False))
'''.encode('utf-8')
    base.save(folder / 'independent-name-preservation.py', program)
    checkpoints = [(r['phase'], session.versions[r['candidate_id']]) for r in assessed['forks'] if r['phase'] in ('B','C')]
    checkpoints.append(('D', candidate))
    results = [base.execute(c, 'name_behavior_at_completed_' + phase, program) for phase, c in checkpoints]
    preserved = bool([p for p, _ in checkpoints] == ['B','C','D'] and all(r['returncode'] == 0 for r in results))
    complete = bool(verified['submitted'] and orientation and preserved
        and assessed['phase_b_policy_before_name'] and assessed['phase_d_current_policy_before_footer']
        and [r['phase'] for r in assessed['forks']] == ['A','B','C']
        and len(assessed['submissions']) == 1 and assessed['submissions'][0]['phase'] == 'D'
        and all(r['consumed_current_active_pass'] for r in assessed['forks'] + assessed['submissions'])
        and all(r['complete'] for rows in assessed['coverage'].values() for r in rows)
        and all(r['returncode'] == 0 for r in assessed['checks'])
        and set(assessed['changed_files']) == {'workflow/progress.py','api/name.py','policies/current.py','api/footer.py'}
        and assessed['unchanged_files'] == 156)
    result = dict(case=task.CASE, version=version, original_contract_completed=complete,
        assessment_sha256=base.sha256_file(folder / 'ASSESSMENT.json'),
        supplement_source_sha256=base.sha256_file(Path(__file__)),
        conservative_screen_retained=dict(overall=assessed['original_contract_screen_passed'],
            explicit_p0_page=assessed['p0_discovery_before_phase_b_policy'],
            byte_identical_b_name=assessed['completed_b_name_preserved']),
        actual_root_p0_then_search_route=orientation,
        name_behavior_at_completed_boundaries_preserved=preserved, independent_behavior_checks=results,
        evidence=['C09 actual root P0 and requested search; C10 exact policy acquisition; C11 actual policy input before edit.',
            'C21 failed C check is retained. C24 repairs the dynamic dependency; C25 passes and C26 consumes the pass.',
            'C27 reacquires current post-C policy; C28 uses it before the footer edit. C30 consumes the actual D pass.'],
        limits=['This is a separately declared post-run interpretation of the original contract, not a changed screen.',
            'The intermediate C policy edit did regress names; preservation holds after the recorded correction at completion.',
            'Root orientation plus directory search is an alternative to an additional p0_page request.',
            'Examples assess saved behavior; they are not independent model trials or proof of arbitrary future policy changes.'])
    base.save(folder / 'CONTRACT-REVIEW-SUPPLEMENT.json', result)
    print(json.dumps(result, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--version', default='001')
    review(parser.parse_args().version)
