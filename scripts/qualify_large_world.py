from __future__ import annotations

import json
import tempfile
from pathlib import Path
from typing import Any

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict
from working_set_exp.large_world import (
    CASE_IDS, CONDITIONS, PHASE_IDS, READ_MODE, SEEDS, case_definitions, hidden_grade, load_fixture,
    run_branch, run_shared_prefix, verify_bank, verify_package,
)
from working_set_exp.recurrent_pressure import verify_closure
from working_set_exp.request import render_reasoning_prompt
from working_set_exp.runtime import CallOutcome, PHYSICAL_CONTEXT, PreparedCall, endpoint_request, guard, load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "012_large_world_recurrent_continuity"


class ScriptedActor:
    def __init__(self, profile: Any, fixture: Any, phase_id: str, patch: dict[str, str]):
        self.profile = profile
        self.fixture = fixture
        self.phase_id = phase_id
        self.patch = patch
        self.step = 0
        self.prepared: PreparedCall | None = None
        self.request: dict[str, Any] | None = None

    def _actions(self, request: dict[str, Any]) -> list[dict[str, Any] | str]:
        phase = self.fixture.phases[self.phase_id]
        rows: list[dict[str, Any] | str] = []
        if self.phase_id == "A":
            rows.append({"action": "begin"})
            rows.extend({"action": "read", "path": path, "start_line": 1} for path in phase.required)
            rows.append({"action": "read", "path": phase.target, "start_line": 1})
        elif self.fixture.family == "large_world_evolving_source":
            rows.append({"action": "p0_page", "path": "policies", "offset": 0})
            rows.append({"action": "read", "path": "policies/current.py", "start_line": 1})
            if phase.target != "policies/current.py":
                rows.append({"action": "read", "path": phase.target, "start_line": 1})
        else:
            rows.append("reopen_current_probe")
            rows.append({"action": "read", "path": phase.target, "start_line": 1})
        rows.append("patch")
        rows.extend({"action": "read", "path": path, "start_line": 1} for path in phase.required)
        rows.append({"action": "check", "check_id": "prefork" if self.phase_id == "A" else "public", "expected_candidate_id": "CURRENT"})
        if phase.probe_id:
            rows.append({"action": "probe", "probe_id": phase.probe_id})
        rows.append({"action": "submit" if self.phase_id == "D" else "fork_ready", "expected_candidate_id": "CURRENT"})
        return rows

    def _resolve(self, item: dict[str, Any] | str, request: dict[str, Any]) -> dict[str, Any]:
        if item == "reopen_current_probe":
            handle = next(
                row["handle"] for row in reversed(request["observation_directory"]["entries"])
                if row["action"] == "probe" and row["candidate_id"] == request["candidate_id"]
            )
            return {"action": "reopen_observation", "handle": handle}
        if item == "patch":
            target = self.patch["path"]
            latest = next(
                pair["result"] for pair in reversed(request["history"])
                if pair["response"].get("action") == "read" and pair["response"].get("path") == target
            )
            return {
                "action": "patch", "path": target, "old": self.patch["old"], "new": self.patch["new"],
                "expected_candidate_id": request["candidate_id"], "expected_file_sha256": latest["file_sha256"],
            }
        result = dict(item)
        if result.get("expected_candidate_id") == "CURRENT":
            result["expected_candidate_id"] = request["candidate_id"]
        return result

    def prepare(self, request: bytes, *, stage: str, probe_id: str | None, call_id: str, active_total_ceiling: int) -> PreparedCall:
        admission = guard(self.profile, request, active_total_ceiling=active_total_ceiling, reasoning_enabled=True)
        rendered = render_reasoning_prompt(request, enabled=True)
        body = endpoint_request(
            self.profile, request, stage=stage, probe_id=probe_id, seed=SEEDS[0], reasoning_enabled=True,
            read_mode=READ_MODE, hierarchical_p0=True,
        )
        self.request = load_json_strict(request)
        self.prepared = PreparedCall(call_id, body, rendered, admission["offline_prompt_tokens"], active_total_ceiling, admission["authorized"], admission)
        return self.prepared

    def invoke(self, prepared: PreparedCall) -> CallOutcome:
        assert self.request is not None
        actions = self._actions(self.request)
        action = self._resolve(actions[self.step], self.request)
        self.step += 1
        assistant = canonical_json_bytes(action)
        raw = canonical_json_bytes({
            "id": "scripted-" + prepared.call_id,
            "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": assistant.decode()}}],
            "usage": {"prompt_tokens": prepared.offline_prompt_tokens, "completion_tokens": 1},
        })
        return CallOutcome(
            prepared.endpoint_request, prepared.rendered_prompt, raw, assistant, prepared.offline_prompt_tokens,
            prepared.offline_prompt_tokens, 1, 0, 0, "scripted-" + prepared.call_id,
        )


def main() -> None:
    profile = load_runtime(EXPERIMENT / "RUNTIME_PROFILE.json")
    definitions = {row["fixture_id"]: row for row in case_definitions()}
    rows = []
    with tempfile.TemporaryDirectory(prefix="e12-qualification-") as raw:
        root = Path(raw)
        for fixture_id in CASE_IDS:
            fixture = load_fixture(EXPERIMENT / "fresh_bank", fixture_id)
            patches = definitions[fixture_id]["patches"]
            prefix = run_shared_prefix(
                fixture, seed=SEEDS[0], actor=ScriptedActor(profile, fixture, "A", patches[0]),
                output_dir=root / fixture_id / "prefix",
            )
            if prefix.disposition != "phase_complete":
                raise RuntimeError(f"scripted prefix failed: {fixture_id} {prefix.disposition}")
            for condition in CONDITIONS:
                def factory(phase_id: str, *, _fixture=fixture, _patches=patches):
                    return ScriptedActor(profile, _fixture, phase_id, _patches[PHASE_IDS.index(phase_id)])
                summary = run_branch(
                    fixture, prefix, seed=SEEDS[0], condition=condition, actor_factory=factory,
                    output_dir=root / fixture_id / condition,
                )
                hidden = False
                if summary["submitted"]:
                    candidate_id = summary["candidate_id"]
                    snap = root / fixture_id / condition / "phase-d" / "snap" / candidate_id[:32]
                    from working_set_exp.candidate import Candidate
                    candidate = Candidate.create({p.relative_to(snap).as_posix(): p.read_bytes() for p in snap.rglob("*") if p.is_file()})
                    hidden = hidden_grade(fixture, candidate)["passed"]
                rows.append({"fixture_id": fixture_id, "condition": condition, "summary": summary, "hidden_passed": hidden})
    if sum(row["hidden_passed"] for row in rows if row["condition"] == "T25") != len(CASE_IDS):
        print(json.dumps(rows, indent=2))
        raise RuntimeError("scripted T25 large-world paths did not all hidden-pass")
    result = {
        "schema_version": "experiment-012-offline-qualification-v1",
        "bank": verify_bank(EXPERIMENT / "fresh_bank"),
        "package": verify_package(EXPERIMENT / "execution_package", bank=EXPERIMENT / "fresh_bank", profile=profile),
        "closure": verify_closure(ROOT, EXPERIMENT / "EXECUTABLE_CLOSURE.json"),
        "paths": rows, "model_calls": 0,
    }
    atomic_write(EXPERIMENT / "OFFLINE_QUALIFICATION.json", canonical_json_bytes(result))
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
