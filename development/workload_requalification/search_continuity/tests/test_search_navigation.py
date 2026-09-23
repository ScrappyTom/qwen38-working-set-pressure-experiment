"""CPU projection/transition qualification; no model or checker execution."""
import copy
import json
from pathlib import Path
import sys
import unittest

AREA = Path(__file__).resolve().parents[1]
ROOT = AREA.parents[2]
sys.path[:0] = [str(AREA), str(ROOT / 'src'),
               str(ROOT / 'development/workload_requalification/navigation_continuity')]
import navigation
import search_navigation as new
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file
from working_set_exp.observations import ObservationStore


class Session(new.SearchNavigationMixin, navigation.NavigationSession):
    pass


def session():
    candidate = Candidate.create({'a.py': b'def alpha():\n    return 1\n', 'b.py': b'value = 2\n'})
    return Session(candidate, {'public': b'# no execution'}, 'Inspect.', edit_checks={},
                   observations=ObservationStore(AREA / 'not-executed', replay=True),
                   call_limit=100, request_limit=100)


def search(s, query='alpha'):
    return s.execute(dict(action='search', path='a.py', query=query, offset=0, limit=8), lambda v: 0)


def account(s):
    return s.execute(dict(action='record_account', text='Inspect the found region.'), lambda v: 0)


def strip(view):
    result = copy.deepcopy(view)
    for row in result['recent_activity']:
        row.pop('navigation', None)
    return result


