from __future__ import annotations

from typing import Any

from .candidate import Candidate
from .jsonutil import canonical_json_bytes, sha256_bytes
from .p0 import build_p0


SYSTEM_PROMPT = (
    "You are the coding actor in a controlled context-reconstruction experiment. "
    "Follow the exact staged task and current request. Return one strict bare JSON action object and no prose or hidden reasoning. "
    "P0 is task-independent readable orientation, not a relevance judgment. If its contract says the repository view is incomplete, use p0_page to expand exact readable structure. Read exact current source before mutation and reacquire any absent governing fact. "
    "Observation directory rows are identities, not their exact bodies; use reopen_observation before relying on a historical dynamic result. "
    "Treat candidate and file bindings as exact. Never invent paths, handles, check IDs, or facts."
)

REASONING_DIAGNOSTIC_SYSTEM_PROMPT = (
    "You are the coding actor in a controlled context-reconstruction experiment. "
    "Follow the exact staged task and current request. Return one strict bare JSON action object in final content and no prose or wrapper. "
    "If private reasoning is enabled, keep it only in the separate reasoning channel; the final content must still be exactly one action. "
    "P0 is task-independent readable orientation, not a relevance judgment. If its contract says the repository view is incomplete, use p0_page to expand exact readable structure. Read exact current source before mutation and reacquire any absent governing fact. "
    "Observation directory rows are identities, not their exact bodies; use reopen_observation before relying on a historical dynamic result. "
    "Treat candidate and file bindings as exact. Never invent paths, handles, check IDs, or facts."
)


TOOL_CONTRACT = {
    "tree": "shallow deterministic candidate-relative directory page",
    "search": "literal case-folded current-source search",
    "read": "exact current whole-line page with non-guessing continuation",
    "patch": "one exact candidate/file-bound replacement",
    "check": "stage-bound exact check on the expected candidate",
    "probe": "stage-bound exact external runtime observation when listed",
    "fork_ready": "mechanical boundary gate after required reads and the current stage check",
    "reopen_observation": "continuation-only exact reopen by listed handle",
    "reopen_result": "exact reopen of a result body named by an active-phase receipt handle",
    "reopen_event": "exact reopen of bulky action payload fields named by a signal-bearing active-phase event",
    "submit": "continuation-only terminal candidate submission",
}


def observation_directory(rows: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "schema_version": "exact-observation-directory-v1",
        "complete_for_reopenable_dynamic_prefix_results": True,
        "semantic_previews": False,
        "ordering": "sequence_ascending",
        "entries": [
            {
                "handle": row["handle"],
                "sequence": row["sequence"],
                "action": row["action"],
                "target": row["target"],
                "candidate_id": row["candidate_id"],
                "size_bytes": row["size_bytes"],
                "sha256": row["sha256"],
                "access": "reopen_observation",
            }
            for row in rows
        ],
    }


