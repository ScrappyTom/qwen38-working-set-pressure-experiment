"""Artifact import and deterministic unit-map construction."""

from __future__ import annotations

import ast
import json
import re
from dataclasses import replace
from typing import Iterable

from .content_log import ContentLog
from .hashing import sha256_text, stable_id
from .records import AddressMap, Artifact, ArtifactReviewStatus, ArtifactState, ArtifactUnit


def import_artifact(log: ContentLog, *, kind: str, path_or_name: str, text: str) -> Artifact:
    blob = log.append_blob(text, media_type="text/plain", name=path_or_name)
    artifact_id = stable_id("artifact", {"kind": kind, "path": path_or_name})
    return Artifact(
        artifact_id=artifact_id,
        kind=kind,
        path_or_name=path_or_name,
        version_hash=blob.sha256,
        blob_ref=blob.blob_ref,
        text=text,
    )


def build_address_map(artifact: Artifact) -> AddressMap:
    if artifact.kind in {"python", "code", "source"} or artifact.path_or_name.endswith(".py"):
        units = _unitize_python(artifact)
    elif artifact.kind in {"markdown", "document", "md"} or artifact.path_or_name.endswith((".md", ".markdown")):
        units = _unitize_markdown(artifact)
    elif artifact.kind in {"html", "web_page", "web"} or artifact.path_or_name.endswith((".html", ".htm")):
        units = _unitize_html(artifact)
    elif artifact.kind in {"json", "world_map", "ceiba_world_map", "surface_map"} or artifact.path_or_name.endswith(".json"):
        units = _unitize_json(artifact)
    elif artifact.kind in {"log", "verifier", "transcript"}:
        units = _unitize_log(artifact)
    else:
        units = _unitize_text(artifact)

    map_id = stable_id(
        "map",
        {
            "artifact_id": artifact.artifact_id,
            "version_hash": artifact.version_hash,
            "addresses": sorted(units),
        },
    )
    return AddressMap(map_id=map_id, artifact_id=artifact.artifact_id, version_hash=artifact.version_hash, units=units)


def artifact_state_from_map(artifact: Artifact, address_map: AddressMap) -> ArtifactState:
    exact_units = [
        unit
        for unit in address_map.units.values()
        if unit.unit_kind
        in {
            "file",
            "section",
            "error",
            "function",
            "class",
            "web_page",
            "ui_element",
            "link",
            "heading",
            "json",
            "json_value",
            "world_map",
            "surface",
            "semantic_block",
            "image_region",
        }
    ]
    exact_units.sort(key=lambda unit: (unit.parent_address is None, unit.start_line, unit.address))
    exact_refs = [unit.exact_ref for unit in exact_units]
    return ArtifactState(
        artifact_id=artifact.artifact_id,
        kind=artifact.kind,
        path_or_name=artifact.path_or_name,
        version_hash=artifact.version_hash,
        address_map_ref=address_map.map_id,
        review_status=ArtifactReviewStatus.MAPPED,
        exact_window_refs=exact_refs[:8],
    )


def resolve_address(address_maps: dict[str, AddressMap], address_or_ref: str) -> ArtifactUnit | None:
    for address_map in address_maps.values():
        for unit in address_map.units.values():
            if address_or_ref in {unit.address, unit.unit_id, unit.exact_ref}:
                return unit
    return None


def mark_artifact_stale(state: ArtifactState) -> ArtifactState:
    return replace(state, review_status=ArtifactReviewStatus.STALE)


def exact_text_for_unit(artifact: Artifact, unit: ArtifactUnit) -> str:
    if unit.inline_text is not None:
        return unit.inline_text
    lines = artifact.text.splitlines()
    return "\n".join(lines[unit.start_line - 1 : unit.end_line])


