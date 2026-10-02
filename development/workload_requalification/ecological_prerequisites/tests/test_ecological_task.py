"""Declared source-exposure barrier; inert CPU state/guard qualification only.

Zero input measurement is deliberately synthetic. This suite executes no
checker, model, tokenizer or native runtime and makes no capacity claim.
"""
import copy
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import bootstrap
import ecological_task as module
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file

OLD = bootstrap.ROOT / 'development/workload_requalification/ecological_observation_entry/run-002'
OLD_SEAL_SHA = '9bfe049626221c1b91be59e209bf4e21c16a82c52022346ef803adb726e2b947'


class EcologicalPrerequisiteTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='e19-prerequisite-cpu-')
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.no_subprocess = patch('subprocess.Popen',
            side_effect=AssertionError('Prerequisite CPU tests must not execute a checker'))
        self.no_subprocess.start()
        self.addCleanup(self.no_subprocess.stop)
        self.session = module.initial_session(self.folder)
        self.preceding = []

    def deliver(self):
        view = self.session.view()
        self.session.mark_delivered(view)
        self.session.begin_request()
        return view

    def operation(self, action=None, account=None, *, deliver=True):
        if deliver:
            self.deliver()
        else:
            # Only the preceding empty/old decision was dispatched. The new
            # acquisition result is not yet a model input.
            self.session.begin_request()
        reply = {'discussion': 'Inert CPU exposure/guard qualification.'}
        if action is not None:
            reply['operation'] = action
        if account is not None:
            reply['account'] = account
        return module.process_reply(self.session, reply, lambda view: 0, self.preceding)

    def act(self, action, **kwargs):
        return self.operation(action, **kwargs)['operations'][-1]['result']

    def read(self, path, first=1, last=1, **kwargs):
        result = self.act({'action': 'read', 'path': path, 'start_line': first, 'end_line': last}, **kwargs)
        self.assertTrue(result['accepted'])
        return result

    def status(self):
        return self.session.view()['task_prerequisites']

    def exposures(self):
        return self.session.prerequisite_state()['exposures']

    def original_patch(self):
        return load_json_strict((OLD / 'calls/C03-reply.json').read_bytes())['operation']

    def expose_four(self):
        # Only the target must supply all of the old text for the test edit.
        # One exact nonempty header from each other path is exposure, not a
        # claim of full-file inspection or semantic comprehension.
        for path in module.REQUIRED_INSPECTION_PATHS:
            self.read(path, last=0 if path == module.TARGET else 1)

    def test_fresh_declared_policy_preserves_all_original_sources(self):
        self.assertEqual(sha256_file(OLD / 'RESPONSE_SEAL.json'), OLD_SEAL_SHA)
        seal = load_json_strict((OLD / 'RESPONSE_SEAL.json').read_bytes())
        self.assertEqual(len(seal['source_sha256']), 444)
        for path, digest in seal['source_sha256'].items():
            with self.subTest(original_source=path):
                self.assertEqual(sha256_file(bootstrap.ROOT / path), digest)
        self.assertEqual(self.session.candidate.candidate_id, module.STARTING_ID)
        self.assertEqual(self.session.candidate.file_map, module.starting_files())
        self.assertEqual((len(self.session.candidate.files),
            sum(len(raw) for _, raw in self.session.candidate.files)), (25, 128545))
        self.assertEqual((self.session.requests_used, self.session.calls_used), (0, 0))
        self.assertEqual((self.session.request_limit, self.session.call_limit), (24, 72))
        self.assertEqual(self.session.pairs, [])
        self.assertEqual(self.session.ranges, [])
        self.assertEqual(self.session.saved, {})
        self.assertIsNone(self.session.working_account())
        self.assertIsNone(self.session.check_state())
        self.assertEqual(self.session.edit_checks, {})
        self.assertEqual(self.session.checkers, {'public': module.public_checker()})
        status = self.status()
        self.assertTrue(status['active'])
        self.assertIs(status['exposure_is_not_inspection'], True)
        self.assertEqual(status['required_paths'], list(module.REQUIRED_INSPECTION_PATHS))
        self.assertEqual(status['missing_paths'], list(module.REQUIRED_INSPECTION_PATHS))
        self.assertEqual(self.exposures(), {})
        self.assertIsNone(status['first_mutation'])
        self.assertEqual(self.session.view()['task'], module.task_text())
        self.assertEqual(self.session.view()['working_set']['sources'], [])
        self.assertNotIn(module.hidden_checker().decode(), canonical_json_bytes(self.session.view()).decode())

    def test_actual_c03_proposal_and_literal_region_block_missing_three(self):
        # This is a counterfactual under the NEW declared policy, not replay of
        # the old host's accepted edit and not a claim of model recovery.
        self.read(module.TARGET, last=0)
        self.operation({'action': 'reopen_observation', 'handle': 'OBS-0002'},
            account='Only summary_graph.py has been read; the other named paths remain pending.')
        before = self.session.candidate
        selected = copy.deepcopy((self.session.ranges, self.session.saved))
        proposal = self.original_patch()
        self.assertEqual(proposal['expected_candidate_id'], before.candidate_id)
        self.assertEqual(proposal['expected_file_sha256'], before.file_sha256(module.TARGET))
        self.assertIn(proposal['old'], self.session.view()['working_set']['sources'][0]['content'])
        rejected = self.act(proposal)
        pending = list(module.REQUIRED_INSPECTION_PATHS[1:])
        self.assertFalse(rejected['accepted'])
        self.assertEqual(rejected['rejection_code'], 'missing_source_prerequisites')
        self.assertEqual(rejected['missing_paths'], pending)
        self.assertEqual(self.session.candidate, before)
        self.assertEqual((self.session.ranges, self.session.saved), selected)
        self.assertIsNone(self.status()['first_mutation'])
        witness = self.exposures()[module.TARGET]
        self.assertEqual((witness['request_number'], witness['archive_actions_before_request'],
            witness['source_result_handle']), (2, 1, 'RES-0001'))
        self.assertEqual(witness['candidate_id'], before.candidate_id)
        self.assertEqual(witness['file_sha256'], before.file_sha256(module.TARGET))
        self.assertEqual((witness['start_line'], witness['end_line']), (1, 148))
        self.assertEqual(witness['content_sha256'], sha256_bytes(before.file_map[module.TARGET]))
        region = next(source for source in self.session.view()['working_set']['sources']
            if source['path'] == module.TARGET)
        rejected = self.act({'action': 'replace_region', 'region': region['region_ref'],
            'new': region['content'].replace(proposal['old'], proposal['new']),
            'expected_candidate_id': before.candidate_id})
        self.assertFalse(rejected['accepted'])
        self.assertEqual(rejected['rejection_code'], 'missing_source_prerequisites')
        self.assertEqual(rejected['missing_paths'], pending)
        self.assertEqual(self.session.candidate, before)
        self.assertIsNone(self.status()['first_mutation'])
        for path in pending:
            self.read(path)
        accepted = self.act(proposal)
        self.assertTrue(accepted['accepted'])
        self.assertNotEqual(self.session.candidate, before)
        self.assertEqual(set(self.exposures()), set(module.REQUIRED_INSPECTION_PATHS))
        self.assertFalse(self.status()['active'])
        self.assertIsNotNone(self.status()['first_mutation'])
        self.assertIsNone(self.session.check_state())
        self.assertEqual({p: raw for p, raw in self.session.candidate.files if p != module.TARGET},
            {p: raw for p, raw in before.files if p != module.TARGET})

    def test_acquisition_and_render_do_not_credit_release_does_not_erase_exposure(self):
        self.read(module.TARGET, last=0, deliver=False)
        self.assertEqual(self.exposures(), {})
        for _ in range(3):
            self.session.view()  # Rendering/measuring a candidate input is not dispatch.
        self.assertEqual(self.exposures(), {})
        self.deliver()
        self.assertEqual(set(self.exposures()), {module.TARGET})
        for path in module.REQUIRED_INSPECTION_PATHS[1:]:
            self.act({'action': 'work_on', 'sources': [{'path': path, 'start_line': 1, 'end_line': 1}],
                'results': []})
        self.act({'action': 'work_on_exact', 'regions': [], 'results': []})
        self.assertEqual(set(self.exposures()), set(module.REQUIRED_INSPECTION_PATHS))
        self.assertEqual(self.status()['missing_paths'], [])
        self.assertEqual(self.session.view()['working_set']['sources'], [])
        for path in module.REQUIRED_INSPECTION_PATHS[1:]:
            witness = self.exposures()[path]
            header = self.session.candidate.file_map[path].decode().splitlines(keepends=True)[0].encode()
            self.assertEqual((witness['start_line'], witness['end_line']), (1, 1))
            self.assertEqual((witness['size_bytes'], witness['content_sha256']),
                (len(header), sha256_bytes(header)))
        self.assertIs(self.status()['exposure_is_not_inspection'], True)
        past_exposures = copy.deepcopy(self.exposures())
        before = self.session.candidate
        rejected = self.act(self.original_patch())
        self.assertFalse(rejected['accepted'])
        self.assertNotEqual(rejected.get('rejection_code'), 'missing_source_prerequisites')
        self.assertIn('visible', rejected['error'])
        self.assertEqual(self.session.candidate, before)
        self.assertEqual(self.exposures(), past_exposures)
        self.assertIsNone(self.status()['first_mutation'])
        self.read(module.TARGET, last=0)
        self.assertTrue(self.act(self.original_patch())['accepted'])

    def test_non_source_material_and_partial_history_do_not_credit(self):
        self.operation(account='I inspected all four required files and everything is correct.')
        self.assertEqual(self.exposures(), {})
        self.assertTrue(self.act({'action': 'reopen_observation', 'handle': 'OBS-0002'})['accepted'])
        self.assertTrue(self.act({'action': 'p0_page', 'path': module.SUMMARIES, 'offset': 0})['accepted'])
        self.deliver()
        self.assertEqual(self.exposures(), {})
        acquired = self.read(module.SUMMARIES, deliver=False)
        handle = acquired['exact_result_handle'] if 'exact_result_handle' in acquired else f'RES-{len(self.session.pairs):04d}'
        self.session.ranges = []
        self.session.last = None
        raw = self.session.payload(handle)
        prefix = raw[:min(128, len(raw)-1)].decode('utf-8')
        self.session.saved = {handle: dict(accepted=True, kind='saved_bytes', handle=handle, offset=0,
            next_offset=len(prefix.encode()), total_bytes=len(raw), sha256=sha256_bytes(raw), exact_utf8=prefix)}
        self.deliver()
        self.assertEqual(self.exposures(), {})
        self.assertEqual(self.session.delivered_sources, [])
        self.session.saved[handle].update(next_offset=None, exact_utf8=raw.decode())
        self.deliver()
        self.assertEqual(set(self.exposures()), {module.SUMMARIES})
        self.assertEqual(self.status()['missing_paths'], [p for p in module.REQUIRED_INSPECTION_PATHS if p != module.SUMMARIES])

    def test_malformed_or_empty_exact_source_never_earns_credit(self):
        self.read(module.SUMMARIES, deliver=False)
        good = self.session.view()
        original = next(s for s in good['working_set']['sources'] if s['path'] == module.SUMMARIES)
        changes = {
            'kind': {'kind': 'outline'},
            'wrong_path': {'path': module.TARGET},
            'wrong_candidate': {'candidate_id': 'a'*64},
            'wrong_fingerprint': {'file_sha256': 'b'*64},
            'wrong_bytes': {'content': original['content'] + '# forged\n'},
            'wrong_range': {'returned_start_line': 2},
            'boolean_range': {'returned_start_line': True},
            'empty_eof': {'content': '', 'returned_start_line': 99999, 'returned_end_line': 99998},
        }
        for label, change in changes.items():
            incoming = copy.deepcopy(good)
            incoming['working_set']['sources'][0].update(change)
            with self.subTest(label=label), patch.object(self.session, 'view', return_value=incoming):
                self.session.mark_delivered(incoming)
            self.assertEqual(self.exposures(), {})
        self.session.mark_delivered(good)
        self.assertEqual(set(self.exposures()), {module.SUMMARIES})
        fresh = module.initial_session(self.folder / 'empty')
        self.session = fresh
        line_count = len(fresh.candidate.file_map[module.SUMMARIES].decode().splitlines())
        result = self.act({'action': 'read', 'path': module.SUMMARIES,
            'start_line': line_count+1, 'end_line': 0})
        self.assertFalse(result['accepted'])
        self.deliver()
        self.assertEqual(self.exposures(), {})

    def test_changed_file_invalidates_applicability_without_inventing_mutation(self):
        self.expose_four()
        self.deliver()
        saved = copy.deepcopy(self.exposures())
        before = self.session.candidate
        files = before.file_map
        files[module.SUMMARIES] += b'\n# Deliberate inert changed-version fixture.\n'
        changed = Candidate.create(files, max_file_bytes=before.max_file_bytes)
        # This simulates a new designated version before a first host edit. It
        # is not a saved action, model outcome, or restored legitimate trajectory.
        self.session.candidate = changed
        self.session.versions[changed.candidate_id] = changed
        self.session.ranges = []
        self.session.saved = {}
        self.session.last = None
        self.assertEqual(self.exposures(), saved)
        self.assertEqual(self.status()['missing_paths'], [module.SUMMARIES])
        self.assertIsNone(self.status()['first_mutation'])
        self.read(module.TARGET, last=0)
        proposal = self.original_patch()
        proposal['expected_candidate_id'] = changed.candidate_id
        rejected = self.act(proposal)
        self.assertFalse(rejected['accepted'])
        self.assertEqual(rejected['missing_paths'], [module.SUMMARIES])
        self.assertEqual(self.session.candidate, changed)
        self.assertIsNone(self.status()['first_mutation'])

    def test_literal_region_acceptance_preserves_first_boundary_on_later_edit(self):
        self.expose_four()
        self.deliver()
        source = next(row for row in self.session.view()['working_set']['sources']
            if row['path'] == module.TARGET)
        before = self.session.candidate
        proposal = self.original_patch()
        accepted = self.act({'action': 'replace_region', 'region': source['region_ref'],
            'new': source['content'].replace(proposal['old'], proposal['new']),
            'expected_candidate_id': before.candidate_id})
        self.assertTrue(accepted['accepted'])
        boundary = copy.deepcopy(self.status()['first_mutation'])
        self.assertEqual(boundary['action_handle'], accepted['exact_action_handle'])
        self.assertEqual(boundary['previous_candidate_id'], before.candidate_id)
        self.assertEqual(boundary['candidate_id'], self.session.candidate.candidate_id)
        self.assertEqual(accepted['source_prerequisite_boundary'], boundary)
        # A later ordinary guarded edit may proceed without reopening unrelated
        # prerequisite files, but the first temporal boundary does not move.
        first_line = self.session.candidate.file_map[module.TARGET].decode().splitlines(keepends=True)[0]
        later = self.act({'action': 'patch', 'path': module.TARGET,
            'old': first_line, 'new': first_line + '# Inert second CPU edit.\n',
            'expected_candidate_id': self.session.candidate.candidate_id,
            'expected_file_sha256': self.session.candidate.file_sha256(module.TARGET)})
        self.assertTrue(later['accepted'])
        self.assertEqual(self.status()['first_mutation'], boundary)
        self.assertIsNone(self.session.check_state())

    def test_multidigit_boundary_typed_restore_and_prerequisite_tamper_rejection(self):
        self.expose_four()
        for number in range(5):
            self.operation(account='CPU pending finding ' + str(number))
        self.assertEqual(self.session.calls_used, 9)
        proposal = self.original_patch()
        accepted = self.act(proposal)
        self.assertTrue(accepted['accepted'])
        self.assertEqual(self.session.calls_used, 10)
        saved = module.snapshot(self.session)
        self.assertEqual(set(saved['diffs']), {10})
        self.assertIsNotNone(saved['source_prerequisites']['first_mutation'])
        self.assertFalse(self.status()['active'])
        for value in (saved, load_json_strict(canonical_json_bytes(saved))):
            incoming = copy.deepcopy(value)
            restored = module.restore(incoming, self.session.candidate, self.folder, replay=True)
            self.assertEqual(incoming, value)
            self.assertEqual(restored.view(), self.session.view())
            self.assertEqual(module.snapshot(restored), saved)
        encoded = load_json_strict(canonical_json_bytes(saved))
        changes = []
        value = copy.deepcopy(encoded)
        value['source_prerequisites']['policy']['required_paths'] = list(module.REQUIRED_INSPECTION_PATHS[:1])
        changes.append(('weakened_policy', value))
        value = copy.deepcopy(encoded)
        value['source_prerequisites']['exposures'].pop(module.SUMMARIES)
        changes.append(('missing_boundary_prerequisite', value))
        value = copy.deepcopy(encoded)
        value['source_prerequisites']['first_mutation'] = None
        changes.append(('erased_boundary', value))
        value = copy.deepcopy(encoded)
        value['diffs']['010'] = value['diffs'].pop('10')
        changes.append(('diff_alias', value))
        value = copy.deepcopy(encoded)
        value['diffs'][10] = value['diffs']['10']
        changes.append(('diff_collision', value))
        for field, replacement in {
            'path': module.TARGET,
            'candidate_id': 'a'*64,
            'file_sha256': 'b'*64,
            'start_line': 2,
            'end_line': 0,
            'content_sha256': 'c'*64,
            'size_bytes': 0,
            'region_ref': 'SRC-forged',
            'request_number': 24,
            'archive_actions_before_request': 72,
            'source_result_handle': 'RES-9999',
            'presentation_sha256': 'd'*64,
        }.items():
            value = copy.deepcopy(encoded)
            value['source_prerequisites']['exposures'][module.SUMMARIES][field] = replacement
            changes.append(('witness_' + field, value))
        for field, replacement in {
            'action_handle': 'EVT-0009',
            'request_number': 24,
            'path': module.SUMMARIES,
            'previous_candidate_id': 'a'*64,
            'candidate_id': 'b'*64,
            'exposures_sha256': 'c'*64,
        }.items():
            value = copy.deepcopy(encoded)
            value['source_prerequisites']['first_mutation'][field] = replacement
            changes.append(('boundary_' + field, value))
        for label, value in changes:
            with self.subTest(label=label), self.assertRaises(ValueError):
                module.restore(value, self.session.candidate, self.folder, replay=True)


if __name__ == '__main__':
    unittest.main()
