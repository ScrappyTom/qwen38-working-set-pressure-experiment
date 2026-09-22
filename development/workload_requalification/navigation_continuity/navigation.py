"""Opt-in bounded historical navigation; no source acquisition or authority."""
from __future__ import annotations

import copy

from working_set_exp.coherent_diagnostic_session import CoherentDiagnosticSession
from working_set_exp import decision_view
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes

NAVIGATION_BYTES = 8192
IMMEDIATE_CHANGE_BYTES = 8192
MAX_NAVIGATION_PAGES = 6
SETTING = "navigation_projection_pages"
CHANGE_SETTING = "immediate_change_detail_mode"
REFERENCE_ADDITION = """
Recent activity may include navigation from an accepted tree or p0_page result.
It is historical navigation, not exact source or edit authority. observed_page
preserves the returned scope, entries and pagination; observed_candidate_id is
its original version. candidate_matches_current does not turn historical counts
into a new observation. An outline reference can still match an unchanged file
after another file changes; file_matches_current reports only that fingerprint
comparison. Obtain exact current source before editing. Duplicate page detail may
be shown once with shown_at_sequence. Navigation outside the bounded recent view
or omitted for capacity remains in its RES result; a recent row without navigation
does not present its result body. Use existing saved-result selection for material
you need to retain longer. No need to count or budget its bytes yourself.

An accepted edit's immediate applied_change, when shown, is the actual saved
unified diff, not the reason for the edit or a correctness judgment. Its old side
is historical text and grants no editing authority. Literal replacement may include
the separately recorded boundary separator supplied by the host. The exact proposal
remains in EVT; the exact applied_diff is in the same-sequence RES result. If change
detail is marked omitted or is absent from this bounded view, its body is not shown;
retrieve that saved result through the ordinary paged route. Omission never undoes
the edit. Earlier changes are not kept indefinitely in ordinary feedback.
""".strip()


def _navigation_pair(pair):
    action, result = pair["response"], pair["result"]
    if not result.get("accepted") or action.get("action") not in ("tree", "p0_page"):
        return False
    if action["action"] == "p0_page" and result.get("kind") not in ("root", "directory", "file_outline"):
        return False
    return (isinstance(result.get("entries"), list) and
            all(k in result for k in ("path", "offset", "total_entries", "next_offset", "candidate_id")))


def _page(pair, candidate):
    action, result = pair["response"], pair["result"]
    page = {k: copy.deepcopy(result[k]) for k in ("path", "offset", "total_entries", "next_offset", "entries")}
    page["kind"] = result.get("kind", "directory")
    if "limit" in action:
        page["requested_limit"] = action["limit"]
    if result.get("kind") == "file_outline":
        # Join only exact corresponding archived extent facts. Never synthesize
        # an address from an outline name, infer a parent, or acquire its source.
        for entry in page["entries"]:
            matches = [r for r in result.get("regions", [])
                       if r.get("path") == result["path"] and r.get("name") == entry.get("name")
                       and r.get("start_line") == entry.get("start_line")
                       and r.get("end_line") == entry.get("end_line")
                       and "region_ref" in r and "file_sha256" in r]
            if len(matches) == 1:
                region = matches[0]
                entry["source_reference"] = {k: region[k] for k in ("region_ref", "file_sha256")}
                entry["source_reference"]["file_matches_current"] = (
                    region["path"] in candidate.file_map and
                    candidate.file_sha256(region["path"]) == region["file_sha256"])
    return dict(observed_candidate_id=result["candidate_id"],
                candidate_matches_current=result["candidate_id"] == candidate.candidate_id,
                observation="historical_navigation_not_source", observed_page=page)


def _key(pair):
    # Identity includes original version and page/request scope. No cross-version
    # merging, even if some visible entries happen to share their spelling.
    return sha256_bytes(canonical_json_bytes(pair))