def _unitize_python(artifact: Artifact) -> dict[str, ArtifactUnit]:
    lines = artifact.text.splitlines()
    root = _make_unit(artifact, "file", "file", artifact.path_or_name, 1, max(len(lines), 1), None)
    units = {root.address: root}
    child_addresses: list[str] = []

    try:
        tree = ast.parse(artifact.text)
    except SyntaxError:
        return _with_children(units, root.address, child_addresses)

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            kind = "class" if isinstance(node, ast.ClassDef) else "function"
            start = getattr(node, "lineno", 1)
            end = getattr(node, "end_lineno", start)
            address = f"{kind}:{node.name}"
            unit = _make_unit(artifact, address, kind, node.name, start, end, "file")
            units[unit.address] = unit
            child_addresses.append(unit.address)

    return _with_children(units, root.address, child_addresses)


def _unitize_markdown(artifact: Artifact) -> dict[str, ArtifactUnit]:
    lines = artifact.text.splitlines()
    root = _make_unit(artifact, "document", "document", artifact.path_or_name, 1, max(len(lines), 1), None)
    units = {root.address: root}
    headings: list[tuple[int, str, str]] = []

    for idx, line in enumerate(lines, start=1):
        match = re.match(r"^(#{1,6})\s+(.+)$", line)
        if match:
            title = match.group(2).strip()
            slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or f"section-{idx}"
            headings.append((idx, f"section:{slug}", title))

    child_addresses: list[str] = []
    for pos, (start, address, title) in enumerate(headings):
        end = headings[pos + 1][0] - 1 if pos + 1 < len(headings) else max(len(lines), start)
        unit = _make_unit(artifact, address, "section", title, start, end, "document")
        units[unit.address] = unit
        child_addresses.append(unit.address)

    if not child_addresses:
        paragraph_units = _paragraph_units(artifact, "document")
        units.update(paragraph_units)
        child_addresses.extend(paragraph_units)

    return _with_children(units, root.address, child_addresses)


def _unitize_log(artifact: Artifact) -> dict[str, ArtifactUnit]:
    lines = artifact.text.splitlines()
    root = _make_unit(artifact, "log", "log", artifact.path_or_name, 1, max(len(lines), 1), None)
    units = {root.address: root}
    child_addresses: list[str] = []

    for idx, line in enumerate(lines, start=1):
        lowered = line.lower()
        if any(token in lowered for token in ("error", "failed", "traceback", "exception")):
            start = max(1, idx - 2)
            end = min(max(len(lines), 1), idx + 3)
            address = f"error:{idx}"
            unit = _make_unit(artifact, address, "error", line.strip()[:80] or address, start, end, "log")
            units[unit.address] = unit
            child_addresses.append(unit.address)

    if not child_addresses:
        return _unitize_text(artifact)
    return _with_children(units, root.address, child_addresses)


def _unitize_html(artifact: Artifact) -> dict[str, ArtifactUnit]:
    lines = artifact.text.splitlines()
    root = _make_unit(artifact, "web_page", "web_page", artifact.path_or_name, 1, max(len(lines), 1), None)
    units = {root.address: root}
    child_addresses: list[str] = []
    seen: dict[str, int] = {}
    patterns = [
        (r"<h[1-6][^>]*>(.*?)</h[1-6]>", "heading"),
        (r"<a\b[^>]*>(.*?)</a>", "link"),
        (r"<button\b[^>]*>(.*?)</button>", "ui_element"),
        (r"<input\b[^>]*>", "ui_element"),
        (r"<textarea\b[^>]*>", "ui_element"),
        (r"<select\b[^>]*>", "ui_element"),
    ]
    for idx, line in enumerate(lines, start=1):
        for pattern, kind in patterns:
            for match in re.finditer(pattern, line, flags=re.IGNORECASE):
                raw_title = re.sub(r"<[^>]+>", "", match.group(1) if match.groups() else match.group(0)).strip()
                title = raw_title or kind
                slug = re.sub(r"[^a-z0-9]+", "-", title.lower()).strip("-") or kind
                seen[slug] = seen.get(slug, 0) + 1
                suffix = f"-{seen[slug]}" if seen[slug] > 1 else ""
                address = f"{kind}:{slug}{suffix}"
                unit = _make_unit(artifact, address, kind, title[:80], idx, idx, "web_page")
                units[unit.address] = unit
                child_addresses.append(unit.address)

    if not child_addresses:
        paragraph_units = _paragraph_units(artifact, "web_page")
        units.update(paragraph_units)
        child_addresses.extend(paragraph_units)
    return _with_children(units, root.address, child_addresses)


