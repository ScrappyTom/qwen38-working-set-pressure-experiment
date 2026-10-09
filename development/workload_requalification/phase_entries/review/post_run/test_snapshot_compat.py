"""Actual serialized checkpoint and negative controls for the evaluator fix."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
import phase_task as study
from snapshot_compat import restored_diff_keys
from working_set_exp.jsonutil import canonical_json_bytes


class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.task = study.Task('002')
        stem = self.task.RUN / 'after/C09-O01'
        self.state = self.task.read(Path(str(stem) + '-state.json'))
        self.candidate = self.task.candidate_from_snapshot(self.task.read(Path(str(stem) + '-candidate.json')))

    def restore(self, state):
        return self.task.restore(state, self.candidate, self.task.RUN, replay=True)

    def test_original_failure_then_exact_restore(self):
        with self.assertRaisesRegex(ValueError, 'checkpoint reconstruction differs'):
            self.restore(self.state)
        prior = canonical_json_bytes(self.state)
        with restored_diff_keys(study.Task):
            restored = self.restore(self.state)
        self.assertEqual(canonical_json_bytes(self.state), prior)
        saved = self.task.RUN / 'after/C09-O01-state.json'
        self.assertEqual(canonical_json_bytes(self.task.snapshot(restored)), saved.read_bytes())

    def test_changed_diff_still_rejected(self):
        state = copy.deepcopy(self.state)
        state['diffs']['14'] += '\nunauthorized change'
        with restored_diff_keys(study.Task), self.assertRaisesRegex(ValueError, 'diff history differs'):
            self.restore(state)

    def test_other_state_restriction_still_enforced(self):
        state = copy.deepcopy(self.state)
        state['request_limit'] += 1
        with restored_diff_keys(study.Task), self.assertRaisesRegex(ValueError, 'shape/opportunity differs'):
            self.restore(state)

    def test_noncanonical_key_rejected(self):
        state = copy.deepcopy(self.state)
        state['diffs']['014'] = state['diffs'].pop('14')
        with restored_diff_keys(study.Task), self.assertRaisesRegex(ValueError, 'noncanonical diff'):
            self.restore(state)


if __name__ == '__main__':
    unittest.main()
