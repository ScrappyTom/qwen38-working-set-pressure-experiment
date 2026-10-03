"""Real checker, restoration and information transitions; no model inference."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
import dispatch_task as study
import reference_work
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict


class DispatchTaskTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.folder = Path(self.tmp.name)
        self.addCleanup(self.tmp.cleanup)
        self.module = study.Task()
        self.state = study.read(study.AREA/'cpu-route-002/route/08-state.json')
        self.candidate = study.candidate_from_snapshot(next(
            v for v in self.state['source_versions'] if v['candidate_id']==self.state['candidate_id']))

    def completed(self):
        return self.module.restore(self.state,self.candidate,study.AREA/'cpu-route-002/scripted',replay=True)

    def successor(self):
        # Explicit engineering fixture; not a forged model-run seal.
        module = object.__new__(study.Task)
        module.phase,module.version,module.AREA = 'dynamic','engineering',study.AREA
        module.PACKAGE = self.folder/'future'
        module.inherited = study.AREA/'cpu-route-002/scripted'
        module.inherited_state,module.inherited_candidate = self.state,self.candidate
        module.INHERITED_REQUESTS = self.state['requests_used']
        module.INHERITED_OPERATIONS = len(self.state['pairs'])
        module.MAX_REQUESTS,module.MAX_OPERATIONS = module.INHERITED_REQUESTS+24,module.INHERITED_OPERATIONS+72
        return module

    def act(self,session,operation):
        session.mark_delivered(session.view())
        session.begin_request()
        return study.process_reply(session,dict(discussion='CPU qualification operation.',operation=operation),lambda view:0,[])

    def run_check(self,files,phase):
        candidate = study.Candidate.create(files,max_file_bytes=study.FILE_LIMIT)
        source = study.checker(phase,self.candidate if phase=='dynamic' else None)
        store = study.ObservationStore(self.folder/phase,timeout=60)
        result = store.execute(candidate,source,'public','CHK-0001')
        rows = [load_json_strict(raw) for raw in (store.directory('CHK-0001')/'stdout.bin').read_bytes().splitlines()]
        return result,rows

    def test_exact_source_and_empty_entry(self):
        session = self.module.initial_session()
        self.assertEqual(len(session.candidate.files),8)
        self.assertEqual(session.requests_used,0)
        self.assertFalse(session.ranges)
        self.assertIsNone(session.working_account())
        self.assertNotIn('source_prerequisites',study.snapshot(session))

    def test_original_preservation_and_feature_failure_are_distinct(self):
        result,rows = self.run_check(study.starting_files(),'union')
        self.assertFalse(result['passed'])
        records = {r['case']:r for r in rows if 'case' in r}
        self.assertTrue(records['original_single_dispatch_suite']['passed'])
        self.assertEqual(records['original_single_dispatch_suite']['tests'],24)
        self.assertFalse(records['union_feature_contract']['passed'])
        self.assertGreater(records['union_feature_contract']['errors'],0)

    def test_complete_reference_and_sensitivity(self):
        result,rows = self.run_check(self.candidate.file_map,'union')
        self.assertTrue(result['passed'])
        record = next(r for r in rows if r.get('case')=='regressions_expose_original_missing_feature')
        self.assertTrue(record['passed'])
        self.assertFalse(record['original_execution']['passed'])
        self.assertEqual(record['original_execution']['tests'],4)

    def test_exact_restoration_and_corrupt_diff_rejection(self):
        session = self.completed()
        self.assertEqual(canonical_json_bytes(study.snapshot(session)),canonical_json_bytes(self.state))
        bad = copy.deepcopy(self.state)
        bad['diffs'][next(iter(bad['diffs']))] += '\nchanged'
        with self.assertRaises(AssertionError):self.module.restore(bad,self.candidate,self.folder)

    def test_release_retains_history_and_removes_authority(self):
        prior = self.completed()
        oldsource = next(s for s in prior.view()['working_set']['sources'] if s['path']=='Lib/functools.py')
        module = self.successor()
        future = module.initial_session()
        self.assertEqual(future.pairs,prior.pairs)
        self.assertEqual(future.working_account(),prior.working_account())
        self.assertFalse(future.view()['working_set']['sources'])
        self.assertFalse(future.view()['verification']['checks']['public']['applies_to_current'])
        edit = dict(action='replace_region',region=oldsource['region_ref'],
            expected_candidate_id=future.candidate.candidate_id,new=oldsource['content']+'\n# CPU source-authority qualification.\n')
        self.act(future,edit)
        self.assertFalse(future.pairs[-1]['result']['accepted'])
        self.assertEqual(future.candidate.candidate_id,prior.candidate.candidate_id)
        self.act(future,dict(action='read',path='Lib/functools.py',
            start_line=oldsource['returned_start_line'],end_line=oldsource['returned_end_line']))
        shown = next(s for s in future.view()['working_set']['sources'] if s['path']=='Lib/functools.py')
        self.assertEqual(shown['region_ref'],oldsource['region_ref'])
        self.act(future,edit)
        self.assertTrue(future.pairs[-1]['result']['accepted'])

    def test_dynamic_check_and_docs_use_candidate(self):
        files = dict(self.candidate.file_map)
        files['tests/test_virtual_registration.py'] = reference_work.DYNAMIC_TESTS.encode()
        files['Doc/howto/union-dispatch.rst'] = reference_work.DOC.encode()
        result,rows = self.run_check(files,'dynamic')
        self.assertTrue(result['passed'])
        doc = next(r for r in rows if r.get('case')=='executable_documentation')
        self.assertGreaterEqual(doc['attempted'],6)
        before = next(r for r in rows if r.get('case')=='regressions_expose_historical_virtual_behavior')
        self.assertTrue(before['passed'])
        self.assertEqual(before['historical_execution']['failures'],2)

    def test_historical_union_bug_reaches_primary_diagnostics(self):
        files = dict(self.candidate.file_map)
        files['Lib/functools.py'] = (study.AREA/'upstream/merged/functools.py').read_bytes()
        files['tests/test_virtual_registration.py'] = reference_work.DYNAMIC_TESTS.encode()
        files['Doc/howto/union-dispatch.rst'] = reference_work.DOC.encode()
        result,rows = self.run_check(files,'dynamic')
        self.assertFalse(result['passed'])
        dynamic = next(r for r in rows if r.get('case')=='late_virtual_registration_contract')
        self.assertFalse(dynamic['passed'])
        self.assertIn("'default'",'\n'.join(row['trace'] for row in dynamic['details']))
        doc = next(r for r in rows if r.get('case')=='executable_documentation')
        self.assertGreater(doc['failed'],0)


if __name__=='__main__': unittest.main()
