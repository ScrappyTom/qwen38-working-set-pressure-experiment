"""E20 continuous dispatched-source coverage; no candidate/check/model execution.

All complete-input measurements here are synthetic zero. They qualify state and
guards only, not native fit or model use. Native qualification is separate.
"""
import copy
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

PREFIX = 'src/addressable_information_layer/'
HASHING, IMPORTERS = PREFIX+'hashing.py', PREFIX+'importers.py'
OLD = bootstrap.ROOT / 'development/workload_requalification/ecological_prerequisites/run-001'
OLD_SEAL_SHA = 'bde101537a5531ae0a1b260850728513bd3e719c9c488db7459311e4dc70d04d'


class CompleteCoverageTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='e20-coverage-cpu-')
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.no_subprocess = patch('subprocess.Popen',
            side_effect=AssertionError('Continuous coverage CPU tests must not execute a checker'))
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
            # The result acquired by this reply has not itself been dispatched.
            self.session.begin_request()
        reply = {'discussion': 'Inert CPU continuous-coverage qualification.'}
        if action is not None:
            reply['operation'] = action
        if account is not None:
            reply['account'] = account
        return module.process_reply(self.session, reply, lambda view: 0, self.preceding)

    def act(self, action, **kwargs):
        return self.operation(action, **kwargs)['operations'][-1]['result']

    def read(self, path, first=1, last=0, **kwargs):
        result = self.act({'action': 'read', 'path': path,
            'start_line': first, 'end_line': last}, **kwargs)
        self.assertTrue(result['accepted'])
        return result

    def select(self, path, first=1, last=0):
        result = self.act({'action': 'work_on',
            'sources': [{'path': path, 'start_line': first, 'end_line': last}], 'results': []})
        self.assertTrue(result['accepted'])
        return result

    def complete_all(self):
        # Replace rather than accumulate the eleven bodies. This is a cumulative
        # exposure test, not a requirement that they be simultaneously resident.
        for path in module.REQUIRED_INSPECTION_PATHS:
            self.select(path)
        self.deliver()

    def cosmetic_patch(self, path=IMPORTERS):
        candidate = self.session.candidate
        old = candidate.file_map[path].decode().splitlines(keepends=True)[0]
        return dict(action='patch', path=path, old=old,
            new=old+'# Inert CPU mutation-boundary fixture.\n',
            expected_candidate_id=candidate.candidate_id,
            expected_file_sha256=candidate.file_sha256(path))

    def status(self):
        return self.session.view()['task_prerequisites']

    def coverage(self):
        return self.session.coverage_state()['coverage']

    def row(self, path):
        return next(row for row in self.status()['coverage'] if row['path'] == path)

    def test_exact_fresh_entry_and_original_460_sources_remain_unchanged(self):
        self.assertEqual(sha256_file(OLD/'RESPONSE_SEAL.json'), OLD_SEAL_SHA)
        old_seal = load_json_strict((OLD/'RESPONSE_SEAL.json').read_bytes())
        self.assertEqual(len(old_seal['source_sha256']), 460)
        for path, digest in old_seal['source_sha256'].items():
            with self.subTest(source=path):
                self.assertEqual(sha256_file(bootstrap.ROOT/path), digest)
        candidate = self.session.candidate
        self.assertEqual(candidate.candidate_id,
            '2355c3eaa32dcf8db2659a75feb3a93309255fbff60e14b7f154dc34c47675c0')
        self.assertEqual(candidate.file_map, module.starting_files())
        self.assertEqual((len(candidate.files), sum(len(raw) for _, raw in candidate.files)), (25, 128546))
        self.assertEqual(candidate.max_file_bytes, 24000)
        self.assertEqual(len(candidate.file_map[PREFIX+'__init__.py']), 69)
        self.assertEqual(tuple(module.REQUIRED_INSPECTION_PATHS), tuple(module.fixture()['required_inspection_paths']))
        self.assertEqual((len(module.REQUIRED_INSPECTION_PATHS),
            sum(len(candidate.file_map[p]) for p in module.REQUIRED_INSPECTION_PATHS),
            sum(len(candidate.file_map[p].decode().splitlines()) for p in module.REQUIRED_INSPECTION_PATHS)),
            (11, 72238, 2045))
        self.assertEqual((self.session.requests_used, self.session.calls_used), (0, 0))
        self.assertEqual((self.session.request_limit, self.session.call_limit), (24, 72))
        self.assertEqual(self.session.pairs, [])
        self.assertEqual(self.session.ranges, [])
        self.assertEqual(self.session.saved, {})
        self.assertIsNone(self.session.working_account())
        self.assertIsNone(self.session.check_state())
        self.assertEqual(self.session.edit_checks, {})
        self.assertEqual(self.session.checkers, {'public': module.public_checker()})
        self.assertEqual(self.session.view()['task'], module.task_text())
        self.assertEqual(self.session.view()['working_set']['sources'], [])
        self.assertNotIn('imported_observations', self.session.view())
        self.assertNotIn(module.hidden_checker().decode(), canonical_json_bytes(self.session.view()).decode())
        self.assertEqual(self.coverage(), {})
        self.assertEqual(len(self.status()['coverage']), 11)
        self.assertEqual(self.status()['missing_paths'], list(module.REQUIRED_INSPECTION_PATHS))
        self.assertIsNone(self.session.coverage_state()['first_mutation'])
        self.assertTrue(self.status()['active'])
        self.assertEqual(self.session.coverage_state()['policy'], module.coverage_policy())

    def test_dispatch_only_merged_adjacent_and_overlap_use_multiple_carriers(self):
        self.read(HASHING, 1, 10, deliver=False)
        for _ in range(3):
            self.session.view()  # Admission/rendering is not actual dispatch.
        self.assertEqual(self.coverage(), {})
        self.deliver()
        self.assertEqual(self.coverage()[HASHING]['intervals'], [[1, 10]])
        self.read(HASHING, 11, 20)
        merged = next(row for row in self.session.view()['working_set']['sources'] if row['path'] == HASHING)
        self.assertEqual((merged['returned_start_line'], merged['returned_end_line']), (1, 20))
        self.assertEqual(self.coverage()[HASHING]['intervals'], [[1, 10]])
        self.deliver()
        self.assertEqual(self.coverage()[HASHING]['intervals'], [[1, 20]])
        witnesses = self.coverage()[HASHING]['witnesses']
        self.assertEqual({w['source_result_handle'] for w in witnesses}, {'RES-0001', 'RES-0002'})
        self.assertEqual([(w['start_line'], w['end_line']) for w in witnesses], [(1, 10), (11, 20)])
        self.read(HASHING, 5, 25)
        self.deliver()
        self.assertEqual(self.coverage()[HASHING]['intervals'], [[1, 25]])
        witnesses = self.coverage()[HASHING]['witnesses']
        self.assertEqual((witnesses[-1]['start_line'], witnesses[-1]['end_line']), (21, 25))
        self.assertEqual(witnesses[-1]['source_result_handle'], 'RES-0003')
        self.assertEqual(witnesses[-1]['source_index'], 0)
        exact = self.session.candidate.file_map[HASHING].decode().splitlines(keepends=True)
        for witness in witnesses:
            body = ''.join(exact[witness['start_line']-1:witness['end_line']]).encode()
            self.assertEqual((witness['size_bytes'], witness['content_sha256']),
                (len(body), sha256_bytes(body)))
        saved = copy.deepcopy(self.session.coverage_state())
        for _ in range(3):
            self.deliver()
        self.assertEqual(self.session.coverage_state(), saved)
        self.assertEqual(len(self.status()['coverage']), 11)
        for row in self.status()['coverage']:
            self.assertNotIn('witnesses', row)
        self.assertEqual((self.row(HASHING)['covered_lines'], self.row(HASHING)['missing_lines']), (25, 14))

    def test_prefix_and_eof_with_gap_and_eof_only_are_not_complete(self):
        self.select(HASHING, 1, 10)
        self.select(HASHING, 39, 39)
        self.deliver()
        self.assertEqual(self.coverage()[HASHING]['intervals'], [[1, 10], [39, 39]])
        self.assertFalse(self.row(HASHING)['complete'])
        self.assertEqual(self.row(HASHING)['first_missing_interval'], [11, 38])
        self.assertEqual((self.row(HASHING)['covered_lines'], self.row(HASHING)['missing_lines']), (11, 28))
        self.select(HASHING, 11, 38)
        self.assertFalse(self.row(HASHING)['complete'])
        self.deliver()
        self.assertEqual(self.coverage()[HASHING]['intervals'], [[1, 39]])
        self.assertTrue(self.row(HASHING)['complete'])
        self.assertIsNone(self.row(HASHING)['first_missing_interval'])
        # A separate fresh inert fixture isolates the old EOF-without-prefix
        # false positive; this is not an actor allowance reset or model retry.
        self.session = module.initial_session(self.folder/'eof-only')
        self.preceding = []
        self.select(HASHING, 20, 39)
        self.deliver()
        self.assertFalse(self.row(HASHING)['complete'])
        self.assertEqual(self.row(HASHING)['first_missing_interval'], [1, 19])
        result = self.act({'action': 'read', 'path': HASHING, 'start_line': 40, 'end_line': 0})
        self.assertFalse(result['accepted'])
        self.deliver()
        self.assertEqual(self.coverage()[HASHING]['intervals'], [[20, 39]])

    def test_release_retains_complete_coverage_but_not_current_edit_authority(self):
        self.complete_all()
        self.assertEqual(self.status()['missing_paths'], [])
        self.assertTrue(all(row['complete'] for row in self.status()['coverage']))
        self.act({'action': 'work_on_exact', 'regions': [], 'results': []})
        saved = copy.deepcopy(self.session.coverage_state())
        self.assertEqual(self.session.view()['working_set']['sources'], [])
        before = self.session.candidate
        rejected = self.act(self.cosmetic_patch())
        self.assertFalse(rejected['accepted'])
        self.assertNotEqual(rejected.get('rejection_code'), 'missing_source_coverage')
        self.assertIn('visible', rejected['error'])
        self.assertEqual(self.session.candidate, before)
        self.assertEqual(self.session.coverage_state(), saved)
        self.assertIsNone(saved['first_mutation'])
        self.select(IMPORTERS)
        self.assertTrue(self.act(self.cosmetic_patch())['accepted'])
        self.assertIsNone(self.session.check_state())

    def test_accounts_outline_inventory_and_partial_history_never_credit(self):
        self.operation(account='I inspected all eleven files completely and they are safe.')
        self.assertTrue(self.act({'action': 'p0_page', 'path': HASHING, 'offset': 0})['accepted'])
        self.assertTrue(self.act({'action': 'selection_page', 'offset': 0})['accepted'])
        self.deliver()
        self.assertEqual(self.coverage(), {})
        self.read(HASHING, 1, 10, deliver=False)
        handle = f'RES-{len(self.session.pairs):04d}'
        raw = self.session.payload(handle)
        self.session.ranges, self.session.last = [], None
        prefix = raw[:128].decode()
        self.session.saved = {handle: dict(accepted=True, kind='saved_bytes', handle=handle,
            offset=0, next_offset=len(prefix.encode()), total_bytes=len(raw),
            sha256=sha256_bytes(raw), exact_utf8=prefix)}
        self.deliver()
        self.assertEqual(self.coverage(), {})
        self.assertEqual(self.session.delivered_sources, [])
        self.session.saved[handle].update(next_offset=None, exact_utf8=raw.decode())
        self.deliver()
        # A full serialized result may contain only a source excerpt. It credits
        # that exact excerpt, not the unread remainder of the source file.
        self.assertEqual(self.coverage()[HASHING]['intervals'], [[1, 10]])
        self.assertFalse(self.row(HASHING)['complete'])
        self.assertEqual(self.row(HASHING)['first_missing_interval'], [11, 39])

    def test_invalid_source_identity_bytes_extent_and_empty_eof_are_ignored(self):
        self.read(HASHING, 1, 10, deliver=False)
        good = self.session.view()
        source = good['working_set']['sources'][0]
        changes = {
            'outline': {'kind': 'file_outline'},
            'path': {'path': IMPORTERS},
            'candidate': {'candidate_id': 'a'*64},
            'fingerprint': {'file_sha256': 'b'*64},
            'bytes': {'content': source['content']+'# forged\n'},
            'range': {'returned_start_line': 2},
            'boolean': {'returned_start_line': True},
            'empty_eof': {'content': '', 'returned_start_line': 40, 'returned_end_line': 39},
        }
        for label, change in changes.items():
            incoming = copy.deepcopy(good)
            incoming['working_set']['sources'][0].update(change)
            # This inert malformed-presentation fixture bypasses only view
            # equality. The independent exact-source validator still applies.
            with self.subTest(label=label), patch.object(self.session, 'view', return_value=incoming):
                self.session.mark_delivered(incoming)
            self.assertEqual(self.coverage(), {})
        self.session.mark_delivered(good)
        self.assertEqual(self.coverage()[HASHING]['intervals'], [[1, 10]])

    def test_new_file_fingerprint_cannot_complete_old_prefix(self):
        self.select(HASHING, 1, 10)
        self.select(IMPORTERS)
        self.deliver()
        self.assertTrue(self.row(IMPORTERS)['complete'])
        old_hash = self.coverage()[HASHING]['file_sha256']
        files = self.session.candidate.file_map
        files[HASHING] += b'# Inert changed-version fixture.\n'
        changed = Candidate.create(files, max_file_bytes=self.session.candidate.max_file_bytes)
        # Hypothetical designation, not an executed edit or a legitimate
        # restored actor trajectory. It isolates per-file applicability.
        self.session.candidate = changed
        self.session.versions[changed.candidate_id] = changed
        self.session.ranges, self.session.saved, self.session.last = [], {}, None
        self.assertEqual(self.coverage()[HASHING]['file_sha256'], old_hash)
        self.assertEqual(self.row(HASHING)['covered_lines'], 0)
        self.assertEqual(self.row(HASHING)['first_missing_interval'], [1, 40])
        self.assertTrue(self.row(IMPORTERS)['complete'])
        self.select(HASHING, 11, 40)
        self.deliver()
        self.assertEqual(self.coverage()[HASHING]['file_sha256'], changed.file_sha256(HASHING))
        self.assertEqual(self.coverage()[HASHING]['intervals'], [[11, 40]])
        self.assertEqual(self.row(HASHING)['first_missing_interval'], [1, 10])
        self.assertTrue(self.row(IMPORTERS)['complete'])
        self.assertIsNone(self.session.coverage_state()['first_mutation'])

    def test_both_mutation_forms_reject_missing_coverage_and_freeze_first_cosmetic_boundary(self):
        self.assertTrue(self.operation({'action': 'work_on', 'sources': [
            dict(path=path, start_line=1, end_line=1) for path in module.REQUIRED_INSPECTION_PATHS],
            'results': []}, account='Inert CPU account: eleven headers are selected; complete coverage is still pending.')
            ['operations'][-1]['result']['accepted'])
        before = self.session.candidate
        account = copy.deepcopy(self.session.working_account())
        proposal = self.cosmetic_patch()
        rejected = self.act(proposal)
        # Presence of all eleven paths must not inherit E19's one-excerpt rule.
        # The current importer header nevertheless supplies exact edit text.
        missing = list(module.REQUIRED_INSPECTION_PATHS)
        self.assertFalse(rejected['accepted'])
        self.assertEqual(rejected['rejection_code'], 'missing_source_coverage')
        self.assertEqual(rejected['missing_paths'], missing)
        for path in missing:
            self.assertEqual(rejected['missing_extents'][path],
                [[2, len(before.file_map[path].decode().splitlines())]])
        self.assertEqual(self.session.candidate, before)
        self.assertEqual(self.session.working_account(), account)
        self.assertIsNone(self.session.coverage_state()['first_mutation'])
        selected = copy.deepcopy((self.session.ranges, self.session.saved))
        body = next(row for row in self.session.view()['working_set']['sources'] if row['path'] == IMPORTERS)
        rejected = self.act({'action': 'replace_region', 'region': body['region_ref'],
            'new': body['content']+'# Inert literal-region fixture.\n',
            'expected_candidate_id': before.candidate_id})
        self.assertFalse(rejected['accepted'])
        self.assertEqual(rejected['rejection_code'], 'missing_source_coverage')
        self.assertEqual((self.session.ranges, self.session.saved), selected)
        self.assertEqual(self.session.working_account(), account)
        self.assertEqual(self.session.calls_used, 4)
        for path in missing:
            self.select(path)
        self.select(IMPORTERS)
        self.assertEqual(self.status()['missing_paths'], [])
        accepted = self.act(proposal)
        self.assertTrue(accepted['accepted'])
        boundary = copy.deepcopy(self.session.coverage_state()['first_mutation'])
        self.assertEqual(accepted['source_prerequisite_boundary'], boundary)
        self.assertEqual(boundary['previous_candidate_id'], before.candidate_id)
        self.assertEqual(boundary['candidate_id'], self.session.candidate.candidate_id)
        self.assertFalse(self.status()['active'])
        body = self.session.view()['working_set']['sources'][0]
        accepted = self.act({'action': 'replace_region', 'region': body['region_ref'],
            'new': body['content']+'# Inert later literal-region fixture.\n',
            'expected_candidate_id': self.session.candidate.candidate_id})
        self.assertTrue(accepted['accepted'])
        self.assertEqual(self.session.coverage_state()['first_mutation'], boundary)
        self.assertIsNone(self.session.check_state())

    def test_typed_multidigit_restore_and_policy_interval_witness_boundary_corruption(self):
        # Grouped all-file input is admitted only by the synthetic zero measure.
        # It serves decoder testing, not a simultaneous-residence/fit claim.
        self.assertTrue(self.act({'action': 'work_on', 'sources': [
            dict(path=p, start_line=1, end_line=0) for p in module.REQUIRED_INSPECTION_PATHS],
            'results': []})['accepted'])
        for number in range(5):
            self.operation(account='Inert decoder account '+str(number))
        body = next(row for row in self.session.view()['working_set']['sources'] if row['path'] == IMPORTERS)
        self.assertTrue(self.act({'action': 'replace_region', 'region': body['region_ref'],
            'new': body['content']+'# Inert first CPU literal edit.\n',
            'expected_candidate_id': self.session.candidate.candidate_id})['accepted'])
        for number in range(4):
            self.operation(account='Inert later decoder account '+str(number))
        self.assertTrue(self.act(self.cosmetic_patch(HASHING))['accepted'])
        self.assertEqual(self.session.calls_used, 12)
        saved = module.snapshot(self.session)
        self.assertEqual(set(saved['diffs']), {7, 12})
        for value in (saved, load_json_strict(canonical_json_bytes(saved))):
            incoming = copy.deepcopy(value)
            restored = module.restore(incoming, self.session.candidate, self.folder, replay=True)
            self.assertEqual(incoming, value)
            self.assertEqual(restored.view(), self.session.view())
            self.assertEqual(module.snapshot(restored), saved)
        encoded = load_json_strict(canonical_json_bytes(saved))
        changes = []
        value = copy.deepcopy(encoded)
        value['source_prerequisites']['policy']['required_paths'] = [IMPORTERS]
        changes.append(('weakened_policy', value))
        value = copy.deepcopy(encoded)
        value['source_prerequisites']['coverage'].pop(HASHING)
        changes.append(('removed_required_coverage', value))
        for intervals in ([[2, 39]], [[1, 10], [12, 39]], [[1, 40]], [[1, 20], [20, 39]], [[True, 39]]):
            value = copy.deepcopy(encoded)
            value['source_prerequisites']['coverage'][HASHING]['intervals'] = intervals
            changes.append(('interval_'+repr(intervals), value))
        value = copy.deepcopy(encoded)
        value['source_prerequisites']['coverage'][HASHING]['file_sha256'] = 'a'*64
        changes.append(('coverage_fingerprint', value))
        value = copy.deepcopy(encoded)
        value['source_prerequisites']['coverage'][HASHING]['witnesses'].append(
            copy.deepcopy(value['source_prerequisites']['coverage'][HASHING]['witnesses'][0]))
        changes.append(('duplicate_no_new_coverage_witness', value))
        source_index = list(module.REQUIRED_INSPECTION_PATHS).index(HASHING)
        value = copy.deepcopy(encoded)
        value['pairs'][0]['response']['sources'][source_index]['path'] = IMPORTERS
        changes.append(('carrier_requested_different_path', value))
        value = copy.deepcopy(encoded)
        value['pairs'][0]['response']['sources'][source_index]['start_line'] = 2
        changes.append(('carrier_requested_different_prefix', value))
        for field, replacement in {
            'path': IMPORTERS, 'candidate_id': 'a'*64, 'file_sha256': 'b'*64,
            'start_line': 2, 'end_line': 0, 'content_sha256': 'c'*64, 'size_bytes': 0,
            'region_ref': 'SRC-forged', 'request_number': 24,
            'archive_actions_before_request': 72, 'source_result_handle': 'RES-9999',
            'source_index': 9999, 'presentation_sha256': 'd'*64,
        }.items():
            value = copy.deepcopy(encoded)
            value['source_prerequisites']['coverage'][HASHING]['witnesses'][0][field] = replacement
            changes.append(('witness_'+field, value))
        for field, replacement in {
            'action_handle': 'EVT-0006', 'request_number': 24, 'path': HASHING,
            'previous_candidate_id': 'a'*64, 'candidate_id': 'b'*64, 'coverage_sha256': 'c'*64,
        }.items():
            value = copy.deepcopy(encoded)
            value['source_prerequisites']['first_mutation'][field] = replacement
            changes.append(('boundary_'+field, value))
        value = copy.deepcopy(encoded)
        value['source_prerequisites']['first_mutation'] = None
        changes.append(('erased_boundary', value))
        value = copy.deepcopy(encoded)
        value['diffs']['07'] = value['diffs'].pop('7')
        changes.append(('diff_alias', value))
        value = copy.deepcopy(encoded)
        value['diffs'][7] = value['diffs']['7']
        changes.append(('diff_collision', value))
        for label, value in changes:
            with self.subTest(label=label), self.assertRaises(ValueError):
                module.restore(value, self.session.candidate, self.folder, replay=True)


if __name__ == '__main__':
    unittest.main()
