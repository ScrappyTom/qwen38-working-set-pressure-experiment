"""CPU-only custody/restoration checks; no checker, model or native execution."""
import copy
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

AREA = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(AREA))
import continuation_task as module
from working_set_exp.custody import RecordLog, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes
from working_set_exp.observations import ObservationStorageError


class ContinuationTests(unittest.TestCase):
    def setUp(self):
        self.block = patch('working_set_exp.observations.subprocess.Popen',
            side_effect=AssertionError('CPU continuation tests prohibit checker/model execution'))
        self.block.start()
        self.addCleanup(self.block.stop)

    def restored(self, session):
        saved = load_json_strict(canonical_json_bytes(module.snapshot(session)))
        before = copy.deepcopy(saved)
        value = module.restore(saved, session.candidate, module.OLD, replay=True)
        self.assertEqual(saved, before)
        self.assertEqual(value.view(), session.view())
        self.assertEqual(canonical_json_bytes(module.snapshot(value)), canonical_json_bytes(saved))
        return saved

    def test_exact_original_restore_then_sole_limit_change(self):
        original = module.inherited_state()
        session = module.initial_session()
        restored = module.snapshot(session)
        restored['request_limit'] = 20
        self.assertEqual(canonical_json_bytes(restored), canonical_json_bytes(original))
        self.assertEqual((session.requests_used, session.calls_used, session.starting_archive_length), (20, 30, 0))
        self.assertEqual((session.request_limit, session.call_limit), (36, 60))
        self.assertTrue(session.observations.replay)
        self.assertEqual(session.candidate.candidate_id, module.SAVED_ID)
        self.assertEqual(module.candidate_bytes(session.candidate), module.inherited_bytes('final-candidate.json'))
        self.assertEqual(session.working_account()['written_during_request'], 20)
        self.assertIn('only have 1 request left', session.working_account()['text'])
        self.restored(session)
        self.assertIs(module.Task().attach_observations, module.attach_observations)
        self.assertIs(module.Task().decoder_reuse_bindings, module.decoder_reuse_bindings)

    def test_unchanged_task_source_format_scope_and_first_feedback(self):
        original = module.previous.restore(module.inherited_state(),
            module.previous.read_bytes(module.inherited_bytes('final-candidate.json')), module.OLD, replay=True)
        session = module.initial_session(module.OLD, replay=True)
        self.assertEqual(session.task, original.task)
        self.assertEqual(session.checkers, original.checkers)
        self.assertEqual(session.check_contracts, original.check_contracts)
        self.assertEqual(session.edit_checks, original.edit_checks)
        self.assertEqual(session.view()['episode_annotation'], original.view()['episode_annotation'])
        self.assertEqual(module.operating_reference(), module.previous.operating_reference())
        self.assertEqual(module.response_constraints(), module.previous.response_constraints())
        self.assertEqual((module.ACTOR, module.SEED), (module.previous.ACTOR, module.previous.SEED))
        self.assertEqual((AREA / 'SYSTEM.txt').read_bytes(), (module.previous.AREA / 'SYSTEM.txt').read_bytes())
        preceding = module.initial_preceding_feedback()
        self.assertEqual([row['sequence'] for row in preceding], [28, 29])
        self.assertEqual(canonical_json_bytes(preceding), module.inherited_bytes('final-preceding-feedback.json'))
        view = session.view()
        self.assertEqual(view['latest_feedback']['sequence'], 30)
        self.assertEqual(view['latest_feedback']['result']['observation'], 'CHK-0030')
        tests = view['verification']['checks']['tests']
        self.assertTrue(tests['applies_to_current'])
        self.assertFalse(tests['passed'])
        self.assertEqual(tests['assessment']['failed_criteria'], ['detect.error_class'])
        self.assertIsNone(view['verification']['checks']['public'])
        self.assertTrue(any('def test_port_boundary_and_errors' in row['content']
            for row in view['working_set']['sources'] if row['path'] == module.TEST))

    def test_exact_observation_custody_without_execution(self):
        with tempfile.TemporaryDirectory() as raw:
            folder = Path(raw)
            log = RecordLog(folder / 'records.jsonl', 'cpu-inherited-observation')
            session = module.initial_session(module.OLD, replay=True)
            before = canonical_json_bytes(module.snapshot(session))
            module.attach_observations(session, folder / 'scripted', log)
            self.assertEqual(before, canonical_json_bytes(module.snapshot(session)))
            self.assertFalse(session.observations.replay)
            record = session.observations.read('CHK-0030')
            self.assertEqual(record, module.read(module.OLD / 'observations/CHK-0030/outcome.json'))
            for name in ('started.json', 'stdout.bin', 'stderr.bin', 'outcome.json'):
                self.assertEqual((folder / 'scripted/observations/CHK-0030' / name).read_bytes(),
                    module.inherited_bytes('observations/CHK-0030/' + name))
            records = verify_records(log.path, folder)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]['record_type'], 'inherited_observations_copied')
            self.assertTrue(records[0]['payload']['observations_not_reexecuted'])
            self.assertEqual(len(records[0]['artifacts']), 4)
            (folder / 'scripted/observations/CHK-0030/stdout.bin').write_bytes(b'changed')
            with self.assertRaises(ObservationStorageError):
                session.observations.read('CHK-0030')

    def test_stale_guard_rejection_retains_work_and_no_check(self):
        session = module.initial_session(module.OLD, replay=True)
        before = module.candidate_bytes(session.candidate)
        session.mark_delivered(session.view())
        session.begin_request()
        result = module.process_reply(session, dict(discussion='CPU guard regression.', operation=dict(
            action='patch', path=module.TEST, old='def test_port_boundary_and_errors',
            new='def changed_name', expected_candidate_id=module.STARTING_ID,
            expected_file_sha256=session.candidate.file_sha256(module.TEST))), lambda view: 0, [])
        self.assertEqual(len(result['operations']), 1)
        self.assertFalse(result['operations'][0]['result']['accepted'])
        self.assertFalse(result['policy_check']['executed'])
        self.assertEqual(module.candidate_bytes(session.candidate), before)
        self.assertEqual((session.requests_used, session.calls_used), (21, 31))
        self.restored(session)

    def test_later_multidigit_patch_and_literal_replacement_restoration(self):
        session = module.initial_session(module.OLD, replay=True)
        for mode in ('patch', 'replace_region'):
            session.mark_delivered(session.view())
            session.begin_request()
            source = next(row for row in session.view()['working_set']['sources']
                if row['path'] == module.TEST and 'def test_port_boundary_and_errors' in row['content'])
            if mode == 'patch':
                operation = dict(action='patch', path=module.TEST,
                    old='    def test_port_boundary_and_errors(self):',
                    new='    # CPU checkpoint fixture; not a proposed contribution.\n    def test_port_boundary_and_errors(self):',
                    expected_candidate_id=session.candidate.candidate_id,
                    expected_file_sha256=session.candidate.file_sha256(module.TEST))
            else:
                operation = dict(action='replace_region', region=source['region_ref'],
                    new='# CPU literal checkpoint fixture.\n' + source['content'],
                    expected_candidate_id=session.candidate.candidate_id)
            # Direct host operation isolates the intermediate edit checkpoint.
            # process_reply's automatic checker is deliberately not invoked.
            result = session.execute(operation, lambda view: 0)
            self.assertTrue(result['accepted'])
            saved = self.restored(session)
            self.assertTrue(any(int(key) >= 31 for key in saved['diffs']))
        self.assertEqual((session.requests_used, session.calls_used), (22, 32))

    def test_reject_tampered_ancestry_versions_receipts_and_addresses(self):
        session = module.initial_session(module.OLD, replay=True)
        original = load_json_strict(canonical_json_bytes(module.snapshot(session)))
        variants = {}
        for name in ('ancestry', 'account', 'receipt', 'limit', 'counter', 'version', 'alias', 'diff', 'duplicate'):
            state = copy.deepcopy(original)
            if name == 'ancestry': state['starting_archive_length'] = 30
            elif name == 'account': state['pairs'][27]['response']['text'] += ' invented'
            elif name == 'receipt': state['pairs'][29]['result']['passed'] = True
            elif name == 'limit': state['call_limit'] = 61
            elif name == 'counter': state['requests_used'] = 0
            elif name == 'version': state['source_versions'] = state['source_versions'][1:]
            elif name == 'alias': state['diffs']['029'] = state['diffs'].pop('29')
            elif name == 'diff': state['diffs']['29'] += '\nchanged'
            else: state['diffs'][29] = state['diffs']['29']
            variants[name] = state
        for name, state in variants.items():
            with self.subTest(name=name), self.assertRaises(ValueError):
                module.restore(state, session.candidate, module.OLD, replay=True)
        wrong = module.previous.starting_candidate()
        with self.assertRaises(ValueError):
            module.restore(original, wrong, module.OLD, replay=True)


if __name__ == '__main__':
    unittest.main()
