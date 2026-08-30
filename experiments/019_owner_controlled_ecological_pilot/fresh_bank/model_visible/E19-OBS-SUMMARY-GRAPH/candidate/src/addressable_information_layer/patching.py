"""Patch-preview and in-memory apply helpers for bounded draft changes."""

from __future__ import annotations

from .artifact_units import build_address_map, exact_text_for_unit, import_artifact, resolve_address
from .content_log import ContentLog
from .hashing import sha256_text, stable_id
from .records import (
    AddressMap,
    ApplyReceipt,
    ApplyStatus,
    Artifact,
    CurrentFocus,
    ModelResponse,
    PatchPreview,
    PatchPreviewStatus,
)


def create_patch_preview(
    focus: CurrentFocus,
    response: ModelResponse,
    *,
    artifacts: dict[str, Artifact],
    address_maps: dict[str, AddressMap],
) -> PatchPreview:
    target_ref = focus.active_address or (focus.exact_window_refs[0] if focus.exact_window_refs else None)
    if not target_ref:
        return _blocked("no active target address or exact window", response)

    unit = resolve_address(address_maps, target_ref)
    if unit is None and focus.exact_window_refs:
        unit = resolve_address(address_maps, focus.exact_window_refs[0])
    if unit is None:
        return _blocked("active target could not be resolved to an exact unit", response)

    artifact = artifacts.get(unit.artifact_id)
    if artifact is None:
        return _blocked("target artifact missing for patch preview", response)

    before_text = exact_text_for_unit(artifact, unit)
    before_hash = sha256_text(before_text)
    preview_payload = {
        "artifact_id": artifact.artifact_id,
        "address": unit.address,
        "exact_ref": unit.exact_ref,
        "before_hash": before_hash,
        "draft": response.draft,
        "scope": response.edit_scope,
    }
    return PatchPreview(
        preview_id=stable_id("patch_preview", preview_payload),
        status=PatchPreviewStatus.PREVIEWED,
        reason="bounded patch preview created; no file mutation performed",
        artifact_id=artifact.artifact_id,
        address=unit.address,
        exact_ref=unit.exact_ref,
        before_hash=before_hash,
        before_text=before_text,
        proposed_text=response.draft,
        edit_scope=response.edit_scope,
    )


def _blocked(reason: str, response: ModelResponse) -> PatchPreview:
    return PatchPreview(
        preview_id=stable_id("patch_preview", {"status": "blocked", "reason": reason, "draft": response.draft}),
        status=PatchPreviewStatus.BLOCKED,
        reason=reason,
        artifact_id=None,
        address=None,
        exact_ref=None,
        before_hash=None,
        before_text=None,
        proposed_text=response.draft,
        edit_scope=response.edit_scope,
    )


def apply_patch_preview(
    preview: PatchPreview,
    *,
    log: ContentLog,
    artifacts: dict[str, Artifact],
    address_maps: dict[str, AddressMap],
) -> tuple[ApplyReceipt, Artifact | None, AddressMap | None]:
    if preview.status != PatchPreviewStatus.PREVIEWED:
        return _apply_blocked("preview is not in previewed state", preview), None, None
    if not preview.artifact_id or not preview.address or preview.proposed_text is None:
        return _apply_blocked("preview is missing artifact/address/proposed text", preview), None, None

    artifact = artifacts.get(preview.artifact_id)
    if artifact is None:
        return _apply_blocked("preview artifact is missing", preview), None, None
    address_map = address_maps.get(preview.artifact_id)
    if address_map is None:
        return _apply_blocked("preview address map is missing", preview), None, None
    unit = resolve_address({preview.artifact_id: address_map}, preview.address)
    if unit is None:
        return _apply_blocked("preview address no longer resolves", preview), None, None
    before_text = exact_text_for_unit(artifact, unit)
    before_hash = sha256_text(before_text)
    if before_hash != preview.before_hash:
        return _apply_blocked("preview before hash does not match current exact unit", preview), None, None

    lines = artifact.text.splitlines()
    replacement = preview.proposed_text.splitlines()
    new_lines = lines[: unit.start_line - 1] + replacement + lines[unit.end_line :]
    trailing_newline = "\n" if artifact.text.endswith("\n") else ""
    new_text = "\n".join(new_lines) + trailing_newline
    new_artifact = import_artifact(log, kind=artifact.kind, path_or_name=artifact.path_or_name, text=new_text)
    new_map = build_address_map(new_artifact)
    receipt = ApplyReceipt(
        receipt_id=stable_id(
            "apply",
            {
                "preview": preview.preview_id,
                "old_artifact": artifact.artifact_id,
                "new_artifact": new_artifact.artifact_id,
                "after_hash": new_artifact.version_hash,
            },
        ),
        status=ApplyStatus.APPLIED,
        reason="patch preview applied in memory; workspace file was not mutated",
        preview_id=preview.preview_id,
        artifact_id=artifact.artifact_id,
        address=preview.address,
        before_hash=preview.before_hash,
        after_hash=new_artifact.version_hash,
        new_artifact_id=new_artifact.artifact_id,
    )
    log.append_event(
        kind="in_memory_apply",
        actor="host",
        payload={
            "receipt_id": receipt.receipt_id,
            "preview_id": preview.preview_id,
            "old_artifact_id": artifact.artifact_id,
            "new_artifact_id": new_artifact.artifact_id,
            "path_or_name": artifact.path_or_name,
            "after_hash": new_artifact.version_hash,
        },
        refs=[preview.preview_id, artifact.blob_ref, new_artifact.blob_ref],
    )
    return receipt, new_artifact, new_map


def _apply_blocked(reason: str, preview: PatchPreview) -> ApplyReceipt:
    return ApplyReceipt(
        receipt_id=stable_id("apply", {"preview": preview.preview_id, "status": "blocked", "reason": reason}),
        status=ApplyStatus.BLOCKED,
        reason=reason,
        preview_id=preview.preview_id,
        artifact_id=preview.artifact_id,
        address=preview.address,
        before_hash=preview.before_hash,
        after_hash=None,
    )
