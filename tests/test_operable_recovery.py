"""Behavioral boundaries; synthetic sizing is not native/model evidence."""
import base64
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from working_set_exp.accounted_contribution import process_reply
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes
from working_set_exp.observations import ObservationStore, ObservationStorageError, check_report
from working_set_exp.operable_session import OperableSession
from working_set_exp.operable_view import present_receipts, operating_reference
from working_set_exp.working_session import INPUT_LIMIT


class ObservationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ObservationStore(Path(self.temp.name) / 'observations')
        self.candidate = Candidate.create({'app.py': b'value = 2\n'})

    def execute(self, code, **kw):
        store = ObservationStore(self.store.root, **kw) if kw else self.store
        return store, store.execute(self.candidate, code, 'public', 'CHK-0001')

    def test_preserves_long_tail_before_formatter_and_replays_without_execution(self):
        code = b"import sys\nsys.stdout.write('A'*9000+'REAL DIAGNOSTIC');sys.exit(1)\n"
        seen = []
        self.store.on_preserved = lambda record, files: seen.append(self.store.read(record['observation']))
        store, record = self.execute(code)
        self.assertEqual(seen, [record])
        self.assertTrue(record['executed'])
        self.assertFalse(record['passed'])
        self.assertEqual((store.directory('CHK-0001') / 'stdout.bin').read_bytes(), b'A'*9000+b'REAL DIAGNOSTIC')
        self.assertIn('REAL DIAGNOSTIC', check_report(store, record)['report']['stdout_tail']['text'])
        replay = ObservationStore(store.root, replay=True)
        with patch('working_set_exp.observations.subprocess.Popen', side_effect=AssertionError('no rerun')):
            self.assertEqual(replay.execute(self.candidate, code, 'public', 'CHK-0001'), record)
        with self.assertRaisesRegex(ObservationStorageError, 'another operation'):
            replay.execute(self.candidate, code+b'# changed', 'public', 'CHK-0001')

    def test_exact_paging_utf8_binary_and_boundary_validation(self):
        body = ('é'*5000).encode()+b'FINAL'
        self.execute(('import sys\nsys.stdout.buffer.write('+repr(body)+')\n').encode())
        rebuilt, offset = b'', 0
        while True:
            page = self.store.inspect('CHK-0001', 'stdout', offset)
            rebuilt += page['content'].encode()
            if page['next_offset'] is None:
                break
            offset = page['next_offset']
        self.assertEqual(rebuilt, body)
        with self.assertRaisesRegex(ValueError, 'UTF-8'):
            self.store.inspect('CHK-0001', 'stdout', 1)
        self.store.execute(self.candidate, b"import sys;sys.stdout.buffer.write(b'\\xff\\x00')", 'public', 'CHK-0002')
        binary = self.store.inspect('CHK-0002', 'stdout', 0)
        self.assertEqual(binary['encoding'], 'base64')
        self.assertEqual(base64.b64decode(binary['content']), b'\xff\x00')

    def test_capture_limit_and_timeout_are_executed_incomplete_observations(self):
        store, record = self.execute(b"import sys;sys.stdout.write('Q'*20000)", stream_limit=1000)
        self.assertEqual(record['termination'], 'capture_limit')
        self.assertFalse(record['capture_complete'])
        self.assertFalse(record['passed'])
        self.assertEqual(record['streams']['stdout']['captured_bytes'], 1000)
        self.assertFalse(store.inspect('CHK-0001', 'stdout', 0)['capture_complete'])
        timeout = ObservationStore(store.root, timeout=.2)
        result = timeout.execute(self.candidate, b'import time;time.sleep(10)', 'public', 'CHK-0002')
        self.assertEqual(result['termination'], 'timeout')
        self.assertTrue(result['executed'])
        self.assertFalse(result['passed'])

    def test_storage_refusal_happens_before_execution_and_has_no_recovery_promise(self):
        with patch('working_set_exp.observations.subprocess.Popen', side_effect=AssertionError('no start')):
            store, result = self.execute(b'print(1)', storage_limit=1000)
        self.assertFalse(result['executed'])
        self.assertFalse(result['accepted'])
        self.assertIsNone(result['observation'])
        self.assertFalse(store.root.exists())

    def test_tampered_capture_is_not_ordinary_rejection(self):
        self.execute(b'print(123)')
        (self.store.directory('CHK-0001')/'stdout.bin').write_bytes(b'changed')
        with self.assertRaises(ObservationStorageError):
            self.store.inspect('CHK-0001', 'stdout', 0)

    def test_primary_failure_wins_over_optional_fault_detail(self):
        full = dict(observation_schema='contribution-check-v2',
            saved_suite=dict(successful=True, tests=5, failures=0, errors=0),
            edited_suite=dict(successful=False, tests=7, failures=2, errors=0,
                details=[dict(test='actual_test', trace='noise\n'*2000+'EXPECTED PRIMARY DIAGNOSTIC'),
                         dict(test='second_test', trace='SECOND FAILURE')]),
            fault_sensitivity={str(n):dict(successful=False, details=['optional'*1000]) for n in range(10)})
        code = ('import sys\nprint('+repr(json.dumps(full))+')\nsys.exit(1)').encode()
        store, record = self.execute(code)
        report = check_report(store, record)['report']
        self.assertEqual(report['primary_real_failure']['test'], 'actual_test')
        self.assertIn('EXPECTED PRIMARY DIAGNOSTIC', report['primary_real_failure']['diagnostic']['text'])
        self.assertEqual(report['primary_real_failure']['additional_failures'], 1)
        self.assertEqual(report['expected_fault_checks']['detected'], 10)
        self.assertEqual(json.loads((store.directory('CHK-0001')/'stdout.bin').read_bytes()), full)


class RecoveryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def session(self, checker=b'print("check ran")', files=None):
        return OperableSession(Candidate.create(files or {'app.py':b'value = 2\n', 'guide.txt':b'Expected: 1\n'}),
            {'public':checker}, 'Correct the guide using the implementation.',
            edit_checks={'guide.txt':'public'}, observations=ObservationStore(Path(self.temp.name)/'obs'),
            call_limit=48, request_limit=16)

    def read(self, session, path='app.py', **kw):
        return session.execute(dict(action='read', path=path, start_line=1, end_line=0), kw.get('measure', lambda v:500))

    def edit(self, session, path='app.py', old='value = 2', new='value = 3'):
        return dict(action='patch', path=path, old=old, new=new,
            expected_candidate_id=session.candidate.candidate_id, expected_file_sha256=session.candidate.file_sha256(path))

    def test_long_escaping_check_is_execution_and_exactly_inspectable(self):
        session = self.session(b"import sys;sys.stdout.write(chr(34)*7500);sys.exit(1)")
        result = session.execute(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id), lambda v:500)
        self.assertTrue(result['accepted'])
        self.assertTrue(result['executed'])
        self.assertFalse(result['passed'])
        self.assertEqual(session.check_state()['candidate_id'], session.candidate.candidate_id)
        result = session.execute(dict(action='inspect_observation', observation=result['observation'], stream='stdout', offset=0), lambda v:500)
        self.assertEqual(result['content'], '"'*4096)

    def test_formatter_failure_cannot_undo_the_recorded_check(self):
        session = self.session()
        with patch('working_set_exp.operable_session.check_report', side_effect=ValueError('broken format')):
            result = session.execute(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id), lambda v:500)
        self.assertTrue(result['executed'])
        self.assertTrue(result['passed'])
        self.assertEqual(result['report_status'], 'unavailable')
        self.assertTrue(session.observations.read(result['observation'])['passed'])

    def test_unexpected_presentation_exception_preserves_executed_outcome(self):
        session = self.session()
        def broken(view):
            raise ValueError('rendering unavailable')
        with self.assertRaisesRegex(RuntimeError, 'Executed observation preserved'):
            session.execute(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id), broken)
        self.assertEqual(len(session.pairs), 1)
        self.assertTrue(session.pairs[0]['result']['executed'])
        self.assertTrue(session.check_state()['passed'])

    def test_recovery_search_keeps_multiple_selectable_results_when_room_exists(self):
        files={'app.py':b'value = 2\n'*30, 'guide.txt':b'Expected: 1\n'}
        session = self.session(files=files)
        session.enter_recovery('capacity')
        result=session.execute(dict(action='search',path='app.py',query='value',offset=0,limit=16),lambda v:1000)
        self.assertEqual(len(result['regions']),16)
        self.assertEqual(session.view()['latest_feedback']['result'],result)

    def test_recovery_hides_designated_bodies_and_removes_edit_authority(self):
        session = self.session()
        self.read(session)
        session.mark_delivered(session.view())
        ranges = copy.deepcopy(session.ranges)
        session.enter_recovery('known capacity obstacle')
        view = session.view()
        self.assertEqual(view['working_set']['sources'], [])
        self.assertNotIn('value = 2', canonical_json_bytes(view).decode())
        session.mark_delivered(view)
        result = session.execute(self.edit(session), lambda v:500)
        self.assertFalse(result['accepted'])
        self.assertEqual(session.ranges, ranges)
        self.assertEqual(session.candidate.file_map['app.py'], b'value = 2\n')

    def test_temporary_inspection_is_delivered_without_altering_designation(self):
        session = self.session()
        self.read(session, 'guide.txt')
        ranges = copy.deepcopy(session.ranges)
        session.enter_recovery('capacity')
        result = self.read(session)
        self.assertEqual(session.ranges, ranges)
        self.assertEqual(session.view()['latest_feedback']['result']['source'], result['source'])
        session.mark_delivered(session.view())
        self.assertTrue(session.execute(self.edit(session), lambda v:500)['accepted'])
        self.assertTrue(session.recovery)

    def test_large_inspection_has_a_real_page_not_just_status(self):
        session = self.session(files={'app.py':b'value = 2\n'*2000, 'guide.txt':b'Expected: 1\n'})
        session.enter_recovery('capacity')
        result = self.read(session)
        self.assertLess(result['source']['returned_end_line'], 2000)
        self.assertGreater(result['source']['returned_end_line'], 0)
        self.assertEqual(session.view()['latest_feedback']['result']['source'], result['source'])
        self.assertEqual(session.ranges, [])

    def test_search_reference_exact_assembly_and_stale_reference_rejection(self):
        session = self.session()
        found = session.execute(dict(action='search', path='app.py', query='value', offset=0, limit=4), lambda v:500)
        self.assertTrue(found['accepted'], found)
        reference = found['regions'][0]['region_ref']
        session.enter_recovery('capacity')
        group = dict(action='work_on_exact', regions=[reference], results=[])
        assembled = session.execute(group, lambda v:500)
        self.assertTrue(assembled['complete_requested_group'])
        self.assertFalse(session.recovery)
        session.mark_delivered(session.view())
        self.assertTrue(session.execute(self.edit(session), lambda v:500)['accepted'])
        result = session.execute(group, lambda v:500)
        self.assertFalse(result['accepted'])
        self.assertIn('stale', result['error'])

    def test_exact_group_is_never_qualified_by_hiding_or_shortening_it(self):
        session = self.session()
        reference = self.read(session)['source']['region_ref']
        prior = copy.deepcopy(session.ranges)
        session.enter_recovery('capacity')
        def measure(v):
            return 500 if v['presentation']['mode']=='recovery' else INPUT_LIMIT+1
        result = session.execute(dict(action='work_on_exact', regions=[reference], results=[]), measure)
        self.assertFalse(result['accepted'])
        self.assertEqual(session.ranges, prior)
        self.assertTrue(session.recovery)
        self.assertFalse(session.delivery_blocked)

    def test_joint_account_exact_replacement_measures_final_arrangement(self):
        session = self.session()
        self.read(session)
        self.read(session, 'guide.txt')
        reference = session.selection_inventory()['entries'][0]['region_ref']
        session.enter_recovery('capacity')
        session.mark_delivered(session.view())
        session.begin_request()
        def measure(v):
            return INPUT_LIMIT+1 if len(v['working_set']['sources'])>1 else 500
        result = process_reply(session, dict(discussion='Change support.', account='Still provisional.',
            operation=dict(action='work_on_exact', regions=[reference], results=[])), measure, [])
        self.assertEqual(len(result['operations']), 2)
        self.assertTrue(all(o['result']['accepted'] for o in result['operations']))
        self.assertEqual(session.working_account()['text'], 'Still provisional.')
        self.assertEqual(session.working_account()['input_candidate_id'], session.candidate.candidate_id)

    def test_recovery_receipts_do_not_reintroduce_source_or_account_bodies(self):
        session = self.session()
        self.read(session)
        previous = copy.deepcopy(session.last)
        session.execute(dict(action='record_account', text='ACCOUNT '*10000), lambda v:500)
        session.enter_recovery('capacity')
        receipts = present_receipts(session.view(), [previous])
        wire = canonical_json_bytes(dict(view=session.view(), receipts=receipts)).decode()
        self.assertNotIn('value = 2', wire)
        self.assertLess(len(wire), 8000)
        self.assertFalse(session.view()['working_account']['text_complete'])
        self.assertEqual(json.loads(session.payload(session.working_account()['action_handle']))['text'], 'ACCOUNT '*10000)

    def test_feedback_priority_enters_recovery_and_keeps_execution_and_selection(self):
        session = self.session(b"raise AssertionError('ACTUAL FAILURE')")
        self.read(session)
        prior = copy.deepcopy(session.ranges)
        def measure(v):
            return 500 if v['presentation']['mode']=='recovery' else INPUT_LIMIT+1
        result = session.execute(dict(action='check', check_id='public', expected_candidate_id=session.candidate.candidate_id), measure)
        self.assertTrue(result['executed'])
        self.assertEqual(session.ranges, prior)
        self.assertFalse(session.delivery_blocked)
        self.assertIn('ACTUAL FAILURE', canonical_json_bytes(session.view()).decode())
        self.assertEqual(session.view()['presentation']['mode'], 'recovery')

    def test_exact_group_archive_supplies_source_only_when_fully_delivered(self):
        session = self.session()
        reference = self.read(session)['source']['region_ref']
        session.execute(dict(action='work_on_exact', regions=[reference], results=[]), lambda v:500)
        session.execute(dict(action='work_on', sources=[], results=['RES-0002']), lambda v:500)
        session.mark_delivered(session.view())
        self.assertTrue(session.execute(self.edit(session), lambda v:500)['accepted'])

    def test_contract_explains_independent_routes_and_contains_all_new_forms(self):
        reference = operating_reference({'public':'The public check.'})
        for name in ('inspect_observation', 'work_on_exact', 'selection_page', 'A partial page of serialized saved-result bytes'):
            self.assertIn(name, reference)


if __name__ == '__main__':
    unittest.main()
