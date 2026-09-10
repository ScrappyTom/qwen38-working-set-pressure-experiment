from datetime import datetime
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import continue_interface_follow_on as cont


class ContinuationTests(unittest.TestCase):
    def test_339_is_monitored_and_stale_or_missing_monitoring_stops(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "memory.csv"
            path.write_text("2026/09/10 10:00:00.000, 0, 12288, 11777, 339\n")
            sampled = datetime(2026, 9, 10, 10).timestamp()
            report = cont.monitoring(path, now=sampled + .2)
            self.assertEqual(report["latest_free_mib"], 339)
            self.assertTrue(report["below_original_reference"])
            with self.assertRaisesRegex(ValueError, "stale"):
                cont.monitoring(path, now=sampled + 10)
            path.write_text("")
            with self.assertRaisesRegex(ValueError, "unavailable"):
                cont.monitoring(path, now=sampled)

    def test_advisory_memory_does_not_waive_runtime_failures(self):
        evidence = {"full_offload": True, "context_matches": True, "q4_k_and_v": True,
                    "mtp_disabled": True, "truncation_observed": False, "cuda_failure_observed": False}
        with patch.object(cont.base, "runtime_evidence", return_value=evidence):
            cont.healthy_runtime(Path("unused"))
            evidence["cuda_failure_observed"] = True
            with self.assertRaisesRegex(ValueError, "runtime failure"):
                cont.healthy_runtime(Path("unused"))
            evidence["cuda_failure_observed"] = False
            evidence["context_matches"] = False
            with self.assertRaisesRegex(ValueError, "identity differs"):
                cont.healthy_runtime(Path("unused"))

    def test_frozen_remaining_plan_excludes_q1_and_refuses_modified_requests(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(cont, "CONT", Path(directory)):
            (cont.CONT / "SPEC.md").write_text("Test-only amendment identity")
            plan = cont.prepare_plan()
            self.assertEqual([r["id"] for r in plan["rows"]], ["Q2", "Q3", "D1", "D2", "D3", "D4"])
            self.assertEqual(cont.load_plan(), plan)
            plan["rows"][0]["id"] = "Q1"
            (cont.CONT / "CONTINUATION_MANIFEST.json").write_text(json.dumps(plan))
            with self.assertRaisesRegex(ValueError, "remaining requests changed"):
                cont.load_plan()
            with patch.object(cont.base, "native_render") as render:
                with self.assertRaisesRegex(ValueError, "Q1 cannot be repeated"):
                    cont.execute("qualification", plan, "unused", cont.CONT, None, None)
                render.assert_not_called()

    def test_runtime_log_distinguishes_original_policy_from_amendment(self):
        with tempfile.TemporaryDirectory() as directory:
            log = cont.ContinuationLog(Path(directory) / "records.jsonl", "test")
            payload = {"actor": cont.base.ACTOR}
            record = log.append("runtime_prepared", payload, [])
            self.assertEqual(payload, {"actor": cont.base.ACTOR})
            self.assertEqual(record["payload"]["original_package_actor"]["minimum_free_gpu_mib"], 350)
            self.assertNotIn("minimum_free_gpu_mib", record["payload"]["actor"])
            self.assertTrue(record["payload"]["memory_policy"]["reference_is_advisory"])

    def test_design_requires_bound_content_review_even_with_owner_memory_override(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(cont, "CONT", Path(directory)), \
                patch.object(cont, "prior_q1"), patch.object(cont, "healthy_runtime"):
            root = Path(directory)
            (root / "CONTINUATION_MANIFEST.json").write_bytes(b"{}")
            run = root / "qualification-001"
            run.mkdir()
            (run / "RESPONSE_SEAL.json").write_bytes(b"{}")
            manifest_sha = cont.sha256_file(root / "CONTINUATION_MANIFEST.json")
            seal = {"disposition": "completed_nonexecuting_stage", "continuation_manifest_sha256": manifest_sha,
                    "memory": {"samples": 100, "min_free_mib": 339}}
            records = [{"record_type": "invocation_completed", "payload": {"id": name, "finish_reason": "stop", "within_proposed_generation_reserve": True}}
                       for name in ("Q2", "Q3")]
            records.append({"record_type": "stage_closed", "payload": {"owned_server_shutdown_verified": True, "dedicated_port_free": True}})
            decision = {"qualification_seal_sha256": cont.sha256_file(run / "RESPONSE_SEAL.json"),
                        "prior_q1_seal_sha256": cont.sha256_file(cont.PRIOR / "RESPONSE_SEAL.json"),
                        "continuation_manifest_sha256": manifest_sha, "continue_to_design": True, "memory_policy": cont.POLICY,
                        "q1_correct_fields": 4, "q2_correct_fields": 8, "q3_operational_criteria_passed": 4}
            with patch.object(cont, "verified_seal", return_value=seal), patch.object(cont, "verify_records", return_value=records), \
                    patch.object(cont, "reviewed_files", return_value=decision):
                cont.require_design_review(root / "review.json")
                decision["q3_operational_criteria_passed"] = 3
                with self.assertRaisesRegex(ValueError, "content criteria failed"):
                    cont.require_design_review(root / "review.json")
                decision["q3_operational_criteria_passed"] = 4
                decision["prior_q1_seal_sha256"] = "wrong"
                with self.assertRaisesRegex(ValueError, "not bound to Q1"):
                    cont.require_design_review(root / "review.json")


if __name__ == "__main__":
    unittest.main()
