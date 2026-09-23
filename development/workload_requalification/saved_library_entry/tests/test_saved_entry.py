import json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import saved_task as s

class EntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.session=s.Task().initial_session()
    def test_exact_historical_entry_and_new_allowance(self):
        x=self.session;candidate,pairs=s.historical.starting_evidence()
        self.assertEqual(x.candidate,candidate);self.assertEqual(x.pairs,pairs)
        self.assertEqual((x.requests_used,x.calls_used,x.starting_archive_length),(0,0,32))
        self.assertEqual((x.request_limit,x.call_limit),(32,96))
        self.assertFalse(x.ranges or x.saved or x.working_account())
        self.assertEqual(x.task,(s.historical.AREA/'TASK.txt').read_text())
    def test_historical_check_is_not_new_observation(self):
        x=self.session;check=x.view()['verification']['checks']['public']
        self.assertFalse(check['passed']);self.assertTrue(check['candidate_matches'])
        self.assertFalse(check['check_definition_matches'] or check['applies_to_current'])
        self.assertIn('assessment_unavailable',check)
        result=json.loads(x.payload('RES-0030'))
        self.assertEqual(result,x.pairs[29]['result'])
        self.assertFalse(result['streams_truncated'])
        self.assertEqual(len(result['stdout'].encode()),656)
    def test_exact_old_versions_and_episode_rows(self):
        x=self.session;self.assertEqual(len(x.versions),5)
        self.assertIn(s.previous.original.STARTING_ID,x.versions)
        self.assertTrue(all(r['episode']=='prior_work' for r in x.view()['recent_activity']))
        self.assertEqual(x.candidate.file_map['Lib/configparser.py'],s.historical.starting_evidence()[0].file_map['Lib/configparser.py'])
        self.assertIn(b'self.append(lineno, line)',x.candidate.file_map['Lib/configparser.py'])
    def test_snapshot_retains_new_presentation_setting(self):
        self.assertEqual(s.Task().snapshot(self.session)['recovery_recent_count'],0)
        self.assertFalse(self.session.view()['verification']['submission']['eligible'])

if __name__=='__main__':unittest.main()
