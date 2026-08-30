"""Recursive summary graph and freshness checks."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .hashing import stable_id
from .records import AddressMap, Artifact, SummaryNode
from .summaries import build_summary


@dataclass(frozen=True)
class SummaryGraph:
    graph_id: str
    unit_summaries: list[SummaryNode]
    unit_summary_ids: list[str]
    artifact_summary_ids: list[str]
    collection_summary: SummaryNode | None
    stale_summary_ids: list[str] = field(default_factory=list)


def build_summary_graph(artifacts: dict[str, Artifact], address_maps: dict[str, AddressMap]) -> tuple[dict[str, SummaryNode], SummaryGraph]:
    summaries = {artifact_id: build_summary(artifact, address_maps[artifact_id]) for artifact_id, artifact in artifacts.items()}
    unit_summaries = _build_unit_summaries(address_maps)
    collection = _build_collection_summary(summaries)
    graph = SummaryGraph(
        graph_id=stable_id(
            "summary_graph",
            {
                "unit_summaries": sorted(summary.summary_id for summary in unit_summaries),
                "summaries": sorted(summary.summary_id for summary in summaries.values()),
                "collection": collection.summary_id if collection else None,
            },
        ),
        unit_summaries=unit_summaries,
        unit_summary_ids=[summary.summary_id for summary in unit_summaries],
        artifact_summary_ids=[summary.summary_id for summary in summaries.values()],
        collection_summary=collection,
    )
    return summaries, graph


def stale_summaries(summaries: dict[str, SummaryNode], address_maps: dict[str, AddressMap]) -> list[str]:
    stale: list[str] = []
    for artifact_id, summary in summaries.items():
        address_map = address_maps.get(artifact_id)
        if address_map is None:
            stale.append(summary.summary_id)
            continue
        current_hashes = sorted(unit.content_hash for unit in address_map.units.values())
        summary_hashes = sorted(summary.input_hashes)
        if current_hashes != summary_hashes:
            stale.append(summary.summary_id)
    return stale


def summary_graph_status(
    summaries: dict[str, SummaryNode],
    graph: SummaryGraph,
    address_maps: dict[str, AddressMap],
) -> dict[str, Any]:
    """Return deterministic freshness information for artifact and collection summaries."""

    stale_artifact_summary_ids = stale_summaries(summaries, address_maps)
    current_summary_ids = sorted(summary.summary_id for summary in summaries.values())
    graph_summary_ids = sorted(graph.artifact_summary_ids)
    collection_stale = bool(stale_artifact_summary_ids) or current_summary_ids != graph_summary_ids
    if graph.collection_summary is not None:
        collection_stale = collection_stale or sorted(graph.collection_summary.input_hashes) != graph_summary_ids
    missing_artifact_ids = sorted(artifact_id for artifact_id in summaries if artifact_id not in address_maps)
    return {
        "graph_id": graph.graph_id,
        "unit_summary_count": len(graph.unit_summary_ids),
        "artifact_summary_count": len(summaries),
        "stale_artifact_summary_ids": stale_artifact_summary_ids,
        "collection_summary_id": graph.collection_summary.summary_id if graph.collection_summary else None,
        "collection_stale": collection_stale,
        "missing_artifact_ids": missing_artifact_ids,
    }


def _build_unit_summaries(address_maps: dict[str, AddressMap]) -> list[SummaryNode]:
    unit_summaries: list[SummaryNode] = []
    for artifact_id in sorted(address_maps):
        address_map = address_maps[artifact_id]
        for unit in sorted(address_map.units.values(), key=lambda item: item.address):
            if unit.parent_address is None:
                continue
            axes = {
                "identity": f"{unit.unit_kind} {unit.address}",
                "purpose": "unit-level awareness summary",
                "claims_facts": [],
                "interfaces_dependencies": [],
                "constraints": [],
                "current_state": f"unit hash {unit.content_hash[:12]} lines {unit.start_line}-{unit.end_line}",
                "risks_unknowns": ["unit summary is awareness only; exact descent required for claims or edits"],
                "available_exact_descents": [unit.exact_ref],
                "title": unit.title,
            }
            unit_summaries.append(
                SummaryNode(
                    summary_id=stable_id(
                        "summary",
                        {
                            "policy": "unit_summary.v0.1",
                            "artifact": artifact_id,
                            "unit": unit.unit_id,
                            "hash": unit.content_hash,
                        },
                    ),
                    artifact_id=artifact_id,
                    input_unit_ids=[unit.unit_id],
                    input_hashes=[unit.content_hash],
                    policy_id="unit_summary.v0.1",
                    axes=axes,
                    exact_descents=[unit.exact_ref],
                    authoritative=False,
                )
            )
    return unit_summaries


def _build_collection_summary(summaries: dict[str, SummaryNode]) -> SummaryNode | None:
    if not summaries:
        return None
    ordered = [summaries[key] for key in sorted(summaries)]
    axes = {
        "identity": "collection summary",
        "purpose": "cross-artifact awareness summary",
        "claims_facts": [],
        "interfaces_dependencies": [],
        "constraints": [],
        "current_state": f"{len(ordered)} artifact summaries",
        "risks_unknowns": ["collection summary is awareness only; exact descent required for claims or edits"],
        "available_exact_descents": [ref for summary in ordered for ref in summary.exact_descents[:3]],
        "artifact_summaries": [summary.summary_id for summary in ordered],
    }
    return SummaryNode(
        summary_id=stable_id("summary", {"collection": [summary.summary_id for summary in ordered]}),
        artifact_id="collection",
        input_unit_ids=[summary.summary_id for summary in ordered],
        input_hashes=[summary.summary_id for summary in ordered],
        policy_id="collection_summary.v0.1",
        axes=axes,
        exact_descents=axes["available_exact_descents"],
        authoritative=False,
    )
