"""Validate copied observations, including undisplayed bytes and inventory changes."""
from pathlib import Path
import tempfile
import unittest

import interpolation_continuation as task


class InheritedObservationTests(unittest.TestCase):
    def test_exact_bytes_and_changed_hidden_tail(self):
        original = task.verified_observation_files(task.OLD/'observations')
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            for name, raw in original:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            self.assertEqual(original,task.verified_observation_files(root))
            path = next(root.rglob('stdout.bin'))
            path.write_bytes(path.read_bytes()+b' ')
            with self.assertRaisesRegex(AssertionError,'stdout.bin'):
                task.verified_observation_files(root)

    def test_missing_or_extra_observation_file(self):
        original = task.verified_observation_files(task.OLD/'observations')
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            with self.assertRaisesRegex(AssertionError,'inventory'):
                task.verified_observation_files(root)
            for name,raw in original:
                p=root/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(raw)
            (root/'unexpected.bin').write_bytes(b'new')
            with self.assertRaisesRegex(AssertionError,'inventory'):
                task.verified_observation_files(root)
