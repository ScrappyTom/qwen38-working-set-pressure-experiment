"""Offline task-construction probe, not a frozen acceptance test or model input."""
import json
import sys

sys.path.insert(0, "src")
from addressable_information_layer.artifact_units import build_address_map, exact_text_for_unit, import_artifact, resolve_address
from addressable_information_layer.content_log import ContentLog
from addressable_information_layer.patching import apply_patch_preview
from addressable_information_layer.records import PatchPreview, PatchPreviewStatus
from addressable_information_layer.reopen import materialize_reopen

log = ContentLog()
old = import_artifact(log, kind="python", path_or_name="report.py",
                      text="def calculate():\n    return 1\n\ndef untouched():\n    return 7\n")
old_map = build_address_map(old)
old_unit = resolve_address({old.artifact_id: old_map}, "function:calculate")


def apply(current, address_map, proposed, preview_id):
    unit = resolve_address({current.artifact_id: address_map}, "function:calculate")
    preview = PatchPreview(preview_id, PatchPreviewStatus.PREVIEWED, "offline construction probe", current.artifact_id,
                           unit.address, unit.exact_ref, unit.content_hash, exact_text_for_unit(current, unit), proposed, "function")
    return apply_patch_preview(preview, log=log, artifacts={current.artifact_id: current}, address_maps={current.artifact_id: address_map})


replacement = "def calculate():\n    interim = 2\n    return interim"
receipt, updated, propagated_map = apply(old, old_map, replacement, "offline-preview-1")
fresh_map = build_address_map(updated)
independent_unit = resolve_address({updated.artifact_id: fresh_map}, "function:calculate")
current = materialize_reopen("function:calculate", artifacts={updated.artifact_id: updated}, address_maps={updated.artifact_id: propagated_map})
unchanged = materialize_reopen("function:untouched", artifacts={updated.artifact_id: updated}, address_maps={updated.artifact_id: propagated_map})
stale = materialize_reopen(old_unit.exact_ref, artifacts={updated.artifact_id: updated}, address_maps={updated.artifact_id: propagated_map})
second_receipt, second, second_map = apply(updated, propagated_map, "def calculate():\n    return 3", "offline-preview-2")
second_reopen = None if second is None else materialize_reopen("function:calculate", artifacts={second.artifact_id: second}, address_maps={second.artifact_id: second_map})
no_change_receipt, no_change, no_change_map = apply(old, old_map, exact_text_for_unit(old, old_unit), "offline-preview-unchanged")
no_change_reopen = materialize_reopen(old_unit.exact_ref, artifacts={no_change.artifact_id: no_change}, address_maps={no_change.artifact_id: no_change_map})

print(json.dumps({
    "first_apply": receipt.status.value,
    "independent_extraction_correct": exact_text_for_unit(updated, independent_unit) == replacement,
    "propagated_map_matches_updated_version": propagated_map.version_hash == updated.version_hash,
    "current_reopen": {"status": current.status.value, "reason": current.reason, "text": current.materialized_text},
    "unchanged_function_reopen": {"status": unchanged.status.value, "text": unchanged.materialized_text},
    "old_exact_reference": {"status": stale.status.value, "reason": stale.reason},
    "second_apply": second_receipt.status.value,
    "second_reopen": None if second_reopen is None else {"status": second_reopen.status.value, "text": second_reopen.materialized_text},
    "unchanged_content_reopen": {"status": no_change_reopen.status.value, "text": no_change_reopen.materialized_text},
}, sort_keys=True))

assert receipt.status.value == "applied"
assert exact_text_for_unit(updated, independent_unit) == replacement
assert current.status.value == "materialized" and current.materialized_text == replacement
assert unchanged.status.value == "materialized" and unchanged.materialized_text == "def untouched():\n    return 7"
assert stale.status.value == "blocked"
assert second_receipt.status.value == "applied"
assert second_reopen.status.value == "materialized" and second_reopen.materialized_text == "def calculate():\n    return 3"
assert no_change_reopen.status.value == "materialized" and no_change_reopen.materialized_text == exact_text_for_unit(old, old_unit)
