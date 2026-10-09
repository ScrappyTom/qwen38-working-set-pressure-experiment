"""Complete exact legacy receipt delivery, not a claim of current applicability."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import closure_task as module
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes


class CaptureVisibilityTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='capture-visibility-')
        self.addCleanup(self.temp.cleanup)
        self.task = module.Task('E14-CLOSURE-MINT', replay_folder=Path(self.temp.name))
        self.session = self.task.initial_session()
        self.legacy = self.task.inherited_pairs()[0]['result']

    def page(self, result):
        raw = canonical_json_bytes(result)
        return dict(kind='saved_bytes', handle='RES-0001', offset=0, next_offset=None,
                    total_bytes=len(raw), sha256=sha256_bytes(raw), exact_utf8=raw.decode())

    def view_with(self, page):
        view = self.session.view()
        view['working_set']['saved_results'] = [page]
        return view

    def act(self, operation):
        self.session.mark_delivered(self.session.view())
        self.session.begin_request()
        return self.task.process_reply(self.session, dict(discussion='CPU qualification.', operation=operation),
                                       lambda view: 0, [])['operations'][-1]['result']

    def test_actual_mint_inputs_change_only_complete_visibility(self):
        run = self.task.RUN
        for tag, stem in [('C02', 'C01-O01'), ('C03', 'C02-O02')]:
            with self.subTest(tag=tag):
                state = self.task.read(run / f'after/{stem}-state.json')
                candidate = self.task.read(run / f'after/{stem}-candidate.json')
                session = self.task.restore(state, candidate, run, replay=True)
                wire = self.task.read(run / f'calls/{tag}-wire-request.json')
                expected = load_json_strict(wire['messages'][-1]['content'].encode())['workspace']
                row, = [r for r in expected['imported_observations']['entries'] if r['handle']=='OBS-0002']
                self.assertFalse(row['shown_complete'])
                row['shown_complete'] = True
                self.assertEqual(session.view(), expected)
                self.assertEqual(self.task.snapshot(session), state)

    def test_incomplete_corrupt_or_mismatched_receipts_do_not_claim_visibility(self):
        page = self.page(self.legacy)
        self.assertEqual(self.session._shown_acquisitions(self.view_with(page)), {'OBS-0002'})
        bad = [dict(page, next_offset=10), dict(page, offset=1), dict(page, sha256='0'*64),
               dict(page, exact_utf8=page['exact_utf8'][:-1])]
        for change in [dict(accepted=False), dict(handle='OBS-0001'), dict(handle='OBS-9999'),
                       dict(size_bytes=207), dict(exact_result_sha256='0'*64),
                       dict(exact_result_utf8=self.legacy['exact_result_utf8'].replace('M8::','M9::')),
                       dict(source_edit_authority=True)]:
            bad.append(self.page({**self.legacy, **change}))
        for i, wrong in enumerate(bad):
            with self.subTest(case=i):
                self.assertEqual(self.session._shown_acquisitions(self.view_with(wrong)), set())

    def test_legacy_selection_release_and_modern_replacement_preserve_history(self):
        original = canonical_json_bytes(self.session.pairs)
        self.assertTrue(self.act(dict(action='work_on', sources=[], results=['RES-0001']))['accepted'])
        view = self.session.view()
        self.assertTrue(view['imported_observations']['entries'][1]['shown_complete'])
        self.assertFalse(view['verification']['submission']['eligible'])
        self.session.mark_delivered(view)
        self.assertEqual(self.session.delivered_sources, [])
        current = self.session.candidate
        rejected = self.act(dict(action='patch', path='codec/label.py',
            old=current.file_map['codec/label.py'].decode(), new='def codec_label(value):\n    return value\n',
            expected_candidate_id=current.candidate_id, expected_file_sha256=current.file_sha256('codec/label.py')))
        self.assertFalse(rejected['accepted'])
        modern = self.act(dict(action='reopen_observation', handle='OBS-0002'))
        self.assertEqual(set(self.session.saved), {modern['exact_result_handle']})
        self.assertTrue(self.session.view()['imported_observations']['entries'][1]['shown_complete'])
        for field, value in [('target', 'wrong'), ('observed_candidate_id', '0'*64),
                             ('source_edit_authority', True), ('retrieval_only', False)]:
            self.assertIsNone(self.session._capture_identity({**modern, field:value}))
        self.assertEqual(self.session.payload('RES-0001'), canonical_json_bytes(self.legacy))
        self.assertEqual(canonical_json_bytes(self.session.pairs[:5]), original)
        self.assertTrue(self.act(dict(action='work_on', sources=[], results=[]))['accepted'])
        self.assertFalse(any(r['shown_complete'] for r in self.session.view()['imported_observations']['entries']))
        self.assertEqual(self.session.candidate, current)
        self.assertFalse(self.session.view()['verification']['submission']['eligible'])


if __name__ == '__main__':
    unittest.main()
