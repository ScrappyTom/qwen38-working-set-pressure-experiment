import copy
from contextlib import contextmanager, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import run_interface_comparison as run
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.jsonutil import canonical_json_bytes


HEALTH = {"memory": {"latest_free_mib": 335}, "effective_runtime": {"test_double": True}}


class ComparisonExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = run.proposed_manifest()
        cls.row = next(r for r in cls.plan["rows"] if r["id"] == "C09")

    def fixture(self, folder):
        value, _ = run.fresh_state(self.row)
        return value, ArtifactStore(folder), RecordLog(folder / "records.jsonl", "test-only")

    def response(self, value, action=None, **changes):
        action = action or {"action": "patch", "path": "service.py", "old": "return 1", "new": "return 2",
                            "expected_candidate_id": value.state.candidate.candidate_id,
                            "expected_file_sha256": value.state.candidate.file_sha256("service.py")}
        response = {"choices": [{"finish_reason": "stop", "message": {
            "content": canonical_json_bytes(action).decode(), "reasoning_content": "test-only exact reasoning"}}],
            "usage": {"prompt_tokens": self.row["prompt_tokens"], "completion_tokens": 100,
                      "prompt_tokens_details": {"cached_tokens": 0}}, "timings": {"cache_n": 0}}
        response.update(changes)
        return response

    def test_frozen_execution_configuration_and_schedule_cannot_change(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_bytes(canonical_json_bytes(self.plan))
            with patch.object(run, "MANIFEST", path):
                self.assertEqual(run.load_manifest(), self.plan)
                for field, value in (("actor", {**self.plan["actor"], "context": 32768}),
                                     ("rows", self.plan["rows"][::-1]), ("owner_authorized_completion_calls", 17)):
                    altered = copy.deepcopy(self.plan)
                    altered[field] = value
                    path.write_bytes(canonical_json_bytes(altered))
                    with self.assertRaisesRegex(ValueError, "manifest differs"):
                        run.load_manifest()

    def test_native_mismatch_stops_before_any_completion(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(run, "runtime_check", return_value=HEALTH), \
             patch.object(run.base, "native_render", return_value=(b"{}", b"changed input", 1)), \
             patch.object(run.base, "post") as post:
            folder = Path(directory)
            with self.assertRaisesRegex(ValueError, "native preparation differs"):
                run.execute(self.plan, "unused", folder, ArtifactStore(folder), RecordLog(folder / "records.jsonl", "test"))
            post.assert_not_called()

    def test_one_patch_executes_after_raw_and_fields_are_preserved_on_a_fresh_state(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            value, store, log = self.fixture(folder)
            before = value.state.candidate.candidate_id
            raw = canonical_json_bytes(self.response(value))
            original_execute = value.execute
            def execute(action):
                self.assertEqual((folder / 'calls/C09-endpoint-response.json').read_bytes(), raw)
                self.assertTrue((folder / 'calls/C09-assistant-reasoning.txt').exists())
                self.assertTrue((folder / 'calls/C09-assistant-content.txt').exists())
                return original_execute(action)
            with patch.object(value, "execute", side_effect=execute) as actual:
                outcome = run.receive_and_execute(value, self.row, raw, 1.0, store, log, lambda: HEALTH)
            actual.assert_called_once()
            self.assertTrue(outcome["host_result"]["result"]["accepted"])
            self.assertNotEqual(value.state.candidate.candidate_id, before)
            next_value, _ = run.fresh_state(self.row)
            self.assertEqual(next_value.state.candidate.candidate_id, before)
            self.assertEqual(next_value.state.candidate.file_map['service.py'], b'def value():\n    return 1\n')
            records = verify_records(folder / 'records.jsonl', folder)
            self.assertEqual(records[0]['record_type'], 'response_received')
            self.assertEqual(records[-1]['record_type'], 'invocation_completed')

    def test_failed_check_and_stale_guard_are_recorded_outcomes_without_rescue(self):
        for stale in (False, True):
            with self.subTest(stale=stale), tempfile.TemporaryDirectory() as directory:
                value, store, log = self.fixture(Path(directory))
                action = {'action':'check','check_id':'public','expected_candidate_id':
                          '0'*64 if stale else value.state.candidate.candidate_id}
                with patch.object(value, 'execute', wraps=value.execute) as actual:
                    outcome = run.receive_and_execute(value,self.row,canonical_json_bytes(self.response(value,action)),1,store,log,lambda:HEALTH)
                actual.assert_called_once()
                result=outcome['host_result']['result']
                self.assertEqual(result['accepted'], not stale)
                if not stale:
                    self.assertFalse(result['passed'])

    def test_incomplete_accounting_cache_and_channel_errors_preserve_text_without_execution(self):
        for defect in ('incomplete','accounting','cache','tool_channel','bad_final','stale_telemetry'):
            with self.subTest(defect=defect), tempfile.TemporaryDirectory() as directory:
                folder=Path(directory)
                value,store,log=self.fixture(folder)
                response=self.response(value)
                if defect=='incomplete': response['choices'][0]['finish_reason']='length'
                if defect=='accounting': response['usage']['prompt_tokens']+=1
                if defect=='cache': response['timings']['cache_n']=1
                if defect=='tool_channel': response['choices'][0]['message']['tool_calls']=[{'id':'unexpected'}]
                if defect=='bad_final': response['choices'][0]['message']['content']='{"action":'
                raw=canonical_json_bytes(response)
                def health():
                    if defect=='stale_telemetry': raise ValueError('GPU monitoring is stale')
                    return HEALTH
                with patch.object(value,'execute') as actual:
                    with self.assertRaises((ValueError,RuntimeError)):
                        run.receive_and_execute(value,self.row,raw,1,store,log,health)
                actual.assert_not_called()
                self.assertEqual((folder/'calls/C09-endpoint-response.json').read_bytes(),raw)
                self.assertEqual((folder/'calls/C09-assistant-content.txt').read_text(),response['choices'][0]['message']['content'])
                host=json.loads((folder/'calls/C09-host-result.json').read_bytes())
                self.assertFalse(host['execution_attempted'])
                verify_records(folder/'records.jsonl',folder)

    def test_malformed_envelope_is_preserved_before_parsing(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            value,store,log=self.fixture(folder)
            with patch.object(value,'execute') as actual:
                with self.assertRaises(ValueError):
                    run.receive_and_execute(value,self.row,b'{"broken":',1,store,log,lambda:HEALTH)
            actual.assert_not_called()
            self.assertEqual((folder/'calls/C09-endpoint-response.json').read_bytes(),b'{"broken":')
            self.assertTrue((folder/'calls/C09-state-after.json').exists())
            verify_records(folder/'records.jsonl',folder)

    def test_unexpected_executor_failure_preserves_observed_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            folder=Path(directory)
            value,store,log=self.fixture(folder)
            before=value.state.candidate.candidate_id
            raw=canonical_json_bytes(self.response(value))
            actual=value.execute
            def mutate_then_fail(action):
                actual(action)
                raise RuntimeError('test failure after mutation')
            with patch.object(value,'execute',side_effect=mutate_then_fail):
                with self.assertRaisesRegex(RuntimeError,'after mutation'):
                    run.receive_and_execute(value,self.row,raw,1,store,log,lambda:HEALTH)
            after=json.loads((folder/'calls/C09-candidate-after.json').read_bytes())
            self.assertNotEqual(after['candidate_id'],before)
            host=json.loads((folder/'calls/C09-host-result.json').read_bytes())
            self.assertTrue(host['execution_attempted'])
            self.assertFalse(host['executed'])
            verify_records(folder/'records.jsonl',folder)

    def test_transport_failure_seals_one_attempt_and_refuses_a_restart(self):
        @contextmanager
        def runtime(args,store,log):
            (args.output/'private-runtime').mkdir()
            (args.output/'memory.csv').write_text('2026/09/10 12:00:00.000, 0, 12288, 11953, 335\n')
            log.append('runtime_ready',{'test_double':True},[])
            try: yield 'test-only'
            finally: log.append('runtime_closed',{'owned_server_shutdown_verified':True,'dedicated_port_free':True},[])
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            folder=Path(directory)
            manifest=folder/'manifest.json'
            manifest.write_bytes(canonical_json_bytes(self.plan))
            args=SimpleNamespace(model=Path('unused-model'),server=Path('unused-server'))
            with patch.object(run,'RUN',folder/'run-001'),patch.object(run,'MANIFEST',manifest), \
                 patch.object(run.base,'owned_runtime',runtime),patch.object(run,'runtime_check',return_value=HEALTH), \
                 patch.object(run,'preflight'),patch.object(run.base,'running_process_ids',return_value=[]), \
                 patch.object(run.base,'port_free',return_value=True), \
                 patch.object(run.base,'post',side_effect=run.base.ResponseFailure('test transport',b'partial response')) as post:
                with self.assertRaisesRegex(RuntimeError,'test transport'):
                    run.run_once(args,self.plan)
                post.assert_called_once()
                with self.assertRaisesRegex(ValueError,'no resume or retry'):
                    run.run_once(args,self.plan)
            seal=json.loads((folder/'run-001/RESPONSE_SEAL.json').read_bytes())
            self.assertEqual(seal['disposition'],'stopped_without_retry')
            self.assertEqual((seal['sent_requests'],seal['received_responses'],seal['completed_responses']),(1,0,0))
            self.assertEqual((folder/'run-001/calls/C01-transport-body.bin').read_bytes(),b'partial response')


if __name__=='__main__':
    unittest.main()
