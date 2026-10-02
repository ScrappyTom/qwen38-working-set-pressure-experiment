"""Exact OBS entry, custody and authority boundaries; no executed checks."""
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
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes


class EcologicalObservationTaskTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix='e19-observation-cpu-')
        self.addCleanup(self.temporary.cleanup)
        self.folder = Path(self.temporary.name)
        self.no_subprocess = patch('subprocess.Popen',
            side_effect=AssertionError('OBS entry CPU tests must not execute a checker'))
        self.no_subprocess.start()
        self.addCleanup(self.no_subprocess.stop)
        self.session = module.initial_session(self.folder)
        self.preceding = []

    def operation(self, action=None, account=None):
        self.session.mark_delivered(self.session.view())
        self.session.begin_request()
        reply = {'discussion': 'Task-local CPU custody and authority qualification.'}
        if action is not None:
            reply['operation'] = action
        if account is not None:
            reply['account'] = account
        # Synthetic zero measures state/guards only. Native preparation owns
        # real complete-input fit; this suite makes no capacity claim.
        return module.process_reply(self.session, reply, lambda view: 0, self.preceding)

    def act(self, action):
        return self.operation(action)['operations'][-1]['result']

    def acquire(self, handle):
        result = self.act({'action': 'reopen_observation', 'handle': handle})
        self.assertTrue(result['accepted'])
        return result

    def shown(self):
        return {row['handle'] for row in
            self.session.view()['imported_observations']['entries'] if row['shown_complete']}

    def test_exact_fresh_entry_preserves_verifier_origin_without_body_exposure(self):
        rows, inventory, bodies = module.imports()
        candidate = self.session.candidate
        self.assertEqual(candidate.candidate_id,
            '476f83a90c40b0897e1ab5d6bc00bbb52cf3a4fe60cc11c1dd47ab3da85d0172')
        self.assertEqual(candidate.file_map, module.starting_files())
        self.assertEqual((len(candidate.files), sum(len(raw) for _, raw in candidate.files)), (25, 128545))
        self.assertEqual(candidate.max_file_bytes, 24000)
        self.assertEqual(len(candidate.file_map['src/addressable_information_layer/__init__.py']), 69)
        self.assertEqual((self.session.request_limit, self.session.call_limit), (24, 72))
        self.assertEqual((self.session.requests_used, self.session.calls_used), (0, 0))
        self.assertEqual(self.session.starting_archive_length, 0)
        self.assertEqual(self.session.pairs, [])
        self.assertFalse(self.session.ranges)
        self.assertEqual(self.session.saved, {})
        self.assertEqual(self.session.edit_checks, {})
        self.assertEqual(self.session.checkers, {'public': module.public_checker()})
        self.assertIsNone(self.session.working_account())
        self.assertIsNone(self.session.check_state())
        view = self.session.view()
        self.assertEqual(view['task'], module.task_text())
        self.assertEqual(view['working_set']['sources'], [])
        self.assertEqual(view['verification']['after_accepted_edit'], {})
        self.assertEqual([row['handle'] for row in rows], ['OBS-0001', 'OBS-0002'])
        self.assertTrue(all(row['action'] == 'verifier' for row in rows))
        for row in rows:
            normalized = inventory[row['handle']]
            self.assertEqual(normalized, {**row, 'action': 'capture'})
            raw = bodies[row['handle']]
            self.assertEqual((len(raw), sha256_bytes(raw)), (row['size_bytes'], row['sha256']))
            self.assertEqual(load_json_strict(raw)['candidate_id'], row['candidate_id'])
        self.assertEqual([len(bodies[row['handle']]) for row in rows], [157, 336])
        entries = view['imported_observations']['entries']
        self.assertEqual([entry['observed_candidate_id'] for entry in entries],
                         [row['candidate_id'] for row in rows])
        self.assertNotEqual(entries[0]['observed_candidate_id'], candidate.candidate_id)
        self.assertEqual(entries[1]['observed_candidate_id'], candidate.candidate_id)
        self.assertFalse(any(entry['shown_complete'] or entry['latest_acquisition_result'] for entry in entries))
        rendered = canonical_json_bytes(view).decode()
        self.assertNotIn('collection_stale_when_graph_ids_differ', rendered)
        self.assertNotIn('missing_artifact_ids_direction', rendered)
        self.assertNotIn(module.hidden_checker().decode(), rendered)

    def test_public_reply_forms_and_imported_pass_cannot_authorize_work(self):
        reply = {'discussion': 'Select a recorded observation.',
                 'operation': {'action': 'reopen_observation', 'handle': 'OBS-0002'}}
        self.assertEqual(module.decode_reply(canonical_json_bytes(reply).decode()), reply)
        for scope in ('hidden', 'tests', 'examples'):
            with self.subTest(scope=scope), self.assertRaises(ValueError):
                module.decode_reply(json.dumps({'discussion': 'Unsupported check.',
                    'operation': {'action': 'check', 'check_id': scope,
                                  'expected_candidate_id': module.STARTING_ID}}))
        before = self.session.candidate
        result = self.acquire('OBS-0001')
        self.assertTrue(result['retrieval_only'])
        self.assertIs(result['source_edit_authority'], False)
        self.assertEqual(result['content_utf8'].encode(), self.session.imported_record('OBS-0001')[1])
        self.assertEqual(self.session.candidate, before)
        self.session.mark_delivered(self.session.view())
        self.assertEqual(self.session.delivered_sources, [])
        self.assertIsNone(self.session.check_state())
        old = before.file_map[module.TARGET].decode().splitlines(keepends=True)[0]
        rejected = self.act({'action': 'patch', 'path': module.TARGET, 'old': old,
            'new': old + '# CPU source guard.\n',
            'expected_candidate_id': before.candidate_id,
            'expected_file_sha256': before.file_sha256(module.TARGET)})
        self.assertFalse(rejected['accepted'])
        self.assertFalse(self.act({'action': 'submit', 'expected_candidate_id': before.candidate_id})['accepted'])
        self.assertEqual(self.session.candidate, before)
        self.assertIsNone(self.session.check_state())
        self.assertEqual(self.shown(), {'OBS-0001'})

    def test_retained_acquisition_deduplicates_and_explicit_groups_release_only_display(self):
        first = self.acquire('OBS-0002')
        self.assertEqual(self.shown(), {'OBS-0002'})
        self.assertTrue(self.act({'action': 'read', 'path': module.TARGET, 'start_line': 1, 'end_line': 3})['accepted'])
        self.assertEqual(self.shown(), {'OBS-0002'})
        legacy = self.acquire('OBS-0001')
        self.assertEqual(self.shown(), {'OBS-0001', 'OBS-0002'})
        repeated = self.acquire('OBS-0002')
        self.assertNotEqual(first['exact_result_handle'], repeated['exact_result_handle'])
        self.assertEqual(len(self.session.saved), 2)
        self.assertNotIn(first['exact_result_handle'], self.session.saved)
        for result in (first, repeated):
            self.assertEqual(load_json_strict(self.session.payload(result['exact_result_handle'])), result)
            self.assertEqual(result['observed_candidate_id'], module.STARTING_ID)
        self.assertTrue(self.act({'action': 'work_on',
            'sources': [{'path': module.TARGET, 'start_line': 1, 'end_line': 3}],
            'results': [legacy['exact_result_handle']]})['accepted'])
        self.assertEqual(self.shown(), {'OBS-0001'})
        region = next(source['region_ref'] for source in self.session.view()['working_set']['sources']
                      if source['path'] == module.TARGET)
        self.assertTrue(self.act({'action': 'work_on_exact', 'regions': [region],
            'results': [repeated['exact_result_handle']]})['accepted'])
        self.assertEqual(self.shown(), {'OBS-0002'})
        self.assertTrue(self.act({'action': 'work_on_exact', 'regions': [], 'results': []})['accepted'])
        self.assertEqual(self.shown(), set())
        self.assertEqual(self.session.saved, {})
        for result in (first, legacy, repeated):
            self.assertEqual(load_json_strict(self.session.payload(result['exact_result_handle'])), result)
        self.assertEqual(self.session.candidate.candidate_id, module.STARTING_ID)
        self.assertIsNone(self.session.check_state())

    def test_unknown_and_corrupt_capture_rejections_preserve_work(self):
        self.operation({'action': 'reopen_observation', 'handle': 'OBS-0001'},
            account='CPU pending question; imported observations are historical, not a current check.')
        self.act({'action': 'read', 'path': module.TARGET, 'start_line': 1, 'end_line': 3})
        before = (self.session.candidate, copy.deepcopy(self.session.ranges),
                  copy.deepcopy(self.session.saved), self.session.working_account(), self.session.check_state())
        result = self.act({'action': 'reopen_observation', 'handle': 'OBS-9999'})
        self.assertFalse(result['accepted'])
        self.assertIn('unavailable', result['error'])
        self.assertEqual((self.session.candidate, self.session.ranges, self.session.saved,
                          self.session.working_account(), self.session.check_state()), before)
        exact = self.session._imported_bodies
        self.session._imported_bodies = tuple((handle, raw + b' ') if handle == 'OBS-0002'
            else (handle, raw) for handle, raw in exact)
        try:
            result = self.act({'action': 'reopen_observation', 'handle': 'OBS-0002'})
            self.assertFalse(result['accepted'])
            self.assertIn('binding', result['error'])
            self.assertEqual((self.session.candidate, self.session.ranges, self.session.saved,
                              self.session.working_account(), self.session.check_state()), before)
        finally:
            self.session._imported_bodies = exact
        self.assertEqual(self.shown(), {'OBS-0001'})
        self.assertTrue(self.acquire('OBS-0002')['accepted'])

    def test_typed_restore_binds_original_and_transport_rows_after_multidigit_edit(self):
        self.acquire('OBS-0002')
        for number in range(7):
            self.operation(account='CPU pending finding ' + str(number))
        self.act({'action': 'read', 'path': module.TARGET, 'start_line': 1, 'end_line': 3})
        before = self.session.candidate
        old = before.file_map[module.TARGET].decode().splitlines(keepends=True)[0]
        outcome = self.operation({'action': 'patch', 'path': module.TARGET, 'old': old,
            'new': old + '# CPU typed reconstruction.\n',
            'expected_candidate_id': before.candidate_id,
            'expected_file_sha256': before.file_sha256(module.TARGET)})
        self.assertTrue(outcome['operations'][-1]['result']['accepted'])
        self.assertEqual(len(outcome['operations']), 1)
        self.assertNotIn('policy_check', outcome)
        self.assertIsNone(self.session.check_state())
        self.assertEqual({p: raw for p, raw in self.session.candidate.files if p != module.TARGET},
                         {p: raw for p, raw in before.files if p != module.TARGET})
        saved = module.snapshot(self.session)
        self.assertEqual(set(saved['diffs']), {10})
        self.assertEqual(saved['original_observation_state']['rows'], module.imports()[0])
        self.assertTrue(all(row['action'] == 'capture' for row in saved['imported_capture_state']['inventory']))
        self.assertEqual(saved['imported_capture_state']['retention_policy'],
                         'retain-requested-immutable-captures-v1')
        self.assertEqual(self.shown(), {'OBS-0002'})
        self.assertEqual(next(row['observed_candidate_id'] for row in
            self.session.view()['imported_observations']['entries'] if row['handle'] == 'OBS-0002'), module.STARTING_ID)
        for value in (saved, load_json_strict(canonical_json_bytes(saved))):
            incoming = copy.deepcopy(value)
            restored = module.restore(incoming, self.session.candidate, self.folder, replay=True)
            self.assertEqual(incoming, value)
            self.assertEqual(restored.view(), self.session.view())
            self.assertEqual(module.snapshot(restored), saved)
        encoded = load_json_strict(canonical_json_bytes(saved))
        for label in ('original_action', 'original_candidate', 'transport_action', 'transport_candidate',
                      'body_hash', 'retention_policy', 'diff_alias', 'diff_collision', 'diff_receipt'):
            value = copy.deepcopy(encoded)
            if label == 'original_action': value['original_observation_state']['rows'][0]['action'] = 'capture'
            elif label == 'original_candidate': value['original_observation_state']['rows'][0]['candidate_id'] = 'a'*64
            elif label == 'transport_action': value['imported_capture_state']['inventory'][0]['action'] = 'verifier'
            elif label == 'transport_candidate': value['imported_capture_state']['inventory'][0]['candidate_id'] = 'a'*64
            elif label == 'body_hash': value['imported_capture_state']['body_sha256']['OBS-0002'] = 'a'*64
            elif label == 'retention_policy': value['imported_capture_state']['retention_policy'] = 'other'
            elif label == 'diff_alias': value['diffs']['010'] = value['diffs'].pop('10')
            elif label == 'diff_collision': value['diffs'][10] = value['diffs']['10']
            else: value['diffs']['10'] += '\nforged'
            with self.subTest(label=label), self.assertRaises(ValueError):
                module.restore(value, self.session.candidate, self.folder, replay=True)


if __name__ == '__main__':
    unittest.main()
