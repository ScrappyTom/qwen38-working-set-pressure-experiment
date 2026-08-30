from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Protocol

from .candidate import Candidate
from .custody import ArtifactStore, RecordLog, verify_records
from .fixture import Fixture
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, utc_now
from .request import build_request, fork_binding
from .runtime import (
    C50_PROMPT_CEILING,
    CapacityStopped,
    OUTPUT_TOKENS,
    PHYSICAL_CONTEXT,
    RUNTIME_ALLOWANCE,
    T25_TOTAL_CEILING,
    CallOutcome,
    PreparedCall,
    RuntimeProfile,
    TransportStopped,
    endpoint_request,
    guard,
    render_prompt,
    tokenizer_count,
)
from .tools import SessionState, ToolExecutor, strict_action


PREFIX_CALL_LIMIT = 14
BRANCH_CALL_LIMIT = 8


class Actor(Protocol):
    def prepare(self, request: bytes, *, stage: str, probe_id: str | None, call_id: str, active_total_ceiling: int) -> PreparedCall: ...
    def invoke(self, prepared: PreparedCall) -> CallOutcome: ...


class ScriptedActor:
    def __init__(
        self,
        profile: RuntimeProfile,
        seed: int,
        policy: Callable[[dict[str, Any]], dict[str, Any]],
        *,
        read_mode: str = "actor_selected_count",
    ):
        self.profile = profile
        self.seed = seed
        self.policy = policy
        self.requests: dict[str, bytes] = {}
        self.call_ids: set[str] = set()
        self.read_mode = read_mode

    def prepare(self, request: bytes, *, stage: str, probe_id: str | None, call_id: str, active_total_ceiling: int) -> PreparedCall:
        if call_id in self.call_ids:
            raise RuntimeError("scripted call ID reused")
        self.call_ids.add(call_id)
        admission = guard(self.profile, request, active_total_ceiling=active_total_ceiling)
        self.requests[call_id] = request
        return PreparedCall(
            call_id=call_id,
            endpoint_request=endpoint_request(
                self.profile,
                request,
                stage=stage,
                probe_id=probe_id,
                seed=self.seed,
                read_mode=self.read_mode,
            ),
            rendered_prompt=render_prompt(request),
            offline_prompt_tokens=admission["offline_prompt_tokens"],
            active_total_ceiling=active_total_ceiling,
            authorized=admission["authorized"],
            admission=admission,
        )

    def invoke(self, prepared: PreparedCall) -> CallOutcome:
        request = load_json_strict(self.requests[prepared.call_id])
        action = self.policy(request)
        assistant = canonical_json_bytes(action)
        raw = canonical_json_bytes(
            {
                "id": "scripted-" + prepared.call_id,
                "choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": assistant.decode("utf-8")}}],
                "usage": {
                    "prompt_tokens": prepared.offline_prompt_tokens,
                    "completion_tokens": max(1, len(assistant) // 4),
                },
            }
        )
        return CallOutcome(
            endpoint_request=prepared.endpoint_request,
            rendered_prompt=prepared.rendered_prompt,
            raw_endpoint_response=raw,
            assistant_content=assistant,
            offline_prompt_tokens=prepared.offline_prompt_tokens,
            server_prompt_tokens=prepared.offline_prompt_tokens,
            completion_tokens=max(1, len(assistant) // 4),
            accounting_delta=0,
            elapsed_ms=0,
            response_id="scripted-" + prepared.call_id,
        )


@dataclass
class PrefixOutcome:
    state: SessionState
    history: list[dict[str, Any]]
    observations: list[dict[str, Any]]
    reopenable: dict[str, bytes]
    binding: dict[str, Any]
    calls: int
    output_dir: Path


def _save_candidate(store: ArtifactStore, candidate: Candidate, prefix: str) -> list[dict[str, Any]]:
    artifacts: list[dict[str, Any]] = []
    for path, data in candidate.files:
        relative = f"{prefix}/{path}"
        target = store.root / Path(*relative.split("/"))
        if target.exists():
            # Candidate snapshots are content-addressed. Returning to a prior
            # exact candidate is a valid state transition, so an already
            # custodied identical snapshot is reusable. A byte mismatch at
            # the same address remains an integrity failure.
            if not target.is_file() or target.read_bytes() != data:
                raise FileExistsError(f"candidate snapshot identity collision: {relative}")
            artifacts.append({"path": relative, "size_bytes": len(data), "sha256": sha256_bytes(data)})
        else:
            artifacts.append(store.put(relative, data))
    return artifacts


def _snapshot_prefix(candidate: Candidate) -> str:
    # The complete candidate identity remains in the record payload. A 128-bit
    # directory component keeps Windows custody paths below the legacy limit.
    return f"snap/{candidate.candidate_id[:32]}"


def _dynamic_observation_target(action: dict[str, Any]) -> str:
    if action["action"] == "check":
        return action["check_id"]
    if action["action"] == "probe":
        return action["probe_id"]
    return "continuation_boundary"


def _execute_call(
    *,
    actor: Actor,
    request: bytes,
    stage: str,
    probe_id: str | None,
    call_id: str,
    active_total_ceiling: int,
    executor: ToolExecutor,
    store: ArtifactStore,
    log: RecordLog,
    artifact_prefix: str,
) -> tuple[dict[str, Any], dict[str, Any], CallOutcome]:
    prepared = actor.prepare(
        request,
        stage=stage,
        probe_id=probe_id,
        call_id=call_id,
        active_total_ceiling=active_total_ceiling,
    )
    prepared_artifacts = [
        store.put(f"{artifact_prefix}-coding-request.json", request),
        store.put(f"{artifact_prefix}-endpoint-request.json", prepared.endpoint_request),
        store.put(f"{artifact_prefix}-rendered-prompt.txt", prepared.rendered_prompt),
    ]
    log.append(
        "external_call_prepared",
        {
            "call_id": call_id,
            "stage": stage,
            "offline_prompt_tokens": prepared.offline_prompt_tokens,
            "active_total_ceiling": active_total_ceiling,
        },
        prepared_artifacts,
    )
    if not prepared.authorized:
        log.append(
            "capacity_stopped",
            {"call_id": call_id, "stage": stage, "admission": prepared.admission, "http_calls": 0},
            [],
        )
        raise CapacityStopped(prepared.admission)
    try:
        outcome = actor.invoke(prepared)
    except TransportStopped as exc:
        artifacts: list[dict[str, Any]] = []
        if exc.response_body is not None:
            artifacts.append(store.put(f"{artifact_prefix}-endpoint-error-response.bin", exc.response_body))
        log.append(
            "external_call_stopped",
            {
                "call_id": call_id,
                "stage": stage,
                "http_status": exc.http_status,
                "error_type": type(exc).__name__,
                "error": str(exc),
            },
            artifacts,
        )
        raise
    response_artifacts = [
        store.put(f"{artifact_prefix}-endpoint-response.json", outcome.raw_endpoint_response),
        store.put(f"{artifact_prefix}-assistant-content.json", outcome.assistant_content),
    ]
    if outcome.reasoning_content:
        response_artifacts.append(
            store.put(f"{artifact_prefix}-assistant-reasoning.txt", outcome.reasoning_content)
        )
    try:
        action = strict_action(outcome.assistant_content)
        result = executor.execute(action)
    except Exception as exc:
        action = {"unparsed_response_sha256": sha256_bytes(outcome.assistant_content)}
        result = {"accepted": False, "error_code": "protocol_rejected", "detail": str(exc)}
    result_bytes = canonical_json_bytes(result)
    result_artifact = store.put(f"{artifact_prefix}-result.json", result_bytes)
    artifacts = [*response_artifacts, result_artifact]
    if action.get("action") == "patch" and result.get("accepted"):
        artifacts.extend(_save_candidate(store, executor.state.candidate, _snapshot_prefix(executor.state.candidate)))
    action_payload = {
        "call_id": call_id,
        "action": action,
        "result": result,
        "candidate_id": executor.state.candidate.candidate_id,
        "offline_prompt_tokens": outcome.offline_prompt_tokens,
        "server_reported_prompt_tokens": outcome.server_prompt_tokens,
        "server_usage_semantics": "may_exclude_exact_cached_prefix_tokens",
        "completion_tokens": outcome.completion_tokens,
        "accounting_delta": outcome.accounting_delta,
        "elapsed_ms": outcome.elapsed_ms,
        "response_id": outcome.response_id,
    }
    if outcome.reasoning_content:
        action_payload.update(
            {
                "reasoning_content_bytes": len(outcome.reasoning_content),
                "reasoning_content_sha256": sha256_bytes(outcome.reasoning_content),
            }
        )
    log.append("action_result", action_payload, artifacts)
    return action, result, outcome


def run_prefix(
    fixture: Fixture,
    *,
    seed: int,
    actor: Actor,
    output_dir: Path,
    profile: RuntimeProfile,
    fixed_record_timestamp: str | None = None,
    prefix_call_limit: int = PREFIX_CALL_LIMIT,
    continuation_call_limit: int = BRANCH_CALL_LIMIT,
    one_shot_probe: bool = False,
    reasoning_enabled: bool = False,
    read_mode: str = "actor_selected_count",
    acquisition_contract: bool = False,
    require_pressure_eligible: bool = True,
) -> PrefixOutcome:
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    store = ArtifactStore(output_dir)
    run_id = f"{fixture.fixture_id}-seed-{seed}-prefix"
    log = RecordLog(output_dir / "records.jsonl", run_id, fixed_created_at_utc=fixed_record_timestamp)
    state = SessionState(fixture.initial)
    executor = ToolExecutor(
        state,
        required_full_reads=fixture.required_full_reads,
        prefork_checker=fixture.prefork_checker,
        public_checker=fixture.public_checker,
        final_target=fixture.final_target,
        probe_id=fixture.probe_id,
        probe_body=fixture.probe_body,
        read_mode=read_mode,
    )
    history: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    reopenable: dict[str, bytes] = {}
    log.append(
        "prefix_started",
        {"fixture_id": fixture.fixture_id, "seed": seed, "candidate_id": state.candidate.candidate_id},
        _save_candidate(store, state.candidate, _snapshot_prefix(state.candidate)),
    )
    calls = 0
    http_completion_calls = 0
    while calls < prefix_call_limit and not state.fork_ready:
        calls += 1
        stage = "setup" if calls == 1 else "prefix"
        visible_probe_id = None if one_shot_probe and state.probe_done else fixture.probe_id
        request = build_request(
            fixture_id=fixture.fixture_id,
            task=fixture.task,
            candidate=state.candidate,
            stage=stage,
            visible_history=history,
            prefix_calls_used=calls - 1,
            continuation_calls_used=0,
            probe_id=visible_probe_id,
            observations=observations,
            reconstructed=False,
            fork_binding=None,
            prefix_call_limit=prefix_call_limit,
            continuation_call_limit=continuation_call_limit,
            read_mode=read_mode,
            acquisition_contract=acquisition_contract,
        )
        call_id = f"{fixture.fixture_id}-S{seed}-P{calls:02d}"
        action, result, _ = _execute_call(
            actor=actor,
            request=request,
            stage=stage,
            probe_id=visible_probe_id,
            call_id=call_id,
            active_total_ceiling=PHYSICAL_CONTEXT,
            executor=executor,
            store=store,
            log=log,
            artifact_prefix=f"transcript/{calls:03d}",
        )
        http_completion_calls += 1
        history.append({"response": action, "result": result})
        if action.get("action") in {"probe", "check", "fork_ready"} and result.get("accepted"):
            body = canonical_json_bytes(result)
            handle = f"OBS-{len(observations) + 1:04d}"
            reopenable[handle] = body
            observations.append(
                {
                    "handle": handle,
                    "sequence": calls,
                    "action": action["action"],
                    "target": _dynamic_observation_target(action),
                    "candidate_id": result.get("checked_candidate_id", result.get("candidate_id", state.candidate.candidate_id)),
                    "size_bytes": len(body),
                    "sha256": sha256_bytes(body),
                }
            )
    if not state.fork_ready:
        disposition = "prefix_incomplete"
        binding = {}
    else:
        binding = fork_binding(
            fixture_id=fixture.fixture_id,
            seed=seed,
            task=fixture.task,
            candidate=state.candidate,
            prefix_history=history,
            observations=observations,
            last_record_sha256=log.previous or "",
        )
        prospective = build_request(
            fixture_id=fixture.fixture_id,
            task=fixture.task,
            candidate=state.candidate,
            stage="continuation",
            visible_history=history,
            prefix_calls_used=calls,
            continuation_calls_used=0,
            probe_id=fixture.probe_id,
            observations=observations,
            reconstructed=False,
            fork_binding=binding,
            prefix_call_limit=prefix_call_limit,
            continuation_call_limit=continuation_call_limit,
            read_mode=read_mode,
            acquisition_contract=acquisition_contract,
        )
        pressure = guard(
            profile,
            prospective,
            active_total_ceiling=T25_TOTAL_CEILING,
            reasoning_enabled=reasoning_enabled,
        )
        c50 = guard(
            profile,
            prospective,
            active_total_ceiling=PHYSICAL_CONTEXT,
            reasoning_enabled=reasoning_enabled,
        )
        if pressure["authorized"] or not c50["authorized"]:
            disposition = "pressure_boundary_not_eligible"
        else:
            disposition = "fork_eligible"
        atomic_write(
            output_dir / "A25_CAPACITY_REFERENCE.json",
            canonical_json_bytes(
                {
                    "schema_version": "experiment-002-a25-reference-v1",
                    "http_calls": 0,
                    "prospective_request_sha256": sha256_bytes(prospective),
                    "t25_guard": pressure,
                    "c50_guard": c50,
                    "disposition": "stopped_before_http" if not pressure["authorized"] else "unexpectedly_admitted",
                }
            ),
        )
    stopped = log.append(
        "prefix_stopped",
        {
            "disposition": disposition,
            "calls": calls,
            "prepared_invocations": calls,
            "http_completion_calls": http_completion_calls,
            "candidate_id": state.candidate.candidate_id,
            "fork_binding": binding,
        },
        [],
    )
    summary = {
        "schema_version": "experiment-002-prefix-summary-v1",
        "run_id": run_id,
        "fixture_id": fixture.fixture_id,
        "seed": seed,
        "disposition": disposition,
        "calls": calls,
        "prepared_invocations": calls,
        "http_completion_calls": http_completion_calls,
        "candidate_id": state.candidate.candidate_id,
        "history_sha256": sha256_bytes(canonical_json_bytes(history)),
        "observation_count": len(observations),
        "fork_binding": binding,
        "last_record_sha256": stopped["record_sha256"],
    }
    atomic_write(output_dir / "SUMMARY.json", canonical_json_bytes(summary))
    if require_pressure_eligible and disposition != "fork_eligible":
        raise RuntimeError(f"prefix did not reach an eligible fork: {disposition}")
    return PrefixOutcome(state, history, observations, reopenable, binding, calls, output_dir)


def run_branch(
    fixture: Fixture,
    prefix: PrefixOutcome,
    *,
    condition: str,
    seed: int,
    actor: Actor,
    output_dir: Path,
    fixed_record_timestamp: str | None = None,
    progress_pointer: dict[str, Any] | None = None,
    prefix_call_limit: int = PREFIX_CALL_LIMIT,
    branch_call_limit: int = BRANCH_CALL_LIMIT,
) -> dict[str, Any]:
    if condition not in {"C50", "T25", "T25-M", "T25-P", "R0", "R1"}:
        raise ValueError("invalid branch condition")
    if output_dir.exists():
        raise FileExistsError(output_dir)
    output_dir.mkdir(parents=True)
    store = ArtifactStore(output_dir)
    log = RecordLog(
        output_dir / "records.jsonl",
        f"{fixture.fixture_id}-seed-{seed}-{condition}",
        fixed_created_at_utc=fixed_record_timestamp,
    )
    state = prefix.state.clone_for_branch()
    executor = ToolExecutor(
        state,
        required_full_reads=fixture.required_full_reads,
        prefork_checker=fixture.prefork_checker,
        public_checker=fixture.public_checker,
        final_target=fixture.final_target,
        probe_id=fixture.probe_id,
        probe_body=fixture.probe_body,
        reopenable=prefix.reopenable,
    )
    latest = prefix.history[-1]
    reconstructed = condition != "C50"
    base_history = list(prefix.history) if condition == "C50" else [latest]
    branch_history: list[dict[str, Any]] = []
    log.append(
        "branch_started",
        {
            "condition": condition,
            "seed": seed,
            "fork_binding": prefix.binding,
            "candidate_id": state.candidate.candidate_id,
            "prefix_summary_sha256": sha256_bytes((prefix.output_dir / "SUMMARY.json").read_bytes()),
        },
        _save_candidate(store, state.candidate, _snapshot_prefix(state.candidate)),
    )
    calls = 0
    http_completion_calls = 0
    maximum_prompt = 0
    capacity_stop: dict[str, Any] | None = None
    while calls < branch_call_limit and not state.submitted:
        calls += 1
        visible_history = [*base_history, *branch_history]
        request = build_request(
            fixture_id=fixture.fixture_id,
            task=fixture.task,
            candidate=state.candidate,
            stage="continuation",
            visible_history=visible_history,
            prefix_calls_used=prefix.calls,
            continuation_calls_used=calls - 1,
            probe_id=fixture.probe_id,
            observations=prefix.observations,
            reconstructed=reconstructed,
            fork_binding=prefix.binding,
            progress_pointer=progress_pointer,
            prefix_call_limit=prefix_call_limit,
            continuation_call_limit=branch_call_limit,
        )
        call_id = f"{fixture.fixture_id}-S{seed}-{condition}-{calls:02d}"
        try:
            action, result, outcome = _execute_call(
                actor=actor,
                request=request,
                stage="continuation",
                probe_id=fixture.probe_id,
                call_id=call_id,
                active_total_ceiling=T25_TOTAL_CEILING if reconstructed else PHYSICAL_CONTEXT,
                executor=executor,
                store=store,
                log=log,
                artifact_prefix=f"transcript/{calls:03d}",
            )
        except CapacityStopped as exc:
            capacity_stop = exc.admission
            maximum_prompt = max(maximum_prompt, exc.admission["offline_prompt_tokens"])
            break
        maximum_prompt = max(maximum_prompt, outcome.offline_prompt_tokens)
        http_completion_calls += 1
        branch_history.append({"response": action, "result": result})
    disposition = (
        "submitted"
        if state.submitted
        else "capacity_stopped_before_http"
        if capacity_stop is not None
        else "continuation_budget_exhausted"
    )
    stopped = log.append(
        "branch_stopped",
        {
            "disposition": disposition,
            "condition": condition,
            "calls": calls,
            "prepared_invocations": calls,
            "http_completion_calls": http_completion_calls,
            "candidate_id": state.candidate.candidate_id,
            "submitted": state.submitted,
            "public_check_passed": state.public_check_passed,
            "capacity_stop": capacity_stop,
        },
        [],
    )
    summary = {
        "schema_version": "experiment-002-branch-summary-v1",
        "fixture_id": fixture.fixture_id,
        "condition": condition,
        "seed": seed,
        "fork_binding": prefix.binding,
        "disposition": disposition,
        "calls": calls,
        "prepared_invocations": calls,
        "http_completion_calls": http_completion_calls,
        "candidate_id": state.candidate.candidate_id,
        "submitted": state.submitted,
        "public_check_passed": state.public_check_passed,
        "capacity_stop": capacity_stop,
        "maximum_offline_prompt_tokens": maximum_prompt,
        "branch_history_sha256": sha256_bytes(canonical_json_bytes(branch_history)),
        "last_record_sha256": stopped["record_sha256"],
    }
    atomic_write(output_dir / "SUMMARY.json", canonical_json_bytes(summary))
    return summary


def verify_run(run_dir: Path) -> dict[str, Any]:
    records = verify_records(run_dir / "records.jsonl", run_dir)
    summary = load_json_strict((run_dir / "SUMMARY.json").read_bytes())
    if records[-1]["record_sha256"] != summary["last_record_sha256"]:
        raise ValueError("summary record binding differs")
    return {"verified": True, "record_count": len(records), "disposition": summary["disposition"]}


def replay_prefix(
    fixture: Fixture,
    run_dir: Path,
    *,
    read_mode: str = "actor_selected_count",
    require_pressure_eligible: bool = True,
) -> PrefixOutcome:
    records = verify_records(run_dir / "records.jsonl", run_dir)
    summary = load_json_strict((run_dir / "SUMMARY.json").read_bytes())
    state = SessionState(fixture.initial)
    executor = ToolExecutor(
        state,
        required_full_reads=fixture.required_full_reads,
        prefork_checker=fixture.prefork_checker,
        public_checker=fixture.public_checker,
        final_target=fixture.final_target,
        probe_id=fixture.probe_id,
        probe_body=fixture.probe_body,
        read_mode=read_mode,
    )
    history: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    reopenable: dict[str, bytes] = {}
    last_action_record_sha256 = ""
    for record in records:
        if record["record_type"] != "action_result":
            continue
        action = record["payload"]["action"]
        expected = record["payload"]["result"]
        observed = executor.execute(action)
        if canonical_json_bytes(observed) != canonical_json_bytes(expected):
            raise ValueError(f"prefix replay result differs at sequence {record['sequence']}")
        if state.candidate.candidate_id != record["payload"]["candidate_id"]:
            raise ValueError("prefix replay candidate differs")
        history.append({"response": action, "result": expected})
        if action.get("action") in {"probe", "check", "fork_ready"} and expected.get("accepted"):
            body = canonical_json_bytes(expected)
            handle = f"OBS-{len(observations) + 1:04d}"
            reopenable[handle] = body
            observations.append(
                {
                    "handle": handle,
                    "sequence": len(history),
                    "action": action["action"],
                    "target": _dynamic_observation_target(action),
                    "candidate_id": expected.get(
                        "checked_candidate_id", expected.get("candidate_id", state.candidate.candidate_id)
                    ),
                    "size_bytes": len(body),
                    "sha256": sha256_bytes(body),
                }
            )
        last_action_record_sha256 = record["record_sha256"]
    if not state.fork_ready or (require_pressure_eligible and summary["disposition"] != "fork_eligible"):
        raise ValueError("prefix replay is not fork eligible")
    binding = fork_binding(
        fixture_id=fixture.fixture_id,
        seed=summary["seed"],
        task=fixture.task,
        candidate=state.candidate,
        prefix_history=history,
        observations=observations,
        last_record_sha256=last_action_record_sha256,
    )
    if canonical_json_bytes(binding) != canonical_json_bytes(summary["fork_binding"]):
        raise ValueError("prefix replay fork binding differs")
    if summary["history_sha256"] != sha256_bytes(canonical_json_bytes(history)):
        raise ValueError("prefix replay history differs")
    return PrefixOutcome(
        state=state,
        history=history,
        observations=observations,
        reopenable=reopenable,
        binding=binding,
        calls=summary["calls"],
        output_dir=run_dir,
    )


def scripted_policy(fixture: Fixture, *, condition: str) -> Callable[[dict[str, Any]], dict[str, Any]]:
    read_index = 0
    target_read = False
    final_info = False
    patched_prefork = False
    checked_prefork = False
    forked = False
    patched_final = False
    checked_final = False
    probe_done = False

    def policy(request: dict[str, Any]) -> dict[str, Any]:
        nonlocal read_index, target_read, final_info, patched_prefork, checked_prefork, forked, patched_final, checked_final, probe_done
        if request["stage"] == "setup":
            return {"action": "begin"}
        history = request["history"]
        candidate_id = request["candidate_id"]
        if request["stage"] == "prefix":
            if fixture.probe_id and not probe_done:
                probe_done = True
                return {"action": "probe", "probe_id": fixture.probe_id}
            if read_index < len(fixture.required_full_reads):
                path = fixture.required_full_reads[read_index]
                read_index += 1
                return {"action": "read", "path": path, "start_line": 1, "line_count": 500}
            if not target_read:
                target_read = True
                return {"action": "read", "path": "staging/readiness.py", "start_line": 1, "line_count": 100}
            if not patched_prefork:
                patched_prefork = True
                latest = history[-1]["result"]
                return {"action": "patch", "path": "staging/readiness.py", "old": "    return 0", "new": "    return len(AUDIT_GROUPS)", "expected_candidate_id": candidate_id, "expected_file_sha256": latest["file_sha256"]}
            if not checked_prefork:
                checked_prefork = True
                return {"action": "check", "check_id": "prefork", "expected_candidate_id": candidate_id}
            forked = True
            return {"action": "fork_ready", "expected_candidate_id": candidate_id}
        if condition == "T25" and not final_info:
            final_info = True
            if fixture.family == "source_reacquisition":
                return {"action": "read", "path": "policy/channel.py", "start_line": 1, "line_count": 500}
            handle = next(row["handle"] for row in request["observation_directory"]["entries"] if row["action"] == "probe")
            return {"action": "reopen_observation", "handle": handle}
        if not target_read or forked:
            forked = False
            target_read = True
            return {"action": "read", "path": fixture.final_target, "start_line": 1, "line_count": 100}
        if not patched_final:
            patched_final = True
            latest = history[-1]["result"]
            if fixture.family == "source_reacquisition":
                old, new = "    return name.strip().lower()", '    return "stable-" + name.strip().lower()'
            else:
                old, new = "    return name.strip().upper()", '    return "XP9:" + name.strip().upper()'
            return {"action": "patch", "path": fixture.final_target, "old": old, "new": new, "expected_candidate_id": candidate_id, "expected_file_sha256": latest["file_sha256"]}
        if not checked_final:
            checked_final = True
            return {"action": "check", "check_id": "public", "expected_candidate_id": candidate_id}
        return {"action": "submit", "expected_candidate_id": candidate_id}

    return policy
