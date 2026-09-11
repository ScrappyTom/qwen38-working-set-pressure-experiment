from __future__ import annotations

import copy
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import prepare_compiler_incident as prep
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict


class CompilerIncidentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.records = prep.capture_records()
        cls.fixture = prep.constructed_fixture(cls.records)
        cls.report = prep.expected_report(cls.records)

    def test_capture_reproduces_saved_screen_without_incidental_cache_files(self):
        self.assertEqual(len(self.fixture.initial.files), 6)
        self.assertFalse(any("__pycache__" in path for path, _ in self.fixture.initial.files))
        self.assertEqual(self.records, load_json_strict((prep.AREA / "screen-001/captures.json").read_bytes()))
        self.assertEqual(prep.capture_records(), self.records)
        self.assertEqual(self.fixture.initial.candidate_id,
                         load_json_strict((prep.AREA / "screen-001/candidate.json").read_bytes())["candidate_id"])

    def test_complete_repair_and_evidence_report_are_both_required(self):
        rows = prep.behavior_matrix(self.fixture)
        self.assertEqual([row["variant"] for row in rows if row["result"]["passed"]], ["complete"])
        self.assertTrue(all(row["result"]["stdout"].rstrip().endswith("/26 contract cases passed") for row in rows))

    def test_repaired_historical_calls_and_trees_match_original_independently(self):
        result = prep.repaired_capture_probe(self.fixture, self.records)
        self.assertTrue(result["trees_equal_original"] and result["calls_equal_original"])

    def test_reports_follow_actual_trees_not_selected_function_names(self):
        self.assertEqual(self.report["builds"][0]["changed_functions"], ["_normal_dist_inv_cdf"])
        self.assertEqual(self.report["builds"][1]["changed_functions"], ["_normal_dist_inv_cdf", "weibullvariate"])
        altered = copy.deepcopy(self.records)
        altered[2]["compile_request"]["functions"] = []
        self.assertEqual(prep.expected_report(altered), self.report)
        self.assertEqual(self.report["builds"][0]["first_change"],
                         {"function":"_normal_dist_inv_cdf", "before":"-log(r)", "after":"log(r)"})

    def test_each_capture_adds_information_absent_from_the_other_two(self):
        evidence = prep.counterfactual_checks(self.records)
        self.assertEqual(evidence["original_variant_records"][1:], self.records[1:])
        self.assertEqual(evidence["build_a_variant_records"][0], self.records[0])
        self.assertEqual(evidence["build_a_variant_records"][2], self.records[2])
        self.assertEqual(evidence["build_b_variant_records"][:2], self.records[:2])
        self.assertEqual(len({canonical_json_bytes(report) for report in evidence["reports"]}), 4)

    def test_dump_decoding_cannot_execute_supplied_code(self):
        for text in ("__import__('os').getcwd()", "Module(body=[x for x in []], type_ignores=[])",
                     "UnknownNode()", "Module(surprise=Constant(value=1))"):
            with self.assertRaises((ValueError, TypeError)):
                prep.decode_dump(text)

    def test_equivalent_expression_spelling_is_accepted_but_wrong_facts_are_not(self):
        report = copy.deepcopy(self.report)
        report["builds"].reverse()
        report["builds"][0]["first_change"]["before"] = "  (-log( r ))  "
        candidate = prep.repaired_candidate(self.fixture, report=report)
        self.assertTrue(prep.run_checker(candidate, self.fixture.public_checker)["passed"])
        report["builds"][0]["first_change"]["before"] = "+log(r)"
        candidate = prep.repaired_candidate(self.fixture, report=report)
        self.assertFalse(prep.run_checker(candidate, self.fixture.public_checker)["passed"])

    def test_all_short_routes_finish_with_a_current_checked_candidate(self):
        for kind in prep.ROUTES:
            value, snapshots = prep.qualification_actions(self.fixture, kind)
            self.assertLess(len(snapshots), prep.prior.CALL_LIMIT)
            self.assertTrue(value.state.submitted and value.state.public_check_passed)
            self.assertTrue(snapshots[-2]["result"]["passed"])
            for snapshot in snapshots[-2:]:
                self.assertEqual(snapshot["action"]["expected_candidate_id"], value.state.candidate.candidate_id)
            with self.assertRaises(ValueError):
                prep.prior.request_for(value, prep.prior.pilot.tool_reference(prep.prior.pilot.grammar_for(value)))

    def test_clone_preserves_passing_check_and_linked_maps_without_mutating_parent(self):
        _, snapshots = prep.qualification_actions(self.fixture, "schema_informed_minimum")
        value = prep.new_state("pre-submit", self.fixture)
        for snapshot in snapshots[:-1]:
            self.assertEqual(value.execute(snapshot["action"]), snapshot["result"])
        self.assertTrue(value.state.public_check_passed)
        cloned = prep.exact_clone(value)
        self.assertTrue(cloned.state.public_check_passed)
        self.assertEqual(cloned.executor.execute(dict(action="reopen_event", handle="EVT-0006")),
                         value.executor.execute(dict(action="reopen_event", handle="EVT-0006")))
        clone_result = cloned.execute(prep.patch_action(cloned, prep.TARGET, prep.GOOD, prep.PARTIAL))
        self.assertTrue(clone_result["accepted"])
        self.assertFalse(cloned.state.public_check_passed)
        self.assertTrue(value.state.public_check_passed)
        self.assertNotEqual(cloned.state.candidate, value.state.candidate)

    def test_large_capture_and_canonical_recovery_fit_actual_wrappers(self):
        value = prep.new_state("exact", self.fixture)
        reference = prep.prior.pilot.tool_reference(prep.prior.pilot.grammar_for(value))
        for handle, raw in self.fixture.observation_bodies:
            before = copy.deepcopy(value.state)
            result = value.execute(dict(action="reopen_observation", handle=handle))
            self.assertTrue(result["accepted"])
            self.assertEqual(result["exact_result_utf8"].encode(), raw)
            self.assertEqual(value.state, before)
            self.assertLessEqual(len(canonical_json_bytes(result)), 22_000)
        request = prep.prior.request_for(value, reference, externalized=1)
        self.assertFalse(prep.original_visible(request, "OBS-0001", self.fixture))
        self.assertTrue(prep.original_visible(request, "OBS-0003", self.fixture))
        before_maps = copy.deepcopy((value.event_payloads, value.result_payloads))
        value.execute(dict(action="reopen_observation", handle="OBS-0001"))
        after = prep.prior.request_for(value, reference, externalized=2)
        self.assertTrue(prep.original_visible(after, "OBS-0001", self.fixture))
        self.assertEqual((value.event_payloads, value.result_payloads), before_maps)

    def test_reference_and_only_declared_residency_change_survive_request_building(self):
        value = prep.new_state("pair", self.fixture)
        value.execute(dict(action="reopen_observation", handle="OBS-0001"))
        reference = prep.prior.pilot.tool_reference(prep.prior.pilot.grammar_for(value))
        requests = [prep.prior.request_for(value, reference, externalized=n) for n in (0, 1)]
        states = [load_json_strict(r["messages"][1]["content"].encode()) for r in requests]
        for state in states:
            state.pop("active_phase_event_frame")
            state.pop("event_frame_verification")
        self.assertEqual(states[0], states[1])
        self.assertEqual(requests[0]["messages"][0], requests[1]["messages"][0])
        self.assertEqual(requests[0]["response_format"], requests[1]["response_format"])
        self.assertIn(reference, requests[0]["messages"][0]["content"])
        self.assertEqual(requests[0]["chat_template_kwargs"], {"enable_thinking":True,"reasoning_effort":"xhigh"})

    def test_rendering_transport_uses_no_completion_endpoint(self):
        value = prep.new_state("transport", self.fixture)
        reference = prep.prior.pilot.tool_reference(prep.prior.pilot.grammar_for(value))
        request = prep.prior.request_for(value, reference)
        endpoints = []
        def post(url, endpoint, body, timeout):
            endpoints.append(endpoint)
            self.assertIn(endpoint, ("/apply-template", "/tokenize"))
            return canonical_json_bytes({"prompt":"test"} if endpoint == "/apply-template" else {"tokens":[1,2,3]})
        self.assertEqual(prep.prior.pilot.render_only("unused", request, post=post)[3], 3)
        self.assertEqual(endpoints, ["/apply-template", "/tokenize"])

    def test_external_continuation_replays_real_tools_and_delivers_recovered_evidence(self):
        _, snapshots = prep.qualification_actions(self.fixture, "report_incremental")
        seen = []
        def save(stem, request):
            # Synthetic counts exercise control flow only; actual capacity is
            # measured separately with the selected native template/tokenizer.
            state = load_json_strict(request["messages"][1]["content"].encode())
            visible = sum(prep.original_visible(request, h, self.fixture) for h,_ in self.fixture.observation_bodies)
            count = 4100 + 400 * len(state["active_phase_event_frame"]["events"]) + 3500 * visible
            return {"stem":stem, "prompt_tokens":count, "fits_working_set":count <= 16000}
        rows = [save(str(i), snapshot["before_request"]) for i,snapshot in enumerate(snapshots)]
        result = prep.external_continuation(self.fixture, snapshots, rows, save, lambda stem,payload: seen.append((stem,payload)))
        self.assertTrue(result["natural_boundary"] and result["qualified"])
        self.assertEqual(len(result["recovery"]), 1)
        self.assertTrue(result["recovery"][0]["next_input_contains_original_and_b"])
        self.assertEqual(result["total_actions"], len(snapshots)+1)
        self.assertLessEqual(result["maximum_admitted_input"], 16000)
        self.assertTrue(seen[0][1]["same_full_request"])


if __name__ == "__main__":
    unittest.main()
