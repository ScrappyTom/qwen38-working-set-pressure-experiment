"""Earned boundary regressions, including real saved states and partial coverage."""
import json
from pathlib import Path
import tempfile
import unittest

from working_set_exp import decision_view, feedback_assessment
from working_set_exp.candidate import Candidate
from working_set_exp.feedback_session import FeedbackSession
from working_set_exp.jsonutil import sha256_bytes
from working_set_exp.observations import ObservationStore
import test_decision_interface as legacy_tests

ROOT = Path(__file__).resolve().parents[1]
OLD = ROOT/'development/decision_interface/channel_repair/run-001'


class FeedbackTests(unittest.TestCase):
    setUp = legacy_tests.DecisionTests.setUp
    read = legacy_tests.DecisionTests.read

    def session(self, files=None, code=b'print("observed")', **kwargs):
        files = files or {'app.py':b'value = 2\n','test.py':b'assert 2 == 2\n'}
        return FeedbackSession(Candidate.create(files),
            {'tests':code,'public':code}, 'Contribute.',observations=self.store,
            edit_checks={'test.py':'tests'} if 'test.py' in files else {},call_limit=48,request_limit=16,**kwargs)

    def test_saved_failure_has_primary_diagnostic_truthful_counts_and_blocked_mutations(self):
        value=feedback_assessment.overview(feedback_assessment.assessment(ObservationStore(OLD/'observations',replay=True),'CHK-0015'))
        rows={r['criterion']:r for r in value['criteria']}
        self.assertIn('ValueError not raised', rows['edited_suite.execution']['diagnostics'][0]['diagnostic']['text'])
        self.assertEqual((rows['required_paths']['missing_paths_total'],rows['required_paths']['missing_paths_shown'],
                          rows['required_paths']['missing_paths_remaining']),(17,2,15))
        for row in value['criteria']:
            if row['criterion'].startswith('detect.'):
                self.assertIsNone(row['fault_detected'])
                self.assertIsNone(row['met'])
        self.assertNotIn('additional_missing_paths',rows['required_paths'])
        self.assertFalse(value['normal_control_passed'])

    def test_all_check_pages_reconstruct_without_silently_losing_list_totals(self):
        store=ObservationStore(OLD/'observations',replay=True)
        rows=[];offset=0
        while True:
            page=feedback_assessment.inspect_check(store,'CHK-0015',offset)
            rows+=page['entries']
            if page['next_offset'] is None:break
            offset=page['next_offset']
        self.assertEqual(rows,feedback_assessment.assessment(store,'CHK-0015')['criteria'])
        self.assertEqual(next(r for r in rows if r['criterion']=='required_paths')['missing_paths_remaining'],1)

    def test_ambiguous_hidden_match_is_addressed_and_reusable_but_not_edit_authority(self):
        s=self.session(files={'app.py':b'same = 1\nother = 2\nsame = 1\n'})
        self.read(s,'app.py',1,1);s.mark_delivered(s.view())
        action=dict(action='patch',path='app.py',expected_candidate_id=s.candidate.candidate_id,
            expected_file_sha256=s.candidate.file_sha256('app.py'),old='same = 1',new='same = 3')
        result=s.execute(action,lambda v:1000)
        self.assertEqual(result['match_count'],2)
        self.assertEqual(result['rejection_code'],'ambiguous_old')
        self.assertEqual([r['start_line'] for r in result['match_regions']],[1,3])
        hidden=result['match_regions'][1]['region_ref']
        edit=dict(action='replace_region',region=hidden,expected_candidate_id=s.candidate.candidate_id,new='same = 3')
        self.assertFalse(s.execute(edit,lambda v:1000)['accepted'])
        s.execute(dict(action='work_on_exact',regions=[hidden],results=[]),lambda v:1000)
        s.mark_delivered(s.view())
        self.assertTrue(s.execute(edit,lambda v:1000)['accepted'])
        self.assertEqual(s.candidate.file_map['app.py'],b'same = 1\nother = 2\nsame = 3')

    def test_rejection_causes_stale_guard_and_repeated_anchor_are_distinct(self):
        s=self.session(files={'app.py':b'x\nx\nx\nx\nx\n'})
        action=dict(action='patch',path='app.py',expected_candidate_id=s.candidate.candidate_id,
            expected_file_sha256=s.candidate.file_sha256('app.py'),old='x',new='y')
        first=s.execute(action,lambda v:1000)
        self.assertEqual((first['match_count'],first['matches_shown'],first['matches_remaining']),(5,4,1))
        again=s.execute(action,lambda v:1000)
        self.assertEqual(again['same_old_as_rejected_action'],'EVT-0001')
        for changes,code in ((dict(old='z'),'old_not_found'),(dict(new='x'),'unchanged_replacement'),
                             (dict(old=''),'empty_anchor'),(dict(expected_candidate_id='0'*64),'stale_binding')):
            self.assertEqual(s.execute({**action,**changes},lambda v:1000)['rejection_code'],code)

    def test_non_eof_literal_boundary_preserves_proposal_and_following_line(self):
        for ending in ('\n','\r\n'):
            with self.subTest(ending=ending):
                s=self.session(files={'app.py':('old'+ending+'tail'+ending).encode()})
                self.read(s,'app.py',1,1);s.mark_delivered(s.view())
                ref=s.view()['working_set']['sources'][0]['region_ref']
                header=dict(discussion='Edit one complete line.',operation=dict(action='replace_region',region=ref,
                    expected_candidate_id=s.candidate.candidate_id))
                reply=decision_view.decode_reply(json.dumps(header)+'\nSOURCE\nnew')
                result=s.execute(reply['operation'],lambda v:1000)
                self.assertEqual(result['supplied_boundary_separator'],ending)
                self.assertEqual(s.pairs[-1]['response']['new'],'new')
                self.assertEqual(s.candidate.file_map['app.py'],('new'+ending+'tail'+ending).encode())
                self.assertEqual(result['proposed_text_sha256'],sha256_bytes(b'new'))

    def test_empty_deletion_eof_and_explicit_blank_lines_stay_exact(self):
        for first,last,new,expected in ((1,1,'',b'tail\n'),(2,2,'last',b'old\nlast'),(1,1,'new\n\n',b'new\n\ntail\n')):
            s=self.session(files={'app.py':b'old\ntail\n'})
            self.read(s,'app.py',first,last);s.mark_delivered(s.view())
            ref=s.view()['working_set']['sources'][0]['region_ref']
            r=s.execute(dict(action='replace_region',region=ref,expected_candidate_id=s.candidate.candidate_id,new=new),lambda v:1000)
            self.assertTrue(r['accepted']);self.assertEqual(s.candidate.file_map['app.py'],expected)
            self.assertEqual(r['supplied_boundary_separator'],'')

    def test_range_and_file_completeness_are_distinct_in_recovery_and_after_edit(self):
        s=self.session(files={'app.py':b'one\ntwo\nthree\n','empty.py':b''})
        self.read(s,'app.py',1,2)
        v=s.view();row=v['visibility']['retained_inventory']['entries'][0]
        self.assertTrue(row['selected_extent_shown_in_full']);self.assertFalse(row['whole_file_shown'])
        self.assertEqual(row['file_total_lines'],3)
        s.enter_recovery('test');v=s.view()
        self.assertFalse(v['visibility']['retained_inventory']['entries'][0]['selected_extent_shown_in_full'])
        self.read(s,'empty.py');source=next(r for r in s.view()['working_set']['sources'] if r['path']=='empty.py')
        self.assertEqual(source['file_total_lines'],0);self.assertTrue(source['whole_file_shown'])


class TaskCheckerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        import feedback_task as task
        cls.task=task
        cls.temp=tempfile.TemporaryDirectory()
        cls.store=ObservationStore(Path(cls.temp.name)/'observations')
        cls.initial=task.Task().initial_session().candidate

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def check(self,files,tag):
        c=Candidate.create(files,max_file_bytes=self.initial.max_file_bytes)
        record=self.store.execute(c,self.task.checker('public'),'public',tag)
        raw=json.loads((self.store.directory(tag)/'stdout.bin').read_bytes())
        return record,raw

    def test_prior_partial_contribution_is_not_complete_coverage(self):
        raw=json.loads((OLD/'final-candidate.json').read_text())
        files={f['path']:f['content_utf8'].encode() for f in raw['files']}
        record,value=self.check(files,'CHK-0001')
        self.assertFalse(record['passed'])
        self.assertTrue(value['observed_paths']['successful'])
        faults=value['fault_sensitivity']['error_class']
        missed=[r['target'] for r in faults['targets'] if not r['detected']]
        self.assertEqual(len(missed),6)
        self.assertTrue(all(r[1]=='bytes' for r in missed))
        self.assertFalse(value['tests_passed'])
        self.assertTrue(value['documentation_changes'])
        report=feedback_assessment.overview(feedback_assessment.assessment(self.store,'CHK-0001'))
        criterion=next(r for r in report['criteria'] if r['criterion']=='detect.error_class')
        self.assertEqual(criterion['undetected_targets_total'],6)

    def test_reference_contribution_and_api_only_partial_assertion(self):
        files=self.initial.file_map
        reference=(ROOT/'development/working_account/url_ports/REFERENCE_TEST.py').read_bytes()
        files[self.task.TEST] += b'\n'+reference
        doc=(ROOT/'development/working_account/url_ports/REFERENCE_DOC.txt').read_bytes()
        files[self.task.DOC]=files[self.task.DOC].replace(b'URL Parsing\n-----------\n',doc+b'\nURL Parsing\n-----------\n',1)
        record,value=self.check(files,'CHK-0002')
        self.assertTrue(record['passed'],value)
        self.assertEqual(sum(len(r['targets']) for r in value['fault_sensitivity'].values()),72)
        # Keep exact-class assertions only on one API. Path execution alone must
        # not make the other API's missing assertions look complete.
        partial=reference.replace(b'self.assertIs(type(caught.exception), ValueError)',
            b"self.assertTrue(api is urllib.parse.urlparse or type(caught.exception) is ValueError)")
        files[self.task.TEST]=self.initial.file_map[self.task.TEST]+b'\n'+partial
        record,value=self.check(files,'CHK-0003')
        self.assertFalse(record['passed'])
        missed=[r['target'] for r in value['fault_sensitivity']['error_class']['targets'] if not r['detected']]
        self.assertEqual(len(missed),7)
        self.assertTrue(all(r[0]=='urlparse' for r in missed))


if __name__=='__main__':
    unittest.main()
