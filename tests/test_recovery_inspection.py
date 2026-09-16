"""Recovery must permit a requested inspection without unrequested bulk revival."""
import copy
import unittest

from working_set_exp.candidate import Candidate
from working_set_exp.recovery_inspection_session import RecoveryInspectionSession
from test_decision_interface import DecisionTests


class RecoveryInspectionTests(unittest.TestCase):
    setUp = DecisionTests.setUp

    def session(self):
        source = ''.join(f'line_{i} = {i}\n' for i in range(1, 181))
        session = RecoveryInspectionSession(Candidate.create({'app.py':source.encode()}),
            {'public':b'print("ok")'}, 'Contribute.', observations=self.store,
            edit_checks={}, call_limit=72, request_limit=24)
        session.enter_recovery('fixture')
        result = self.read(session, 1, 180, lambda v:1000)
        self.assertTrue(result['accepted'])
        return session

    @staticmethod
    def read(session, first, last, measure=lambda v:1000):
        return session.execute(dict(action='read', path='app.py', start_line=first, end_line=last), measure)

    @staticmethod
    def capacity(view):
        size = sum(len(s['content']) for s in view['working_set']['sources'])
        return 1000 if size < 500 else 24000

    def test_omitted_bulk_stays_designated_but_small_inspection_fits(self):
        session = self.session()
        old_regions = copy.deepcopy(session.ranges)
        old_candidate = session.candidate.candidate_id
        ref = session.view()['working_set']['sources'][0]['region_ref']
        self.assertTrue(session._fits_feedback(self.capacity))
        self.assertEqual(session.view()['working_set']['sources'], [])
        session.mark_delivered(session.view())
        result = self.read(session, 10, 14, self.capacity)
        self.assertTrue(result['accepted'])
        source, = session.view()['working_set']['sources']
        self.assertEqual((source['returned_start_line'],source['returned_end_line']), (10,14))
        self.assertEqual(session.ranges, old_regions)
        self.assertEqual(session.candidate.candidate_id, old_candidate)
        self.assertTrue(session.view()['presentation']['selected_bodies_omitted'])
        self.assertEqual(session.resolve_region(ref), dict(path='app.py',start_line=1,end_line=180))
        session.mark_delivered(session.view())
        result = session.execute(dict(action='replace_region', region=ref,
            expected_candidate_id=old_candidate, new='x = 1\n'), self.capacity)
        self.assertFalse(result['accepted'])
        self.assertIn('not visible', result['error'])

    def test_overlapping_and_contained_reads_are_one_current_body(self):
        session = self.session()
        session._fits_feedback(self.capacity)
        self.assertTrue(self.read(session,10,14,self.capacity)['accepted'])
        first = session.view()['working_set']['sources'][0]['region_ref']
        self.assertTrue(self.read(session,12,18,self.capacity)['accepted'])
        self.assertTrue(self.read(session,13,14,self.capacity)['accepted'])
        source, = session.view()['working_set']['sources']
        self.assertEqual((source['returned_start_line'],source['returned_end_line']), (10,18))
        self.assertEqual(session.resolve_region(first), dict(path='app.py',start_line=10,end_line=14))
        clone=session.clone()
        self.assertEqual(clone.parked_source_regions,session.parked_source_regions)
        clone.parked_source_regions=()
        self.assertTrue(session.parked_source_regions)

    def test_visible_comparison_partner_survives_then_fallback_can_inspect_again(self):
        session = self.session()
        session._fits_feedback(self.capacity)
        self.assertTrue(self.read(session,10,14,self.capacity)['accepted'])
        self.assertTrue(self.read(session,50,53,self.capacity)['accepted'])
        self.assertEqual([(s['returned_start_line'],s['returned_end_line']) for s in session.view()['working_set']['sources']],[(10,14),(50,53)])
        self.assertTrue(session._fits_feedback(lambda v:24000 if v['working_set']['sources'] else 1000))
        self.assertTrue(self.read(session,170,174,self.capacity)['accepted'])
        self.assertEqual(len(session.view()['working_set']['sources']),1)
        self.assertEqual(session.ranges,[dict(path='app.py',start_line=1,end_line=180)])

    def test_edit_refresh_stale_address_and_exact_group_transition(self):
        session = self.session()
        session._fits_feedback(self.capacity)
        self.assertTrue(self.read(session,10,14,self.capacity)['accepted'])
        source,=session.view()['working_set']['sources']
        old_ref=source['region_ref']
        session.mark_delivered(session.view())
        result=session.execute(dict(action='replace_region',region=old_ref,
            expected_candidate_id=session.candidate.candidate_id,
            new=source['content'].replace('line_11 = 11','line_11 = 110\nextra = 1')),self.capacity)
        self.assertTrue(result['accepted'])
        with self.assertRaisesRegex(ValueError,'stale'):
            session.resolve_region(old_ref)
        source,=session.view()['working_set']['sources']
        self.assertEqual((source['returned_start_line'],source['returned_end_line']),(10,15))
        current=source['region_ref']
        result=session.execute(dict(action='work_on_exact',regions=[current],results=[]),self.capacity)
        self.assertTrue(result['accepted'])
        self.assertFalse(session.recovery)
        self.assertEqual(session.view()['working_set']['sources'][0]['region_ref'],current)


if __name__=='__main__':
    unittest.main()
