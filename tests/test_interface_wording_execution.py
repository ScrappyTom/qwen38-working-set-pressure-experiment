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
import run_interface_wording as run
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.jsonutil import canonical_json_bytes


HEALTH = {"memory": {"latest_free_mib": 327}, "effective_runtime": {"test_double": True}}


class WordingExecutionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = run.proposed_manifest()
        cls.row = cls.plan["rows"][1]  # W02, actual wording condition on I3.

    def response(self, row, action):
        return canonical_json_bytes({"choices": [{"finish_reason": "stop", "message": {
            "content": canonical_json_bytes(action).decode(), "reasoning_content": "test-only synthetic output"}}],
            "usage": {"prompt_tokens": row["prompt_tokens"], "completion_tokens": 100,
                      "prompt_tokens_details": {"cached_tokens": 0}}, "timings": {"cache_n": 0}})

    @contextmanager
    def fake_runtime(self, args, store, log):
        (args.output / "private-runtime").mkdir()
        (args.output / "memory.csv").write_text("2026/09/10 20:00:00.000, 0, 12288, 11961, 327\n")
        log.append("runtime_ready", {"test_double": True}, [])
        try:
            yield "test-only"
        finally:
            log.append("runtime_closed", {"owned_server_shutdown_verified": True, "dedicated_port_free": True}, [])

    @contextmanager
    def local_attempt(self, folder):
        manifest = folder / "manifest.json"
        manifest.write_bytes(canonical_json_bytes(self.plan))
        args = SimpleNamespace(model=Path("unused-model"), server=Path("unused-server"), owner_approval="test-only approval")
        with patch.object(run, "RUN", folder / "run-001"), patch.object(run, "MANIFEST", manifest), \
             patch.object(run.base, "owned_runtime", self.fake_runtime), \
             patch.object(run.shared, "runtime_check", return_value=HEALTH), \
             patch.object(run.base, "running_process_ids", return_value=[]), \
             patch.object(run.base, "port_free", return_value=True):
            yield args

    def test_frozen_scope_config_and_offline_exclusions_cannot_change(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "manifest.json"
            path.write_bytes(canonical_json_bytes(self.plan))
            with patch.object(run, "MANIFEST", path):
                self.assertEqual(run.load_manifest(), self.plan)
                for field, value in (("actor", {**self.plan["actor"], "context": 32768}),
                                     ("rows", self.plan["rows"][::-1]), ("maximum_completion_calls", 12),
                                     ("excluded_input_ids", []), ("owner_approval_required_before_run", False)):
                    changed = copy.deepcopy(self.plan)
                    changed[field] = value
                    path.write_bytes(canonical_json_bytes(changed))
                    with self.assertRaisesRegex(ValueError, "manifest differs"):
                        run.load_manifest()

    def test_approval_is_required_before_creating_attempt_or_starting_runtime(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(run.base, "owned_runtime") as runtime, \
             patch.object(run.base, "post") as post:
            target = Path(directory) / "run-001"
            with patch.object(run, "RUN", target):
                for approval in (None, "", "   "):
                    args = SimpleNamespace(owner_approval=approval)
                    with self.assertRaisesRegex(ValueError, "separate owner approval"):
                        run.run_once(args, self.plan)
            self.assertFalse(target.exists())
            runtime.assert_not_called()
            post.assert_not_called()

    def test_offline_input_cannot_be_used_as_an_execution_row(self):
        package = run.verified_preparation()
        offline = next(r for r in package["rows"] if r["id"] == "E01")
        with self.assertRaisesRegex(ValueError, "outside W01-W08"):
            run.fresh_state(offline)
        changed = copy.deepcopy(self.plan)
        changed["rows"][-1] = offline
        with patch.object(run.base, "post") as post:
            with self.assertRaisesRegex(ValueError, "wording schedule differs"):
                run.preflight(changed, "unused", None, None, None)
            post.assert_not_called()

    def test_native_mismatch_stops_before_any_completion(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(run.shared, "runtime_check", return_value=HEALTH), \
             patch.object(run.base, "native_render", return_value=(b"{}", b"changed input", 1)), \
             patch.object(run.base, "post") as post:
            folder = Path(directory)
            with self.assertRaisesRegex(ValueError, "native preparation differs"):
                run.execute(self.plan, "unused", folder, ArtifactStore(folder), RecordLog(folder / "records.jsonl", "test"))
            post.assert_not_called()

    def test_wording_action_uses_original_host_and_next_conversation_is_fresh(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            value, request = run.fresh_state(self.row)
            self.assertEqual(request, (run.PACKAGE / self.row["request_path"]).read_bytes())
            before = value.state.candidate.candidate_id
            action = {"action": "patch", "path": "service.py", "old": "return 1", "new": "return 2",
                      "expected_candidate_id": before, "expected_file_sha256": value.state.candidate.file_sha256("service.py")}
            raw = self.response(self.row, action)
            actual_execute = value.execute
            def execute_once(action):
                self.assertEqual((folder / "calls/W02-endpoint-response.json").read_bytes(), raw)
                self.assertTrue((folder / "calls/W02-assistant-reasoning.txt").exists())
                self.assertTrue((folder / "calls/W02-assistant-content.txt").exists())
                return actual_execute(action)
            with patch.object(value, "execute", side_effect=execute_once) as executor:
                outcome = run.shared.receive_and_execute(value, self.row, raw, 1, ArtifactStore(folder),
                                                        RecordLog(folder / "records.jsonl", "test"), lambda: HEALTH)
            executor.assert_called_once()
            self.assertTrue(outcome["host_result"]["result"]["accepted"])
            self.assertNotEqual(value.state.candidate.candidate_id, before)
            fresh, _ = run.fresh_state(self.plan["rows"][2])
            self.assertEqual(fresh.state.candidate.candidate_id, before)
            self.assertEqual(fresh.state.candidate.file_map["service.py"], b"def value():\n    return 1\n")

    def test_complete_mock_attempt_dispatches_only_eight_and_seals_exact_replayable_output(self):
        by_request = {(run.PACKAGE / r["request_path"]).read_bytes(): r for r in self.plan["rows"]}
        native_ids, completion_ids = [], []
        def native(url, request):
            row = by_request[canonical_json_bytes(request)]
            native_ids.append(row["id"])
            stem = "requests/" + row["id"]
            return ((run.PACKAGE / (stem + "-template-response.json")).read_bytes(),
                    (run.PACKAGE / row["rendered_path"]).read_bytes(), row["prompt_tokens"])
        def complete(url, route, raw, timeout):
            self.assertEqual(route, "/v1/chat/completions")
            self.assertEqual(timeout, run.base.HTTP_TIMEOUT_SECONDS)
            row = by_request[raw]
            completion_ids.append(row["id"])
            return self.response(row, {"action": "read", "path": "service.py", "start_line": 1})
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            folder = Path(directory)
            with self.local_attempt(folder) as args, patch.object(run.base, "native_render", side_effect=native), \
                 patch.object(run.base, "post", side_effect=complete) as post:
                seal = run.run_once(args, self.plan)
            expected = [r["id"] for r in self.plan["rows"]]
            self.assertEqual(native_ids, expected)
            self.assertEqual(completion_ids, expected)
            self.assertEqual(post.call_count, 8)
            self.assertEqual((seal["sent_requests"], seal["received_responses"], seal["completed_responses"]), (8, 8, 8))
            records = verify_records(folder / "run-001/records.jsonl", folder / "run-001")
            self.assertEqual(records[0]["payload"]["owner_approval"], "test-only approval")
            self.assertEqual(seal["disposition"], "completed_matched_comparison")
            self.assertFalse(any("/E0" in r["path"] for r in seal["files"]))
            for row in self.plan["rows"]:
                value, _ = run.fresh_state(row)
                stem = folder / "run-001/calls" / row["id"]
                action = json.loads(Path(str(stem) + "-action.json").read_bytes())
                actual = json.loads(Path(str(stem) + "-host-result.json").read_bytes())
                self.assertEqual(value.execute(action), actual["result"])
                self.assertEqual(run.prep.reference.session_bytes(value.state), Path(str(stem) + "-state-after.json").read_bytes())

    def test_transport_failure_preserves_partial_bytes_and_refuses_restart(self):
        with tempfile.TemporaryDirectory() as directory, redirect_stdout(io.StringIO()):
            folder = Path(directory)
            with self.local_attempt(folder) as args, patch.object(run, "preflight"), \
                 patch.object(run.base, "post", side_effect=run.base.ResponseFailure("test transport", b"partial response")) as post:
                with self.assertRaisesRegex(RuntimeError, "test transport"):
                    run.run_once(args, self.plan)
                post.assert_called_once()
                with self.assertRaisesRegex(ValueError, "no resume or retry"):
                    run.run_once(args, self.plan)
            seal = json.loads((folder / "run-001/RESPONSE_SEAL.json").read_bytes())
            self.assertEqual(seal["disposition"], "stopped_without_retry")
            self.assertEqual((seal["sent_requests"], seal["received_responses"], seal["completed_responses"]), (1, 0, 0))
            self.assertEqual((folder / "run-001/calls/W01-transport-body.bin").read_bytes(), b"partial response")


if __name__ == "__main__":
    unittest.main()
