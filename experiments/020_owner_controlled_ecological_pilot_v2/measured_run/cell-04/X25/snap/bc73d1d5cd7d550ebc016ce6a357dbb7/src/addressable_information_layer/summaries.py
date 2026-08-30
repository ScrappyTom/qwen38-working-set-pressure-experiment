"""One-level non-authoritative summary ladder for v0.1."""

from __future__ import annotations

from .hashing import stable_id
from .records import AddressMap, Artifact, SummaryNode


SUMMARY_POLICY_ID = "task_axis_summary.v0.1"


def build_summary(artifact: Artifact, address_map: AddressMap) -> SummaryNode:
    units = list(address_map.units.values())
    child_units = [unit for unit in units if unit.parent_address is not None]
    descents = [unit.exact_ref for unit in child_units[:12]]
    unit_titles = [f"{unit.unit_kind}:{unit.title}" for unit in child_units[:12]]
    axes = {
        "identity": f"{artifact.kind} artifact {artifact.path_or_name}",
        "purpose": _purpose_hint(artifact),
        "claims_facts": [],
        "interfaces_dependencies": _interfaces_hint(artifact.text),
        "constraints": [],
        "current_state": f"mapped {len(units)} units at hash {artifact.version_hash[:12]}",
        "risks_unknowns": _risk_hints(artifact),
        "available_exact_descents": descents,
        "unit_titles": unit_titles,
    }
    summary_id = stable_id(
        "summary",
        {
            "artifact": artifact.artifact_id,
            "map": address_map.map_id,
            "policy": SUMMARY_POLICY_ID,
            "input_hashes": [unit.content_hash for unit in units],
        },
    )
    return SummaryNode(
        summary_id=summary_id,
        artifact_id=artifact.artifact_id,
        input_unit_ids=[unit.unit_id for unit in units],
        input_hashes=[unit.content_hash for unit in units],
        policy_id=SUMMARY_POLICY_ID,
        axes=axes,
        exact_descents=descents,
        authoritative=False,
    )


def _purpose_hint(artifact: Artifact) -> str:
    if artifact.kind in {"python", "code", "source"} or artifact.path_or_name.endswith(".py"):
        return "code/source file"
    if artifact.kind in {"markdown", "document", "md"}:
        return "document or specification artifact"
    if artifact.kind in {"log", "verifier", "transcript"}:
        return "execution, verifier, or process history artifact"
    return "general text artifact"


def _interfaces_hint(text: str) -> list[str]:
    hints: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if stripped.startswith(("import ", "from ")):
            hints.append(stripped[:120])
        elif stripped.startswith(("def ", "class ")):
            hints.append(stripped[:120])
    return hints[:12]


def _risk_hints(artifact: Artifact) -> list[str]:
    risks: list[str] = []
    lowered = artifact.text.lower()
    if "todo" in lowered:
        risks.append("contains todo marker")
    if "error" in lowered or "failed" in lowered:
        risks.append("contains failure/error language")
    if not risks:
        risks.append("summary is awareness only; exact descent required for claims or edits")
    return risks

