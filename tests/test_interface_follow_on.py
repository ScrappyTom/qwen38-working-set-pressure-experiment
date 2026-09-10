import contextlib
import copy
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
import run_interface_follow_on as follow
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.interface_consultation import development_states, endpoint_request
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


class FollowOnTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.base = endpoint_request(development_states(ROOT)[0], seed=42, mode="diagnostic")

    def test_requests_are_fresh_and_cannot_inherit_history_or_caps(self):
        first = follow.request_for(self.base, "system", "first")
        second = follow.request_for(self.base, "system", "second")
        first["messages"].append({"role": "assistant", "content": "prior answer"})
        self.assertEqual(len(second["messages"]), 2)
        self.assertEqual(second["messages"][1]["content"], "second")
        with self.assertRaisesRegex(ValueError, "fresh"):
            follow.validate_request(first)
        for key in ("max_tokens", "n_predict", "thinking_budget_tokens", "reasoning_budget_tokens"):
            bad = copy.deepcopy(second)
            bad[key] = 512
            with self.assertRaisesRegex(ValueError, "caps generation"):
                follow.validate_request(bad)
        bad = copy.deepcopy(second)
        bad["tools"] = [{"name": "patch"}]
        with self.assertRaisesRegex(ValueError, "action channel"):
            follow.validate_request(bad)

    def test_configuration_mismatch_is_rejected_before_runtime_use(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            actor = copy.deepcopy(follow.ACTOR)
            actor.update(context=32768, kv_k="q8_0")
            follow.write_json(root / "PACKAGE_MANIFEST.json", {"actor": actor})
            with self.assertRaisesRegex(ValueError, "configuration differs"):
                follow.validate_package(root)

    def test_preparation_only_renders_and_tokenizes_all_seven_independent_requests(self):
        routes = []

        def fake_post(base, route, raw, timeout):
            routes.append(route)
            value = load_json_strict(raw)
            if route == "/apply-template":
                return canonical_json_bytes({"prompt": "\n".join(m["content"] for m in value["messages"])})
            if route == "/tokenize":
                return canonical_json_bytes({"tokens": list(range(len(value["content"].split())))})
            self.fail("preparation attempted inference: " + route)

        sources = {
            "new_long_context_fixture.py": b"def build_prompt(n):\n    return ' cedar' * n\n",
            "coding-reasoning-v1.txt": b"Return the requested coding answers.",
            "expected.json": canonical_json_bytes({"coding_reasoning_v1": {"example": "evaluator-only-answer"}}),
        }

        def fixture_git(args):
            return sources[args[-1].rsplit("/", 1)[-1]]

        with tempfile.TemporaryDirectory() as directory, patch.object(follow, "post", side_effect=fake_post), \
                patch.object(follow.subprocess, "check_output", side_effect=fixture_git), contextlib.redirect_stdout(io.StringIO()):
            folder = Path(directory) / "package"
            manifest = follow.prepare_package(folder, Path("unused-profile"), "unused-base")
            self.assertEqual([r["id"] for r in manifest["rows"]], ["Q1", "Q2", "Q3", "D1", "D2", "D3", "D4"])
            self.assertEqual(manifest["completion_calls_made_during_preparation"], 0)
            self.assertEqual(set(routes), {"/apply-template", "/tokenize"})
            grammar = (folder / "ACTION_SCHEMA.json").read_text()
            for row in manifest["rows"]:
                request = load_json_strict((folder / row["request_path"]).read_bytes())
                self.assertEqual([m["role"] for m in request["messages"]], ["system", "user"])
                self.assertNotIn("evaluator-only-answer", canonical_json_bytes(request).decode())
                if row["id"] not in {"Q1", "Q2"}:
                    rendered = (folder / row["rendered_path"]).read_text()
                    self.assertIn(grammar, rendered)
                    self.assertIn("full saved original result JSON", rendered)
            construction = load_json_strict((folder / "RETENTION_CONSTRUCTION.json").read_bytes())
            self.assertLessEqual(construction["selected_prompt_tokens"], 36096)
            self.assertGreater(construction["next_prompt_tokens"], 36096)
            self.assertEqual(follow.validate_package(folder), manifest)

    def test_raw_malformed_response_enters_custody_before_parse_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            log = RecordLog(folder / "records.jsonl", "test")
            with self.assertRaises(ValueError):
                follow.receive_nonexecuting(ArtifactStore(folder), log, {"id": "Q1"}, b'{"broken":', 1.0)
            records = verify_records(folder / "records.jsonl", folder)
            self.assertEqual(records[0]["record_type"], "response_received")
            self.assertEqual((folder / "calls/Q1-endpoint-response.json").read_bytes(), b'{"broken":')

    def test_an_action_shaped_design_answer_never_executes(self):
        response = {"choices": [{"finish_reason": "stop", "message": {"content": '{"action":"submit"}', "reasoning_content": "saved thinking"}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20, "prompt_tokens_details": {"cached_tokens": 0}}}
        with tempfile.TemporaryDirectory() as directory, patch("working_set_exp.tools.ToolExecutor.execute") as execute:
            folder = Path(directory)
            result = follow.receive_nonexecuting(ArtifactStore(folder), RecordLog(folder / "records.jsonl", "test"),
                                                {"id": "D1", "stage": "design", "prompt_tokens": 10}, canonical_json_bytes(response), 1)
            execute.assert_not_called()
            self.assertFalse(result["host_result"]["executed"])
            self.assertEqual((folder / "calls/D1-assistant-reasoning.txt").read_text(), "saved thinking")

    def test_incomplete_response_is_preserved_and_stops(self):
        response = {"choices": [{"finish_reason": "length", "message": {"content": "partial", "reasoning_content": "unfinished"}}],
                    "usage": {"prompt_tokens": 10, "completion_tokens": 20, "prompt_tokens_details": {"cached_tokens": 0}}}
        with tempfile.TemporaryDirectory() as directory:
            folder = Path(directory)
            with self.assertRaisesRegex(ValueError, "incomplete"):
                follow.receive_nonexecuting(ArtifactStore(folder), RecordLog(folder / "records.jsonl", "test"),
                    {"id": "Q1", "stage": "qualification", "prompt_tokens": 10}, canonical_json_bytes(response), 1)
            self.assertEqual((folder / "calls/Q1-assistant-content.txt").read_text(), "partial")

    def prepared_minimal_stage(self, folder):
        rows = []
        package = folder / "package"
        package.mkdir()
        for identifier in follow.CALIBRATION_IDS:
            request = follow.request_for(self.base, "system", identifier)
            raw = canonical_json_bytes(request)
            (package / (identifier + ".json")).write_bytes(raw)
            rows.append({"id": identifier, "stage": "qualification", "request_path": identifier + ".json",
                         "prompt_tokens": 10, "rendered_sha256": sha256_bytes(b"rendered")})
        return SimpleNamespace(package=package, output=folder, stage="qualification"), {"rows": rows}

    def test_memory_failure_withholds_requests_without_a_preset_switch(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(follow, "native_render", return_value=(b"{}", b"rendered", 10)), \
                patch.object(follow, "memory_stats", return_value={"samples": 1, "min_free_mib": 349}), patch.object(follow, "post") as post:
            folder = Path(directory)
            args, manifest = self.prepared_minimal_stage(folder)
            log = RecordLog(folder / "records.jsonl", "test")
            with self.assertRaisesRegex(ValueError, "GPU reserve"):
                follow.execute_stage(args, manifest, "unused", ArtifactStore(folder), log)
            post.assert_not_called()
            self.assertFalse(any(r["record_type"] == "invocation_started" for r in verify_records(folder / "records.jsonl", folder)))

    def test_transport_failure_has_one_attempt_and_preserves_received_bytes(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(follow, "native_render", return_value=(b"{}", b"rendered", 10)), \
                patch.object(follow, "memory_stats", return_value={"samples": 1, "min_free_mib": 500}), \
                patch.object(follow, "runtime_evidence", return_value={"truncation_observed": False, "cuda_failure_observed": False}), \
                patch.object(follow, "post", side_effect=follow.ResponseFailure("timed out", b"received prefix")) as post, contextlib.redirect_stdout(io.StringIO()):
            folder = Path(directory)
            args, manifest = self.prepared_minimal_stage(folder)
            with self.assertRaises(follow.ResponseFailure):
                follow.execute_stage(args, manifest, "unused", ArtifactStore(folder), RecordLog(folder / "records.jsonl", "test"))
            self.assertEqual(post.call_count, 1)
            self.assertEqual((folder / "calls/Q1-transport-body.bin").read_bytes(), b"received prefix")

    def test_memory_guard_ignores_an_incomplete_sample_line(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.csv"
            path.write_bytes(b"2026/09/10 01:00:00, 0, 12288, 11800, 488\r\n2026/09/10 01:00:01, 0, 12288, 11800, 4")
            self.assertEqual(follow.memory_stats(path), {"samples": 1, "min_free_mib": 488, "max_free_mib": 488})

    def test_design_requires_a_complete_bound_review_and_qualified_memory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            package, run = root / "package", root / "run"
            package.mkdir()
            run.mkdir()
            (package / "PACKAGE_MANIFEST.json").write_bytes(b"{}")
            (run / "RESPONSE_SEAL.json").write_bytes(b"{}")
            seal = {"stage": "qualification", "disposition": "completed_nonexecuting_stage",
                    "package_sha256": sha256_file(package / "PACKAGE_MANIFEST.json"),
                    "memory": {"samples": 100, "min_free_mib": 400},
                    "effective_runtime": {"full_offload": True, "context_matches": True, "q4_k_and_v": True,
                        "mtp_disabled": True, "truncation_observed": False, "cuda_failure_observed": False}}
            records = [{"record_type": "invocation_completed", "payload": {"id": identifier, "finish_reason": "stop", "within_proposed_generation_reserve": True}}
                       for identifier in follow.CALIBRATION_IDS]
            records.append({"record_type": "stage_closed", "payload": {"owned_server_shutdown_verified": True, "dedicated_port_free": True}})
            audits = []
            for number in range(5):
                path = root / f"audit-{number}.md"
                path.write_text("review product")
                audits.append({"path": path.name, "sha256": sha256_file(path)})
            decision = {"qualification_seal_sha256": sha256_file(run / "RESPONSE_SEAL.json"),
                        "package_sha256": seal["package_sha256"], "continue_to_design": True,
                        "direct_review_completed_by_reviewer": False, "q1_correct_fields": 4,
                        "q2_correct_fields": 8, "q3_operational_criteria_passed": 4, "audit_files": audits}
            review = root / "decision.json"
            with patch.object(follow, "verify_seal", return_value=seal), patch.object(follow, "verify_records", return_value=records):
                review.write_bytes(canonical_json_bytes(decision))
                with self.assertRaisesRegex(ValueError, "direct review"):
                    follow.require_qualification(package, run, review)
                decision["direct_review_completed_by_reviewer"] = True
                review.write_bytes(canonical_json_bytes(decision))
                follow.require_qualification(package, run, review)
                seal["memory"]["min_free_mib"] = 349
                with self.assertRaisesRegex(ValueError, "GPU reserve"):
                    follow.require_qualification(package, run, review)


if __name__ == "__main__":
    unittest.main()
