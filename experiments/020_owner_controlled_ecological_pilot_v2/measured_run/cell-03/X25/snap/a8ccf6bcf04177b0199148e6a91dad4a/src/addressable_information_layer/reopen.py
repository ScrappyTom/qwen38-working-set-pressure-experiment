"""Exact materialization for visible artifact handles."""

from __future__ import annotations

from .artifact_units import exact_text_for_unit, resolve_address
from .hashing import sha256_text, stable_id
from .records import AddressMap, Artifact, ReopenReceipt, ReopenStatus


def materialize_reopen(
    requested_ref_or_address: str,
    *,
    artifacts: dict[str, Artifact],
    address_maps: dict[str, AddressMap],
    max_chars: int = 4000,
) -> ReopenReceipt:
    unit = resolve_address(address_maps, requested_ref_or_address)
    if unit is None:
        return ReopenReceipt(
            receipt_id=stable_id("reopen", {"request": requested_ref_or_address, "status": "blocked"}),
            requested_ref_or_address=requested_ref_or_address,
            status=ReopenStatus.BLOCKED,
            reason="request did not resolve to a visible exact handle or address",
        )

    artifact = artifacts.get(unit.artifact_id)
    if artifact is None:
        return ReopenReceipt(
            receipt_id=stable_id("reopen", {"request": requested_ref_or_address, "unit": unit.unit_id, "status": "blocked"}),
            requested_ref_or_address=requested_ref_or_address,
            status=ReopenStatus.BLOCKED,
            reason="resolved unit artifact is missing",
            artifact_id=unit.artifact_id,
            address=unit.address,
            exact_ref=unit.exact_ref,
        )

    exact_text = exact_text_for_unit(artifact, unit)
    observed_hash = sha256_text(exact_text)
    if observed_hash != unit.content_hash:
        return ReopenReceipt(
            receipt_id=stable_id(
                "reopen",
                {"request": requested_ref_or_address, "unit": unit.unit_id, "status": "blocked", "reason": "hash_mismatch"},
            ),
            requested_ref_or_address=requested_ref_or_address,
            status=ReopenStatus.BLOCKED,
            reason="exact unit hash mismatch; artifact map is stale",
            artifact_id=unit.artifact_id,
            address=unit.address,
            exact_ref=unit.exact_ref,
            version_hash=artifact.version_hash,
            content_hash=unit.content_hash,
            start_line=unit.start_line,
            end_line=unit.end_line,
        )

    truncated = len(exact_text) > max_chars
    materialized = exact_text[:max_chars] if truncated else exact_text
    return ReopenReceipt(
        receipt_id=stable_id(
            "reopen",
            {
                "request": requested_ref_or_address,
                "unit": unit.unit_id,
                "content_hash": unit.content_hash,
                "max_chars": max_chars,
            },
        ),
        requested_ref_or_address=requested_ref_or_address,
        status=ReopenStatus.MATERIALIZED,
        reason="exact unit materialized",
        artifact_id=artifact.artifact_id,
        address=unit.address,
        exact_ref=unit.exact_ref,
        version_hash=artifact.version_hash,
        content_hash=unit.content_hash,
        start_line=unit.start_line,
        end_line=unit.end_line,
        materialized_text=materialized,
        truncated=truncated,
    )

