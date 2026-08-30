from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict
from working_set_exp.recurrent_pressure import verify_closure
from working_set_exp.request import render_reasoning_prompt
from working_set_exp.runtime import CallOutcome, PreparedCall, endpoint_request, guard, load_runtime
from working_set_exp.unified_receipts import CASE_IDS, CONDITIONS, READ_MODE, SEEDS, case_definitions, hidden_grade, load_fixture, run_branch, run_shared_prefix, validate_authorization, verify_bank, verify_package

ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "014_unified_active_phase_receipts"


class ScriptedActor:
    def __init__(self, profile: Any, fixture: Any, phase_id: str, patch: dict[str, str]):
        self.profile, self.fixture, self.phase_id, self.patch = profile, fixture, phase_id, patch
        self.step = 0
        self.request: dict[str, Any] | None = None

    def _actions(self) -> list[dict[str, Any] | str]:
        phase = self.fixture.phases[self.phase_id]
        if self.phase_id == "A":
            rows: list[dict[str, Any] | str] = [{"action": "begin"}]
            rows += [{"action": "read", "path": path, "start_line": 1} for path in phase.required]
            rows += [{"action": "read", "path": phase.target, "start_line": 1}, "patch",
                     {"action": "check", "check_id": "prefork", "expected_candidate_id": "CURRENT"}]
            if phase.probe_id:
                rows.append({"action": "probe", "probe_id": phase.probe_id})
            rows.append({"action": "fork_ready", "expected_candidate_id": "CURRENT"})
            return rows
        rows = []
        if self.fixture.family.endswith("closure"):
            rows += ["reopen_current_probe", {"action": "read", "path": phase.target, "start_line": 1}, "patch"]
        else:
            rows += [{"action": "check", "check_id": "public", "expected_candidate_id": "CURRENT"},
                     {"action": "read", "path": phase.target, "start_line": 1}, "patch"]
        rows += [{"action": "read", "path": path, "start_line": 1} for path in phase.required]
        rows += [{"action": "check", "check_id": "public", "expected_candidate_id": "CURRENT"},
                 {"action": "submit", "expected_candidate_id": "CURRENT"}]
        return rows

    def _resolve(self, item: dict[str, Any] | str) -> dict[str, Any]:
        assert self.request is not None
        if item == "reopen_current_probe":
            handle = next(row["handle"] for row in reversed(self.request["observation_directory"]["entries"])
                          if row["action"] == "probe" and row["candidate_id"] == self.request["candidate_id"])
            return {"action": "reopen_observation", "handle": handle}
        if item == "patch":
            target = self.patch["path"]
            result = next(pair["result"] for pair in reversed(self.request["history"])
                          if pair["response"].get("action") == "read" and pair["response"].get("path") == target)
            return {"action": "patch", "path": target, "old": self.patch["old"], "new": self.patch["new"],
                    "expected_candidate_id": self.request["candidate_id"], "expected_file_sha256": result["file_sha256"]}
        result = dict(item)
        if result.get("expected_candidate_id") == "CURRENT":
            result["expected_candidate_id"] = self.request["candidate_id"]
        return result

    def prepare(self, request: bytes, *, stage: str, probe_id: str | None, call_id: str, active_total_ceiling: int) -> PreparedCall:
        self.request = load_json_strict(request)
        admission = guard(self.profile, request, active_total_ceiling=active_total_ceiling, reasoning_enabled=True)
        body = endpoint_request(self.profile, request, stage=stage, probe_id=probe_id, seed=SEEDS[0],
                                reasoning_enabled=True, read_mode=READ_MODE, hierarchical_p0=True, result_reopen=True)
        return PreparedCall(call_id, body, render_reasoning_prompt(request, enabled=True),
                            admission["offline_prompt_tokens"], active_total_ceiling, admission["authorized"], admission)

    def invoke(self, prepared: PreparedCall) -> CallOutcome:
        action = self._resolve(self._actions()[self.step]); self.step += 1
        assistant = canonical_json_bytes(action)
        raw = canonical_json_bytes({"id": "scripted-" + prepared.call_id,
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": assistant.decode()}}],
            "usage": {"prompt_tokens": prepared.offline_prompt_tokens, "completion_tokens": 1}})
        return CallOutcome(prepared.endpoint_request, prepared.rendered_prompt, raw, assistant,
                           prepared.offline_prompt_tokens, prepared.offline_prompt_tokens, 1, 0, 0,
                           "scripted-" + prepared.call_id)


def main() -> None:
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    definitions = {row["fixture_id"]: row for row in case_definitions()}
    rows = []
    with tempfile.TemporaryDirectory(prefix="e14-qualification-") as raw:
        root = Path(raw)
        for fixture_id in CASE_IDS:
            fixture = load_fixture(EXPERIMENT / "fresh_bank", fixture_id)
            patches = definitions[fixture_id]["patches"]
            prefix = run_shared_prefix(fixture, seed=SEEDS[0], actor=ScriptedActor(profile, fixture, "A", patches[0]),
                                       output_dir=root / fixture_id / "prefix")
            for condition in CONDITIONS:
                summary = run_branch(fixture, prefix, seed=SEEDS[0], condition=condition,
                                     actor=ScriptedActor(profile, fixture, "B", patches[1]),
                                     output_dir=root / fixture_id / condition)
                snap = root / fixture_id / condition / "phase-b" / "snap" / summary["candidate_id"][:32]
                candidate = Candidate.create({p.relative_to(snap).as_posix(): p.read_bytes() for p in snap.rglob("*") if p.is_file()})
                rows.append({"fixture_id": fixture_id, "condition": condition, "summary": summary,
                             "hidden_passed": hidden_grade(fixture, candidate)["passed"]})
    if not all(row["hidden_passed"] and row["summary"]["submitted"] for row in rows):
        raise RuntimeError("Experiment 014 scripted path failed")
    result = {"schema_version": "experiment-014-offline-qualification-v1",
              "bank": verify_bank(EXPERIMENT / "fresh_bank"),
              "package": verify_package(EXPERIMENT / "execution_package", bank=EXPERIMENT / "fresh_bank", profile=profile),
              "closure": verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json"),
              "authorization": validate_authorization(EXPERIMENT), "paths": rows, "model_calls": 0}
    atomic_write(EXPERIMENT / "OFFLINE_QUALIFICATION.json", canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
