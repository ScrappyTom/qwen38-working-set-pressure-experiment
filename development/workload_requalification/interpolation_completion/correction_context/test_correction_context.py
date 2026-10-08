"""Transition and source-authority checks; synthetic counts are not native fit."""
import copy
from pathlib import Path
import tempfile
import unittest

import study
from correction_context import CorrectionContextMixin
from working_set_exp.candidate import Candidate
from working_set_exp.coherent_diagnostic_session import CoherentDiagnosticSession
from working_set_exp.observations import ObservationStore


class Session(CorrectionContextMixin, CoherentDiagnosticSession):
    pass


class CorrectionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.session = Session(Candidate.create({'app.py': b'a = 1\nb = 2\nc = 3\n'}),
            {'public': b'print("ok")', 'failed': b'raise AssertionError("ordinary failure")'},
            'Edit a source.', observations=ObservationStore(Path(self.temp.name)),
            edit_checks={}, call_limit=40)
        self.session.execute(dict(action='read', path='app.py', start_line=1, end_line=3), lambda v: 100)
        self.session.mark_delivered(self.session.view())

    def patch(self, old='b = 2\n', new='b = 4\nx = 5\n'):
        s = self.session
        return dict(action='patch', path='app.py', old=old, new=new,
                    expected_candidate_id=s.candidate.candidate_id,
                    expected_file_sha256=s.candidate.file_sha256('app.py'))

    @staticmethod
    def recovery_only(view):
        return 1000 if view['presentation']['mode'] == 'recovery' else 24000

    def test_changed_lines_and_delivery_authority(self):
        s = self.session
        self.assertTrue(s.execute(self.patch(), self.recovery_only)['accepted'])
        source, = s.view()['working_set']['sources']
        self.assertEqual((source['returned_start_line'], source['returned_end_line']), (2, 3))
        self.assertEqual(source['content'], 'b = 4\nx = 5\n')
        self.assertEqual(s.ranges, [dict(path='app.py', start_line=1, end_line=4)])
        # Constructing the new view is not delivery; old authority must fail.
        rejected = s.clone().execute(self.patch('b = 4', 'b = 6'), self.recovery_only)
        self.assertFalse(rejected['accepted'])
        s.mark_delivered(s.view())
        self.assertTrue(s.execute(self.patch('b = 4', 'b = 6'), self.recovery_only)['accepted'])
        self.assertEqual(s.candidate.file_map['app.py'], b'a = 1\nb = 6\nx = 5\nc = 3\n')

    def test_failed_and_passed_checks_keep_exact_focus(self):
        s = self.session
        s.execute(self.patch(), self.recovery_only)
        expected = copy.deepcopy(s.view()['working_set']['sources'])
        for scope in ('failed', 'public'):
            result = s.execute(dict(action='check', check_id=scope,
                                    expected_candidate_id=s.candidate.candidate_id), self.recovery_only)
            self.assertTrue(result['executed'])
            self.assertEqual(result['passed'], scope == 'public')
            self.assertEqual(s.view()['working_set']['sources'], expected)
            self.assertTrue(s.observations.read(result['observation'])['capture_complete'])

    def test_full_region_fallback(self):
        s = self.session
        def limited(view):
            if view['presentation']['mode'] == 'ordinary': return 24000
            size = sum(len(r['content']) for r in view['working_set']['sources'])
            return 24000 if size > 20 else 1000
        s.execute(self.patch(new='x = 0\n' * 30), limited)
        self.assertEqual(s.view()['working_set']['sources'], [])
        self.assertTrue(s.recovery)
        self.assertEqual(s.candidate.file_map['app.py'].count(b'x = 0'), 30)
        self.assertFalse(s.clone().execute(self.patch('a = 1', 'a = 9'), limited)['accepted'])

    def test_existing_inspection_is_not_evicted_for_new_target(self):
        s = self.session
        s.enter_recovery('engineering capacity state')
        s.recovery_focus = [dict(path='app.py', start_line=1, end_line=1)]
        def limited(view):
            size = sum(len(r['content']) for r in view['working_set']['sources'])
            return 24000 if size > 20 else 1000
        s.execute(self.patch(new='x = 0\n' * 30), limited)
        self.assertEqual(s.view()['working_set']['sources'][0]['content'], 'a = 1\n')
        self.assertEqual(s.recovery_focus, [dict(path='app.py', start_line=1, end_line=1)])

    def test_rejected_and_deleted_edits_supply_no_invented_target(self):
        s = self.session
        stale = self.patch(); stale['expected_candidate_id'] = '0' * 64
        self.assertFalse(s.execute(stale, self.recovery_only)['accepted'])
        self.assertIsNone(s.recent_replacement())
        # Re-deliver the source before a valid deletion.
        s.execute(dict(action='read', path='app.py', start_line=1, end_line=3), lambda v:100)
        s.mark_delivered(s.view())
        s.execute(self.patch(new=''), self.recovery_only)
        self.assertIsNone(s.recent_replacement())

    def test_region_replacement_preserves_actual_separator(self):
        s = self.session
        s.execute(dict(action='work_on', sources=[dict(path='app.py', start_line=2, end_line=2)], results=[]), lambda v:100)
        s.mark_delivered(s.view())
        region = s.view()['working_set']['sources'][0]['region_ref']
        result = s.execute(dict(action='replace_region', region=region,
            expected_candidate_id=s.candidate.candidate_id, new='b = 8\ny = 9'), self.recovery_only)
        self.assertTrue(result['accepted'])
        self.assertEqual(result['supplied_boundary_separator'], '\n')
        self.assertEqual(s.view()['working_set']['sources'][0]['content'], 'b = 8\ny = 9\n')

    def test_ordinary_view_unchanged_and_selection_can_replace(self):
        s = self.session
        s.execute(self.patch(), lambda v:100)
        self.assertFalse(s.recovery)
        self.assertEqual(s.recovery_focus, [])
        s.execute(dict(action='work_on', sources=[dict(path='app.py', start_line=1, end_line=1)], results=[]), lambda v:100)
        self.assertEqual(s.view()['working_set']['sources'][0]['content'], 'a = 1\n')

    def test_actual_failed_check_state_preserves_all_recorded_facts(self):
        task, s, feedback = study.restored()
        before = copy.deepcopy(task.snapshot(s))
        self.assertEqual(s.view()['working_set']['sources'], [])
        self.assertTrue(s._fits_feedback(lambda v: 1000))
        source, = s.view()['working_set']['sources']
        self.assertEqual((source['returned_start_line'],source['returned_end_line']), (2204,2356))
        self.assertIn('except configparser.InterpolationMissingOptionError as e:', source['content'])
        for field in ('pairs','candidate_id','source_versions','ranges','saved','diffs','delivered_sources'):
            self.assertEqual(task.snapshot(s)[field], before[field])
        self.assertEqual(len(feedback), 2)
        self.assertFalse(s.pairs[-1]['result']['passed'])
        self.assertTrue(s.observations.read('CHK-0150')['capture_complete'])
        # The existing checkpoint machinery must preserve the admitted focus.
        restored = task.restore(task.snapshot(s), s.candidate, task.RUN, replay=True)
        self.assertEqual(restored.view()['working_set']['sources'], s.view()['working_set']['sources'])


if __name__ == '__main__': unittest.main()
