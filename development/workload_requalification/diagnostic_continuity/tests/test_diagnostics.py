import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import bootstrap
import diagnostic_reports as reports
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes
from working_set_exp.observations import ObservationStore

OLD = bootstrap.ROOT / 'development/workload_requalification/configparser_operational/run-001/observations/CHK-0054'


class DiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.full = json.loads((OLD/'stdout.bin').read_bytes())

    def store(self, full=None, raw=None):
        folder = self.root/'CHK-0054'
        folder.mkdir(exist_ok=True)
        raw = canonical_json_bytes(full or self.full) if raw is None else raw
        meta = json.loads((OLD/'outcome.json').read_bytes())
        meta['streams']['stdout'].update(captured_bytes=len(raw),observed_pipe_bytes=len(raw),sha256=sha256_bytes(raw))
        (folder/'stdout.bin').write_bytes(raw)
        (folder/'stderr.bin').write_bytes(b'')
        (folder/'outcome.json').write_bytes(canonical_json_bytes(meta))
        return ObservationStore(self.root,replay=True)

    def test_live_three_failures_all_visible_with_scope_outcomes(self):
        store = self.store()
        original = (store.directory('CHK-0054')/'stdout.bin').read_bytes()
        view = reports.overview(reports.assessment(store,'CHK-0054'))
        self.assertEqual((view['diagnostics_total'],view['diagnostics_shown'],view['diagnostics_remaining']),(3,3,0))
        self.assertEqual([d['diagnostic']['text'] for d in view['diagnostics']],
                         [d['trace'] for d in self.full['candidate_tests']['details']])
        scopes = {c['criterion']:c for c in view['criteria']}
        self.assertTrue(scopes['contract.execution']['met'])
        self.assertTrue(scopes['upstream.execution']['met'])
        self.assertFalse(scopes['candidate_tests.execution']['met'])
        self.assertIn('mkstemp',view['diagnostics'][2]['diagnostic']['text'])
        self.assertEqual(original,(store.directory('CHK-0054')/'stdout.bin').read_bytes())
        self.assertNotIn('diagnostic_records',view)

    def test_every_diagnostic_direct_address_and_exact_fields(self):
        store = self.store()
        overview = reports.overview(reports.assessment(store,'CHK-0054'))
        for row, expected in zip(overview['diagnostics'],self.full['candidate_tests']['details']):
            page = reports.inspect_check(store,'CHK-0054',row['inspect']['offset'])
            self.assertEqual([(r['field'],r['text']) for r in page['entries']],list(expected.items()))
            self.assertTrue(all(r['complete'] for r in page['entries']))

    def test_long_unicode_escaping_fields_reassemble_without_loss(self):
        value = copy.deepcopy(self.full)
        detail = dict(test='long'+('λ😀\\\"\x01'*500),trace='TRACE\n'+('λ😀\\\"\x01\n'*2000))
        value['candidate_tests'].update(details=[detail],failures=1,errors=0)
        store = self.store(value)
        offset = 0
        fields = {'test':bytearray(),'trace':bytearray()}
        while True:
            page = reports.inspect_check(store,'CHK-0054',offset)
            self.assertLess(len(canonical_json_bytes(page)),22000)
            for part in page['entries']:
                target = fields[part['field']]
                self.assertEqual(len(target),part['start_byte'])
                target.extend(part['text'].encode())
                self.assertEqual(len(target),part['end_byte'])
                self.assertEqual(part['field_sha256'],sha256_bytes(detail[part['field']].encode()))
            if page['next_offset'] is None: break
            self.assertGreater(page['next_offset'],offset)
            offset = page['next_offset']
        self.assertEqual({k:bytes(v).decode() for k,v in fields.items()},detail)

    def test_other_failing_scope_not_hidden_by_many_subtests(self):
        value = copy.deepcopy(self.full)
        value['contract'].update(successful=False,failures=9,details=[dict(test=f'contract{i}',trace=f'failure{i}') for i in range(9)])
        view = reports.overview(reports.assessment(self.store(value),'CHK-0054'))
        self.assertEqual([r['criterion'] for r in view['diagnostics'][:4]],
                         ['contract.execution','candidate_tests.execution']*2)
        self.assertEqual(view['diagnostics_shown']+view['diagnostics_remaining'],12)
        self.assertLessEqual(len(canonical_json_bytes(view['diagnostics'])),reports.OVERVIEW_DETAIL_BYTES)
        remaining=reports.inspect_check(self.store(value),'CHK-0054',view['next_unshown_diagnostic']['offset'])
        self.assertTrue(remaining['entries'])

    def test_stale_checker_and_invalid_offsets_rejected(self):
        store = self.store()
        with self.assertRaises(ValueError):
            reports.assessment(store,'CHK-0054',{'checker_sha256':'wrong'})
        for offset in (-1,True,100000):
            with self.assertRaises(ValueError):reports.inspect_check(store,'CHK-0054',offset)

    def test_unknown_observation_does_not_gain_inferred_diagnostics(self):
        view = reports.overview(reports.assessment(self.store(raw=b'unknown output'),'CHK-0054'))
        self.assertFalse(view['assessment_available'])
        self.assertEqual(view['diagnostics'],[])
        self.assertEqual(view['criteria'][0]['criterion'],'public_execution')

    def test_historical_projection_unchanged(self):
        store = self.store()
        value = reports.legacy.assessment(store,'CHK-0054')
        self.assertEqual(len(value['criteria'][0]['diagnostics']),2)
        self.assertEqual(len(reports.legacy.overview(value)['criteria'][0]['diagnostics']),1)


if __name__ == '__main__':unittest.main()
