"""Restore every actual native checkpoint, including 2-to-3 digit diff addresses."""
import copy
from pathlib import Path
import sys
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import completion_task as entry
import qualified_task


class CheckpointQualification(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.task = qualified_task.Task()
        cls.folder = entry.AREA / 'preparation-001'
        cls.paths = sorted((cls.folder / 'route').glob('*-state.json'))
        cls.final = entry.read(cls.paths[-1])

    def restore(self, state):
        candidate = next(v for v in state['source_versions'] if v['candidate_id'] == state['candidate_id'])
        return self.task.restore(state, candidate, self.folder / 'scripted', replay=True)

    def test_original_mismatch_is_reproduced(self):
        state = entry.read(self.folder / 'route/08-state.json')
        candidate = next(v for v in state['source_versions'] if v['candidate_id'] == state['candidate_id'])
        with self.assertRaises(AssertionError):
            entry.Task().restore(state, candidate, self.folder / 'scripted', replay=True)

    def test_all_native_checkpoints_roundtrip_exactly(self):
        self.assertEqual(len(self.paths), 12)
        for path in self.paths:
            with self.subTest(checkpoint=path.name):
                state = entry.read(path)
                unchanged = copy.deepcopy(state)
                restored = self.restore(state)
                self.assertEqual(state, unchanged)
                self.assertEqual(entry.canonical_json_bytes(entry.snapshot(restored)), path.read_bytes())
                # Native measurements used this exact model-facing state.
                following = entry.read(path.with_name(path.name.replace('-state', '-following')))
                self.assertEqual(restored.view(), following)

    def test_noncanonical_and_aliased_addresses_reject(self):
        for key in ('033', '+33', '33.0', ' 33', '\u0663\u0663', 0, -1, True):
            with self.subTest(address=repr(key)):
                state = copy.deepcopy(self.final)
                state['diffs'][key] = state['diffs']['33']
                with self.assertRaises(ValueError):
                    self.restore(state)
        state = copy.deepcopy(self.final)
        state['diffs'][33] = state['diffs']['33']
        with self.assertRaises(ValueError):
            self.restore(state)

    def test_missing_changed_and_reassigned_diffs_reject(self):
        for which in ('missing', 'changed_old', 'changed_new', 'reassigned', 'missing_receipt'):
            with self.subTest(change=which):
                state = copy.deepcopy(self.final)
                if which == 'missing':
                    del state['diffs']['109']
                elif which == 'changed_old':
                    state['diffs']['33'] += '\n'
                elif which == 'changed_new':
                    state['diffs']['109'] += '\n'
                elif which == 'reassigned':
                    state['diffs']['108'] = state['diffs'].pop('109')
                else:
                    del state['pairs'][108]['result']['applied_diff']
                with self.assertRaises(ValueError):
                    self.restore(state)


if __name__ == '__main__':
    unittest.main(verbosity=2)
