"""Entry, observation environment and temporal audit boundaries; no inference."""
import copy
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import source_task as study
from qualification_route import journey
from temporal_audit import Trace
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes


class EntryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='e18_source_cpu_')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.folder = Path(cls.temp.name)
        cls.session = study.initial_session(cls.folder)
        cls.rows = []
        cls.result = journey(study.Task(), cls.session, lambda view: len(canonical_json_bytes(view)) // 3 + 1000,
            record=lambda row, current: cls.rows.append(copy.deepcopy(row)))

    def test_original_entry_and_declared_clarification_have_no_selected_solution(self):
        s = study.initial_session()
        self.assertEqual(s.candidate.candidate_id, study.STARTING_ID)
        self.assertEqual(len(s.candidate.files), 130)
        self.assertFalse(s.pairs or s.ranges or s.saved or s.working_account() or s.check_state())
        self.assertEqual((s.requests_used, s.calls_used, s.request_limit, s.call_limit), (0, 0, 24, 72))
        self.assertEqual(study.public_checker(), study.hidden_checker())
        self.assertNotIn('ember-', s.task)
        self.assertIn('after that change in a fresh Python process', s.task)
        self.assertEqual((study.AREA / 'TASK.txt').read_text(encoding='utf-8'), s.task)

    def test_complete_supported_journey_and_snapshot_restore(self):
        self.assertTrue(self.result['submitted'])
        self.assertTrue(self.result['audit']['temporal_contract_met'])
        self.assertEqual((self.result['requests'], self.result['new_operations']), (13, 13))
        for row in self.rows:
            self.assertTrue(row['input_support'])
        state = study.snapshot(self.session)
        restored = study.restore(state, self.session.candidate, self.folder, replay=True)
        self.assertEqual(study.snapshot(restored), state)
        self.assertEqual(restored.view(), self.session.view())
        for path, raw in study.starting_candidate().files:
            if path not in (study.TARGET, study.POLICY, study.SECONDARY):
                self.assertEqual(self.session.candidate.file_map[path], raw)

    def audit_rows(self, rows):
        trace = Trace(study)
        for row in rows:
            trace.observe(row['name'], row['before_view'], row['outcome']['operations'], self.session.versions)
        return trace.result()

    def test_incomplete_ledger_not_promoted_by_whole_file_or_eof_flags(self):
        rows = copy.deepcopy(self.rows)
        path = study.REQUIRED_INSPECTION_PATHS[0]
        for row in rows:
            view = row['before_view']
            for source in view['working_set']['sources']:
                if source['path'] == path:
                    source['content'] = ''.join(source['content'].splitlines(keepends=True)[1:])
                    source['returned_start_line'] = 2
                    source['whole_file_shown'] = True
        audit = self.audit_rows(rows)
        self.assertFalse(audit['complete_ledger_delivery'][path])
        self.assertFalse(audit['temporal_contract_met'])

    def test_refresh_without_a_requested_reacquisition_is_not_credited(self):
        rows = copy.deepcopy(self.rows)
        row = next(r for r in rows if r['name'] == 'reacquire-policy')
        row['outcome']['operations'][0]['action'] = dict(action='history', offset=0, limit=1)
        audit = self.audit_rows(rows)
        self.assertTrue(audit['all_ledgers_delivered'])
        self.assertTrue(audit['prescribed_edit_order'])
        self.assertFalse(audit['requested_current_policy_delivered_before_secondary'])

    def test_later_policy_delivery_cannot_retroactively_support_secondary_edit(self):
        rows = copy.deepcopy(self.rows)
        for row in rows:
            if row['name'] in ('secondary-support', 'secondary-work'):
                view = row['before_view']
                view['working_set']['sources'] = [s for s in view['working_set']['sources'] if s['path'] != study.POLICY]
                # Ordinary feedback contains only metadata/source-free references;
                # remove a source-bearing read receipt if a host version includes it.
                if view.get('latest_feedback'):
                    view['latest_feedback']['result'] = dict(accepted=True, body_omitted=True)
        self.assertFalse(self.audit_rows(rows)['requested_current_policy_delivered_before_secondary'])

    def test_original_checker_matches_ordinary_environment_on_pass_and_meaningful_failure(self):
        final = self.session.candidate
        bad = Candidate.create({**final.file_map, study.TARGET:
            b'from policy.current import active_prefix\n\ndef normalize_primary(value: str) -> str:\n    return active_prefix() + value.strip().casefold()\n'})
        for index, candidate in enumerate((final, bad), 1):
            with self.subTest(dynamic=(candidate is bad)), tempfile.TemporaryDirectory(prefix='e18_ordinary_') as name:
                root = Path(name)
                for path, body in candidate.files:
                    dest = root / path
                    self.assertTrue(dest.resolve().is_relative_to(root.resolve()))
                    dest.parent.mkdir(parents=True, exist_ok=True)
                    dest.write_bytes(body)
                (root / '_public_check.py').write_bytes(study.public_checker())
                observed = subprocess.run([sys.executable, '-B', '-X', 'utf8', '_public_check.py'],
                    cwd=root, capture_output=True, timeout=30)
                checked = self.session.observations.execute(candidate, study.public_checker(), 'public', f'CHK-{90+index:04d}')
                self.assertEqual(observed.returncode == 0, checked['passed'])
                self.assertEqual(checked['passed'], candidate is final)
                if candidate is bad:
                    self.assertIn(b"assert normalize_primary(' A ') == 'ember-a'", observed.stderr)
                    self.assertTrue(checked['capture_complete'])


if __name__ == '__main__':
    unittest.main(verbosity=2)