def _shown_latest(view, pair, sequence):
    latest = view.get("latest_feedback")
    if not latest or latest.get("sequence") != sequence:
        return False
    shown, original = latest["result"], pair["result"]
    keys = ["entries", "path", "offset", "total_entries", "next_offset", "candidate_id"]
    keys.extend(key for key in ("kind", "regions") if key in original)
    return shown.get("accepted") is True and all(
        key in shown and shown[key] == original[key] for key in keys)


def project_navigation(view, pairs, candidate, *, page_limit=MAX_NAVIGATION_PAGES,
                       byte_limit=NAVIGATION_BYTES):
    """Project only already-present recent rows; return a new view.

    A negative page limit removes ALL optional additions, byte-for-byte preserving
    the incoming view. This is the last admission fallback, not a storage policy.
    The permanent reference explains that rows without detail expose handles only.
    """
    if type(page_limit) is not int or not -1 <= page_limit <= MAX_NAVIGATION_PAGES:
        raise ValueError("navigation page limit outside the supported bounded range")
    if type(byte_limit) is not int or byte_limit < 0:
        raise ValueError("navigation byte limit invalid")
    result = copy.deepcopy(view)
    if page_limit < 0:
        return result
    baseline_bytes = len(canonical_json_bytes(view))
    represented, complete = {}, 0
    recent = result.get("recent_activity", [])
    # Respect the existing six-row window even if a caller explicitly renders a
    # longer history page. Oldest optional pages yield first, without ranking.
    for row in reversed(recent[-MAX_NAVIGATION_PAGES:]):
        sequence = row.get("sequence")
        if type(sequence) is not int or not 1 <= sequence <= len(pairs):
            continue
        pair = pairs[sequence - 1]
        if not _navigation_pair(pair):
            continue
        key = _key(pair)
        if _shown_latest(view, pair, sequence):
            detail = dict(detail_status="already_in_latest_feedback", shown_at_sequence=sequence)
            represented[key] = sequence
        elif key in represented:
            detail = dict(detail_status="duplicate_returned_page", shown_at_sequence=represented[key])
        elif complete >= page_limit:
            detail = dict(detail_status="omitted_for_input_admission_budget")
        else:
            detail = dict(detail_status="complete_returned_navigation_page", **_page(pair, candidate))
        row["navigation"] = detail
        if len(canonical_json_bytes(result)) - baseline_bytes > byte_limit:
            row["navigation"] = dict(detail_status="omitted_for_navigation_byte_allowance")
            if len(canonical_json_bytes(result)) - baseline_bytes > byte_limit:
                row.pop("navigation")  # A zero-cost fallback is required.
        elif detail["detail_status"] == "complete_returned_navigation_page":
            represented[key] = sequence
            complete += 1
    return result


def project_immediate_change(view, *, mode=2, byte_limit=IMMEDIATE_CHANGE_BYTES,
                             historical_diffs=None):
    """Present the exact latest applied diff, complete or omitted.

    historical_diffs is qualification-only, explicitly supplied for old snapshots
    whose original RES records did not contain a diff. It creates no recovery claim
    and never writes to those records. Modes: 2 full if byte allowance permits,
    1 omission metadata only, 0 no optional addition. The raw result is preserved.
    """
    if type(mode) is not int or mode not in (0,1,2):
        raise ValueError("immediate change mode outside the supported range")
    if type(byte_limit) is not int or byte_limit < 0:
        raise ValueError("immediate change byte limit invalid")
    value = copy.deepcopy(view)
    receipt = value.get("latest_feedback")
    if not receipt:
        return value
    result = receipt["result"]
    exact = result.pop("applied_diff", None)
    sequence = receipt["sequence"]
    historical = False
    if (not result.get("accepted") or
            receipt.get("action_summary",{}).get("action") not in ("patch","replace_region")):
        return value
    if exact is None and historical_diffs is not None:
        exact = historical_diffs.get(sequence)
        historical = exact is not None
    if exact is None or mode == 0:
        return value
    if not isinstance(exact,str):
        raise ValueError("applied diff is not exact text")
    base = len(canonical_json_bytes(value))
    raw = exact.encode()
    detail = dict(format="unified_diff", byte_count=len(raw), sha256=sha256_bytes(raw),
                  establishes="actual_saved_change_not_correctness_or_edit_authority")
    if historical:
        detail["qualification_origin"] = "archived_snapshot_diff; original_RES_has_no_applied_diff"
    else:
        detail.update(exact_result_handle=f"RES-{sequence:04d}",exact_result_field="applied_diff")
    detail["detail_status"] = "omitted_for_input_admission_budget"
    if mode == 2:
        detail.update(detail_status="complete_applied_diff",diff_utf8=exact)
    receipt["applied_change"] = detail
    if len(canonical_json_bytes(value))-base > byte_limit:
        detail.pop("diff_utf8",None)
        detail["detail_status"] = "omitted_for_change_byte_allowance"
        if len(canonical_json_bytes(value))-base > byte_limit:
            receipt.pop("applied_change")
    return value


