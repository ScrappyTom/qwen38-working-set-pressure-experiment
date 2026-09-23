"""Prospective exact recent search projection; no new acquisition or authority."""
from __future__ import annotations

import copy

import navigation as previous
from working_set_exp.jsonutil import canonical_json_bytes


REFERENCE_ADDITION = """
Recent navigation may also show an exact historical search page: its query,
matches, reusable regions and pagination. These are the results of the recorded
search, not a new search of the current candidate. Region file_matches_current
compares the recorded fingerprint only. Matching lines and region addresses do
not make a region's full source visible or authorize editing. Read or select its
exact source before editing. Search context and enclosing-function regions retain
their original different extents. Absent or explicitly omitted detail remains in
the row's exact RES result. The same bounded navigation allowance applies to tree,
outline and search pages; no search result is automatically retained indefinitely.
""".strip()


def search_pair(pair):
    action, result = pair["response"], pair["result"]
    return (
        action.get("action") == "search" and result.get("accepted") is True
        and all(k in result for k in (
            "candidate_id", "path", "query", "offset", "total_matches",
            "next_offset", "matches", "regions"))
        and isinstance(result["matches"], list)
        and isinstance(result["regions"], list)
    )


def search_page(pair, candidate):
    result = pair["result"]
    page = {k: copy.deepcopy(result[k]) for k in (
        "path", "query", "offset", "total_matches", "next_offset", "matches", "regions")}
    page["kind"] = "literal_search"
    page["requested_limit"] = pair["response"]["limit"]
    for region in page["regions"]:
        region["file_matches_current"] = (
            region["path"] in candidate.file_map
            and candidate.file_sha256(region["path"]) == region["file_sha256"])
    return dict(observed_candidate_id=result["candidate_id"],
                candidate_matches_current=result["candidate_id"] == candidate.candidate_id,
                observation="historical_navigation_not_source", observed_page=page)


def shown_latest(view, pair, sequence):
    if not search_pair(pair):
        return previous._shown_latest(view, pair, sequence)
    latest = view.get("latest_feedback")
    if not latest or latest.get("sequence") != sequence:
        return False
    shown, original = latest["result"], pair["result"]
    return shown.get("accepted") is True and all(
        k in shown and shown[k] == original[k] for k in (
            "candidate_id", "path", "query", "offset", "total_matches",
            "next_offset", "matches", "regions"))


def project(view, pairs, candidate, *, page_limit=previous.MAX_NAVIGATION_PAGES,
            byte_limit=previous.NAVIGATION_BYTES):
    """Reproject the same recent window under one shared optional allowance.

    Incoming navigation belongs to the predecessor projection. Removing it before
    measuring avoids granting searches an additional independent byte allowance.
    No archive, selection, account, source, change or required feedback is mutated.
    """
    if type(page_limit) is not int or not -1 <= page_limit <= previous.MAX_NAVIGATION_PAGES:
        raise ValueError("navigation page limit outside the supported bounded range")
    if type(byte_limit) is not int or byte_limit < 0:
        raise ValueError("navigation byte limit invalid")
    result = copy.deepcopy(view)
    for row in result.get("recent_activity", []):
        row.pop("navigation", None)
    if page_limit < 0:
        return result
    baseline_bytes = len(canonical_json_bytes(result))
    represented, complete = {}, 0
    for row in reversed(result.get("recent_activity", [])[-previous.MAX_NAVIGATION_PAGES:]):
        sequence = row.get("sequence")
        if type(sequence) is not int or not 1 <= sequence <= len(pairs):
            continue
        pair = pairs[sequence - 1]
        is_search = search_pair(pair)
        if not is_search and not previous._navigation_pair(pair):
            continue
        key = previous._key(pair)
        if shown_latest(view, pair, sequence):
            detail = dict(detail_status="already_in_latest_feedback", shown_at_sequence=sequence)
            represented[key] = sequence
        elif key in represented:
            detail = dict(detail_status="duplicate_returned_page", shown_at_sequence=represented[key])
        elif complete >= page_limit:
            detail = dict(detail_status="omitted_for_input_admission_budget")
        else:
            detail = dict(detail_status="complete_returned_navigation_page",
                          **(search_page(pair, candidate) if is_search else previous._page(pair, candidate)))
        row["navigation"] = detail
        if len(canonical_json_bytes(result)) - baseline_bytes > byte_limit:
            row["navigation"] = dict(detail_status="omitted_for_navigation_byte_allowance")
            if len(canonical_json_bytes(result)) - baseline_bytes > byte_limit:
                row.pop("navigation")
        elif detail["detail_status"] == "complete_returned_navigation_page":
            represented[key] = sequence
            complete += 1
    return result


class SearchNavigationMixin:
    """Place before an existing NavigationMixin-based task session.

    The inherited admission loop calls self.view for every optional-detail trial,
    so the same stored page setting controls this joint projection. No new mutable
    state or checkpoint field is introduced. A successor must add the reference.
    """
    def view(self, **kwargs):
        value = super().view(**kwargs)
        limit = self.last.get(previous.SETTING, previous.MAX_NAVIGATION_PAGES) if self.last else previous.MAX_NAVIGATION_PAGES
        return project(value, self.pairs, self.candidate,
                       page_limit=limit if self.navigation_enabled else -1,
                       byte_limit=self.navigation_byte_limit)
