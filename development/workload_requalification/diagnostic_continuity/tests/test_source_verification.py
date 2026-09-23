from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import bootstrap
import source_verification as verify
from working_set_exp.jsonutil import sha256_bytes


class VerificationTests(unittest.TestCase):
    def test_all_files_checked_and_changed_bytes_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            for name in ('a','b','c'): (root/name).write_bytes(name.encode())
            bound={name:sha256_bytes(name.encode()) for name in ('a','b','c')}
            verify.verify_sources(root,bound)
            # Same length; no timestamp/size cache can substitute for hashing.
            (root/'a').write_bytes(b'x')
            (root/'b').unlink()
            with patch.object(verify,'sha256_file',wraps=verify.sha256_file) as observed:
                with self.assertRaisesRegex(RuntimeError,'source changed: a'):
                    verify.verify_sources(root,bound)
                self.assertEqual({c.args[0].name for c in observed.call_args_list},set(bound))

    def test_missing_file_and_bad_concurrency(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(RuntimeError,'source unavailable: missing'):
                verify.verify_sources(temp,{'missing':'0'})
            for workers in (0,9,True):
                with self.assertRaises(ValueError): verify.verify_sources(temp,{},workers=workers)


if __name__ == '__main__':unittest.main()
