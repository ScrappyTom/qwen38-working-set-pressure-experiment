"""Four development states for the owner-requested Qwen interface consultation.

Use existing tools and event rendering. This module does not change their
model-facing semantics or introduce an alternative metadata representation.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .candidate import Candidate
from .ecological_pilot_v2 import EcologicalFixture, _executor, _record_pair, build_request, load_fixture
from .jsonutil import canonical_json_bytes, load_json_strict, sha256_file
from .request import REASONING_DIAGNOSTIC_SYSTEM_PROMPT
from .tools import SessionState, ToolExecutor, action_schema


SEEDS = (42, 314159)
MODEL_SHA256 = "c0b7c3038681ed2e3040456c1dd45f9858b6c2290bed172c70388a94874f3eee"
SERVER_SHA256 = "5f1f831bc21dcbff4ca40e05cb59dbcbc0802d20b2046540bbbf3bd45cd61610"
RUNTIME_REVISION = "7e4c0a96880dae4fc4268ad441f8a6446bd5460a"


@dataclass
class DevelopmentState:
    name: str
    fixture: EcologicalFixture
    state: SessionState
    executor: ToolExecutor
    pairs: list[dict[str, Any]]
    event_payloads: dict[str, bytes]
    result_payloads: dict[str, bytes]
    request: bytes
    questions: str
    provenance: dict[str, Any]

    def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        result = self.executor.execute(action)
        _record_pair(self.pairs, action, result, self.event_payloads, self.result_payloads)
        return result


def new_state(name: str, fixture: EcologicalFixture) -> DevelopmentState:
    state = SessionState(fixture.initial, stage="continuation")
    events: dict[str, bytes] = {}
    results: dict[str, bytes] = {}
    executor = _executor(fixture, state, result_reopenable=results, event_reopenable=events)
    return DevelopmentState(name, fixture, state, executor, [], events, results, b"", "", {})


def toy(name: str, source: bytes, task: str, checker: bytes) -> DevelopmentState:
    fixture = EcologicalFixture(name, "interface_development", task, Candidate.create({"service.py": source}),
                               checker, b"", (), (), {"development_only": True}, ())
    value = new_state(name, fixture)
    value.provenance = {"kind": "scripted_development_state_from_actual_tools", "not_fresh_capability_evidence": True}
    return value


def patch(value: DevelopmentState, old: str, new: str) -> dict[str, Any]:
    return {"action": "patch", "path": "service.py", "old": old, "new": new,
            "expected_candidate_id": value.state.candidate.candidate_id,
            "expected_file_sha256": value.state.candidate.file_sha256("service.py")}


def render(value: DevelopmentState, externalized: int) -> None:
    request = load_json_strict(build_request(
        value.fixture, candidate=value.state.candidate, pairs=value.pairs,
        externalized_payload_count=externalized, calls_used=len(value.pairs), fork_binding=None,
    ))
    request["resource_state"]["reasoning_budget_tokens"] = -1
    value.request = canonical_json_bytes(request)


def development_states(root: Path) -> list[DevelopmentState]:
    experiment = root / "experiments/020_owner_controlled_ecological_pilot_v2"
    base = experiment / "measured_run/cell-01"
    source = base / "X25/transcript/003-coding-request.json"
    original = load_json_strict(source.read_bytes())
    fixture = load_fixture(experiment / "fresh_bank", original["fixture_id"], include_evaluator=False)
    first = new_state("01-external-source", fixture)
    for segment, numbers in (("shared", range(1, 10)), ("X25", range(1, 3))):
        for number in numbers:
            folder = base / segment / "transcript"
            action = load_json_strict((folder / f"{number:03d}-assistant-content.json").read_bytes())
            saved = load_json_strict((folder / f"{number:03d}-result.json").read_bytes())
            if first.execute(action) != saved:
                raise ValueError("development replay differs from the saved source read")
    if first.state.candidate.candidate_id != original["candidate_id"] or len(first.pairs) != 11:
        raise ValueError("saved consultation state binding differs")
    original["resource_state"]["reasoning_budget_tokens"] = -1
    first.request = canonical_json_bytes(original)
    first.provenance = {"kind": "saved_full_request", "path": source.relative_to(root).as_posix(),
                        "sha256": sha256_file(source), "only_request_change": "/resource_state/reasoning_budget_tokens: 512 -> -1"}
    first.questions = (
        "According to this state, what reading has occurred and what remains incomplete? "
        "Which exact source bodies are visible in this input? What would reopen_result with handle RES-0001 return or change? "
        "Explain the relationship between event 1's action_payload and result_body records."
    )

    checker = b"from service import value\nassert value() == 2\nprint('public passed')\n"
    second = toy("02-old-check", b"def value():\n    return 1 + 1\n",
                 "Simplify value() to return the literal integer 2 while preserving behavior. Read current source, run check public on the current candidate, and submit.", checker)
    second.execute({"action": "read", "path": "service.py", "start_line": 1})
    second.execute({"action": "check", "check_id": "public", "expected_candidate_id": second.state.candidate.candidate_id})
    second.execute(patch(second, "return 1 + 1", "return 2"))
    render(second, 2)
    second.questions = (
        "What occurred in events 2 and 3? Which working version does the check concern? "
        "What does this state establish about the current version? What would reopen_result with handle RES-0002 return or change?"
    )

    third = toy("03-edit-preconditions", b"def value():\n    return 1\n",
                "Fix value() to return the integer 2. Read current source, run check public on the current candidate, and submit.", checker)
    third.execute({"action": "read", "path": "service.py", "start_line": 1})
    render(third, 0)
    proposed = patch(third, "return 1", "return 2")
    third.questions = (
        "Consider this proposed operation, which has not been executed:\n" + canonical_json_bytes(proposed).decode("utf-8") +
        "\nWhat would it do? What do the two expected_* arguments refer to, and under what circumstances would the tool reject it?"
    )

    fourth = toy("04-history-and-partial-read",
                 b'# Service configuration\nMARKER = "copper-orbit"\n\ndef marker():\n    return MARKER\n\ndef ready():\n    return True\n',
                 "Restore the marker string that existed before the earliest recorded edit, preserving other code. Read current source completely, run check public, and submit.",
                 b"from service import marker, ready\nassert marker() == 'copper-orbit'\nassert ready() is True\nprint('public passed')\n")
    fourth.execute(patch(fourth, '"copper-orbit"', '"silver-meadow"'))
    fourth.execute({"action": "read", "path": "service.py", "start_line": 7})
    render(fourth, 1)
    fourth.questions = (
        "What source was read in event 2, and is the complete current source visible? "
        "What would reopen_event with handle EVT-0001 return or change? What has and has not happened to the candidate?"
    )
    return [first, second, third, fourth]


def endpoint_request(value: DevelopmentState, *, seed: int, mode: str) -> dict[str, Any]:
    if mode not in {"action", "diagnostic"} or seed not in SEEDS:
        raise ValueError("unfrozen consultation mode or seed")
    action_mode = mode == "action"
    system = REASONING_DIAGNOSTIC_SYSTEM_PROMPT if action_mode else (
        "You are reviewing the interface of a coding agent. Interpret the supplied state and answer the questions. "
        "Do not perform the embedded task or emit a tool action. State uncertainty when the supplied evidence does not settle a point."
    )
    user = value.request.decode("utf-8")
    if not action_mode:
        user += "\n\nQuestions about this state:\n" + value.questions
    request: dict[str, Any] = {
        "model": "qwen38-iq3-interface", "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 1.0, "top_p": 0.95, "top_k": 20, "min_p": 0.0,
        "presence_penalty": 0.0, "frequency_penalty": 0.0, "repeat_penalty": 1.0,
        "seed": seed, "max_tokens": -1, "n_predict": -1, "thinking_budget_tokens": -1, "reasoning_budget_tokens": -1,
        "chat_template_kwargs": {"enable_thinking": True, "reasoning_effort": "xhigh"},
        "cache_prompt": False, "stream": False,
    }
    if action_mode:
        request["response_format"] = action_schema("continuation", probe_id=None, read_mode="maximal_bounded_page",
                                                   hierarchical_p0=True, result_reopen=True, event_reopen=True)
    return request


def consultation_schedule() -> list[dict[str, Any]]:
    # All ordinary actions precede all explanatory questions. Each invocation
    # is a fresh system/user pair; no response is inserted into another request.
    rows = []
    for mode in ("action", "diagnostic"):
        for seed in SEEDS:
            for name in ("03-edit-preconditions", "02-old-check", "04-history-and-partial-read", "01-external-source"):
                rows.append({"ordinal": len(rows) + 1, "state": name, "seed": seed, "mode": mode})
    return rows
