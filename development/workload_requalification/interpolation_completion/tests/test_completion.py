"""Meaningful checker counterexamples, environment parity and real entry guards."""
import ast
import doctest
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import completion_task as entry
import engineering_reference as reference
from working_set_exp.jsonutil import canonical_json_bytes
from working_set_exp.observations import ObservationStore

OUT = entry.AREA / os.environ.get('INTERPOLATION_CPU_OUTPUT', 'cpu-checker-001')


class CompletionQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        OUT.mkdir(exist_ok=False)
        cls.task = entry.Task()
        cls.test, cls.doc = reference.test_addition(), reference.doc_addition()

    def execute(self, name, candidate, scope='public', original=False):
        folder = OUT / name
        folder.mkdir(exist_ok=False)
        entry.save(folder, 'candidate.json', entry.candidate_bytes(candidate))
        store = ObservationStore(folder / 'capture', timeout=120)
        code = entry.original.checker(scope) if original else entry.checker(scope)
        receipt = store.execute(candidate, code, scope, 'CHK-0001')
        full = json.loads((store.directory('CHK-0001') / 'stdout.bin').read_bytes())
        assessment = entry.completion_reports.assessment(store, 'CHK-0001')
        entry.save(folder, 'assessment.json', assessment)
        print(json.dumps(dict(case=name, passed=receipt['passed'], bytes=receipt['streams']['stdout']['captured_bytes'],
                              failed=assessment['failed_criteria'])), flush=True)
        self.assertTrue(receipt['executed'] and receipt['capture_complete'])
        return receipt, full, assessment

    def test_01_baseline_and_complete_reference(self):
        result, full, assessment = self.execute('baseline', self.task.inherited_candidate)
        self.assertFalse(result['passed'])
        row = next(r for r in assessment['criteria'] if r['criterion'] == 'required_paths')
        self.assertEqual(row['missing_operation_total'], 20)
        self.assertEqual(len(row['missing_groups']), 2)
        self.assertTrue(all(r['met'] is None for r in assessment['criteria'] if r['criterion'].startswith('detect.')))
        good, full, _ = self.execute('complete', reference.candidate(self.test, self.doc))
        self.assertTrue(good['passed'])
        self.assertTrue(full['legacy_public_passed'])
        self.assertEqual(full['examples']['environment']['__name__'], '__main__')
        for name in ('restored_class','restored_diagnostic','restored_arguments','restored_option','restored_section','restored_reference'):
            self.assertEqual(len(full['fault_sensitivity'][name]['targets']), 16)
            self.assertTrue(full['fault_sensitivity'][name]['all_targets_detected'])

    def test_02_exact_arguments_not_implied_by_other_attributes(self):
        weak = self.test.replace('                    self.assertEqual(result.args, expected_args)\n', '')
        self.assertNotEqual(weak, self.test)
        candidate = reference.candidate(weak, self.doc)
        old, _, _ = self.execute('arguments-omitted-original', candidate, original=True)
        self.assertTrue(old['passed'], 'Preserve a reproduced checker blind spot, not an assumed one')
        result, full, _ = self.execute('arguments-omitted-qualified', candidate)
        self.assertFalse(result['passed'])
        self.assertFalse(full['fault_sensitivity']['restored_arguments']['all_targets_detected'])
        weak = self.test.replace("                    self.assertEqual((result.option, result.section, result.reference),\n                                     ('value', 'main', reference))\n", '')
        self.assertNotEqual(weak, self.test)
        result, full, _ = self.execute('attributes-omitted', reference.candidate(weak, self.doc))
        self.assertFalse(result['passed'])
        self.assertFalse(full['fault_sensitivity']['restored_option']['all_targets_detected'])

    def test_03_class_diagnostic_and_missing_path(self):
        weak = self.test.replace('self.assertIs(type(result), type(error))', 'self.assertIsInstance(result, type(error))')
        result, full, _ = self.execute('subclass-permitted', reference.candidate(weak,self.doc))
        self.assertFalse(result['passed'])
        self.assertFalse(full['fault_sensitivity']['restored_class']['all_targets_detected'])
        weak = self.test.replace('                    self.assertEqual(str(result), str(error))\n','').replace(
            '                    self.assertEqual(result.message, error.message)\n','')
        result, full, _ = self.execute('diagnostic-omitted', reference.candidate(weak,self.doc))
        self.assertFalse(result['passed'])
        self.assertFalse(full['fault_sensitivity']['restored_diagnostic']['all_targets_detected'])
        weak = self.test.replace("                self.assertEqual(parser.get('main', 'value', raw=True), raw)\n", '')
        result, full, _ = self.execute('raw-bypass-omitted', reference.candidate(weak,self.doc))
        self.assertFalse(result['passed'])
        self.assertEqual(full['observed_paths']['raw_bypass'], [])

    def test_04_wrong_expectation_and_protected_work(self):
        weak = self.test.replace("expected_args = ('value', 'main', raw, reference)", "expected_args = ('value', 'other', raw, reference)")
        result, full, assessment = self.execute('wrong-lookup-expectation', reference.candidate(weak,self.doc))
        self.assertFalse(result['passed'])
        self.assertFalse(full['edited_suite']['successful'])
        self.assertTrue(any(r.get('diagnostics') for r in assessment['criteria']))
        self.assertTrue(all(r['met'] is None for r in assessment['criteria'] if r['criterion'].startswith('detect.')))
        def mutate(files): files['Lib/configparser.py'] += b'\n# forbidden change\n'
        result, full, _ = self.execute('library-change', reference.candidate(self.test,self.doc,mutate))
        self.assertFalse(result['passed'])
        self.assertFalse(full['existing_work_preserved'])

    def test_05_example_namespace_matches_ordinary_path(self):
        extra = "\n   >>> class Demonstration: pass\n   >>> Demonstration\n   <class '__main__.Demonstration'>\n"
        for label, text, success in (('namespace-pass',self.doc+extra,True),
                                     ('namespace-failure',(self.doc+extra).replace("__main__.Demonstration", "builtins.Demonstration"),False)):
            result, full, _ = self.execute(label, reference.candidate(self.test,text),scope='examples')
            self.assertEqual(result['passed'],success)
            # An ordinary testfile obtains __main__ itself. Use the exact new
            # standalone example text with the actual candidate library module.
            with tempfile.TemporaryDirectory() as folder:
                root=Path(folder)
                lib=root/'configparser.py'; lib.write_bytes(self.task.inherited_candidate.file_map['Lib/configparser.py'])
                doc=root/'examples.txt'; doc.write_text(text,encoding='utf-8')
                import importlib.util
                spec=importlib.util.spec_from_file_location('configparser',lib)
                module=importlib.util.module_from_spec(spec)
                previous=sys.modules.get('configparser'); sys.modules['configparser']=module
                spec.loader.exec_module(module)
                output=io.StringIO()
                import contextlib
                try:
                    with contextlib.redirect_stdout(output):
                        observed=doctest.testfile(str(doc),module_relative=False,verbose=False)
                finally:
                    if previous is None: sys.modules.pop('configparser',None)
                    else: sys.modules['configparser']=previous
                self.assertEqual(observed.failed,full['examples']['failures'])
                self.assertEqual(observed.attempted,full['examples']['examples'])
                entry.save(OUT/label,'ordinary-doctest.json',dict(attempted=observed.attempted,failed=observed.failed,details=output.getvalue()))

    def test_06_release_history_authority_and_restoration(self):
        session=self.task.initial_session()
        self.assertEqual((session.requests_used,session.calls_used),(32,101))
        self.assertEqual(session.pairs,self.task.inherited_state['pairs'])
        self.assertEqual(session.working_account()['action_handle'],'EVT-0097')
        self.assertEqual(session.ranges,[])
        state=entry.snapshot(session)
        restored=self.task.restore(state,session.candidate,INHERITED := entry.INHERITED,replay=True)
        self.assertEqual(entry.snapshot(restored),state)
        content=session.candidate.file_map[entry.TEST].decode()
        anchor=''.join(content.splitlines(keepends=True)[-3:])
        proposal=dict(action='patch',path=entry.TEST,old=anchor,new=anchor+'\n# new comment\n',
            expected_candidate_id=session.candidate.candidate_id,expected_file_sha256=session.candidate.file_sha256(entry.TEST))
        reply=dict(discussion='Offline source authority qualification.',operation=proposal)
        result=entry.process_reply(session,reply,lambda view:0,[])
        self.assertFalse(result['operations'][-1]['result']['accepted'])
        self.assertEqual(len(result['operations']),1)
        self.assertEqual(session.candidate.candidate_id,self.task.inherited_candidate.candidate_id)
        operation=dict(action='read',path=entry.TEST,start_line=len(content.splitlines())-3,end_line=0)
        result=entry.process_reply(session,dict(discussion='Acquire current anchor.',operation=operation),lambda view:0,[])
        self.assertTrue(result['operations'][-1]['result']['accepted'])
        session.mark_delivered(session.view())
        self.assertTrue(session.delivered_sources)
        state=entry.snapshot(session)
        self.assertEqual(entry.snapshot(self.task.restore(state,session.candidate,entry.INHERITED,replay=True)),state)


if __name__=='__main__': unittest.main(verbosity=2)
