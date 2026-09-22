"""Original contract, captured evidence, and report semantics; no model/runtime."""
import ast
import copy
import os
from pathlib import Path
import tempfile
import unittest

import configparser_task as task
import configparser_reports as reports
import qualify_configparser as qualification
from working_set_exp import working_view
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.observations import ObservationStore

EVIDENCE = Path(os.environ.get('CONFIGPARSER_CPU_EVIDENCE', str(task.AREA/'checker-qualification-005')))


class ChangedOutcome:
    def __init__(self, store, **changes): self.store, self.changes = store, changes
    def directory(self, handle): return self.store.directory(handle)
    def read(self, handle): return {**self.store.read(handle), **self.changes}


class EntryTests(unittest.TestCase):
    def test_exact_original_empty_entry_and_file_allowance(self):
        with tempfile.TemporaryDirectory() as raw:
            session=task.initial_session(Path(raw)/'observations')
            view=session.view()
            self.assertEqual(session.candidate.candidate_id,task.STARTING_ID)
            self.assertEqual(sum(len(v) for _,v in session.candidate.files),337239)
            self.assertEqual(session.candidate.max_file_bytes,1048576)
            self.assertEqual(sha256_bytes(session.task.encode()),task.TASK_SHA)
            self.assertEqual((session.request_limit,session.call_limit),(40,80))
            self.assertEqual(session.pairs,[]);self.assertEqual(session.ranges,[])
            self.assertIsNone(session.working_account())
            self.assertEqual(session.edit_checks,{})
            self.assertEqual(set(session.checkers),{'public'})
            self.assertFalse(view['verification']['submission']['eligible'])
            self.assertIn('before this repair session',view['episode_annotation'])
            self.assertFalse((Path(raw)/'observations').exists())

    def test_entry_and_reference_expose_no_reference_repair(self):
        with tempfile.TemporaryDirectory() as raw:
            session=task.initial_session(Path(raw)/'observations')
            visible=canonical_json_bytes(session.view()).decode()+task.operating_reference()
        edits=load_json_strict((task.ORIGINAL/'REFERENCE_EDITS.json').read_bytes())['rows']
        self.assertTrue(all(r['new'] not in visible for r in edits))
        self.assertNotIn('reference-candidate',visible)
        self.assertNotIn('reference-qualification',visible)

    def test_task_reference_describes_exact_explicit_policy(self):
        text=task.operating_reference()
        self.assertIn('edits do not trigger checks',text)
        self.assertIn('expected failure is successful regression detection',text)
        self.assertIn('does not establish accurate prose',text)
        self.assertNotIn('Each declared fault target',text)
        self.assertNotIn('check_after',text)
        self.assertNotIn('automatic check consumes',text)

    def test_reply_schema_accepts_public_and_rejects_unsupported_combination(self):
        schema=task.reply_schema()['json_schema']['schema']
        check=dict(discussion='Check.',operation=dict(action='check',check_id='public',expected_candidate_id='a'*64))
        working_view.validate(check,schema)
        for scope in ('tests','examples'):
            with self.assertRaises(ValueError):
                working_view.validate({**check,'operation':{**check['operation'],'check_id':scope}},schema)
        patch=dict(action='patch',path='Lib/configparser.py',old='old',new='new',
                   expected_candidate_id='a'*64,expected_file_sha256='b'*64)
        working_view.validate(dict(discussion='Save.',operation=patch),schema)
        with self.assertRaises(ValueError):
            working_view.validate(dict(discussion='Save.',operation=patch,check_after='public'),schema)

    def test_only_observation_boundary_changes_acceptance_ast(self):
        original=ast.parse(task.original_checker())
        adapted=ast.parse(task.checker())
        old={n.name:n for n in original.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        new={n.name:n for n in adapted.body if isinstance(n,(ast.FunctionDef,ast.ClassDef))}
        for name in ('ContinuationContract','module_from_source','cases'):
            self.assertEqual(ast.dump(old[name]),ast.dump(new[name]))
        # Everything in main before the destructive formatter is unchanged.
        old_prefix=[]
        for stmt in old['main'].body:
            if isinstance(stmt,ast.For):break
            old_prefix.append(ast.dump(stmt))
        new_prefix=[]
        for stmt in new['main'].body:
            if isinstance(stmt,ast.Assign) and any(isinstance(t,ast.Name) and t.id=='report' for t in stmt.targets):break
            new_prefix.append(ast.dump(stmt))
        self.assertEqual(old_prefix,new_prefix)
        self.assertEqual([ast.dump(n) for n in original.body[:3]],[ast.dump(n) for n in adapted.body[:3]])
        self.assertNotEqual(sha256_bytes(task.checker()),task.CHECKER_SHA)


class SavedObservationTests(unittest.TestCase):
    def store(self,case='correct_reference',version='adapted',boundary=False):
        path=EVIDENCE/'boundaries'/case/'observations' if boundary else EVIDENCE/case/version/'observations'
        return ObservationStore(path,replay=True)

    def test_all_original_variants_have_equivalent_real_execution(self):
        for name,candidate,expected in qualification.variants():
            with self.subTest(case=name):
                old=self.store(name,'legacy');new=self.store(name)
                self.assertIs(old.read('CHK-0001')['passed'],expected)
                self.assertIs(new.read('CHK-0001')['passed'],expected)
                before=load_json_strict((old.directory('CHK-0001')/'stdout.bin').read_bytes())
                after=load_json_strict((new.directory('CHK-0001')/'stdout.bin').read_bytes())
                self.assertEqual(qualification.comparable(before),qualification.comparable(after))
                self.assertTrue(reports.supported_shape(after))
                self.assertEqual(new.read('CHK-0001')['candidate_id'],candidate.candidate_id)

    def test_expected_original_failures_do_not_become_current_failures(self):
        value=reports.assessment(self.store(),'CHK-0001')
        detection=next(r for r in value['criteria'] if r['criterion']=='regression_detects_original')
        self.assertIs(detection['met'],True)
        self.assertIs(detection['original_parser_comparison']['successful'],False)
        self.assertEqual(detection['original_parser_comparison']['errors'],2)
        self.assertEqual(detection['added_test_count'],1)
        self.assertEqual(value['failed_criteria'],[])
        self.assertEqual(reports.overview(value)['criteria'],[])
        self.assertFalse(value['documentation_accuracy_automatically_established'])

    def test_wrong_location_keeps_real_diagnostic_before_expected_failure(self):
        store=self.store('wrong_line_number')
        value=reports.assessment(store,'CHK-0001')
        self.assertEqual(value['failed_criteria'],['contract.execution','candidate_tests.execution'])
        first=reports.overview(value)['criteria'][0]
        self.assertEqual(first['diagnostics_total'],11)
        self.assertEqual(first['diagnostics_shown'],1)
        self.assertEqual(first['diagnostics_remaining'],10)
        self.assertIn('AssertionError',first['diagnostics'][0]['diagnostic']['text'])
        legacy=load_json_strict((self.store('wrong_line_number','legacy').directory('CHK-0001')/'stdout.bin').read_bytes())
        self.assertEqual(legacy['contract']['details'],[])

    def test_vacuous_test_and_missing_doc_are_distinct_unmet_criteria(self):
        for case,criterion in [('vacuous_added_test','regression_detects_original'),('documentation_unchanged','documentation_directive_present')]:
            with self.subTest(case=case):
                value=reports.assessment(self.store(case),'CHK-0001')
                self.assertEqual(value['failed_criteria'],[criterion])

    def test_incomplete_execution_cannot_be_hidden_by_passing_summary(self):
        store=self.store('timeout_after_complete_looking_report',boundary=True)
        result=reports.assessment(store,'CHK-0001')
        self.assertTrue(result['assessment_available'])
        self.assertFalse(result['observation_capture_complete'])
        self.assertFalse(result['passed'])
        self.assertEqual(result['failed_criteria'],['public_execution'])
        self.assertEqual(reports.overview(result)['criteria'][0]['termination'],'timeout')

    def test_nonzero_exit_after_passing_summary_remains_failed_execution(self):
        result=reports.assessment(self.store('nonzero_after_passing_report',boundary=True),'CHK-0001')
        self.assertEqual(result['failed_criteria'],['public_execution'])
        self.assertEqual(result['returncode'],2)

    def test_report_exit_mismatch_is_visible_in_both_directions(self):
        for name,passed in [('nonzero_after_passing_report',False),('zero_after_failed_report',True)]:
            with self.subTest(case=name):
                value=reports.overview(reports.assessment(self.store(name,boundary=True),'CHK-0001'))
                self.assertIs(value['passed'],passed)
                self.assertIs(value['reported_passed'],not passed)
                self.assertIs(value['report_execution_consistent'],False)
                self.assertTrue(value['failed_criteria'])

    def test_unknown_or_partial_output_never_invents_suite_criteria(self):
        for name in ('malformed','crash_after_partial','capture_limit','unknown_success','lone_surrogate'):
            with self.subTest(case=name):
                value=reports.assessment(self.store(name,boundary=True),'CHK-0001')
                self.assertFalse(value['assessment_available'])
                self.assertEqual([r['criterion'] for r in value['criteria']],['public_execution'])
                self.assertIs(value['passed'],name=='unknown_success')

    def test_long_escaping_report_is_exactly_recoverable_and_bounded_in_projection(self):
        store=self.store('long_escaping',boundary=True)
        before={p.name:p.read_bytes() for p in store.directory('CHK-0001').iterdir() if p.is_file()}
        qualification.exact_raw_recovery(store)
        value=reports.assessment(store,'CHK-0001')
        overview=reports.overview(value)
        self.assertIn('PRIMARY ASSERTION AT END',overview['criteria'][0]['diagnostics'][0]['diagnostic']['text'])
        self.assertLess(len(canonical_json_bytes(overview)),16000)
        self.assertLess(len(canonical_json_bytes(reports.inspect_check(store,'CHK-0001',0))),22000)
        self.assertGreater(len(before['stdout.bin']),100000)
        self.assertEqual(before,{p.name:p.read_bytes() for p in store.directory('CHK-0001').iterdir() if p.is_file()})

    def test_full_criteria_pages_and_report_counts_agree(self):
        store=self.store('original');value=reports.assessment(store,'CHK-0001')
        rows=[];offset=0
        while True:
            page=reports.inspect_check(store,'CHK-0001',offset);rows.extend(page['entries'])
            if page['next_offset'] is None:break
            offset=page['next_offset']
        self.assertEqual(rows,value['criteria'])
        overview=reports.overview(value)
        self.assertEqual(overview['failed_records_total'],len(value['failed_criteria']))
        self.assertEqual(overview['failed_records_total'],overview['failed_records_shown']+overview['failed_records_remaining'])
        with self.assertRaises(ValueError):reports.inspect_check(store,'CHK-0001',True)
        with self.assertRaises(ValueError):reports.inspect_check(store,'CHK-0001',len(rows)+1)

    def test_checker_identity_mismatch_rejected(self):
        with self.assertRaises(ValueError):
            reports.assessment(self.store(),'CHK-0001',{'checker_sha256':'0'*64})

    def test_unknown_or_inconsistent_structures_decline_interpretation(self):
        value=load_json_strict((self.store().directory('CHK-0001')/'stdout.bin').read_bytes())
        changes=[('passed',False),('regression_detects_original',False),('added_tests',['same','same']),
                 ('documentation_semantics_require_direct_review',False)]
        for key,replacement in changes:
            with self.subTest(key=key):
                wrong=copy.deepcopy(value);wrong[key]=replacement
                self.assertFalse(reports.supported_shape(wrong))
        wrong=copy.deepcopy(value);wrong['contract']['tests']=True
        self.assertFalse(reports.supported_shape(wrong))

    def test_lone_surrogate_falls_back_without_losing_observation(self):
        store=self.store('lone_surrogate',boundary=True)
        raw=(store.directory('CHK-0001')/'stdout.bin').read_bytes()
        self.assertIn(b'\\ud800',raw)
        result=reports.assessment(store,'CHK-0001')
        self.assertFalse(result['assessment_available'])
        self.assertEqual(result['failed_criteria'],['public_execution'])
        qualification.exact_raw_recovery(store)

    def test_immediate_and_standing_actual_views_preserve_failure(self):
        path=EVIDENCE/'wrong_line_number/adapted'
        immediate=load_json_strict((path/'immediate-view.json').read_bytes())
        standing=load_json_strict((path/'standing-view.json').read_bytes())
        expected=immediate['latest_feedback']['result']['report']
        self.assertEqual(expected,standing['verification']['checks']['public']['assessment'])
        self.assertIn('contract.execution',expected['failed_criteria'])
        self.assertFalse(standing['verification']['submission']['eligible'])

    def test_actual_unexpected_success_has_runner_diagnostic_in_both_views(self):
        area=EVIDENCE/'suite-edges/unexpected_success'
        old=load_json_strict((area/'legacy/observations/CHK-0001/stdout.bin').read_bytes())
        new=load_json_strict((area/'adapted/observations/CHK-0001/stdout.bin').read_bytes())
        self.assertEqual(qualification.comparable(old),qualification.comparable(new))
        self.assertFalse(new['candidate_tests']['successful'])
        self.assertEqual(new['candidate_tests']['details'],[])
        for name in ('immediate','standing'):
            view=load_json_strict((area/f'adapted/{name}-view.json').read_bytes())
            row=view['verification']['checks']['public']['assessment']['criteria'][0]
            self.assertEqual(row['criterion'],'candidate_tests.execution')
            self.assertFalse(row['met'])
            self.assertEqual(row['diagnostics_total'],0)
            self.assertIn('UNEXPECTED SUCCESS:',row['runner_diagnostic']['text'])
            self.assertIn('test_unexpected_success_probe',row['runner_diagnostic']['text'])
        overview=load_json_strict((EVIDENCE/'boundaries/crash_after_partial/overview.json').read_bytes())
        self.assertIn('REAL LATER FAILURE',overview['criteria'][0]['stderr']['text'])

    def test_qualification_status_sources_and_sealed_outputs_match(self):
        seal=load_json_strict((EVIDENCE/'SEAL.json').read_bytes())
        result=load_json_strict((EVIDENCE/'RESULTS.json').read_bytes())
        self.assertEqual(seal['status'],'qualified_cpu_only')
        self.assertEqual(result['status'],'qualified_cpu_only')
        self.assertEqual((result['completion_requests'],result['native_requests']),(0,0))
        self.assertEqual(len(result['cases']),7);self.assertEqual(len(result['boundaries']),9)
        self.assertEqual(len(result['suite_edges']),1)
        self.assertEqual(seal['source_sha256'],task.source_identities())
        self.assertEqual(sha256_bytes(canonical_json_bytes(seal['files'])),seal['aggregate_sha256'])
        for row in seal['files']:
            path=EVIDENCE/row['path']
            self.assertTrue(path.resolve().is_relative_to(EVIDENCE.resolve()))
            self.assertEqual(path.stat().st_size,row['size_bytes'])
            self.assertEqual(sha256_file(path),row['sha256'])


if __name__=='__main__': unittest.main()
