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
import prepare_interface_comparison as comparison
from working_set_exp.jsonutil import canonical_json_bytes


class ComparisonPreparationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.values = comparison.development_states(ROOT)
        cls.grammar = comparison.endpoint_request(cls.values[0], seed=42, mode="action")["response_format"]
        cls.reference = comparison.tool_reference(cls.grammar)

    def test_only_visible_reference_differs_and_order_is_balanced(self):
        before = [v.request for v in self.values]
        rows = comparison.schedule()
        self.assertEqual(len(rows), 16)
        self.assertEqual(len({(r["state"], r["seed"], r["condition"]) for r in rows}), 16)
        for i in range(0, 16, 2):
            pair = rows[i:i + 2]
            requests = {r["condition"]: comparison.request_for(self.values[r["state_index"]], r, self.reference) for r in pair}
            legacy, variant = requests["legacy"], requests["visible_reference"]
            self.assertEqual([m["role"] for m in legacy["messages"]], ["system", "user"])
            self.assertEqual(legacy["messages"][1], variant["messages"][1])
            self.assertEqual(variant["messages"][0]["content"], legacy["messages"][0]["content"] + "\n\n" + self.reference)
            self.assertEqual({k: v for k, v in legacy.items() if k != "messages"},
                             {k: v for k, v in variant.items() if k != "messages"})
            self.assertFalse(legacy["cache_prompt"])
            self.assertTrue(all(legacy[k] == -1 for k in ("max_tokens", "n_predict", "thinking_budget_tokens", "reasoning_budget_tokens")))
            for row in pair:
                expected = comparison.endpoint_request(self.values[row["state_index"]], seed=row["seed"], mode="action")
                user = json.loads(requests[row["condition"]]["messages"][1]["content"])
                original = json.loads(expected["messages"][1]["content"])
                self.assertEqual(user, comparison.neutral_ids(original, row["state"]))
        for i in range(0, 16, 4):
            self.assertEqual({rows[i]["condition"], rows[i + 2]["condition"]}, set(comparison.CONDITIONS))
        self.assertEqual(before, [v.request for v in self.values])
        changed = comparison.request_for(self.values[0], rows[0], self.reference)
        changed["messages"].append({"role": "assistant", "content": "contamination"})
        self.assertEqual(len(comparison.request_for(self.values[0], rows[0], self.reference)["messages"]), 2)

    def test_catalog_contains_every_required_form_and_fails_on_new_constraints(self):
        for option in self.grammar["json_schema"]["schema"]["oneOf"]:
            for key in option["required"]:
                self.assertIn("  " + key + ": " + comparison.argument_form(option["properties"][key]), self.reference)
        altered = copy.deepcopy(self.grammar)
        altered["json_schema"]["schema"]["oneOf"][0]["properties"]["path"]["format"] = "new-format"
        with self.assertRaisesRegex(ValueError, "unhandled argument constraint"):
            comparison.tool_reference(altered)
        altered = copy.deepcopy(self.grammar)
        altered["json_schema"]["schema"]["oneOf"].pop()
        with self.assertRaisesRegex(ValueError, "coverage differs"):
            comparison.tool_reference(altered)
        altered = copy.deepcopy(self.grammar)
        altered["json_schema"]["schema"]["oneOf"][0]["required"].pop()
        with self.assertRaisesRegex(ValueError, "optional or missing"):
            comparison.tool_reference(altered)

    def test_native_preparation_has_no_completion_route_and_enforces_room(self):
        routes = []
        def native(url, route, raw, timeout):
            routes.append(route)
            self.assertIn(route, {"/apply-template", "/tokenize"})
            if route == "/apply-template":
                return canonical_json_bytes({"prompt": "native prompt"})
            self.assertEqual(json.loads(raw), {"content": "native prompt", "add_special": False})
            return canonical_json_bytes({"tokens": [1] * comparison.INPUT_CEILING})
        comparison.render_only("unused", {}, native)
        self.assertEqual(routes, ["/apply-template", "/tokenize"])
        def too_large(url, route, raw, timeout):
            return canonical_json_bytes({"prompt": "native prompt"} if route == "/apply-template" else
                                        {"tokens": [1] * (comparison.INPUT_CEILING + 1)})
        with self.assertRaisesRegex(ValueError, "admission margin"):
            comparison.render_only("unused", {}, too_large)

    @contextmanager
    def fake_runtime(self, args, store, log):
        private = args.output / "private-runtime"
        private.mkdir()
        (args.output / "memory.csv").write_text("2026/09/10 12:00:00.000, 0, 12288, 11949, 339\n")
        log.append("runtime_ready", {"test_double": True}, [])
        try:
            yield "test-only"
        finally:
            log.append("runtime_closed", {"test_double": True, "owned_server_shutdown_verified": True, "dedicated_port_free": True}, [])

    def test_sealed_prepare_only_rejects_changed_request_and_configuration(self):
        def render(url, request):
            raw = canonical_json_bytes(request)
            return canonical_json_bytes({"prompt": raw.decode("utf-8")}), raw, canonical_json_bytes({"tokens": [1, 2]}), 2
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "package"
            args = SimpleNamespace(output=output, server=Path("unused-server"), model=Path("unused-model"))
            with patch.object(comparison.base, "owned_runtime", self.fake_runtime), \
                 patch.object(comparison, "render_only", side_effect=render) as renderer, \
                 patch.object(comparison.cont, "monitoring"), patch.object(comparison.cont, "healthy_runtime"), \
                 patch.object(comparison.base, "post", side_effect=AssertionError("unexpected network request")):
                seal = comparison.prepare(args)
            self.assertEqual(renderer.call_count, 16)
            self.assertEqual(seal["completion_calls"], 0)
            manifest = comparison.validate_package(output)
            target = output / manifest["rows"][0]["request_path"]
            original = target.read_bytes()
            changed = json.loads(original)
            changed["messages"][1]["content"] += "\nAnswer from prior call"
            target.write_bytes(canonical_json_bytes(changed))
            with self.assertRaisesRegex(ValueError, "prepared artifact differs"):
                comparison.validate_package(output)
            target.write_bytes(original)
            manifest["actor"]["generation_reserve"] = 20480
            (output / "PACKAGE_MANIFEST.json").write_bytes(canonical_json_bytes(manifest))
            with self.assertRaisesRegex(ValueError, "policy differs"):
                comparison.validate_package(output)

    def test_preparation_failure_is_sealed_without_retry(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "package"
            args = SimpleNamespace(output=output, server=Path("unused-server"), model=Path("unused-model"))
            with patch.object(comparison.base, "owned_runtime", self.fake_runtime), \
                 patch.object(comparison, "render_only", side_effect=ValueError("test admission failure")) as renderer, \
                 patch.object(comparison.cont, "monitoring"):
                with self.assertRaisesRegex(ValueError, "test admission failure"):
                    comparison.prepare(args)
            self.assertEqual(renderer.call_count, 1)
            seal = json.loads((output / "PREPARATION_SEAL.json").read_bytes())
            self.assertEqual(seal["disposition"], "stopped_without_completion")
            self.assertEqual(seal["completion_calls"], 0)
            self.assertFalse((output / "PACKAGE_MANIFEST.json").exists())


if __name__ == "__main__":
    unittest.main()
