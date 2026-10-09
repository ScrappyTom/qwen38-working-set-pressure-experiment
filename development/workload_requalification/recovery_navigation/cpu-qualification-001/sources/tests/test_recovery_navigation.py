"""Recovery information, authority and admission tests, with no model calls."""
import copy
import json
from pathlib import Path
import sys
import unittest

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import fixture
import navigation
import recovery_navigation as new
import search_navigation
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes
from working_set_exp.observations import ObservationStore


class OrdinarySession(search_navigation.SearchNavigationMixin, navigation.NavigationSession):
    pass


class Session(new.RecoveryNavigationMixin, OrdinarySession):
    pass


def session():
    candidate = Candidate.create({'a.py': b'def alpha():\n    return 1\n', 'b.py': b'value = 2\n'})
    return Session(candidate, {'public': b'# not executed'}, 'Inspect code.', edit_checks={},
        observations=ObservationStore(AREA/'not-executed', replay=True),
        call_limit=1000, request_limit=1000)


def search(s, query='alpha', limit=8):
    return s.execute(dict(action='search', path='a.py', query=query, offset=0, limit=limit), lambda _: 0)


def account(s):
    return s.execute(dict(action='record_account', text='Inspect the relevant source.'), lambda _: 0)


def predecessor_view(s):
    other = s.clone()
    other.__class__ = OrdinarySession
    return other.view()


