"""Exact archive with a bounded decision view and transactional input admission.

This is an explicit development successor, not a change to frozen experiments.
The model selects relevant material; the host measures and fits whole pages.
"""
from __future__ import annotations

import copy
import difflib
from typing import Callable

from .candidate import Candidate, CandidateError, canonical_path, MAX_FILES, MAX_TOTAL_BYTES, MAX_LINE_BYTES
from .hierarchical_p0 import p0_page
from .jsonutil import canonical_json_bytes, sha256_bytes
from .tools import SessionState, ToolExecutor
from . import working_view


INPUT_LIMIT = 23_808
CONTROL_ROOM = 1_024
MAX_FRAGMENT_BYTES = 65_536
MAX_ACTION_BYTES = 1_048_576
RECENT_COUNT = 6
HISTORY_PAGE = 8


class CapacityError(ValueError):
    pass


class WorkingSession:
    def __init__(self, candidate: Candidate, checker: bytes, task: str, *, pairs=(), call_limit=24, request_limit=None):
        self.candidate, self.checker, self.task = candidate, checker, task
        self.pairs = copy.deepcopy(list(pairs))
        self.starting_archive_length = len(self.pairs)
        self.call_limit = call_limit
        if request_limit is not None and (type(request_limit) is not int or request_limit < 1):
            raise ValueError("request limit must be a positive integer")
        self.request_limit, self.requests_used = request_limit, 0
        self.ranges: list[dict] = []
        self.saved: dict[str, dict] = {}
        self.versions = {candidate.candidate_id: candidate}
        self.diffs: dict[int, str] = {}
        self.last = None
        self.submitted = False
        self.delivery_blocked = False
        self.delivered_sources: list[dict] = []
        self.admissions: list[dict] = []

    @property
    def calls_used(self):
        return len(self.pairs) - self.starting_archive_length

    def begin_request(self):
        """Count dispatch once, independently of operations in its eventual reply."""
        if self.request_limit is not None:
            if self.requests_used >= self.request_limit or self.submitted or self.delivery_blocked:
                raise ValueError("contribution request allowance is terminal")
            self.requests_used += 1

    def clone(self):
        other = copy.copy(self)
        other.pairs = list(self.pairs)
        other.ranges = copy.deepcopy(self.ranges)
        other.saved = copy.deepcopy(self.saved)
        other.versions, other.diffs = dict(self.versions), dict(self.diffs)
        other.admissions = []
        return other

    def check_state(self):
        for sequence in range(len(self.pairs), 0, -1):
            result = self.pairs[sequence-1]["result"]
            if result.get("accepted") and "checked_candidate_id" in result and "passed" in result:
                return dict(handle=f"RES-{sequence:04d}", candidate_id=result["checked_candidate_id"],
                            passed=result["passed"], applies_to_current=result["checked_candidate_id"] == self.candidate.candidate_id)
        return None

    def summary(self, sequence):
        pair = self.pairs[sequence-1]
        action, result = pair["response"], pair["result"]
        row = dict(sequence=sequence, episode="prior_work" if sequence <= self.starting_archive_length else "this_contribution",
                   action=action["action"], accepted=result.get("accepted"),
                   result_handle=f"RES-{sequence:04d}", action_handle=f"EVT-{sequence:04d}")
        for key in ("path", "handle", "check_id", "query"):
            if key in action:
                row[key] = action[key]
        if action["action"] == "work_on":
            row["source_paths"] = sorted({s["path"] for s in action["sources"]})
        for key in ("candidate_id", "previous_candidate_id", "checked_candidate_id", "passed", "submitted"):
            if key in result:
                row[key] = result[key]
        return row

    def source(self, span):
        path = canonical_path(span["path"])
        data = self.candidate.file_map[path]
        lines = data.decode().splitlines(keepends=True)
        first, last = span["start_line"], span["end_line"]
        if not lines:
            if first != 1:
                raise ValueError("empty file starts at line 1")
            last = 0
        elif not 1 <= first <= len(lines):
            raise ValueError("source start is beyond the file; use source locations or next_start_line")
        else:
            last = min(last or len(lines), len(lines))
            if last < first:
                raise ValueError("source end precedes start")
        return dict(kind="current_source", path=path, candidate_id=self.candidate.candidate_id,
                    file_sha256=self.candidate.file_sha256(path), returned_start_line=first,
                    returned_end_line=last, next_start_line=last+1 if last < len(lines) else None,
                    content="".join(lines[first-1:last]))

    def sources(self):
        return [self.source(span) for span in self.ranges]

    def add_source(self, source):
        self.ranges.append(dict(path=source["path"], start_line=source["returned_start_line"],
                                end_line=source["returned_end_line"]))
        merged = []
        for row in sorted(self.ranges, key=lambda s: (s["path"], s["start_line"])):
            if merged and row["path"] == merged[-1]["path"] and row["start_line"] <= merged[-1]["end_line"]+1:
                merged[-1]["end_line"] = max(merged[-1]["end_line"], row["end_line"])
            else:
                merged.append(dict(row))
        self.ranges = merged

    @staticmethod
    def feedback_sources(feedback):
        if not feedback:
            return []
        result = feedback["result"]
        return ([result["source"]] if "source" in result else result.get("sources", []))

    def _verified_source_ranges(self, sources):
        """Union only exact, version-bound, displayed whole-line source fragments."""
        spans = []
        for source in sources:
            path = source.get("path")
            first, last = source.get("returned_start_line"), source.get("returned_end_line")
            if (source.get("kind") != "current_source" or path not in self.candidate.file_map or
                    source.get("candidate_id") != self.candidate.candidate_id or
                    source.get("file_sha256") != self.candidate.file_sha256(path) or
                    type(first) is not int or type(last) is not int):
                continue
            span = dict(path=path, start_line=first, end_line=last)
            try:
                exact = self.source(span)
            except ValueError:
                continue
            if (exact["returned_start_line"] != first or exact["returned_end_line"] != last or
                    exact["content"] != source.get("content")):
                continue
            spans.append(span)
        merged = []
        for span in sorted(spans, key=lambda s: (s["path"], s["start_line"])):
            if (merged and span["path"] == merged[-1]["path"] and
                    span["start_line"] <= merged[-1]["end_line"] + 1):
                merged[-1]["end_line"] = max(merged[-1]["end_line"], span["end_line"])
            else:
                merged.append(dict(span))
        return merged

    def _sources_outside_feedback(self, latest_sources):
        covered = self._verified_source_ranges(latest_sources)
        remaining = []
        for selected in self.ranges:
            pieces = [dict(selected)]
            for span in covered:
                next_pieces = []
                for piece in pieces:
                    if piece["path"] != span["path"]:
                        next_pieces.append(piece)
                    elif piece["end_line"] == 0 and span["end_line"] == 0:
                        pass  # The empty file is already fully displayed.
                    elif span["end_line"] < piece["start_line"] or span["start_line"] > piece["end_line"]:
                        next_pieces.append(piece)
                    else:
                        if piece["start_line"] < span["start_line"]:
                            next_pieces.append({**piece, "end_line": span["start_line"] - 1})
                        if piece["end_line"] > span["end_line"]:
                            next_pieces.append({**piece, "start_line": span["end_line"] + 1})
                pieces = next_pieces
            remaining.extend(self.source(piece) for piece in pieces)
        return remaining

    def view(self, *, recent_count=RECENT_COUNT):
        latest_sources = self.feedback_sources(self.last)
        sources = self._sources_outside_feedback(latest_sources)
        latest_saved = [] if not self.last else self.last["result"].get("saved_results", [])
        if self.last and self.last["result"].get("kind") == "saved_bytes":
            latest_saved.append(self.last["result"])
        saved = [s for s in self.saved.values() if s not in latest_saved]
        n = len(self.pairs)
        allowance = dict(actions_used=self.calls_used, actions_remaining=self.call_limit-self.calls_used)
        if self.request_limit is not None:
            allowance.update(request_limit=self.request_limit, requests_used=self.requests_used,
                requests_remaining=self.request_limit-self.requests_used,
                request_counting="Remaining requests include the response to this input. Each response consumes one request; its operations consume the separate action allowance.")
        return dict(schema_version="bounded-working-view-v1", task=self.task,
                    candidate_id=self.candidate.candidate_id, current_check=self.check_state(),
                    candidate_limits=dict(existing_files_only=True, max_files=MAX_FILES,
                        max_file_utf8_bytes=self.candidate.max_file_bytes, max_total_utf8_bytes=MAX_TOTAL_BYTES,
                        max_line_utf8_bytes=MAX_LINE_BYTES),
                    current_p0=p0_page(self.candidate, path=".", offset=0),
                    working_set=dict(sources=sources, saved_results=saved), latest_feedback=self.last,
                    recent_activity=[self.summary(i) for i in range(max(1, n-recent_count+1), n+1)] if recent_count else [],
                    archive=dict(action_count=n, prior_work_actions=self.starting_archive_length,
                                 access="history pages and exact result/action retrieval; older records are not all displayed"),
                    allowance=allowance)

    def mark_delivered(self, view):
        if view["candidate_id"] != self.candidate.candidate_id:
            raise ValueError("delivered view has stale current candidate")
        expected = self.view()
        for key in ("task", "working_set", "latest_feedback", "current_check", "archive", "allowance", "candidate_limits", "current_p0"):
            if view[key] != expected[key]:
                raise ValueError("delivered working state differs")
        self.delivered_sources = copy.deepcopy(view["working_set"]["sources"] + self.feedback_sources(view["latest_feedback"]))
        pages = list(view["working_set"]["saved_results"])
        if view["latest_feedback"]:
            result = view["latest_feedback"]["result"]
            pages.extend(result.get("saved_results", []))
            if result.get("kind") == "saved_bytes":
                pages.append(result)
        for page in pages:
            self.delivered_sources.extend(self._archived_sources_visible(page))

    def _archived_sources_visible(self, page):
        """Credit only a fully displayed archived acquisition of unchanged source.

        The source may belong to an older candidate if this file is unchanged.
        Partial serialized results, action text and snippets do not establish
        source delivery. Do not infer hidden fields or recursively mine payloads.
        """
        handle = page.get("handle", "")
        if (page.get("kind") != "saved_bytes" or not handle.startswith("RES-") or
                page.get("offset") != 0 or page.get("next_offset") is not None):
            return []
        body = self.payload(handle)
        if (page.get("exact_utf8", "").encode() != body or page.get("total_bytes") != len(body) or
                page.get("sha256") != sha256_bytes(body)):
            return []
        pair = self.pairs[int(handle.split("-", 1)[1])-1]
        result, action = pair["result"], pair["response"]["action"]
        if not result.get("accepted"):
            return []
        if action == "read":
            sources = [result.get("source", result)]  # Includes legacy exact reads.
        elif action == "work_on":
            sources = result.get("sources", [])
        else:
            return []
        verified = []
        for source in sources:
            path = source.get("path")
            data = self.candidate.file_map.get(path)
            if data is None or source.get("file_sha256") != sha256_bytes(data):
                continue
            first, last = source.get("returned_start_line"), source.get("returned_end_line")
            if not data and source.get("content") == "" and first in (None, 1) and last in (None, 0):
                first, last = 1, 0
            elif (type(first) is not int or type(last) is not int or
                    not 1 <= first <= last <= len(data.decode().splitlines())):
                continue
            current = self.source(dict(path=path, start_line=first, end_line=last))
            if current["content"] == source.get("content"):
                verified.append(current)
        return verified

    def payload(self, handle):
        prefix, number = handle.split("-", 1)
        sequence = int(number)
        if not 1 <= sequence <= len(self.pairs) or prefix not in {"RES", "EVT"}:
            raise ValueError("saved address is unavailable")
        pair = self.pairs[sequence-1]
        return canonical_json_bytes(pair["result"] if prefix == "RES" else pair["response"])

    def _record(self, action, result):
        self.pairs.append(dict(response=copy.deepcopy(action), result=copy.deepcopy(result)))
        summary = {k: v for k, v in action.items() if k not in {"old", "new", "sources", "results"}}
        self.last = dict(sequence=len(self.pairs), action_summary=summary, result=result)

    def _fits(self, measure: Callable, *, margin=CONTROL_ROOM):
        count = measure(self.view())
        self.admissions.append(dict(prompt_tokens=count, margin=margin, candidate_id=self.candidate.candidate_id))
        return count <= INPUT_LIMIT-margin

    def _fit_pages(self, action, spans, handles, measure, replace):
        full = [self.source(s) for s in spans]
        lengths = [max(0, s["returned_end_line"]-s["returned_start_line"]+1) for s in full]
        saved = []
        for handle in handles:
            body = self.payload(handle)
            saved.append(dict(kind="saved_bytes", handle=handle, offset=0, next_offset=None,
                              total_bytes=len(body), sha256=sha256_bytes(body), exact_utf8=body.decode()))
        # One common scale keeps multiple requested sources together; the host
        # does the sizing. Requested end positions remain upper bounds.
        def trial(scale, margin):
            other = self.clone()
            if replace:
                other.ranges, other.saved = [], {}
            sources = []
            for original, length in zip(full, lengths):
                size = min(length, max(1, length*scale//1_000_000)) if length else 0
                span = dict(path=original["path"], start_line=original["returned_start_line"],
                            end_line=original["returned_start_line"]+size-1)
                source = other.source(span)
                other.add_source(source)
                sources.append(source)
            for item in saved:
                other.saved[item["handle"]] = item
            result = (dict(accepted=True, source=sources[0]) if action["action"] == "read" else
                      dict(accepted=True, sources=sources, saved_results=saved))
            other._record(action, result)
            return other if other._fits(measure, margin=margin) else None
        # Bulk acquisition normally leaves headroom. That reserve is spendable:
        # it must not become a second hard ceiling on an otherwise deliverable
        # next page or group. No existing selected source is silently removed.
        for margin in (CONTROL_ROOM, 0):
            result = trial(1_000_000, margin)
            if result:
                return result
            low, high, best = 0, 999_999, None
            while low <= high:
                middle = (low+high)//2
                current = trial(middle, margin)
                if current:
                    best, low = current, middle+1
                else:
                    high = middle-1
            if best is not None:
                return best
            if not replace:
                # Deduplication can remove a trailing selected fragment when
                # feedback reaches its end. A shorter page can therefore cost
                # MORE input, and binary search can miss a fitting interval.
                # Before rejecting an acquisition, test these known layout
                # boundaries with the same exact whole-input admission gate.
                scales = set()
                for original, length in zip(full, lengths):
                    if not length:
                        continue
                    for retained in self.ranges:
                        if retained["path"] != original["path"]:
                            continue
                        for end in (retained["start_line"]-1, retained["start_line"],
                                    retained["end_line"], retained["end_line"]+1):
                            size = end-original["returned_start_line"]+1
                            if 0 < size < length:
                                scales.add((size*1_000_000+length-1)//length)
                for scale in sorted(scales, reverse=True):
                    current = trial(scale, margin)
                    if current:
                        return current
        raise CapacityError("The requested source cannot be placed beside the working set. Use work_on to select the material needed together, or inspect a narrower source location.")

    def _refresh_ranges(self, path, old_text, new_text, start, end, replacement):
        offsets = [0]
        for line in old_text.splitlines(keepends=True):
            offsets.append(offsets[-1]+len(line))
        delta = len(replacement)-(end-start)
        def moved(position, right):
            if position <= start:
                return position
            if position >= end:
                return position+delta
            return start+len(replacement) if right else start
        for span in self.ranges:
            if span["path"] != path:
                continue
            left = offsets[span["start_line"]-1]
            right = offsets[span["end_line"]]
            overlaps = left <= start <= right if start == end else left < end and right > start
            first, last = moved(left, False), moved(right, True)
            if overlaps:
                first, last = min(first, start), max(last, start+len(replacement))
            count = len(new_text.splitlines(keepends=True))
            span["start_line"] = min(count, new_text[:first].count("\n")+1) if count else 1
            span["end_line"] = max(span["start_line"], min(count, new_text[:max(first, last-1)].count("\n")+1)) if count else 0
        # Regenerate and merge adjacent windows after the line transformation.
        sources = self.sources()
        self.ranges = []
        for source in sources:
            self.add_source(source)

    def _patch(self, action):
        path = canonical_path(action["path"])
        before = self.candidate
        if action["expected_candidate_id"] != before.candidate_id or action["expected_file_sha256"] != before.file_sha256(path):
            raise ValueError("stale candidate or pre-edit file binding")
        old, new = action["old"], action["new"]
        if max(len(old.encode()), len(new.encode())) > MAX_FRAGMENT_BYTES:
            raise ValueError("complete edit exceeds the host's 65,536 UTF-8-byte fragment allowance; no edit committed")
        text = before.file_map[path].decode()
        if old == new or text.count(old) != 1:
            raise ValueError("old must identify exactly one occurrence and the edit must change it")
        if not any(span["path"] == path and old in self.source(span)["content"]
                   for span in self._verified_source_ranges(self.delivered_sources)):
            raise ValueError("exact current old source was not visible in the preceding input")
        start, end = text.index(old), text.index(old)+len(old)
        changed = text[:start]+new+text[end:]
        files = before.file_map
        files[path] = changed.encode()
        self.candidate = Candidate.create(files, max_file_bytes=before.max_file_bytes)
        self.versions[self.candidate.candidate_id] = self.candidate
        self._refresh_ranges(path, text, changed, start, end, new)
        self.diffs[len(self.pairs)+1] = "".join(difflib.unified_diff(text.splitlines(keepends=True),
            changed.splitlines(keepends=True), fromfile="a/"+path, tofile="b/"+path))
        return dict(accepted=True, path=path, previous_candidate_id=before.candidate_id,
                    candidate_id=self.candidate.candidate_id, file_sha256=self.candidate.file_sha256(path),
                    replaced_source_lines=[text[:start].count("\n")+1,text[:end-1].count("\n")+1] if old else [],
                    replacement_source_lines=[changed[:start].count("\n")+1,changed[:start+len(new)-1].count("\n")+1] if new else [],
                    exact_action_handle=f"EVT-{len(self.pairs)+1:04d}")

    def _reopen(self, action, measure):
        body = self.payload(action["handle"])
        offset = action["offset"]
        if not 0 <= offset <= len(body):
            raise ValueError("saved offset exceeds the result")
        remaining = body[offset:].decode()  # Reject a guessed non-UTF-8 boundary.
        def trial(size):
            other = self.clone()
            text = remaining[:size]
            next_offset = offset+len(text.encode())
            result = dict(accepted=True, kind="saved_bytes", handle=action["handle"], offset=offset,
                          next_offset=next_offset if next_offset < len(body) else None,
                          total_bytes=len(body), sha256=sha256_bytes(body), exact_utf8=text)
            other.saved[action["handle"]] = result
            other._record(action, result)
            return other if other._fits(measure, margin=0) else None
        best = trial(len(remaining))
        if best:
            return best
        low, high = 1, len(remaining)-1
        while low <= high:
            middle = (low+high)//2
            result = trial(middle)
            if result:
                best, low = result, middle+1
            else:
                high = middle-1
        if best is None:
            raise CapacityError("Saved content cannot fit beside the working set; select the evidence needed together with work_on.")
        return best

    def _ordinary(self, action):
        if action["action"] == "history":
            before = action["before"] or len(self.pairs)+1
            rows = []
            for sequence in range(min(before-1, len(self.pairs)), 0, -1):
                row = self.summary(sequence)
                if not action["path"] or row.get("path") == action["path"] or action["path"] in row.get("source_paths", []):
                    rows.append(row)
                if len(rows) == HISTORY_PAGE:
                    break
            return dict(accepted=True, entries=rows, next_before=rows[-1]["sequence"] if rows and rows[-1]["sequence"] > 1 else None)
        checked = self.check_state()
        if action["action"] == "submit" and not (checked and checked["applies_to_current"] and checked["passed"]):
            return dict(accepted=False, error="the current candidate has no passing public check")
        state = SessionState(self.candidate, stage="continuation",
                             public_check_passed=bool(checked and checked["applies_to_current"] and checked["passed"]))
        executor = ToolExecutor(state, required_full_reads=(), prefork_checker=b"", public_checker=self.checker,
                                final_target="", probe_id=None, probe_body=None, hierarchical_p0=True,
                                read_mode="maximal_bounded_page")
        result = executor.execute(action)
        self.submitted = state.submitted
        return result

    def execute(self, action, measure):
        if self.submitted or self.delivery_blocked or self.calls_used >= self.call_limit:
            raise ValueError("contribution is terminal")
        try:
            if len(canonical_json_bytes(action)) > MAX_ACTION_BYTES:
                raise ValueError("serialized action exceeds host allowance")
            working_view.validate(action, working_view.schema()["json_schema"]["schema"])
            name = action["action"]
            if name == "read":
                spans = [{k: action[k] for k in ("path", "start_line", "end_line")}]
                proposed = self._fit_pages(action, spans, [], measure, False)
            elif name == "work_on":
                proposed = self._fit_pages(action, action["sources"], action["results"], measure, True)
            elif name in {"reopen_result", "reopen_event"}:
                proposed = self._reopen(action, measure)
            else:
                proposed = self.clone()
                result = proposed._patch(action) if name == "patch" else proposed._ordinary(action)
                proposed._record(action, result)
                if not proposed._fits(measure, margin=0):
                    if name == "patch":
                        raise CapacityError("The complete edit and refreshed working material cannot fit the next input; no edit committed. Select a narrower relevant working set with work_on.")
                    # Read-only tools may produce long output. Preserve the exact
                    # result; deliver its actual status and an explicit page address.
                    keys = {"accepted", "candidate_id", "checked_candidate_id", "check_id", "passed", "returncode", "error", "submitted"}
                    brief = {k: v for k, v in result.items() if k in keys}
                    proposed.last = {**proposed.last, "result": brief,
                                     "output_scope": "status_only_full_result_archived",
                                     "full_result_handle": f"RES-{len(proposed.pairs):04d}"}
                    if not proposed._fits(measure, margin=0):
                        # The read-only operation did happen. Preserve its actual
                        # result and stop, rather than relabeling it a rejection.
                        proposed.delivery_blocked = True
        except (CandidateError, ValueError, KeyError, UnicodeError) as error:
            proposed = self.clone()
            proposed._record(action, dict(accepted=False, error=str(error)))
            if not proposed._fits(measure, margin=0):
                raise CapacityError("Rejection cannot be delivered; no state transition committed") from error
        self.__dict__.update(proposed.__dict__)
        return self.pairs[-1]["result"]
