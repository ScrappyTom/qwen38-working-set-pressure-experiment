"""Qualify actual weak artifacts and the missing checker/transport boundaries."""
import ast
import base64
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import contract_task as entry
import engineering_reference as reference
from working_set_exp.candidate import Candidate
from working_set_exp.observations import ObservationStore


class ContractQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.task = entry.Task()
        cls.candidate = cls.task.inherited_candidate
        cls.source = cls.candidate.file_map[entry.TEST].decode()
        cls.corrected = reference.correct(cls.source)
        cls.env = {'__name__': 'independent_checker_functions'}
        exec(compile(entry.checker(cls.candidate), '<successor-checker>', 'exec'), cls.env)

    def execute(self, text, mutate=None):
        files = dict(self.candidate.file_map)
        files[entry.TEST] = text.encode()
        if mutate:
            mutate(files)
        candidate = Candidate.create(files, max_file_bytes=entry.study.FILE_LIMIT)
        with tempfile.TemporaryDirectory() as folder:
            store = ObservationStore(folder, timeout=60)
            observation = store.execute(candidate, entry.checker(self.candidate), 'public', 'CHK-0001')
            rows = [json.loads(line) for line in (store.directory('CHK-0001') / 'stdout.bin').read_bytes().splitlines()]
            report = entry.scoped_reports.assessment(store, 'CHK-0001')
            return observation, {r['case']: r for r in rows if 'case' in r}, report

    def test_actual_weak_artifacts_rejected_and_exact_correction_passes(self):
        observed, rows, report = self.execute(self.source)
        self.assertFalse(observed['passed'])
        self.assertTrue(observed['capture_complete'])
        self.assertTrue(rows['new_overlap_regressions']['passed'])
        self.assertTrue(rows['new_regressions_detect_resolver_fault']['passed'])
        self.assertFalse(rows['authored_exact_exception_class']['passed'])
        self.assertEqual(len(rows['authored_exact_exception_class']['undetected_sites']), 4)
        self.assertEqual(len(rows['authored_exact_diagnostic_text']['undetected_sites']), 2)
        self.assertTrue(report['intentional_faults_present'])
        self.assertNotIn('No injected faults', report['explanation'])
        shown = entry.scoped_reports.overview(report)
        self.assertEqual(set(shown['failed_criteria']), {'authored_exact_exception_class', 'authored_exact_diagnostic_text'})
        self.assertEqual(len(shown['criteria']), 2)
        revised = entry.study.candidate_from_snapshot(entry.read(entry.parent.HERE / 'current_job/run-003/final-candidate.json'))
        bad, r, _ = self.execute(revised.file_map[entry.TEST].decode())
        self.assertFalse(bad['passed'])
        self.assertEqual(len(r['authored_exact_exception_class']['undetected_sites']), 4)
        self.assertEqual(len(r['authored_exact_diagnostic_text']['undetected_sites']), 2)
        good, rows, _ = self.execute(self.corrected)
        self.assertTrue(good['passed'])
        self.assertEqual(rows['authored_exact_exception_class']['evaluated_sites'], 4)
        self.assertTrue(rows['authored_exact_diagnostic_text']['passed'])

    def test_new_methods_in_old_class_count_without_changing_old_assertions(self):
        organized = reference.place_in_old_class(self.corrected)
        original = base64.b64decode(self.env['CONFIG']['saved_tests']).decode()
        self.assertTrue(self.env['preserved_methods'](original, organized))
        result, rows, _ = self.execute(organized)
        self.assertTrue(result['passed'])
        self.assertEqual(rows['new_overlap_regressions']['tests'], 6)
        self.assertTrue(rows['saved_regression_methods_preserved']['passed'])
        altered = organized.replace('self.assertEqual(handler(p), "default")',
            'self.assertTrue(True)', 1)
        self.assertNotEqual(organized, altered)
        self.assertFalse(self.env['preserved_methods'](original, altered))
        rejected, r, _ = self.execute(altered)
        self.assertFalse(rejected['passed'])
        self.assertFalse(r['saved_regression_methods_preserved']['passed'])

    def test_each_site_is_checked_even_when_one_method_has_two_raises(self):
        tree = ast.parse(self.corrected)
        cls = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name != 'LateVirtualRegistration')
        method = next(n for n in cls.body if isinstance(n, ast.FunctionDef) and 'overlapping_unrelated' in n.name)
        raised = next(n for n in ast.walk(method) if isinstance(n, ast.With))
        lines = self.corrected.splitlines(keepends=True)
        indent = ' ' * raised.col_offset
        weak_repeat = indent + 'with self.assertRaises(RuntimeError):\n' + ''.join(lines[raised.body[0].lineno-1:raised.body[-1].end_lineno])
        lines.insert(method.end_lineno, weak_repeat)
        result, rows, _ = self.execute(''.join(lines))
        self.assertFalse(result['passed'])
        self.assertEqual(rows['exception_site_execution_qualified']['observed_sites'], 5)
        self.assertEqual(rows['authored_exact_exception_class']['undetected_sites'],
            [dict(method=[cls.name, method.name], site=2)])
        self.assertEqual(rows['authored_exact_diagnostic_text']['undetected_sites'],
            [dict(method=[cls.name, method.name], site=2)])

    def test_normal_failure_and_protected_file_change_are_not_mutant_success(self):
        tree = ast.parse(self.corrected)
        new_class = next(n for n in tree.body if isinstance(n, ast.ClassDef) and n.name != 'LateVirtualRegistration')
        lines = self.corrected.splitlines(keepends=True)
        begin = new_class.lineno - 1
        wrong = ''.join(lines[:begin]) + ''.join(lines[begin:]).replace('"default")', '"wrong")', 1)
        self.assertNotEqual(wrong, self.corrected)
        result, rows, _ = self.execute(wrong)
        self.assertFalse(result['passed'])
        self.assertFalse(rows['new_regressions_detect_resolver_fault']['passed'])
        result, rows, _ = self.execute(self.corrected,
            lambda f: f.__setitem__('README.md', f['README.md'] + b'changed\n'))
        self.assertFalse(result['passed'])
        self.assertFalse(rows['preserved_material']['passed'])

    def test_released_source_authority_history_and_actual_cumulative_counts(self):
        from run_contract import job_opportunities
        session = self.task.initial_session()
        self.assertEqual(session.candidate.file_map, self.candidate.file_map)
        self.assertEqual(session.pairs, self.task.inherited_state['pairs'])
        self.assertEqual(session.ranges, [])
        self.assertEqual(session.delivered_sources, [])
        self.assertEqual((session.request_limit, session.call_limit), (59, 113))
        view = session.view()
        self.assertEqual(view['allowance']['requests_remaining'], 12)
        self.assertEqual(view['allowance']['actions_remaining'], 36)
        self.assertEqual(view['verification']['checks']['public']['status'], 'not_executed_for_current_candidate_and_checker')
        self.assertEqual(view['prior_work']['latest_accepted_submission']['candidate_id'], self.candidate.candidate_id)
        self.assertTrue(view['verification']['historical_checks']['public']['passed'])
        self.assertEqual(session.working_account(), self.task.restore(entry.snapshot(session), self.candidate, entry.INHERITED, replay=True).working_account())
        inherited = self.task.inherited_state['pairs'][:57]
        suffix = self.task.inherited_state['pairs'][57:]
        row = job_opportunities(suffix, inherited=inherited, call_limit=129)[0]
        self.assertEqual((row['sequence'], row['job_sequence']), (76, 19))
        self.assertEqual((row['calls_remaining_before'], row['calls_remaining_after']), (54, 53))


if __name__ == '__main__':
    unittest.main()
