"""Logged decomposition artifacts for offline planning."""

from __future__ import annotations

from .hashing import stable_id
from .records import DecompositionArtifact, DecompositionStatus, EpisodeState, ModelResponse


def create_decomposition(
    state: EpisodeState,
    response: ModelResponse,
    *,
    source_refs: list[str],
) -> DecompositionArtifact | None:
    if not response.subtargets:
        return None
    status = DecompositionStatus.ACCEPTED if response.operator_confirmed else DecompositionStatus.PROPOSED
    payload = {
        "episode": state.episode_id,
        "objective": state.objective,
        "subtargets": response.subtargets,
        "status": status.value,
        "source_refs": source_refs,
    }
    return DecompositionArtifact(
        decomposition_id=stable_id("decomposition", payload),
        status=status,
        parent_objective=state.objective,
        subtargets=response.subtargets,
        source_refs=source_refs,
        reason="operator-confirmed decomposition" if status == DecompositionStatus.ACCEPTED else "model-proposed decomposition",
    )

