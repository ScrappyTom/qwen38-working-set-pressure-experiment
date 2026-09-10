import copy
from contextlib import contextmanager
import json
from pathlib import Path
from types import SimpleNamespace
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import prepare_interface_wording as wording
from working_set_exp.candidate import Candidate
from working_set_exp.hierarchical_p0 import build_p0_root, p0_page
from working_set_exp.jsonutil import canonical_json_bytes


class WordingPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = wording.reference.development_states(ROOT)
        cls.grammar = wording.reference.endpoint_request(cls.values[0], seed=42, mode="action")["response_format"]
        cls.reference = wording.reference.tool_reference(cls.grammar)

    def test_only_declared_wording_changes_across_all_development_states(self):
        before = [(v.request, wording.reference.candidate_bytes(v.state.candidate),
                   wording.reference.session_bytes(v.state)) for v in self.values]
        for index, value in enumerate(self.values):
            for seed in wording.SEEDS:
                row = {"state": f"I{index + 1}", "seed": seed, "condition": "reference"}
                control = wording.request_for(value, row, self.reference)
                changed = wording.request_for(value, {**row, "condition": "wording"}, self.reference)
                self.assertEqual([m["role"] for m in changed["messages"]], ["system", "user"])
                self.assertEqual({k: v for k, v in control.items() if k != "messages"},
                                 {k: v for k, v in changed.items() if k != "messages"})
                old_user = json.loads(control["messages"][1]["content"])
                new_user = json.loads(changed["messages"][1]["content"])
                old_user["resource_state"].pop(wording.RESOURCE_KEY)
                self.assertEqual(new_user, old_user)
                # Reverse the single sentence edit to check all other system bytes.
                restored = changed["messages"][0]["content"].replace(wording.NEW_NAVIGATION, wording.OLD_NAVIGATION)
                self.assertEqual(restored, control["messages"][0]["content"])
                self.assertTrue(changed["messages"][0]["content"].endswith("\n\n" + self.reference))
                self.assertEqual(changed["response_format"], self.grammar)
                self.assertFalse(changed["cache_prompt"])
                self.assertTrue(all(changed[k] == -1 for k in ("max_tokens", "n_predict", "thinking_budget_tokens", "reasoning_budget_tokens")))
        after = [(v.request, wording.reference.candidate_bytes(v.state.candidate),
                  wording.reference.session_bytes(v.state)) for v in self.values]
        self.assertEqual(after, before)

    def test_exposure_scope_is_eight_new_seed_requests_and_excludes_regressions(self):
        rows = wording.schedule()
        self.assertEqual([r["id"] for r in rows], [f"W{i:02d}" for i in range(1, 9)])
        self.assertTrue(set(wording.SEEDS).isdisjoint(wording.reference.SEEDS))
        self.assertEqual(len({(r["state"], r["seed"], r["condition"]) for r in rows}), 8)
        self.assertEqual({r["state"] for r in rows}, {"I3", "I4"})
        for i in (0, 4):
            self.assertEqual({rows[i]["condition"], rows[i + 2]["condition"]}, set(wording.CONDITIONS))
        all_rows = wording.preparation_rows()
        self.assertEqual(all_rows[:8], rows)
        self.assertEqual([r["id"] for r in all_rows[8:]], ["E01", "E02", "E03", "E04"])
        self.assertTrue(all(r["purpose"] == "offline_input_regression" for r in all_rows[8:]))

    def test_rejects_missing_contract_unknown_scope_and_accumulated_history(self):
        row = {"state": "I3", "seed": wording.SEEDS[0], "condition": "reference"}
        original = wording.request_for(self.values[2], row, self.reference)
        changed = copy.deepcopy(original)
        changed["messages"][0]["content"] = changed["messages"][0]["content"].removesuffix("\n\n" + self.reference)
        with self.assertRaisesRegex(ValueError, "reference is missing"):
            wording.wording_variant(changed)
        changed = copy.deepcopy(original)
        changed["messages"].append({"role": "assistant", "content": "previous answer"})
        with self.assertRaisesRegex(ValueError, "fresh ordinary"):
            wording.wording_variant(changed)
        changed = copy.deepcopy(original)
        operation = next(option for option in changed["response_format"]["json_schema"]["schema"]["oneOf"]
                         if option["properties"]["action"]["const"] == "p0_page")
        operation["properties"]["offset"]["maximum"] += 1
        with self.assertRaisesRegex(ValueError, "tool schema or reference"):
            wording.wording_variant(changed)
        changed = copy.deepcopy(original)
        state = json.loads(changed["messages"][1]["content"])
        state["current_p0"]["complete_for_top_level"] = False
        changed["messages"][1]["content"] = json.dumps(state)
        with self.assertRaisesRegex(ValueError, "P0 scope"):
            wording.wording_variant(changed)

    def test_navigation_claims_match_scoped_paging_and_preserve_reading(self):
        source = "\n".join(f"def f{i}():\n    return {i}\n" for i in range(30)).encode()
        candidate = Candidate.create({"service.py": source, "sub/other.py": b"x = 1\n"})
        root = build_p0_root(candidate)
        self.assertEqual([r["path"] for r in root["entries"]], ["service.py", "sub"])
        first = p0_page(candidate, path="service.py", offset=0)
        last = p0_page(candidate, path="service.py", offset=first["next_offset"])
        self.assertEqual(first["next_offset"], 24)
        self.assertEqual(len(first["entries"]) + len(last["entries"]), 30)
        self.assertIsNone(last["next_offset"])
        self.assertEqual(build_p0_root(candidate), root)
        self.assertFalse(root["complete_for_repository"])
        # Reproduce the observed offset-1 result, including unchanged source coverage.
        value = wording.reference.development_states(ROOT)[3]
        before = wording.reference.session_bytes(value.state)
        result = value.execute({"action": "p0_page", "path": "service.py", "offset": 1})
        self.assertEqual([r["name"] for r in result["entries"]], ["ready"])
        self.assertEqual(wording.reference.session_bytes(value.state), before)

    def test_initial_check_is_not_a_patch_precondition_but_guards_still_apply(self):
        value = wording.reference.development_states(ROOT)[2]
        action = {"action": "patch", "path": "service.py", "old": "return 1", "new": "return 2",
                  "expected_candidate_id": value.state.candidate.candidate_id,
                  "expected_file_sha256": value.state.candidate.file_sha256("service.py")}
        rejected = value.execute({**action, "expected_candidate_id": "0" * 64})
        self.assertFalse(rejected["accepted"])
        self.assertTrue(value.execute(action)["accepted"])
        self.assertEqual(value.state.candidate.file_map["service.py"], b"def value():\n    return 2\n")

    @contextmanager
    def fake_runtime(self, args, store, log):
        (args.output / "private-runtime").mkdir()
        (args.output / "memory.csv").write_text("2026/09/10 20:00:00.000, 0, 12288, 11961, 327\n")
        log.append("runtime_ready", {"test_double": True}, [])
        try:
            yield "test-only"
        finally:
            log.append("runtime_closed", {"test_double": True, "owned_server_shutdown_verified": True, "dedicated_port_free": True}, [])

    def test_native_preparation_uses_only_render_and_tokenize_and_seals_exact_scope(self):
        routes = []
        def native(url, route, raw, timeout):
            routes.append(route)
            if route == "/apply-template":
                request = json.loads(raw)
                return canonical_json_bytes({"prompt": "\n".join(m["content"] for m in request["messages"])})
            self.assertEqual(route, "/tokenize")
            self.assertFalse(json.loads(raw)["add_special"])
            return canonical_json_bytes({"tokens": [1, 2]})
        original_render = wording.reference.render_only
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(output=Path(directory) / "package", model=Path("unused"), server=Path("unused"))
            with patch.object(wording.reference.base, "owned_runtime", self.fake_runtime), \
                 patch.object(wording.reference, "render_only", side_effect=lambda url, request: original_render(url, request, post=native)), \
                 patch.object(wording.reference.cont, "monitoring"), patch.object(wording.reference.cont, "healthy_runtime"):
                seal = wording.prepare(args)
            self.assertEqual(routes, ["/apply-template", "/tokenize"] * 12)
            self.assertEqual(seal["completion_calls"], 0)
            manifest = wording.validate_package(args.output)
            self.assertEqual(manifest["proposed_completion_ids"], [f"W{i:02d}" for i in range(1, 9)])
            self.assertEqual(manifest["proposed_comparison_calls"], 8)
            manifest["proposed_completion_ids"].append("E01")
            (args.output / "PACKAGE_MANIFEST.json").write_bytes(canonical_json_bytes(manifest))
            with self.assertRaisesRegex(ValueError, "exposure scope differs"):
                wording.validate_package(args.output)

    def test_preparation_failure_preserves_partial_input_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            args = SimpleNamespace(output=Path(directory) / "package", model=Path("unused"), server=Path("unused"))
            with patch.object(wording.reference.base, "owned_runtime", self.fake_runtime), \
                 patch.object(wording.reference, "render_only", side_effect=ValueError("test admission failure")) as native, \
                 patch.object(wording.reference.cont, "monitoring"):
                with self.assertRaisesRegex(ValueError, "test admission failure"):
                    wording.prepare(args)
            self.assertEqual(native.call_count, 1)
            seal = json.loads((args.output / "PREPARATION_SEAL.json").read_bytes())
            self.assertEqual(seal["disposition"], "stopped_without_completion")
            self.assertFalse((args.output / "PACKAGE_MANIFEST.json").exists())


if __name__ == "__main__":
    unittest.main()