class RecoveryTests(unittest.TestCase):
    def test_actual_recovery_restores_the_missing_outcomes_without_state_change(self):
        old, s = fixture.restored(projected=False), fixture.restored()
        before = fixture.snapshot(s)
        view = s.view()
        rows = {row['sequence']: row for row in view['recent_activity']}
        zero = rows[25]['navigation']['observed_page']
        located = rows[28]['navigation']['observed_page']
        self.assertEqual((zero['query'], zero['total_matches'], zero['matches']), ('InvalidWriteError', 0, []))
        self.assertEqual([m['line'] for m in located['matches']], [1375, 1392])
        self.assertEqual(located['regions'][0]['region_ref'], s.pairs[27]['result']['regions'][0]['region_ref'])
        stripped = copy.deepcopy(view)
        stripped['recent_activity'] = []
        self.assertEqual(stripped, old.view())
        self.assertEqual(fixture.snapshot(s), before)
        self.assertEqual(fixture.snapshot(s), fixture.snapshot(old))
        self.assertEqual(view['working_set']['sources'], [])

    def test_ordinary_inputs_and_explicit_zero_fallback_are_exact(self):
        for stem in ('C22-O01', 'C23-O01', 'C28-O01', 'C32-O01'):
            with self.subTest(stem=stem):
                old, s = fixture.restored(stem, projected=False), fixture.restored(stem)
                if not s.recovery:
                    self.assertEqual(s.view(), old.view())
                s.last = dict(s.last, **{navigation.SETTING: -1})
                old.last = dict(old.last, **{navigation.SETTING: -1})
                self.assertEqual(s.view(), old.view())

    def test_navigation_does_not_restore_edit_authority_but_delivered_source_does(self):
        s = fixture.restored()
        path = 'Lib/configparser.py'
        exact = '            self._validate_write_key(key)'
        original = s.candidate
        s.mark_delivered(s.view())
        edit = dict(action='patch', path=path, old=exact, new=exact+'  # inspected',
                    expected_candidate_id=original.candidate_id,
                    expected_file_sha256=original.file_sha256(path))
        self.assertFalse(s.execute(edit, lambda _: 0)['accepted'])
        self.assertEqual(s.candidate.candidate_id, original.candidate_id)
        line = original.file_map[path].decode().splitlines().index(exact)+1
        self.assertTrue(s.execute(dict(action='read', path=path, start_line=line, end_line=line), lambda _: 0)['accepted'])
        s.mark_delivered(s.view())
        self.assertTrue(s.execute(edit, lambda _: 0)['accepted'])

    def test_required_rejection_and_check_feedback_survive_optional_fallback(self):
        for stem in ('C23-O01', 'C32-O01'):
            with self.subTest(stem=stem):
                s = fixture.restored(stem)
                pairs = canonical_json_bytes(s.pairs)
                original_result = copy.deepcopy(s.last['result'])
                self.assertTrue(s._fits_feedback(lambda view: 24000 if view['recent_activity'] else 1000))
                self.assertEqual(s.last[navigation.SETTING], -1)
                self.assertEqual(s.view()['recent_activity'], [])
                self.assertEqual(s.last['result'], original_result)
                self.assertEqual(canonical_json_bytes(s.pairs), pairs)
                if stem == 'C32-O01':
                    self.assertTrue(s.view()['latest_feedback']['result']['passed'])
                    self.assertEqual(s.view()['latest_feedback']['result']['observation'], 'CHK-0042')

    def test_group_replacement_returns_to_unchanged_ordinary_contract_and_restores(self):
        s = fixture.restored()
        original = s.candidate.candidate_id
        result = s.execute(dict(action='work_on', sources=[dict(path='Doc/library/configparser.rst',
            start_line=1300, end_line=1410)], saved_results=[]), lambda _: 0)
        self.assertTrue(result['accepted'])
        self.assertFalse(s.recovery)
        self.assertEqual(s.candidate.candidate_id, original)
        state = json.loads(canonical_json_bytes(fixture.snapshot(s)))
        restored = fixture.previous.Task('001').restore(state, s.candidate, fixture.RUN, replay=True)
        self.assertEqual(restored.view(), s.view())
        restored.__class__ = fixture.Session
        self.assertEqual(restored.view(), s.view())

    def test_exact_partial_and_empty_pages_are_historical_not_current_source(self):
        s = session()
        search(s, 'absent')
        search(s, 'e', limit=1)
        account(s)
        s.enter_recovery('qualification capacity obstacle')
        rows = {r['sequence']: r['navigation'] for r in s.view()['recent_activity'] if 'navigation' in r}
        self.assertEqual(rows[1]['observed_page']['total_matches'], 0)
        page = rows[2]['observed_page']
        self.assertIsNotNone(page['next_offset'])
        self.assertEqual(page['matches'], s.pairs[1]['result']['matches'])
        self.assertEqual(rows[2]['observation'], 'historical_navigation_not_source')
        self.assertEqual(s.view()['working_set']['sources'], [])
        s.candidate = Candidate.create({'a.py': b'def alpha():\n    return 2\n', 'b.py': b'value = 2\n'})
        changed = s.view()['recent_activity'][1]['navigation']
        self.assertFalse(changed['candidate_matches_current'])
        self.assertTrue(all(not r['file_matches_current'] for r in changed['observed_page']['regions']))

    def test_unrelated_file_change_latest_deduplication_and_recent_window(self):
        s = session()
        search(s)
        s.enter_recovery('qualification capacity obstacle')
        self.assertEqual(s.view()['recent_activity'][0]['navigation']['detail_status'], 'already_in_latest_feedback')
        account(s)
        s.candidate = Candidate.create({'a.py': s.candidate.file_map['a.py'], 'b.py': b'value = 3\n'})
        detail = s.view()['recent_activity'][0]['navigation']
        self.assertFalse(detail['candidate_matches_current'])
        self.assertTrue(all(r['file_matches_current'] for r in detail['observed_page']['regions']))
        for _ in range(8):
            account(s)
        self.assertEqual(len(s.view()['recent_activity']), 6)
        self.assertFalse(any(row['action'] == 'search' for row in s.view()['recent_activity']))
        self.assertTrue(s.pairs[0]['result']['matches'])

    def test_shared_byte_bound_with_escaping_heavy_detail_and_huge_summaries(self):
        s = session()
        search(s)
        account(s)
        s.enter_recovery('qualification capacity obstacle')
        pairs = copy.deepcopy(s.pairs)
        pairs[0]['result']['matches'][0]['text'] = '\\"'*20000
        before = canonical_json_bytes(pairs)
        base = predecessor_view(s)
        summaries = [s.summary(i) for i in range(1, len(s.pairs)+1)]
        for budget in (0, 1, 100, 1000, 8192):
            result = new.project(base, pairs, s.candidate, summaries, byte_limit=budget)
            self.assertLessEqual(len(canonical_json_bytes(result))-len(canonical_json_bytes(base)), budget)
            self.assertFalse(any('observed_page' in row.get('navigation', {}) for row in result['recent_activity']))
        summaries[0]['query'] = 'x'*30000
        result = new.project(base, pairs, s.candidate, summaries, byte_limit=1000)
        self.assertFalse(any(r['sequence'] == 1 for r in result['recent_activity']))
        self.assertEqual(canonical_json_bytes(pairs), before)
        self.assertEqual(new.project(base, pairs, s.candidate, summaries, page_limit=-1), base)


if __name__ == '__main__':
    unittest.main()
