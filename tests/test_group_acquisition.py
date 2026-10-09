"""Complete requested small regions without displacing an admitted page."""
import copy
import tempfile
import unittest
from pathlib import Path

from working_set_exp.accounted_contribution import process_reply
from working_set_exp.candidate import Candidate
from working_set_exp.decision_session import DecisionSession
from working_set_exp.feedback_session import FeedbackSession, operating_reference
from working_set_exp.jsonutil import canonical_json_bytes
from working_set_exp.observations import ObservationStore


class GroupAcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def session(self, files=None, kind=FeedbackSession):
        return kind(Candidate.create(files or {'small.py': b'first\nsecond\n', 'bulk.py': b'bulk\n' * 100}),
            {'public': b'print("checked")'}, 'Keep exact work.', edit_checks={},
            observations=ObservationStore(Path(self.temp.name) / 'observations'), call_limit=80, request_limit=40)

    @staticmethod
    def group(*spans, results=()):
        return dict(action='work_on', sources=[dict(path=p, start_line=a, end_line=b) for p, a, b in spans],
                    results=list(results))

    @staticmethod
    def extents(view):
        return {row['path']: row['returned_end_line'] - row['returned_start_line'] + 1
                for row in view['working_set']['sources']}

    def measure(self, view):
        n = self.extents(view)
        return 22000 + 100 * n.get('bulk.py', 0) + n.get('small.py', 0)

    def test_completion_preserves_every_bulk_byte_saved_record_and_archive(self):
        s = self.session()
        s.execute(dict(action='record_account', text='A specific unresolved question.'), lambda v: 1000)
        history = canonical_json_bytes(s.pairs)
        action = self.group(('bulk.py', 1, 100), ('small.py', 1, 2), results=['EVT-0001'])
        baseline = s.clone()
        baseline.__class__ = DecisionSession
        before = baseline.execute(action, self.measure)
        result = s.execute(action, self.measure)
        self.assertEqual(before['sources'][1]['returned_end_line'], 1)
        self.assertEqual(result['sources'][0]['content'], before['sources'][0]['content'])
        self.assertEqual(result['sources'][1]['content'], 'first\nsecond\n')
        self.assertTrue(result['sources'][1]['requested_extent_complete'])
        self.assertEqual(s.saved, baseline.saved)
        self.assertEqual(canonical_json_bytes(s.pairs[:-1]), history)
        self.assertEqual(s.working_account()['text'], 'A specific unresolved question.')
        self.assertLessEqual(self.measure(s.view()), 22784)
        self.assertEqual(len(s.pairs), 2)

    def test_individual_regions_of_one_file_survive_completion_without_widening_gaps(self):
        s = self.session({'small.py': b'1\n2\n3\n4\n5\n6\n7\n8\n9\n10\n', 'bulk.py': b'bulk\n' * 100})
        result = s.execute(self.group(('small.py', 1, 2), ('small.py', 9, 10), ('bulk.py', 1, 100)), self.measure)
        self.assertEqual([r['content'] for r in result['sources'][:2]], ['1\n2\n', '9\n10\n'])
        self.assertEqual([r for r in s.ranges if r['path'] == 'small.py'], [
            dict(path='small.py', start_line=1, end_line=2), dict(path='small.py', start_line=9, end_line=10)])
        self.assertEqual([r['returned_end_line'] for r in s.summary(1)['returned_sources'][:2]], [2, 10])
        s.mark_delivered(s.view())
        result = s.execute(dict(action='patch', path='small.py', old='5\n', new='changed\n',
            expected_candidate_id=s.candidate.candidate_id, expected_file_sha256=s.candidate.file_sha256('small.py')),
            lambda v: 1000)
        self.assertFalse(result['accepted'])

    def test_completion_does_not_spend_margin_that_initial_page_preserved(self):
        s = self.session()
        def near_preferred(view):
            n = self.extents(view)
            return 22000 + 78 * n.get('bulk.py', 0) + (500 if n.get('small.py') == 2 else 1)
        result = s.execute(self.group(('bulk.py', 1, 100), ('small.py', 1, 2)), near_preferred)
        self.assertEqual(result['sources'][1]['returned_end_line'], 1)
        self.assertEqual(result['sources'][0]['returned_end_line'], 10)
        self.assertEqual({r['margin'] for r in s.admissions}, {1024})
        self.assertTrue(any(22784 < r['prompt_tokens'] <= 23808 for r in s.admissions))

    def test_hard_fallback_completion_uses_the_already_accepted_hard_margin(self):
        s = self.session()
        def near_hard(view):
            n = self.extents(view)
            return 23500 + 100 * n.get('bulk.py', 0) + n.get('small.py', 0)
        result = s.execute(self.group(('bulk.py', 1, 100), ('small.py', 1, 2)), near_hard)
        self.assertEqual(result['sources'][0]['returned_end_line'], 3)
        self.assertEqual(result['sources'][1]['returned_end_line'], 2)
        self.assertEqual({r['margin'] for r in s.admissions}, {0})
        self.assertLessEqual(near_hard(s.view()), 23808)

    def test_joint_account_recovery_group_admits_complete_final_arrangement(self):
        s = self.session()
        s.execute(dict(action='read', path='bulk.py', start_line=1, end_line=100), lambda v: 1000)
        s.enter_recovery('Actual prior capacity obstacle.')
        s.mark_delivered(s.view())
        prior = canonical_json_bytes(s.pairs)
        s.begin_request()
        feedback = []
        def measure(view):
            self.assertEqual(view['working_account']['text'], 'Preserve this pending distinction.')
            self.assertEqual(feedback[0]['action_summary']['action'], 'record_account')
            return self.measure(view)
        result = process_reply(s, dict(discussion='Replace broad support.', account='Preserve this pending distinction.',
            operation=self.group(('bulk.py', 1, 100), ('small.py', 1, 2))), measure, feedback)
        self.assertEqual([r['result']['accepted'] for r in result['operations']], [True, True])
        self.assertEqual(canonical_json_bytes(s.pairs[:-2]), prior)
        self.assertFalse(s.recovery)
        self.assertEqual(s.sources()[-1]['content'], 'first\nsecond\n')
        self.assertEqual(s.delivered_sources, [])
        s.mark_delivered(s.view())
        self.assertEqual(len(s.delivered_sources), 2)

    def test_group_rows_describe_historical_version_not_refreshed_current_source(self):
        s = self.session()
        original = s.candidate.candidate_id
        s.execute(self.group(('small.py', 2, 2)), lambda v: 1000)
        row, archive = s.summary(1), s.payload('RES-0001')
        self.assertEqual(row['returned_candidate_id'], original)
        self.assertEqual(row['returned_sources'], [dict(path='small.py', returned_start_line=2, returned_end_line=2,
            requested_start_line=2, requested_end_line=2, requested_extent_complete=True)])
        s.mark_delivered(s.view())
        edit = s.execute(dict(action='patch', path='small.py', old='second\n', new='new\nextra\n',
            expected_candidate_id=original, expected_file_sha256=s.candidate.file_sha256('small.py')), lambda v: 1000)
        self.assertTrue(edit['accepted'])
        self.assertEqual(s.summary(1), row)
        self.assertEqual(s.payload('RES-0001'), archive)
        self.assertNotEqual(s.sources()[0]['candidate_id'], original)
        self.assertEqual(s.sources()[0]['returned_end_line'], 3)
        s.execute(self.group(), lambda v: 1000)
        s.mark_delivered(s.view())
        self.assertEqual(s.delivered_sources, [])
        self.assertEqual(s.summary(1), row)

    def test_exact_empty_overlap_and_rejection_have_truthful_group_rows(self):
        s = self.session({'small.py': b'', 'bulk.py': b'1\n2\n3\n'})
        result = s.execute(self.group(('small.py', 1, 0), ('bulk.py', 1, 2), ('bulk.py', 2, 3)), lambda v: 1000)
        self.assertTrue(all(r['requested_extent_complete'] for r in result['sources']))
        references = [r['region_ref'] for r in result['sources']]
        s.execute(dict(action='work_on_exact', regions=references, results=[]), lambda v: 1000)
        row = s.summary(2)
        self.assertTrue(row['complete_requested_group'])
        self.assertEqual([(r['returned_start_line'], r['returned_end_line']) for r in row['returned_sources']],
                         [(1, 0), (1, 2), (2, 3)])
        before = copy.deepcopy(s.ranges)
        s.execute(self.group(('bulk.py', 900, 0)), lambda v: 1000)
        self.assertFalse(s.summary(3)['accepted'])
        self.assertNotIn('returned_sources', s.summary(3))
        self.assertEqual(s.ranges, before)

    def test_recent_ranges_are_in_measured_view_and_history_stays_bounded(self):
        s = self.session()
        seen = []
        def measure(view):
            row = view['recent_activity'][-1]
            self.assertIn('returned_sources', row)
            self.assertIn('returned_candidate_id', row)
            seen.append(copy.deepcopy(row))
            return self.measure(view)
        for _ in range(9):
            s.execute(self.group(('bulk.py', 1, 100), ('small.py', 1, 2)), measure)
        self.assertTrue(seen)
        self.assertLessEqual(len(s.view()['recent_activity']), 6)
        self.assertEqual(len(s.pairs), 9)
        self.assertIn('not current visibility, editing authority or task completion', operating_reference(['public']))


if __name__ == '__main__':
    unittest.main()