def _unitize_json(artifact: Artifact) -> dict[str, ArtifactUnit]:
    lines = artifact.text.splitlines()
    try:
        data = json.loads(artifact.text)
    except json.JSONDecodeError:
        return _unitize_text(artifact)

    root_kind = "world_map" if _looks_like_world_map(data) or artifact.kind in {"world_map", "ceiba_world_map"} else "json"
    root = _make_unit(artifact, root_kind, root_kind, artifact.path_or_name, 1, max(len(lines), 1), None)
    units = {root.address: root}
    child_addresses: list[str] = []

    if isinstance(data, dict):
        for surface in _iter_named_records(data, ("surfaces", "surface_records", "surfaceRecords")):
            address = _unique_address(units, f"surface:{_record_slug(surface, ('surface_id', 'surfaceId', 'id', 'handle', 'name', 'title', 'url'))}")
            title = _record_title(surface, ("title", "name", "url", "surface_id", "id"), "surface")
            units[address] = _make_unit(
                artifact,
                address,
                "surface",
                title,
                1,
                max(len(lines), 1),
                root.address,
                inline_text=_inline_json(surface),
            )
            child_addresses.append(address)
            child_addresses.extend(_add_surface_children(artifact, units, surface, address))

        if not child_addresses:
            for key, value in list(data.items())[:30]:
                address = _unique_address(units, f"json:{_slug(str(key))}")
                units[address] = _make_unit(
                    artifact,
                    address,
                    "json_value",
                    str(key)[:80],
                    1,
                    max(len(lines), 1),
                    root.address,
                    inline_text=_inline_json(value),
                )
                child_addresses.append(address)
    elif isinstance(data, list):
        for idx, value in enumerate(data[:30], start=1):
            address = f"json:item-{idx}"
            units[address] = _make_unit(
                artifact,
                address,
                "json_value",
                f"item {idx}",
                1,
                max(len(lines), 1),
                root.address,
                inline_text=_inline_json(value),
            )
            child_addresses.append(address)

    if not child_addresses:
        return _with_children(units, root.address, child_addresses)
    return _with_children(units, root.address, child_addresses)


def _add_surface_children(
    artifact: Artifact,
    units: dict[str, ArtifactUnit],
    surface: object,
    parent_address: str,
) -> list[str]:
    if not isinstance(surface, dict):
        return []
    lines = artifact.text.splitlines()
    child_addresses: list[str] = []
    for element in _iter_named_records(surface, ("elements", "element_records", "elementRecords", "ui_elements", "uiElements")):
        address = _unique_address(
            units,
            f"ui_element:{_record_slug(element, ('element_id', 'elementId', 'id', 'handle', 'text', 'label', 'name', 'role'))}",
        )
        title = _record_title(element, ("text", "label", "name", "role", "element_id", "id"), "ui_element")
        units[address] = _make_unit(
            artifact,
            address,
            "ui_element",
            title,
            1,
            max(len(lines), 1),
            parent_address,
            inline_text=_inline_json(element),
        )
        child_addresses.append(address)

    for block in _iter_named_records(surface, ("semantic_blocks", "semanticBlocks", "blocks", "text_blocks", "textBlocks")):
        address = _unique_address(units, f"semantic_block:{_record_slug(block, ('block_id', 'blockId', 'id', 'text', 'title'))}")
        title = _record_title(block, ("title", "text", "block_id", "id"), "semantic_block")
        units[address] = _make_unit(
            artifact,
            address,
            "semantic_block",
            title,
            1,
            max(len(lines), 1),
            parent_address,
            inline_text=_inline_json(block),
        )
        child_addresses.append(address)

    for region in _iter_named_records(surface, ("image_regions", "imageRegions", "image_tiles", "imageTiles", "tiles")):
        address = _unique_address(units, f"image_region:{_record_slug(region, ('region_id', 'regionId', 'id', 'label', 'title'))}")
        title = _record_title(region, ("label", "title", "region_id", "id"), "image_region")
        units[address] = _make_unit(
            artifact,
            address,
            "image_region",
            title,
            1,
            max(len(lines), 1),
            parent_address,
            inline_text=_inline_json(region),
        )
        child_addresses.append(address)

    parent = units[parent_address]
    units[parent_address] = replace(parent, child_addresses=list(parent.child_addresses) + child_addresses)
    return child_addresses