def observation_directory_v2(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """Describe mixed-stage observations without claiming a global stage sequence."""
    return {
        "schema_version": "exact-observation-directory-v2",
        "complete_for_listed_reopenable_dynamic_results": True,
        "semantic_previews": False,
        "ordering": "capture_ordinal_ascending",
        "entries": [
            {
                "handle": row["handle"],
                "capture_ordinal": index,
                "source_stage_sequence": row["sequence"],
                "action": row["action"],
                "target": row["target"],
                "candidate_id": row["candidate_id"],
                "size_bytes": row["size_bytes"],
                "sha256": row["sha256"],
                "access": "reopen_observation",
            }
            for index, row in enumerate(rows, 1)
        ],
    }


def available_actions(stage: str, *, probe_id: str | None) -> list[str]:
    if stage == "setup":
        return ["begin"]
    if stage == "prefix":
        result = ["tree", "search", "read", "patch", "check", "fork_ready"]
        if probe_id is not None:
            result.append("probe")
        return result
    if stage == "continuation":
        return ["tree", "search", "read", "patch", "check", "reopen_observation", "submit"]
    if stage == "recurrent":
        result = ["tree", "search", "read", "patch", "check", "reopen_observation", "fork_ready"]
        if probe_id is not None:
            result.append("probe")
        return result
    raise ValueError("invalid request stage")


def build_request(
    *,
    fixture_id: str,
    task: str,
    candidate: Candidate,
    stage: str,
    visible_history: list[dict[str, Any]],
    prefix_calls_used: int,
    continuation_calls_used: int,
    probe_id: str | None,
    observations: list[dict[str, Any]],
    reconstructed: bool,
    fork_binding: dict[str, Any] | None,
    progress_pointer: dict[str, Any] | None = None,
    prefix_call_limit: int = 14,
    continuation_call_limit: int = 8,
    read_mode: str = "actor_selected_count",
    observation_directory_version: int = 1,
    acquisition_contract: bool = False,
) -> bytes:
    p0 = build_p0(candidate)
    value: dict[str, Any] = {
        "schema_version": (
            "experiment-010-acquisition-coding-request-v1"
            if acquisition_contract
            else
            "experiment-002-coding-request-v1"
            if progress_pointer is None and prefix_call_limit == 14 and continuation_call_limit == 8
            else "experiment-003-progress-pointer-coding-request-v1"
        ),
        "fixture_id": fixture_id,
        "stage": stage,
        "task": task,
        "candidate_id": candidate.candidate_id,
        "current_p0": p0,
        "p0_contract": {
            "task_independent": True,
            "semantic_ranking": False,
            "exact_source_required_before_mutation": True,
        },
        "history": visible_history,
        "history_contract": (
            "fresh_context_exact_task_current_world_latest_fork_result_only"
            if reconstructed
            else "exact_append_only_chronology"
        ),
        "older_chronology_present": not reconstructed,
        "invocation_budget": {
            "prefix": {"used": prefix_calls_used, "limit": prefix_call_limit},
            "continuation": {"used": continuation_calls_used, "limit": continuation_call_limit},
        },
        "available_check_ids": ["prefork"] if stage == "prefix" else (["public"] if stage == "continuation" else []),
        "available_probe_ids": [probe_id] if stage == "prefix" and probe_id else [],
        "available_actions": available_actions(stage, probe_id=probe_id),
        "tool_contract": {key: TOOL_CONTRACT[key] for key in available_actions(stage, probe_id=probe_id) if key != "begin"},
        "observation_directory": (
            (observation_directory_v2(observations) if observation_directory_version == 2 else observation_directory(observations))
            if stage == "continuation" else None
        ),
        "fork_binding": fork_binding,
    }
    if progress_pointer is not None:
        value["progress_pointer"] = progress_pointer
    if acquisition_contract and "read" in value["available_actions"]:
        value["tool_contract"]["read"] = (
            "exact current whole-line page with actor-selected count and non-guessing continuation"
            if read_mode == "actor_selected_count"
            else "largest exact current whole-line page that fits the frozen result bound, with non-guessing continuation"
        )
        value["read_paging_mode"] = read_mode
    if reconstructed:
        value["reconstruction_notice"] = (
            "Older exact chronology is externally custodied but absent from this active context. "
            "Use current P0/source tools or the complete observation directory to reacquire any governing fact before action."
        )
    return canonical_json_bytes(value)


def render_prompt(request: bytes) -> bytes:
    user = request.decode("utf-8").strip()
    return (
        "<|im_start|>system\n"
        + SYSTEM_PROMPT
        + "<|im_end|>\n<|im_start|>user\n"
        + user
        + "<|im_end|>\n<|im_start|>assistant\n<think>\n\n</think>\n\n"
    ).encode("utf-8")


def render_reasoning_prompt(request: bytes, *, enabled: bool) -> bytes:
    user = request.decode("utf-8").strip()
    reasoning_instruction = (
        "Reasoning effort is set to low. Keep your thinking brief and focused, moving directly to the conclusion without unnecessary elaboration.\n\n"
        if enabled
        else ""
    )
    assistant_prefix = "<think>\n" if enabled else "<think>\n\n</think>\n\n"
    return (
        "<|im_start|>system\n"
        + reasoning_instruction
        + REASONING_DIAGNOSTIC_SYSTEM_PROMPT
        + "<|im_end|>\n<|im_start|>user\n"
        + user
        + "<|im_end|>\n<|im_start|>assistant\n"
        + assistant_prefix
    ).encode("utf-8")


def fork_binding(
    *,
    fixture_id: str,
    seed: int,
    task: str,
    candidate: Candidate,
    prefix_history: list[dict[str, Any]],
    observations: list[dict[str, Any]],
    last_record_sha256: str,
) -> dict[str, Any]:
    return {
        "schema_version": "experiment-002-exact-fork-binding-v1",
        "fixture_id": fixture_id,
        "seed": seed,
        "task_sha256": sha256_bytes(task.encode("utf-8")),
        "candidate_id": candidate.candidate_id,
        "candidate_manifest_sha256": sha256_bytes(
            canonical_json_bytes(
                [{"path": path, "sha256": sha256_bytes(data)} for path, data in candidate.files]
            )
        ),
        "p0_sha256": sha256_bytes(canonical_json_bytes(build_p0(candidate))),
        "prefix_history_sha256": sha256_bytes(canonical_json_bytes(prefix_history)),
        "observation_directory_sha256": sha256_bytes(canonical_json_bytes(observation_directory(observations))),
        "prefix_last_record_sha256": last_record_sha256,
        "pending_stage": "continuation",
    }
