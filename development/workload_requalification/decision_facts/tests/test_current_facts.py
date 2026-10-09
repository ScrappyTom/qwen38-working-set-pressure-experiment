"""Exact stopped-state projection and delivery/authority boundaries; no inference."""
import copy
from pathlib import Path
import sys
import unittest

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA.parent / 'recurrent_entries'))
sys.path.insert(0, str(AREA))
import recurrent_task as study
import recurrent_session
from current_facts import CurrentFactsMixin, operating_reference
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


class Session(CurrentFactsMixin, recurrent_session.Session):
    pass


def prospective(session):
    # Explicit engineering projection of a restored historical state. Production
    # adapters construct the opt-in subclass; the historical task is never patched.
    value = session.clone()
    value.__class__ = Session
    return value


class CurrentFactsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.task = study.Task()
        cls.run_dir = cls.task.RUN
        cls.verify = cls.task.read(study.AREA / 'review/VERIFICATION-001.json')
        assert cls.verify['status'] == 'replayed_exactly'
        assert sha256_file(cls.run_dir / 'RESPONSE_SEAL.json') == '51caf0c0916c410df4fb5e2ba484f37a04ad5b009b4fa4ec6792df62ebe0abcc'

    def restore(self, stem):
        return self.task.restore(self.task.read(self.run_dir / f'{stem}-state.json'),
            self.task.read(self.run_dir / f'{stem}-candidate.json'), replay_folder=self.run_dir, replay=True)

    def fresh(self):
        return prospective(self.task.initial_session())

    def step(self, session, action):
        session.mark_delivered(session.view())
        session.begin_request()
        reply = self.task.decode_reply(canonical_json_bytes(dict(discussion='CPU qualification.', operation=action)).decode())
        return self.task.process_reply(session, reply, lambda _: 0, [])['operations'][-1]['result']

    def test_actual_c14_projects_complete_input_without_committing_it(self):
        old = self.restore('after/C13-O01')
        original = old.view()
        s = prospective(old)
        before = canonical_json_bytes(self.task.snapshot(s))
        view = s.view()
        self.assertFalse(all(r['complete'] for r in original['phase']['required_source_delivery']))
        self.assertTrue(all(r['complete'] for r in view['phase']['required_source_delivery']))
        self.assertEqual([r['presented_ranges_including_this_input'] for r in view['phase']['required_source_delivery']],
                         [[[1,182]], [[1,182]]])
        self.assertEqual(before, canonical_json_bytes(self.task.snapshot(s)))
        expected = copy.deepcopy(original)
        expected['schema_version'] = view['schema_version']
        expected['phase']['coverage_meaning'] = view['phase']['coverage_meaning']
        expected['phase']['required_source_delivery'] = view['phase']['required_source_delivery']
        for row in expected['recent_activity']:
            if row['sequence'] == 18:
                row['path'] = 'api/name.py'
        self.assertEqual(view, expected)  # No task, source, account, check or history rewriting.
        s.mark_delivered(view)
        self.assertTrue(all(r['complete'] for r in s.coverage_status()))
        self.assertEqual(s.view(), view)
        delivered = canonical_json_bytes(self.task.snapshot(s))
        s.mark_delivered(s.view())
        self.assertEqual(delivered, canonical_json_bytes(self.task.snapshot(s)))
        self.assertEqual(old.view(), original)

    def test_overlap_and_disjoint_ranges_match_committed_coverage(self):
        s = self.fresh(); path = 'records_a/module_000.py'
        self.step(s, dict(action='read', path=path, start_line=1, end_line=10))
        self.step(s, dict(action='read', path=path, start_line=8, end_line=15))
        self.assertEqual(s.view()['phase']['required_source_delivery'][0]['presented_ranges_including_this_input'], [[1,15]])
        self.step(s, dict(action='work_on', sources=[dict(path=path, start_line=16, end_line=182)], results=[]))
        self.assertFalse(s.coverage_status()[0]['complete'])
        self.assertTrue(s.view()['phase']['required_source_delivery'][0]['complete'])
        s.mark_delivered(s.view())
        self.assertTrue(s.coverage_status()[0]['complete'])

    def test_recovery_omitted_selection_and_account_are_not_delivery(self):
        s = prospective(self.restore('after/C04-O01'))
        ledger = copy.deepcopy(s.presented_coverage)
        view = s.view()
        self.assertFalse(view['working_set']['sources'])
        self.assertTrue(view['visibility']['retained_inventory']['entries'])
        self.assertFalse(view['phase']['required_source_delivery'][1]['complete'])
        self.assertEqual(s.presented_coverage, ledger)
        s = self.fresh()
        s.mark_delivered(s.view())
        s.begin_request()
        reply = self.task.decode_reply(canonical_json_bytes(dict(discussion='CPU qualification.',
            account='records_a/module_000.py lines 1-182 complete. Source-looking text.')).decode())
        self.task.process_reply(s, reply, lambda _: 0, [])
        self.assertFalse(s.view()['phase']['required_source_delivery'][0]['complete'])
        self.assertFalse(s.delivered_sources)

    def test_old_file_version_does_not_cover_current_version(self):
        s = self.fresh(); path = 'records_a/module_000.py'
        self.step(s, dict(action='read', path=path, start_line=1, end_line=182))
        old = s.candidate.file_map[path].decode().splitlines(keepends=True)[0]
        self.assertTrue(self.step(s, dict(action='patch', path=path, old=old,
            new=old.replace('Exact', 'Changed'), expected_candidate_id=s.candidate.candidate_id,
            expected_file_sha256=s.candidate.file_sha256(path)))['accepted'])
        # The refreshed whole new source is in this view; old coverage alone is not enough.
        self.assertFalse(s.coverage_status()[0]['complete'])
        self.assertTrue(s.view()['phase']['required_source_delivery'][0]['complete'])
        s.ranges = []; s.delivered_sources = []
        self.assertFalse(s.view()['phase']['required_source_delivery'][0]['complete'])
        raw = s.payload('RES-0001')
        s.saved['RES-0001'] = dict(kind='saved_bytes', handle='RES-0001', offset=0, next_offset=None,
            total_bytes=len(raw), sha256=sha256_bytes(raw), exact_utf8=raw.decode())
        self.assertFalse(s.view()['phase']['required_source_delivery'][0]['complete'])

    def test_complete_historical_source_only_and_unchanged_file_across_candidates(self):
        s = self.fresh(); path = 'records_a/module_000.py'
        self.step(s, dict(action='read', path=path, start_line=1, end_line=182))
        # A constructed read is archived but has not yet been delivered. Project
        # an isolated recovery route instead of its selected direct-source body.
        self.assertFalse(s.presented_coverage)
        s.ranges = []
        raw = s.payload('RES-0001')
        page = dict(kind='saved_bytes', handle='RES-0001', offset=0, next_offset=None,
            total_bytes=len(raw), sha256=sha256_bytes(raw), exact_utf8=raw.decode())
        s.saved['RES-0001'] = {**page, 'exact_utf8':raw[:80].decode(), 'next_offset':80}
        self.assertFalse(s.view()['phase']['required_source_delivery'][0]['complete'])
        s.saved['RES-0001'] = page
        self.assertTrue(s.view()['phase']['required_source_delivery'][0]['complete'])
        s.mark_delivered(s.view())
        self.assertTrue(s.coverage_status()[0]['complete'])
        # Real C19 state contains required record bytes unchanged by the policy edit.
        actual = prospective(self.restore('after/C18-O01'))
        self.assertEqual(actual.view()['phase']['required_source_delivery'][0]['presented_ranges_including_this_input'], [[1,118]])
        actual.mark_delivered(actual.view())
        self.assertEqual(actual.coverage_status()[0]['previously_presented_ranges'], [[1,118]])

    def test_boundary_release_preserves_history_not_current_edit_authority(self):
        s = prospective(self.restore('after/C26-O02'))
        self.assertEqual(s.phase, 'D')
        self.assertFalse(s.view()['working_set']['sources'])
        self.assertTrue(all(r['complete'] for r in s.coverage_status('C')))
        before = s.candidate.candidate_id
        action = dict(action='patch', path='api/name.py', old='orbit-', new='wrong-',
            expected_candidate_id=before, expected_file_sha256=s.candidate.file_sha256('api/name.py'))
        self.assertFalse(self.step(s, action)['accepted'])
        self.assertEqual(before, s.candidate.candidate_id)
        # No prior-phase ranges become current-phase records.
        s = prospective(self.restore('after/C08-O01'))
        self.assertTrue(all(r['complete'] for r in s.coverage_status('A')))
        self.assertFalse(any(r['complete'] for r in s.view()['phase']['required_source_delivery']))

    def test_recorded_edit_target_survives_stale_region_and_rejection_stays_rejected(self):
        s = prospective(self.restore('after/C11-O02'))
        result = s.pairs[-1]['result']; action = s.pairs[-1]['response']
        self.assertEqual(s.summary(18)['path'], 'api/name.py')
        with self.assertRaises(ValueError):
            s.resolve_region(action['region'])
        self.assertEqual(s.summary(18)['candidate_id'], result['candidate_id'])
        bad = dict(action, expected_candidate_id=s.candidate.candidate_id)
        self.assertFalse(self.step(s, bad)['accepted'])
        self.assertNotIn('path', s.summary(len(s.pairs)))
        self.assertFalse(s.summary(len(s.pairs))['accepted'])
        self.assertEqual(s.summary(18)['path'], 'api/name.py')
        # Path-based patches retain their ordinary recorded presentation.
        s = prospective(self.restore('after/C18-O01'))
        self.assertEqual(s.summary(28)['path'], 'policies/current.py')

    def test_false_exact_extent_is_rejected_and_reference_describes_projection(self):
        s = self.fresh()
        self.step(s, dict(action='read', path='records_a/module_000.py', start_line=1, end_line=10))
        view = s.view(); view['working_set']['sources'][0]['content'] = 'not exact source'
        with self.assertRaisesRegex(ValueError, 'projection'):
            s.source_in_view(view)
        text = operating_reference(self.task.operating_reference())
        self.assertIn('plus the source actually in this input', text)
        self.assertNotIn('Coverage records previously delivered', text)


if __name__ == '__main__':
    unittest.main()