def _looks_like_world_map(data: object) -> bool:
    return isinstance(data, dict) and any(key in data for key in ("surfaces", "surface_records", "surfaceRecords", "world_map"))


def _iter_named_records(container: dict[str, object], names: tuple[str, ...]) -> list[object]:
    for name in names:
        value = container.get(name)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            return list(value.values())
    return []


def _record_slug(record: object, fields: tuple[str, ...]) -> str:
    if isinstance(record, dict):
        for field in fields:
            value = record.get(field)
            if value:
                return _slug(str(value))
    return "record"


def _record_title(record: object, fields: tuple[str, ...], fallback: str) -> str:
    if isinstance(record, dict):
        for field in fields:
            value = record.get(field)
            if value:
                return str(value).strip()[:80]
    return fallback


def _unique_address(units: dict[str, ArtifactUnit], address: str) -> str:
    if address not in units:
        return address
    idx = 2
    while f"{address}-{idx}" in units:
        idx += 1
    return f"{address}-{idx}"


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-") or "item"


def _inline_json(value: object) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=True)


def _unitize_text(artifact: Artifact) -> dict[str, ArtifactUnit]:
    lines = artifact.text.splitlines()
    root = _make_unit(artifact, "text", "text", artifact.path_or_name, 1, max(len(lines), 1), None)
    units = {root.address: root}
    child_addresses = list(_paragraph_units(artifact, "text"))
    units.update(_paragraph_units(artifact, "text"))
    return _with_children(units, root.address, child_addresses)


def _paragraph_units(artifact: Artifact, parent: str) -> dict[str, ArtifactUnit]:
    lines = artifact.text.splitlines()
    units: dict[str, ArtifactUnit] = {}
    start: int | None = None
    part = 1
    for idx, line in enumerate(lines + [""], start=1):
        if line.strip() and start is None:
            start = idx
        if start is not None and (not line.strip() or idx > len(lines)):
            end = idx - 1
            address = f"paragraph:{part}"
            title = lines[start - 1].strip()[:80] or address
            units[address] = _make_unit(artifact, address, "paragraph", title, start, end, parent)
            start = None
            part += 1
    return units


def _with_children(units: dict[str, ArtifactUnit], root_address: str, child_addresses: Iterable[str]) -> dict[str, ArtifactUnit]:
    root = units[root_address]
    units[root_address] = replace(root, child_addresses=list(child_addresses))
    return units


def _make_unit(
    artifact: Artifact,
    address: str,
    unit_kind: str,
    title: str,
    start_line: int,
    end_line: int,
    parent_address: str | None,
    inline_text: str | None = None,
) -> ArtifactUnit:
    lines = artifact.text.splitlines()
    text = inline_text if inline_text is not None else ("\n".join(lines[start_line - 1 : end_line]) if lines else artifact.text)
    content_hash = sha256_text(text)
    payload = {
        "artifact_id": artifact.artifact_id,
        "version_hash": artifact.version_hash,
        "address": address,
        "start": start_line,
        "end": end_line,
        "hash": content_hash,
    }
    unit_id = stable_id("unit", payload)
    exact_ref = f"exact:{artifact.artifact_id}:{address}:{content_hash[:12]}"
    return ArtifactUnit(
        unit_id=unit_id,
        artifact_id=artifact.artifact_id,
        address=address,
        unit_kind=unit_kind,
        title=title,
        content_hash=content_hash,
        exact_ref=exact_ref,
        start_line=start_line,
        end_line=end_line,
        parent_address=parent_address,
        inline_text=inline_text,
    )