def present_receipts(view, receipts):
    """Safe preceding-receipt rendering for the explicit-check task adapter.

    This configuration never combines an accepted edit with an automatic check.
    Do not leak raw diff bodies if an outside caller supplies such a receipt;
    its result remains recoverable, but combined-detail admission is unqualified.
    """
    result = decision_view.present_receipts(view, receipts)
    for receipt in result:
        receipt.pop(SETTING,None)
        receipt.pop(CHANGE_SETTING,None)
        receipt["result"].pop("applied_diff",None)
    return result


class NavigationMixin:
    """Mix in before the existing task Session; preserve its task-specific view.

    The optional rendering setting lives in the already-snapshotted last receipt
    wrapper, never in pairs/result bytes. Existing generic checkpoint restoration
    therefore keeps the admitted view without a new top-level snapshot field.
    """
    navigation_byte_limit = NAVIGATION_BYTES
    immediate_change_byte_limit = IMMEDIATE_CHANGE_BYTES
    navigation_enabled = True
    immediate_change_enabled = True
    historical_diff_projection = False  # Explicit old-state qualification only.

    def _patch(self, action):
        result = super()._patch(action)
        if result.get("accepted"):
            # Capture after the inherited literal-boundary handling but before
            # _record archives the result. EVT still stores the original proposal.
            result = {**result, "applied_diff": self.diffs[len(self.pairs)+1]}
        return result

    def view(self, **kwargs):
        value = super().view(**kwargs)
        latest = value.get("latest_feedback")
        if latest:
            latest.pop(SETTING, None)
            latest.pop(CHANGE_SETTING, None)
        change_mode = self.last.get(CHANGE_SETTING,2) if self.last else 2
        value = project_immediate_change(value,
            mode=change_mode if self.immediate_change_enabled else 0,
            byte_limit=self.immediate_change_byte_limit,
            historical_diffs=self.diffs if self.historical_diff_projection else None)
        limit = self.last.get(SETTING, MAX_NAVIGATION_PAGES) if self.last else MAX_NAVIGATION_PAGES
        return project_navigation(value, self.pairs, self.candidate,
                                  page_limit=limit if self.navigation_enabled else -1,
                                  byte_limit=self.navigation_byte_limit)

    def _fits(self, measure, *, margin=1024):
        if self.last is None:
            return super()._fits(measure, margin=margin)
        # Copy before setting: a clone may still share the wrapper. The exact
        # archived pair/result and previous session must never be changed.
        self.last = dict(self.last)
        previous = None
        # Essential receipt first, then immediate applied change, then navigation.
        # Optional omission labels can also yield: permanent reference describes
        # absent detail and the existing exact RES route without a new byte floor.
        choices = [(2,limit) for limit in range(MAX_NAVIGATION_PAGES,-2,-1)]
        choices.extend(((1,-1),(0,-1)))
        for change_mode,limit in choices:
            self.last[SETTING] = limit
            self.last[CHANGE_SETTING] = change_mode
            signature = sha256_bytes(canonical_json_bytes(self.view()))
            if signature == previous:
                continue
            previous = signature
            if super()._fits(measure, margin=margin):
                return True
        return False


class NavigationSession(NavigationMixin, CoherentDiagnosticSession):
    """Default opt-in host; task adapters may mix into their existing Session."""
