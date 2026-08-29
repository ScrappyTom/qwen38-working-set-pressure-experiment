from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from scripts.monitor_live_run import snapshot as live_monitor_snapshot
from scripts.run_observation_final_development import _constructed_middle
from working_set_exp.candidate import Candidate
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict
from working_set_exp.hierarchical_p0 import build_p0_root, p0_page
from working_set_exp.large_world import CASE_IDS as E12_CASE_IDS, hidden_grade as large_hidden_grade, load_fixture as load_large_fixture, verify_bank as verify_large_bank
from working_set_exp.phase_receipts import (
    _receipt as phase_receipt, build_request as build_receipt_request,
    load_fixture as load_receipt_fixture, verify_bank as verify_receipt_bank,
)
from working_set_exp.observation_recurrence import CASE_IDS as E9_CASE_IDS
from working_set_exp.recurrent_acquisition_completion import expected_authorization, verify_prior_partial
from working_set_exp.recurrent_host_v2 import run_t25_final_operational
from working_set_exp.recurrent_pressure import (
    CandidateBoundProbeExecutor,
    MiddleOutcome,
    build_recurrent_request,
    hidden_grade,
    load_recurrent_fixture,
    verify_bank,
)
from working_set_exp.runtime import CallOutcome, HTTP_TIMEOUT_SECONDS, PreparedCall
from working_set_exp.tools import SessionState, ToolExecutor, action_schema


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "007_recurrent_bounded_pressure"
PRIMARY = ROOT / "experiments" / "008_recurrent_bounded_pressure_primary"
OBSERVATION_PRIMARY = ROOT / "experiments" / "009_recurrent_observation_validity"
RECURRENT_ACQUISITION = ROOT / "experiments" / "011_recurrent_acquisition_granularity"
LARGE_WORLD = ROOT / "experiments" / "012_large_world_recurrent_continuity"
PHASE_RECEIPTS = ROOT / "experiments" / "013_active_phase_receipts"
FINAL_TIMEOUT_ATTEMPT = OBSERVATION_PRIMARY / "final_path_rehearsal" / "attempt1_timeout"


class QueueActor:
    def __init__(self, actions: list[dict], *, deny_first: bool = False):
        self.actions = list(actions)
        self.deny_first = deny_first
        self.prepared = 0
        self.requests: list[dict] = []

    def prepare(self, request: bytes, *, stage: str, probe_id: str | None, call_id: str, active_total_ceiling: int) -> PreparedCall:
        self.prepared += 1
        self.requests.append(load_json_strict(request))
        authorized = not (self.deny_first and self.prepared == 1)
        admission = {
            "authorized": authorized,
            "offline_prompt_tokens": 24_000 if not authorized else 1_000,
            "active_total_ceiling_tokens": active_total_ceiling,
            "reasoning_budget_tokens": 512,
            "output_allowance_tokens": 2_500,
        }
        return PreparedCall(call_id, b"{}", request, admission["offline_prompt_tokens"], active_total_ceiling, authorized, admission)

    def invoke(self, prepared: PreparedCall) -> CallOutcome:
        action = self.actions.pop(0)
        assistant = canonical_json_bytes(action)
        raw = canonical_json_bytes({
            "id": "scripted-" + prepared.call_id,
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": assistant.decode()}}],
            "usage": {"prompt_tokens": prepared.offline_prompt_tokens, "completion_tokens": 1},
        })
        return CallOutcome(
            prepared.endpoint_request, prepared.rendered_prompt, raw, assistant,
            prepared.offline_prompt_tokens, prepared.offline_prompt_tokens, 1, 0, 0,
            "scripted-" + prepared.call_id,
        )


