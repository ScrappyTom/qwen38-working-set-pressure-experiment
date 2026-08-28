from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from working_set_exp.fixture import load_fixture
from working_set_exp.jsonutil import load_json_strict
from working_set_exp.reasoning import CASE_IDS, construct_bank, progress_pointer, verify_bank
from working_set_exp.reasoning_replication import (
    CASE_IDS as REPLICATION_CASE_IDS,
    construct_bank as construct_replication_bank,
    progress_pointer as replication_pointer,
    verify_bank as verify_replication_bank,
)
from working_set_exp.request import REASONING_DIAGNOSTIC_SYSTEM_PROMPT, render_reasoning_prompt
from working_set_exp.runtime import OwnedServer, REASONING_BUDGET, RuntimeProfile, endpoint_request


class ReasoningDiagnosticTests(unittest.TestCase):
    def profile(self) -> RuntimeProfile:
        return RuntimeProfile(
            model_alias="actor", model_path=Path("model.gguf"), model_sha256="a" * 64,
            tokenizer_path=Path("tokenizer.exe"), tokenizer_sha256="b" * 64,
            server_path=Path("server.exe"), server_sha256="c" * 64,
            runtime_root=Path("runtime"), build="test",
        )

    def test_fresh_bank_and_pointer(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            bank = Path(raw) / "bank"
            construct_bank(bank)
            self.assertTrue(verify_bank(bank)["verified"])
            for fixture_id in CASE_IDS:
                fixture = load_fixture(bank, fixture_id)
                pointer = progress_pointer(bank, fixture_id)
                self.assertIn(fixture.final_target, pointer["active_step_verbatim"])
                self.assertFalse(pointer["semantic_host_summary"])

    def test_reasoning_prompt_switches_only_reasoning_envelope(self) -> None:
        request = b'{"stage":"continuation"}'
        off = render_reasoning_prompt(request, enabled=False)
        on = render_reasoning_prompt(request, enabled=True)
        self.assertIn(REASONING_DIAGNOSTIC_SYSTEM_PROMPT.encode(), off)
        self.assertIn(b"<think>\n\n</think>\n\n", off)
        self.assertIn(b"Reasoning effort is set to low", on)
        self.assertTrue(on.endswith(b"<|im_start|>assistant\n<think>\n"))
        self.assertNotIn(b"</think>", on.rsplit(b"<|im_start|>assistant", 1)[1])

    def test_reasoning_endpoint_requests_budget_and_final_content_remains_schema_bound(self) -> None:
        profile = self.profile()
        request = b'{"stage":"continuation"}'
        off = load_json_strict(endpoint_request(profile, request, stage="continuation", probe_id=None, seed=7))
        on = load_json_strict(
            endpoint_request(
                profile, request, stage="continuation", probe_id=None, seed=7,
                reasoning_enabled=True,
            )
        )
        self.assertEqual(off["reasoning_budget"], 0)
        self.assertFalse(off["chat_template_kwargs"]["enable_thinking"])
        self.assertNotIn("reasoning_effort", off)
        self.assertEqual(on["reasoning_budget"], REASONING_BUDGET)
        self.assertEqual(on["reasoning_effort"], "low")
        self.assertTrue(on["chat_template_kwargs"]["enable_thinking"])
        self.assertEqual(on["response_format"], off["response_format"])
        self.assertEqual(on["max_tokens"], off["max_tokens"])

    def test_server_reasoning_budget_is_explicitly_configurable(self) -> None:
        server = OwnedServer(
            self.profile(), Path("evidence"), reasoning_mode="auto",
            reasoning_budget=REASONING_BUDGET,
        )
        self.assertEqual(server.reasoning_budget, REASONING_BUDGET)
        with self.assertRaises(ValueError):
            OwnedServer(self.profile(), Path("evidence"), reasoning_mode="auto", reasoning_budget=-2)

    def test_replication_bank_is_fresh_and_mechanically_valid(self) -> None:
        with tempfile.TemporaryDirectory() as raw:
            bank = Path(raw) / "bank"
            construct_replication_bank(bank)
            self.assertTrue(verify_replication_bank(bank)["verified"])
            for fixture_id in REPLICATION_CASE_IDS:
                fixture = load_fixture(bank, fixture_id)
                pointer = replication_pointer(bank, fixture_id)
                self.assertIn(fixture.final_target, pointer["active_step_verbatim"])
                self.assertFalse(pointer["semantic_host_summary"])


if __name__ == "__main__":
    unittest.main()
