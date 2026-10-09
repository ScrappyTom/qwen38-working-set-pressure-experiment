"""Actual E17 transcription failure and current-state guard recovery, without inference."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from working_set_exp.candidate import Candidate
from working_set_exp.feedback_session import FeedbackSession
from working_set_exp.observations import ObservationStore

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT / 'development/workload_requalification/historical_action_entry/run-001'


class BindingDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        row = json.loads((OLD / 'starting-candidate.json').read_text())
        self.session = FeedbackSession(Candidate.create({r['path']: r['content_utf8'].encode() for r in row['files']}),
            {'public': b'print("passed")'}, 'Repair the target.', edit_checks={}, call_limit=24, request_limit=8,
            observations=ObservationStore(Path(self.temp.name) / 'observations'))
        self.measure = lambda value: len(json.dumps(value)) // 3 + 1000
        self.session.execute(dict(action='read', path='report.py', start_line=1, end_line=0), self.measure)
        self.session.mark_delivered(self.session.view())
        self.action = json.loads((OLD / 'calls/C03-reply.json').read_text())['operation']

    def test_actual_file_copy_error_delivers_specific_feedback_and_corrects_without_read(self):
        s = self.session
        candidate, ranges, authority = s.candidate, copy.deepcopy(s.ranges), copy.deepcopy(s.delivered_sources)
        result = s.execute(self.action, self.measure)
        self.assertFalse(result['accepted'])
        self.assertEqual(result['mismatched_bindings'], ['expected_file_sha256'])
        self.assertEqual(result['binding_matches'], dict(expected_candidate_id=True, expected_file_sha256=False))
        self.assertEqual(s.candidate, candidate)
        self.assertEqual(s.ranges, ranges)
        self.assertEqual(s.delivered_sources, authority)
        view = s.view()
        self.assertEqual(view['latest_feedback']['result'], result)
        self.assertNotIn('stale', result['error'])
        s.mark_delivered(view)
        corrected = {**self.action, 'expected_file_sha256': s.candidate.file_sha256('report.py')}
        self.assertTrue(s.execute(corrected, self.measure)['accepted'])
        self.assertEqual(s.candidate.file_map['report.py'], b'def restored_marker() -> str:\n    return "ARCHIVE-Z7"\n')
        self.assertEqual(s.candidate.file_map['archive/source.dat'], candidate.file_map['archive/source.dat'])

    def test_candidate_only_and_real_old_version_report_actual_comparisons(self):
        s = self.session
        action = {**self.action, 'expected_file_sha256': s.candidate.file_sha256('report.py')}
        result = s.execute({**action, 'expected_candidate_id': '0' * 64}, self.measure)
        self.assertEqual(result['mismatched_bindings'], ['expected_candidate_id'])
        self.assertEqual(result['binding_matches'], dict(expected_candidate_id=False, expected_file_sha256=True))
        self.assertTrue(s.execute(action, self.measure)['accepted'])
        successor = s.candidate
        rejected = s.execute(action, self.measure)
        self.assertEqual(rejected['mismatched_bindings'], ['expected_candidate_id', 'expected_file_sha256'])
        self.assertEqual(s.candidate, successor)

    def test_correct_bindings_still_do_not_authorize_undelivered_source(self):
        s = self.session
        s.delivered_sources = []
        action = {**self.action, 'expected_file_sha256': s.candidate.file_sha256('report.py')}
        original = s.candidate
        result = s.execute(action, self.measure)
        self.assertFalse(result['accepted'])
        self.assertNotEqual(result.get('rejection_code'), 'binding_mismatch')
        self.assertEqual(s.candidate, original)


if __name__ == '__main__':
    unittest.main()
