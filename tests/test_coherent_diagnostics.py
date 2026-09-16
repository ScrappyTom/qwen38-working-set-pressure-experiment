"""Information-path regression: one failure must keep its own identity/outcome."""
import copy
import doctest
import io
from pathlib import Path
import unittest

from working_set_exp import coherent_diagnostics as projection
from working_set_exp import feedback_assessment
from working_set_exp.observations import ObservationStore

ROOT = Path(__file__).resolve().parents[1]
OBS = ROOT/'development/decision_interface/recovery_inspection/run-001/observations'


def report(text):
    case = doctest.DocTestParser().get_doctest(text, {}, 'trial', 'examples.rst', 0)
    output = io.StringIO()
    # unittest's -v must not silently change the nested runner's report format.
    result = doctest.DocTestRunner(verbose=False).run(case, out=output.write)
    return output.getvalue(), result.failed


class DiagnosticTests(unittest.TestCase):
    def test_real_four_failures_keep_their_locations(self):
        store = ObservationStore(OBS, replay=True)
        before = feedback_assessment.assessment(store, 'CHK-0046')
        full = projection.assessment(store, 'CHK-0046')
        row = next(r for r in full['criteria'] if r['criterion'] == 'examples.execution')
        self.assertEqual([r['location']['line'] for r in row['diagnostics']], [172,175,178,181])
        self.assertEqual(row['diagnostics_total'], 4)
        self.assertEqual(row['diagnostics_remaining'], 0)
        self.assertTrue(all(r['diagnostic']['complete'] for r in row['diagnostics']))
        self.assertIn('Port out of range', row['diagnostics'][0]['diagnostic']['text'])
        self.assertNotIn('Port out of range', row['diagnostics'][1]['diagnostic']['text'])
        self.assertIn("as '-1'", row['diagnostics'][1]['diagnostic']['text'])
        self.assertIn('Got nothing', row['diagnostics'][2]['diagnostic']['text'])
        self.assertEqual(row['diagnostics'][2]['failure_kind'], 'output_mismatch')
        for key in ('passed','candidate_id','checker_sha256','observation','failed_criteria','normal_control_passed'):
            self.assertEqual(full[key], before[key])
        standing = projection.overview(full)
        shown = next(r for r in standing['criteria'] if r['criterion']=='examples.execution')
        self.assertEqual(shown['diagnostics'], row['diagnostics'])
        page = projection.inspect_check(store,'CHK-0046',0)
        self.assertEqual(page['entries'][0], row)

    def test_standard_exception_and_output_mismatch_are_separate(self):
        raw, failures = report('>>> raise ValueError("wrong")\nValueError: expected\n>>> 2+2\n5\n')
        records = projection.failure_records(raw, failures)
        self.assertEqual([r['failure_kind'] for r in records], ['unexpected_exception','output_mismatch'])
        self.assertEqual(records[0]['failed_example']['text'], 'raise ValueError("wrong")\n')
        self.assertNotIn('2+2', records[0]['diagnostic']['text'])
        self.assertIn('Expected:\n    5\nGot:\n    4', records[1]['diagnostic']['text'])

    def test_expected_nothing_and_multiline_escaped_data(self):
        raw, failures = report('>>> print("quoted \\\"x\\\"\\nnext\\t\\u03bb")\n>>> print("two\\nlines")\nwrong\n')
        records = projection.failure_records(raw, failures)
        self.assertEqual(len(records),2)
        self.assertIn('Expected nothing',records[0]['diagnostic']['text'])
        self.assertIn('λ',records[0]['diagnostic']['text'])
        self.assertNotEqual(records[0]['location']['line'],records[1]['location']['line'])

    def test_large_single_record_keeps_identity_outside_its_excerpt(self):
        raw, failures = report('>>> print("x"*10000)\nother\n>>> 3\n4\n')
        records = projection.failure_records(raw,failures)
        self.assertFalse(records[0]['diagnostic']['complete'])
        self.assertEqual(records[0]['location']['line'],1)
        self.assertEqual(records[0]['failed_example']['text'],'print("x"*10000)\n')
        self.assertEqual(records[1]['location']['line'],3)
        self.assertNotIn('examples.rst',records[0]['diagnostic']['text'])
        self.assertTrue(records[1]['diagnostic']['complete'])

    def test_partial_or_unknown_report_does_not_invent_an_association(self):
        raw, failures = report('>>> 1\n2\n')
        self.assertIsNone(projection.failure_records(raw[12:],failures))
        self.assertIsNone(projection.failure_records(raw,failures+1))
        self.assertIsNone(projection.failure_records('invalid indentation in example',1))
        self.assertEqual(projection.failure_records('',0),[])

    def test_overview_counts_omitted_failure_records_truthfully(self):
        raw, failures = report(''.join('>>> 1\n2\n' for _ in range(7)))
        records = projection.failure_records(raw,failures)
        value = dict(criteria=[dict(criterion='examples.execution',met=False,diagnostics=records[:4],
            diagnostics_total=7,diagnostics_shown=4,diagnostics_remaining=3)])
        before = copy.deepcopy(value)
        row = projection.overview(value)['criteria'][0]
        self.assertEqual((row['diagnostics_total'],row['diagnostics_shown'],row['diagnostics_remaining']), (7,4,3))
        self.assertEqual(value,before)


if __name__ == '__main__':
    unittest.main()
