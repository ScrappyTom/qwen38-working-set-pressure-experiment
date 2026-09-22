"""CPU-only prerequisite closure and original-contract isolation checks."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import navigation_task as task
import repair_task as original
import run_uncoached_contribution as runner
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


class PrerequisiteTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        self.root = Path(self.directory.name)
        self.folder = self.root / 'native'
        self.folder.mkdir()
        (self.root / 'implementation.py').write_bytes(b'# exact implemented source\n')
        (self.root / 'actual-input.json').write_bytes(b'{"actual":"saved input"}')
        self.implementation = {'implementation.py': sha256_file(self.root / 'implementation.py')}
        self.sources = {**self.implementation,
                        'actual-input.json': sha256_file(self.root / 'actual-input.json')}
        self.result = dict(status='passed', completion_requests=0, checks_executed=1)
        (self.folder / 'RESULTS.json').write_bytes(canonical_json_bytes(self.result))
        (self.folder / 'actual-wire.json').write_bytes(b'{"messages":[]}')
        self.seal()
        for name, value in [('ROOT', self.root), ('NATIVE_QUALIFIED', self.folder)]:
            manager = patch.object(task, name, value)
            manager.start()
            self.addCleanup(manager.stop)
        manager = patch.object(task, 'implementation_identities', return_value=self.implementation)
        manager.start()
        self.addCleanup(manager.stop)

    def seal(self, *, sources=None, omit_results=False):
        files = [dict(path=p.name, size_bytes=p.stat().st_size, sha256=sha256_file(p))
                 for p in sorted(self.folder.glob('*.json')) if p.name != 'SEAL.json'
                 and not (omit_results and p.name == 'RESULTS.json')]
        value = dict(status='qualified_no_model_inference', completion_requests=0,
                     source_sha256=self.sources if sources is None else sources, files=files,
                     aggregate_sha256=sha256_bytes(canonical_json_bytes(files)))
        (self.folder / 'SEAL.json').write_bytes(canonical_json_bytes(value))

    def test_valid_native_closure_propagates_implementation_actual_inputs_and_outputs(self):
        result = task.qualification_bindings()
        self.assertEqual(set(result), {'implementation.py', 'actual-input.json',
                                      'native/SEAL.json', 'native/RESULTS.json',
                                      'native/actual-wire.json'})
        for name, digest in result.items():
            self.assertEqual(digest, sha256_file(self.root / name))

    def test_changed_actual_input_is_rejected(self):
        (self.root / 'actual-input.json').write_bytes(b'{"actual":"changed input"}')
        with self.assertRaises(AssertionError):
            task.qualification_bindings()

    def test_missing_implementation_binding_is_rejected(self):
        self.seal(sources={'actual-input.json': self.sources['actual-input.json']})
        with self.assertRaisesRegex(AssertionError, 'source closure'):
            task.qualification_bindings()

    def test_corrupted_qualification_output_is_rejected(self):
        (self.folder / 'actual-wire.json').write_bytes(b'{"messages":["changed"]}')
        with self.assertRaises(AssertionError):
            task.qualification_bindings()

    def test_results_must_belong_to_the_sealed_inventory(self):
        self.seal(omit_results=True)
        with self.assertRaises(AssertionError):
            task.qualification_bindings()

    def test_incomplete_qualification_cannot_authorize_preparation(self):
        self.result['status'] = 'failed_preserved'
        (self.folder / 'RESULTS.json').write_bytes(canonical_json_bytes(self.result))
        self.seal()
        with self.assertRaises(AssertionError):
            task.qualification_bindings()


class OriginalContractTests(unittest.TestCase):
    def test_original_initial_candidates_tasks_checkers_and_policy_are_unchanged(self):
        # Replay mode keeps construction read-only. No checker or runtime is invoked.
        for case in ('artifact_map', 'shift', 'receipts'):
            with self.subTest(case=case):
                old = original.Task(case, replay_folder=task.ROOT / 'no-observations-read')
                new = task.Task(case, replay_folder=task.ROOT / 'no-observations-read')
                before, after = old.initial_session(), new.initial_session()
                old_view, new_view = before.view(), after.view()
                self.assertEqual(old.candidate_bytes(before.candidate), new.candidate_bytes(after.candidate))
                self.assertEqual(before.task, after.task)
                self.assertEqual(before.checkers, after.checkers)
                self.assertEqual(before.check_contracts, after.check_contracts)
                self.assertEqual(before.edit_checks, after.edit_checks)
                self.assertEqual(after.edit_checks, {})
                self.assertEqual((after.request_limit, after.call_limit), (24, 72))
                self.assertEqual((after.requests_used, after.calls_used), (0, 0))
                self.assertFalse(after.pairs)
                self.assertFalse(after.delivered_sources)
                self.assertEqual(new_view['working_set'], {'sources': [], 'saved_results': []})
                self.assertIsNone(new_view['working_account'])
                self.assertEqual(canonical_json_bytes(old_view), canonical_json_bytes(new_view))
                a, b = runner.Adapter(old).request_for(old_view), runner.Adapter(new).request_for(new_view)
                self.assertEqual(a['messages'][1], b['messages'][1])
                self.assertEqual(b['messages'][0]['content'],
                                 a['messages'][0]['content'] + '\n\n' + task.navigation.REFERENCE_ADDITION)
                a_settings, b_settings = copy.deepcopy(a), copy.deepcopy(b)
                a_settings.pop('messages'); b_settings.pop('messages')
                self.assertEqual(a_settings, b_settings)
                self.assertEqual(a['grammar'], b['grammar'])
                self.assertNotIn('response_format', b)
                self.assertEqual(b['chat_template_kwargs'],
                                 dict(enable_thinking=True, reasoning_effort='medium'))
                self.assertEqual(b['seed'], 961221)
                self.assertEqual(new.reply_schema(), old.reply_schema())


if __name__ == '__main__':
    unittest.main()
