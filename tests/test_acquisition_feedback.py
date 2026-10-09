"""Current extent, individual acquisition and input sizing are separate facts."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from working_set_exp.accounted_contribution import process_reply
from working_set_exp.candidate import Candidate
from working_set_exp.decision_view import receipt_view
from working_set_exp.feedback_session import FeedbackSession, operating_reference
from working_set_exp.jsonutil import canonical_json_bytes
from working_set_exp.observations import ObservationStore


class AcquisitionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ObservationStore(Path(self.temp.name) / 'observations')

    def session(self, files=None):
        return FeedbackSession(Candidate.create(files or {'a.py': b'a\nb\nc\nd\n', 'b.py': b'old\n'}),
            {'public': b'print("checked")'}, 'Contribute.', observations=self.store,
            edit_checks={}, call_limit=48, request_limit=24)

    @staticmethod
    def read(s, first=1, last=0, measure=lambda view: 1000):
        return s.execute(dict(action='read', path='a.py', start_line=first, end_line=last), measure)

    def test_requested_subrange_full_file_and_eof_clamp_are_distinct(self):
        for first, last, returned_last, whole in [(1, 0, 4, True), (2, 3, 3, False), (1, 900, 4, True)]:
            with self.subTest(first=first, last=last):
                s = self.session()
                source = self.read(s, first, last)['source']
                self.assertEqual((source['requested_start_line'], source['requested_end_line']), (first, last))
                self.assertEqual(source['returned_end_line'], returned_last)
                self.assertTrue(source['requested_extent_complete'])
                self.assertEqual(source['whole_file_shown'], whole)
                self.assertEqual(source['page_end_reason'], 'requested_extent_delivered')
                compact = s.view()['latest_feedback']['result']['source_regions'][0]
                self.assertEqual(compact['requested_extent_complete'], source['requested_extent_complete'])
                self.assertEqual(compact['whole_file_shown'], whole)

    def test_actual_page_metadata_is_present_during_whole_input_sizing(self):
        s = self.session({'a.py': b'line\n' * 20})
        trials = []
        def measure(view):
            page = view['latest_feedback']['result']['source_regions'][0]
            self.assertIn('page_end_reason', page)
            self.assertEqual(page['requested_end_line'], 20)
            trials.append(copy.deepcopy(page))
            lines = sum(row['returned_end_line'] - row['returned_start_line'] + 1
                        for row in view['working_set']['sources'])
            return 21000 + 300 * lines
        result = self.read(s, 1, 20, measure)['source']
        self.assertGreater(len(trials), 1)
        self.assertEqual(result['returned_end_line'], 5)
        self.assertFalse(result['requested_extent_complete'])
        self.assertFalse(result['whole_file_shown'])
        self.assertEqual(result['page_end_reason'], 'input_sizing_policy')
        self.assertEqual(result['content'], 'line\n' * 5)
        self.assertEqual(result['next_start_line'], 6)

    def test_merged_current_view_does_not_replace_historical_page_extent(self):
        s = self.session()
        self.read(s, 1, 2)
        exact_first = s.payload('RES-0001')
        self.read(s, 3, 3)
        view = s.view()
        self.assertEqual(view['working_set']['source_extent_scope'], 'current_selection_not_one_acquisition')
        source, = view['working_set']['sources']
        self.assertEqual((source['returned_start_line'], source['returned_end_line']), (1, 3))
        page, = view['latest_feedback']['result']['source_regions']
        self.assertEqual((page['returned_start_line'], page['returned_end_line']), (3, 3))
        self.assertEqual(s.summary(1)['returned_range'], dict(start_line=1, end_line=2))
        self.assertEqual(s.payload('RES-0001'), exact_first)
        self.assertNotIn('requested_extent_complete', source)

    def test_group_acquires_unseen_sources_but_authority_requires_delivery(self):
        s = self.session()
        r = s.execute(dict(action='work_on', sources=[dict(path=p, start_line=1, end_line=0)
            for p in ('a.py', 'b.py')], results=[]), lambda view: 1000)
        self.assertTrue(r['accepted'])
        self.assertEqual({row['path'] for row in s.view()['working_set']['sources']}, {'a.py', 'b.py'})
        self.assertTrue(all(row['requested_extent_complete'] for row in r['sources']))
        action = dict(action='patch', path='b.py', old='old', new='new',
            expected_candidate_id=s.candidate.candidate_id, expected_file_sha256=s.candidate.file_sha256('b.py'))
        original = s.candidate
        self.assertFalse(s.execute(action, lambda view: 1000)['accepted'])
        self.assertEqual(s.candidate, original)
        s.mark_delivered(s.view())
        self.assertTrue(s.execute(action, lambda view: 1000)['accepted'])
        self.assertEqual(s.candidate.file_map['b.py'], b'new\n')
        self.assertEqual(next(row['content'] for row in s.view()['working_set']['sources']
                              if row['path'] == 'b.py'), 'new\n')

    def test_exact_group_and_empty_file_are_complete_requested_extents(self):
        s = self.session({'a.py': b'', 'b.py': b'body\n'})
        empty = self.read(s)['source']
        self.assertTrue(empty['requested_extent_complete'])
        self.assertTrue(empty['whole_file_shown'])
        result = s.execute(dict(action='work_on_exact', regions=[empty['region_ref']], results=[]), lambda view: 1000)
        self.assertTrue(result['complete_requested_group'])
        self.assertEqual(result['sources'][0]['page_end_reason'], 'requested_extent_delivered')

    def test_separate_account_success_and_read_rejection_then_joint_replacement(self):
        s = self.session()
        self.read(s, 1, 2)
        before, candidate = copy.deepcopy(s.ranges), s.candidate
        feedback = []
        def crowded(view):
            latest = view['latest_feedback']['result']
            return 30000 if latest.get('accepted') and latest.get('source_regions') else 1000
        result = process_reply(s, dict(discussion='Pending question.', account='Keep this uncertainty.',
            operation=dict(action='read', path='a.py', start_line=3, end_line=4)), crowded, feedback)
        self.assertEqual([row['result']['accepted'] for row in result['operations']], [True, False])
        self.assertEqual(s.ranges, before)
        self.assertEqual(s.candidate, candidate)
        self.assertEqual(s.working_account()['text'], 'Keep this uncertainty.')
        result = process_reply(s, dict(discussion='Replace the group.', account='Retain the question.',
            operation=dict(action='work_on', sources=[dict(path='b.py', start_line=1, end_line=0)], results=[])),
            lambda view: 1000, feedback)
        self.assertEqual([row['result']['accepted'] for row in result['operations']], [True, True])
        self.assertEqual(s.ranges, [dict(path='b.py', start_line=1, end_line=1)])
        self.assertEqual(s.candidate, candidate)

    def test_invalid_joint_group_preserves_account_and_selected_sources(self):
        s = self.session()
        self.read(s)
        s.execute(dict(action='record_account', text='Original uncertainty.'), lambda view: 1000)
        before = (s.candidate, copy.deepcopy(s.ranges), s.working_account())
        result = process_reply(s, dict(discussion='Request invalid range.', account='New account.',
            operation=dict(action='work_on', sources=[dict(path='b.py', start_line=99, end_line=0)], results=[])),
            lambda view: 1000, [])
        self.assertFalse(result['operations'][0]['result']['accepted'])
        self.assertEqual((s.candidate, s.ranges, s.working_account()), before)

    def test_old_receipt_projection_does_not_invent_new_acquisition_facts(self):
        s = self.session()
        result = self.read(s)
        historical = copy.deepcopy(s.last)
        for key in ('requested_start_line', 'requested_end_line', 'requested_extent_complete', 'page_end_reason'):
            historical['result']['source'].pop(key)
        raw = canonical_json_bytes(historical)
        shown = receipt_view(historical)['result']['source_regions'][0]
        self.assertNotIn('requested_extent_complete', shown)
        self.assertEqual(canonical_json_bytes(historical), raw)
        reference = operating_reference(['public'])
        self.assertIn('including source not previously read', reference)
        self.assertIn('may merge several acquired pages and refresh after edits', reference)
        self.assertIn('not a proof that no larger page could fit the hard ceiling', reference)


if __name__ == '__main__':
    unittest.main()