class SearchTests(unittest.TestCase):
    def test_continuation_preserves_state_counters_and_only_changes_projection(self):
        import search_task as task
        import run_uncoached_contribution as runner
        module = task.Task()
        s = module.initial_session()
        old = task.restore(projected=False)
        self.assertEqual(task.snapshot(s), task.snapshot(old))
        self.assertEqual((s.requests_used,s.calls_used,s.starting_archive_length), (13,18,39))
        self.assertEqual((s.request_limit,s.call_limit), (24,72))
        self.assertEqual(strip(s.view()), strip(old.view()))
        self.assertFalse(s.view()['verification']['submission']['eligible'])
        wire = runner.Adapter(module).request_for(s.view())
        prior = task.read(task.OLD/'calls/C13-wire-request.json')
        self.assertEqual({k:v for k,v in wire.items() if k!='messages'},
                         {k:v for k,v in prior.items() if k!='messages'})
        self.assertEqual(module.operating_reference(), task.previous.Task('002').operating_reference()+'\n\n'+new.REFERENCE_ADDITION)

    def test_exact_archived_inputs_gain_locations_without_other_changes(self):
        run = ROOT / 'development/workload_requalification/exception_transport/run-002'
        seal = json.loads((run / 'RESPONSE_SEAL.json').read_text())
        inventory = {r['path']: r for r in seal['files']}
        states = {'C04': 'C03-O01', 'C07': 'C06-O02', 'C10': 'C09-O01', 'C11': 'C10-O02', 'C12': 'C11-O01'}
        initial = json.loads((run / 'starting-candidate.json').read_text())
        candidate = Candidate.create({r['path']: r['content_utf8'].encode() for r in initial['files']},
                                     max_file_bytes=initial['max_file_bytes'])
        for tag, checkpoint in states.items():
            with self.subTest(tag=tag):
                names = [f'calls/{tag}-wire-request.json', f'after/{checkpoint}-state.json', 'starting-candidate.json']
                for name in names:
                    self.assertEqual(sha256_file(run / name), inventory[name]['sha256'])
                wire = json.loads((run / names[0]).read_text())
                view = json.loads(wire['messages'][-1]['content'])['workspace']
                pairs = json.loads((run / names[1]).read_text())['pairs']
                before = canonical_json_bytes(pairs)
                projected = new.project(view, pairs, candidate)
                self.assertEqual(strip(projected), strip(view))
                self.assertEqual(before, canonical_json_bytes(pairs))
                if tag in ('C07', 'C10', 'C12'):
                    pages = [r['navigation']['observed_page'] for r in projected['recent_activity']
                             if 'observed_page' in r.get('navigation', {})]
                    self.assertTrue(any(any(m['line'] == 1052 for m in p.get('matches', [])) for p in pages))

    def test_latest_and_duplicate_searches_are_not_duplicated(self):
        s = session(); search(s)
        self.assertEqual(s.view()['recent_activity'][-1]['navigation']['detail_status'], 'already_in_latest_feedback')
        account(s); search(s); account(s)
        rows = {r['sequence']: r for r in s.view()['recent_activity']}
        self.assertEqual(rows[1]['navigation']['shown_at_sequence'], 3)
        self.assertEqual(rows[3]['navigation']['detail_status'], 'complete_returned_navigation_page')

    def test_file_applicability_is_independent_of_candidate_and_no_source_authority(self):
        s = session(); search(s); account(s)
        original = s.candidate
        unrelated = Candidate.create({'a.py': original.file_map['a.py'], 'b.py': b'value = 3\n'})
        result = new.project(s.view(), s.pairs, unrelated)['recent_activity'][0]['navigation']
        self.assertFalse(result['candidate_matches_current'])
        self.assertTrue(all(r['file_matches_current'] for r in result['observed_page']['regions']))
        changed = Candidate.create({'a.py': b'def alpha():\n    return 2\n', 'b.py': b'value = 2\n'})
        result = new.project(s.view(), s.pairs, changed)['recent_activity'][0]['navigation']
        self.assertTrue(all(not r['file_matches_current'] for r in result['observed_page']['regions']))
        s.mark_delivered(s.view())
        edit = s.execute(dict(action='patch', path='a.py', old='return 1', new='return 2',
                              expected_candidate_id=original.candidate_id,
                              expected_file_sha256=original.file_sha256('a.py')), lambda v: 0)
        self.assertFalse(edit['accepted'])
        self.assertEqual(s.candidate.candidate_id, original.candidate_id)

    def test_empty_and_paginated_pages_preserve_observed_scope(self):
        s = session(); search(s, 'absent'); account(s)
        page = s.view()['recent_activity'][0]['navigation']['observed_page']
        self.assertEqual((page['matches'], page['total_matches'], page['next_offset']), ([], 0, None))
        self.assertNotIn('regions', page)
        s.execute(dict(action='search', path='a.py', query='e', offset=0, limit=1), lambda v: 0)
        account(s)
        pair = s.pairs[-2]
        page = s.view()['recent_activity'][-2]['navigation']['observed_page']
        self.assertEqual(page['next_offset'], pair['result']['next_offset'])
        self.assertEqual(page['matches'], pair['result']['matches'])
        self.assertEqual(page['regions'], [dict(r, file_matches_current=True) for r in pair['result']['regions']])

    def test_shared_budget_and_zero_fallback_preserve_required_view(self):
        s = session()
        s.execute(dict(action='tree', path='.', offset=0, limit=8), lambda v: 0)
        search(s); account(s)
        view = s.view(); baseline = strip(view)
        for budget in (0, 1, 100, 500, 8192):
            result = new.project(view, s.pairs, s.candidate, byte_limit=budget)
            self.assertLessEqual(len(canonical_json_bytes(result))-len(canonical_json_bytes(baseline)), budget)
            self.assertEqual(strip(result), baseline)
        self.assertEqual(new.project(view, s.pairs, s.candidate, page_limit=-1), baseline)
        result = new.project(view, s.pairs, s.candidate, page_limit=1)
        self.assertEqual(sum('observed_page' in r.get('navigation', {}) for r in result['recent_activity']), 1)

    def test_oversized_page_is_not_silently_truncated_and_archive_is_unchanged(self):
        s = session(); search(s); account(s)
        pairs = copy.deepcopy(s.pairs)
        pairs[0]['result']['matches'][0]['text'] = 'x' * 20000
        raw = canonical_json_bytes(pairs)
        view = new.project(s.view(), pairs, s.candidate)
        detail = view['recent_activity'][0]['navigation']
        self.assertEqual(detail['detail_status'], 'omitted_for_navigation_byte_allowance')
        self.assertNotIn('observed_page', detail)
        self.assertEqual(canonical_json_bytes(pairs), raw)

    def test_inherited_admission_can_remove_search_detail_without_blocking_feedback(self):
        s = session(); search(s)
        # Every optional body is expensive; the essential view and omission fit.
        def measure(view):
            return 24000 if any('observed_page' in r.get('navigation', {}) for r in view['recent_activity']) else 1000
        result = s.execute(dict(action='record_account', text='Still investigating.'), measure)
        self.assertTrue(result['accepted'])
        self.assertFalse(s.delivery_blocked)
        self.assertFalse(any('observed_page' in r.get('navigation', {}) for r in s.view()['recent_activity']))
        self.assertEqual(s.pairs[0]['result']['matches'][0]['line'], 1)

    def test_window_is_bounded_and_ordinary_navigation_is_unchanged(self):
        s = session()
        s.execute(dict(action='tree', path='.', offset=0, limit=8), lambda v: 0); account(s)
        base = strip(s.view())
        self.assertEqual(new.project(base, s.pairs, s.candidate), navigation.project_navigation(base, s.pairs, s.candidate))
        search(s)
        for _ in range(8): account(s)
        self.assertFalse(any(r.get('action') == 'search' for r in s.view()['recent_activity']))
        self.assertTrue(s.pairs[2]['result']['matches'])


if __name__ == '__main__':
    unittest.main()