class RecurrentPressureTests(unittest.TestCase):
    def test_large_world_bank_and_hierarchical_p0(self) -> None:
        result = verify_large_bank(LARGE_WORLD / "fresh_bank")
        self.assertEqual(result["file_count"], 667)
        for fixture_id in E12_CASE_IDS:
            fixture = load_large_fixture(LARGE_WORLD / "fresh_bank", fixture_id)
            self.assertEqual(len(fixture.initial.files), 160)
            root = build_p0_root(fixture.initial)
            self.assertFalse(root["complete_for_repository"])
            self.assertLessEqual(len(canonical_json_bytes(root)), 6_000)
            directory = p0_page(fixture.initial, path="policies" if "SOURCE" in fixture_id else "codec", offset=0)
            self.assertTrue(directory["accepted"])
            self.assertTrue(directory["entries"])
            truth = load_json_strict((LARGE_WORLD / "fresh_bank" / "evaluator_only" / fixture_id / "TRUTH.json").read_bytes())
            candidate = fixture.initial
            for patch in truth["patches"]:
                candidate, _ = candidate.patch(
                    path=patch["path"], old=patch["old"], new=patch["new"],
                    expected_candidate_id=candidate.candidate_id,
                    expected_file_sha256=candidate.file_sha256(patch["path"]),
                )
            self.assertTrue(large_hidden_grade(fixture, candidate)["passed"])

    def test_exact_result_reopen_is_opt_in_and_hash_bound(self) -> None:
        fixture = load_large_fixture(LARGE_WORLD / "fresh_bank", "E12-SOURCE-ORBIT")
        body = canonical_json_bytes({"accepted": True, "path": "api/name.py", "content": "exact"})
        enabled = ToolExecutor(
            SessionState(fixture.initial, stage="continuation"), required_full_reads=(),
            prefork_checker=fixture.phases["B"].checker, public_checker=fixture.phases["B"].checker,
            final_target="__none__", probe_id=None, probe_body=None,
            result_reopenable={"RES-0001": body},
        )
        result = enabled.execute({"action": "reopen_result", "handle": "RES-0001"})
        self.assertTrue(result["accepted"])
        self.assertEqual(result["exact_result_utf8"], body.decode())
        disabled = ToolExecutor(
            SessionState(fixture.initial, stage="continuation"), required_full_reads=(),
            prefork_checker=fixture.phases["B"].checker, public_checker=fixture.phases["B"].checker,
            final_target="__none__", probe_id=None, probe_body=None,
        )
        self.assertFalse(disabled.execute({"action": "reopen_result", "handle": "RES-0001"})["accepted"])

    def test_phase_receipt_contains_only_exact_mechanical_fields(self) -> None:
        action = {"action": "read", "path": "records_b/module_000.py", "start_line": 1}
        result = {
            "accepted": True, "path": action["path"], "candidate_id": "a" * 64,
            "file_sha256": "b" * 64, "requested_start_line": 1, "returned_start_line": 1,
            "returned_end_line": 177, "next_start_line": None, "complete": True, "content": "large exact body",
        }
        receipt = phase_receipt(action, result, sequence=1, handle="RES-0001")
        self.assertEqual(receipt["path"], action["path"])
        self.assertTrue(receipt["complete"])
        self.assertNotIn("content", receipt)
        self.assertNotIn("relevant", receipt)
        self.assertNotIn("sufficient", receipt)

    def test_receipt_bank_and_request_separate_ledger_from_exact_body(self) -> None:
        self.assertEqual(verify_receipt_bank(PHASE_RECEIPTS / "fresh_bank")["file_count"], 657)
        fixture = load_receipt_fixture(PHASE_RECEIPTS / "fresh_bank", "E13-SOURCE-LUMEN")
        receipt = phase_receipt(
            {"action": "read", "path": "api/name.py", "start_line": 1},
            {"accepted": True, "path": "api/name.py", "candidate_id": fixture.initial.candidate_id,
             "file_sha256": fixture.initial.file_sha256("api/name.py"), "returned_start_line": 1,
             "returned_end_line": 2, "next_start_line": None, "complete": True, "content": "secret body"},
            sequence=1, handle="RES-0001",
        )
        request = load_json_strict(build_receipt_request(
            fixture, candidate=fixture.initial, phase_id="B", history=[], observations=[], completed=["A"],
            reconstructed=True, boundary_binding={}, calls_used=3, stage="continuation",
            condition="T25-RECEIPTS", receipt_entries=[receipt], externalized_receipt_count=1,
        ))
        self.assertNotIn("condition", request)
        self.assertEqual(request["active_phase_receipt_ledger"]["entries"][0]["result_handle"], "RES-0001")
        self.assertNotIn("secret body", canonical_json_bytes(request).decode())
        self.assertIn("reopen_result", request["available_actions"])

    def test_hierarchical_p0_tool_is_exact_and_opt_in(self) -> None:
        fixture = load_large_fixture(LARGE_WORLD / "fresh_bank", "E12-SOURCE-ORBIT")
        state = SessionState(fixture.initial, stage="recurrent")
        phase = fixture.phases["B"]
        enabled = ToolExecutor(
            state, required_full_reads=(), prefork_checker=phase.checker, public_checker=phase.checker,
            final_target="__none__", probe_id=None, probe_body=None, read_mode="maximal_bounded_page",
            hierarchical_p0=True,
        )
        page = enabled.execute({"action": "p0_page", "path": "policies/current.py", "offset": 0})
        self.assertTrue(page["accepted"])
        self.assertEqual(page["kind"], "file_outline")
        self.assertEqual(page["entries"][0]["name"], "active_policy_prefix")
        disabled = ToolExecutor(
            SessionState(fixture.initial, stage="recurrent"), required_full_reads=(), prefork_checker=phase.checker,
            public_checker=phase.checker, final_target="__none__", probe_id=None, probe_body=None,
            read_mode="maximal_bounded_page",
        )
        rejected = disabled.execute({"action": "p0_page", "path": "policies", "offset": 0})
        self.assertFalse(rejected["accepted"])

    def test_recurrent_acquisition_completion_binds_only_missing_pair_and_partial_seal(self) -> None:
        prior = verify_prior_partial(RECURRENT_ACQUISITION)
        self.assertEqual(prior["http_completion_calls"], 108)
        authorization = expected_authorization(RECURRENT_ACQUISITION, ROOT)
        self.assertEqual(authorization["cell_ordinal"], 4)
        self.assertEqual(authorization["fixture_id"], "E11-OBS-KAPPA")
        self.assertEqual(authorization["seed"], 223607)
        self.assertEqual(authorization["branch_order"], ["T25-L0", "T25-L1"])
        self.assertTrue(authorization["no_resume_or_rewrite_of_prior_partial"])

    def test_recurrent_acquisition_request_preserves_mode_after_phase_b_override(self) -> None:
        fixture = load_recurrent_fixture(RECURRENT_ACQUISITION / "fresh_bank", "E11-OBS-IOTA")
        request = load_json_strict(build_recurrent_request(
            fixture, candidate=fixture.initial, phase="B", history=[], observations=[], reconstructed=True,
            boundary_binding={}, calls_used=0, read_mode="maximal_bounded_page",
            observation_directory_version=2, acquisition_contract=True,
        ))
        self.assertEqual(request["schema_version"], "experiment-011-recurrent-acquisition-request-v1")
        self.assertEqual(request["read_paging_mode"], "maximal_bounded_page")
        self.assertIn("largest exact current whole-line page", request["tool_contract"]["read"])
        self.assertEqual(request["observation_directory"]["schema_version"], "exact-observation-directory-v2")

    def test_live_http_timeout_covers_qualified_physical_worst_case(self) -> None:
        conservative_seconds = (50_176 / 7.0) + (2_500 / 1.1)
        self.assertGreater(HTTP_TIMEOUT_SECONDS, conservative_seconds)

    def test_global_monitor_treats_transport_stop_as_resolved_invocation(self) -> None:
        result = live_monitor_snapshot(FINAL_TIMEOUT_ATTEMPT)
        self.assertEqual(result["prepared_invocations_seen"], 1)
        self.assertEqual(result["resolved_invocations_seen"], 1)
        self.assertIsNone(result["in_flight_prepared_call_id"])

    def test_constructed_final_rehearsal_exposes_stale_and_current_candidate_bindings(self) -> None:
        fixture, middle = _constructed_middle()
        self.assertEqual(middle.disposition, "second_boundary_eligible")
        self.assertEqual(len(middle.observations), 2)
        stale, current = middle.observations
        self.assertNotEqual(stale["candidate_id"], middle.state.candidate.candidate_id)
        self.assertEqual(current["candidate_id"], middle.state.candidate.candidate_id)
        self.assertIn(b"G8++", middle.reopenable[stale["handle"]])
        self.assertIn(b"W6++", middle.reopenable[current["handle"]])
        self.assertEqual(fixture.phase_c_target, "portal/header.py")

    def test_observation_recurrence_bank_is_fresh_valid_and_has_action_headroom(self) -> None:
        result = verify_bank(OBSERVATION_PRIMARY / "fresh_bank")
        self.assertEqual(result["file_count"], 58)
        for fixture_id in E9_CASE_IDS:
            fixture = load_recurrent_fixture(OBSERVATION_PRIMARY / "fresh_bank", fixture_id)
            self.assertEqual(len(fixture.phase_a_required), 3)
            self.assertEqual(len(fixture.phase_b_required), 2)
            self.assertNotEqual(fixture.probe_id, "signal")
            known_good = fixture.initial
            truth = json.loads(
                (OBSERVATION_PRIMARY / "fresh_bank" / "evaluator_only" / fixture_id / "TRUTH.json").read_text()
            )
            for key in ("phase_a_patch", "phase_b_patch", "phase_c_patch"):
                row = truth[key]
                known_good, _ = known_good.patch(
                    path=row["path"], old=row["old"], new=row["new"],
                    expected_candidate_id=known_good.candidate_id,
                    expected_file_sha256=known_good.file_sha256(row["path"]),
                )
            self.assertTrue(hidden_grade(fixture, known_good)["passed"])

    def _source_middle_and_actions(self) -> tuple[object, MiddleOutcome, list[dict], str]:
        fixture = load_recurrent_fixture(PRIMARY / "fresh_bank", "E8-SOURCE")
        run = PRIMARY / "partial_measured_run" / "cell-01" / "T25" / "phase-b"
        summary = load_json_strict((run / "SUMMARY.json").read_bytes())
        snap = run / "snap" / summary["candidate_id"][:32]
        candidate = Candidate.create({path.relative_to(snap).as_posix(): path.read_bytes() for path in snap.rglob("*") if path.is_file()})
        prefix_records = verify_records(PRIMARY / "partial_measured_run" / "cell-01" / "prefix" / "records.jsonl", PRIMARY / "partial_measured_run" / "cell-01" / "prefix")
        middle_records = verify_records(run / "records.jsonl", run)
        prefix_history = [{"response": row["payload"]["action"], "result": row["payload"]["result"]} for row in prefix_records if row["record_type"] == "action_result"]
        middle_history = [{"response": row["payload"]["action"], "result": row["payload"]["result"]} for row in middle_records if row["record_type"] == "action_result"]
        state = SessionState(candidate, stage="recurrent", public_check_passed=True, fork_ready=True)
        outcome = MiddleOutcome(
            state, [prefix_history[-1], *middle_history], [], {}, summary["boundary_binding"],
            summary["calls"], summary["http_completion_calls"], run, summary["disposition"],
        )
        truth = json.loads((PRIMARY / "fresh_bank" / "evaluator_only" / "E8-SOURCE" / "TRUTH.json").read_text())
        patch = truth["phase_c_patch"]
        successor, _ = candidate.patch(
            path=patch["path"], old=patch["old"], new=patch["new"],
            expected_candidate_id=candidate.candidate_id,
            expected_file_sha256=candidate.file_sha256(patch["path"]),
        )
        actions = [
            {"action": "read", "path": truth["governing"]["path"], "start_line": 1, "line_count": 200},
            {"action": "read", "path": patch["path"], "start_line": 1, "line_count": 20},
            {
                "action": "patch", "path": patch["path"], "old": patch["old"], "new": patch["new"],
                "expected_candidate_id": candidate.candidate_id,
                "expected_file_sha256": candidate.file_sha256(patch["path"]),
            },
            {"action": "check", "check_id": "public", "expected_candidate_id": successor.candidate_id},
            {"action": "submit", "expected_candidate_id": successor.candidate_id},
        ]
        return fixture, outcome, actions, successor.candidate_id

    def test_operational_t25_continues_phase_c_when_second_boundary_is_absent(self) -> None:
        fixture, middle, actions, successor_id = self._source_middle_and_actions()
        with tempfile.TemporaryDirectory() as raw:
            summary = run_t25_final_operational(
                fixture, middle, seed=173205, actor=QueueActor(actions), output_dir=Path(raw) / "run",
            )
        self.assertEqual(summary["disposition"], "submitted")
        self.assertTrue(summary["continued_admitted_history"])
        self.assertEqual(summary["runtime_boundary_resets"], 0)
        self.assertEqual(summary["http_completion_calls"], 5)
        self.assertEqual(summary["candidate_id"], successor_id)

    def test_operational_t25_reconstructs_on_actual_midphase_capacity_event(self) -> None:
        fixture, middle, actions, successor_id = self._source_middle_and_actions()
        middle.observations.append({
            "handle": "OBS-0001", "sequence": 1, "action": "check", "target": "public",
            "candidate_id": middle.state.candidate.candidate_id, "size_bytes": 2,
            "sha256": "0" * 64,
        })
        actor = QueueActor(actions, deny_first=True)
        with tempfile.TemporaryDirectory() as raw:
            summary = run_t25_final_operational(
                fixture, middle, seed=173205, actor=actor, output_dir=Path(raw) / "run",
            )
        self.assertEqual(summary["disposition"], "submitted")
        self.assertEqual(summary["runtime_boundary_resets"], 1)
        self.assertEqual(summary["prepared_invocations"], 6)
        self.assertEqual(summary["http_completion_calls"], 5)
        self.assertEqual(summary["candidate_id"], successor_id)
        self.assertEqual(len(actor.requests[1]["history"]), 1)
        self.assertEqual(actor.requests[1]["observation_directory"]["entries"][0]["candidate_id"], middle.state.candidate.candidate_id)

    def test_global_monitor_finds_interrupted_call_not_stale_prior_cell(self) -> None:
        result = live_monitor_snapshot(PRIMARY / "partial_measured_run")
        self.assertEqual(result["prepared_invocations_seen"], 89)
        self.assertEqual(result["completed_actions_seen"], 87)
        self.assertEqual(result["in_flight_prepared_call_id"], "E8-SOURCE-S223607-C50-C02")
        self.assertIn("cell-03/C50/phase-c", result["latest_record"]["records_path"])

    def test_fresh_corrected_primary_bank_and_known_good_candidates(self) -> None:
        result = verify_bank(PRIMARY / "fresh_bank")
        self.assertEqual(result["file_count"], 62)
        for fixture_id in ("E8-SOURCE", "E8-OBSERVATION"):
            fixture = load_recurrent_fixture(PRIMARY / "fresh_bank", fixture_id)
            known_good = fixture.initial
            import json
            truth = json.loads((PRIMARY / "fresh_bank" / "evaluator_only" / fixture_id / "TRUTH.json").read_text())
            for key in ("phase_a_patch", "phase_b_patch", "phase_c_patch"):
                row = truth[key]
                known_good, _ = known_good.patch(
                    path=row["path"], old=row["old"], new=row["new"],
                    expected_candidate_id=known_good.candidate_id,
                    expected_file_sha256=known_good.file_sha256(row["path"]),
                )
            self.assertTrue(hidden_grade(fixture, known_good)["passed"])

    def test_fresh_bank_and_known_good_candidates(self) -> None:
        result = verify_bank(EXPERIMENT / "fresh_bank")
        self.assertEqual(result["file_count"], 62)
        for fixture_id in ("E7-SOURCE", "E7-OBSERVATION"):
            fixture = load_recurrent_fixture(EXPERIMENT / "fresh_bank", fixture_id)
            known_good = fixture.initial
            import json
            truth = json.loads((EXPERIMENT / "fresh_bank" / "evaluator_only" / fixture_id / "TRUTH.json").read_text())
            for key in ("phase_a_patch", "phase_b_patch", "phase_c_patch"):
                row = truth[key]
                known_good, _ = known_good.patch(
                    path=row["path"], old=row["old"], new=row["new"],
                    expected_candidate_id=known_good.candidate_id,
                    expected_file_sha256=known_good.file_sha256(row["path"]),
                )
            self.assertTrue(hidden_grade(fixture, known_good)["passed"])

    def test_recurrent_schema_exposes_existing_boundary_actions(self) -> None:
        schema = action_schema("recurrent", probe_id="session")
        actions = {
            option["properties"]["action"]["const"]
            for option in schema["json_schema"]["schema"]["oneOf"]
        }
        self.assertIn("reopen_observation", actions)
        self.assertIn("fork_ready", actions)
        self.assertIn("probe", actions)
        self.assertNotIn("submit", actions)

    def test_mutation_invalidates_candidate_bound_check(self) -> None:
        fixture = load_recurrent_fixture(EXPERIMENT / "fresh_bank", "E7-SOURCE")
        state = SessionState(fixture.initial, stage="continuation", public_check_passed=True)
        executor = ToolExecutor(
            state, required_full_reads=(), prefork_checker=fixture.phase_a_checker,
            public_checker=fixture.final_checker, final_target=fixture.phase_c_target,
            probe_id=None, probe_body=None,
        )
        result = executor.execute({
            "action": "patch", "path": "delivery/tag.py", "old": "    return code.strip().upper()",
            "new": '    return "quartz-" + code.strip().upper()',
            "expected_candidate_id": state.candidate.candidate_id,
            "expected_file_sha256": state.candidate.file_sha256("delivery/tag.py"),
        })
        self.assertTrue(result["accepted"])
        self.assertFalse(state.public_check_passed)

    def test_probe_version_changes_mechanically_after_mutation(self) -> None:
        fixture = load_recurrent_fixture(EXPERIMENT / "fresh_bank", "E7-OBSERVATION")
        state = SessionState(fixture.initial, stage="recurrent")
        baseline = state.candidate.candidate_id
        executor = CandidateBoundProbeExecutor(
            state, required_full_reads=(), prefork_checker=fixture.phase_a_checker,
            public_checker=fixture.phase_b_checker, final_target=fixture.phase_c_target,
            probe_id=fixture.probe_id, probe_body=fixture.probe_v1, baseline_candidate_id=baseline,
            probe_v1=fixture.probe_v1, probe_v2=fixture.probe_v2,
        )
        first = executor.execute({"action": "probe", "probe_id": "session"})
        self.assertIn("K4::", first["observation"])
        executor.execute({
            "action": "patch", "path": "session/label.py", "old": "    return name.strip().upper()",
            "new": '    return "anything" + name.strip().upper()',
            "expected_candidate_id": state.candidate.candidate_id,
            "expected_file_sha256": state.candidate.file_sha256("session/label.py"),
        })
        second = executor.execute({"action": "probe", "probe_id": "session"})
        self.assertIn("M7::", second["observation"])


if __name__ == "__main__":
    unittest.main()
