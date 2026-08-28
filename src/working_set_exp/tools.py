from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .candidate import Candidate, CandidateError, canonical_path
from .isolation import run_checker
from .jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes


MAX_ACTION_BYTES = 5_000
MAX_READ_CONTENT_BYTES = 18_000
MAX_RESULT_BYTES = 22_000


class ToolError(RuntimeError):
    pass


@dataclass
class SessionState:
    candidate: Candidate
    stage: str = "prefix"
    complete_reads: set[str] = field(default_factory=set)
    read_coverage: dict[str, list[tuple[int, int]]] = field(default_factory=dict)
    prefork_check_passed: bool = False
    public_check_passed: bool = False
    probe_done: bool = False
    fork_ready: bool = False
    submitted: bool = False

    def clone_for_branch(self) -> "SessionState":
        return SessionState(
            candidate=self.candidate,
            stage="continuation",
            complete_reads=set(self.complete_reads),
            read_coverage={path: list(ranges) for path, ranges in self.read_coverage.items()},
            prefork_check_passed=self.prefork_check_passed,
            public_check_passed=False,
            probe_done=self.probe_done,
            fork_ready=self.fork_ready,
            submitted=False,
        )


def strict_action(raw: bytes) -> dict[str, Any]:
    if len(raw) > MAX_ACTION_BYTES:
        raise ToolError("action exceeds byte bound")
    try:
        value = load_json_strict(raw)
    except (UnicodeDecodeError, ValueError) as exc:
        raise ToolError(f"response is not one strict JSON value: {exc}") from exc
    if not isinstance(value, dict) or not isinstance(value.get("action"), str):
        raise ToolError("response must be one JSON action object")
    return value


class ToolExecutor:
    def __init__(
        self,
        state: SessionState,
        *,
        required_full_reads: tuple[str, ...],
        prefork_checker: bytes,
        public_checker: bytes,
        final_target: str,
        probe_id: str | None,
        probe_body: str | None,
        reopenable: dict[str, bytes] | None = None,
    ):
        self.state = state
        self.required_full_reads = required_full_reads
        self.prefork_checker = prefork_checker
        self.public_checker = public_checker
        self.final_target = final_target
        self.probe_id = probe_id
        self.probe_body = probe_body
        self.reopenable = reopenable if reopenable is not None else {}

    def _bounded(self, result: dict[str, Any]) -> dict[str, Any]:
        if len(canonical_json_bytes(result)) > MAX_RESULT_BYTES:
            raise ToolError("tool result exceeds complete result bound")
        return result

    def execute(self, action: dict[str, Any]) -> dict[str, Any]:
        name = action.get("action")
        try:
            if name == "begin":
                return self._bounded({"accepted": True, "stage": self.state.stage})
            if name == "tree":
                return self._tree(action)
            if name == "search":
                return self._search(action)
            if name == "read":
                return self._read(action)
            if name == "patch":
                return self._patch(action)
            if name == "check":
                return self._check(action)
            if name == "probe":
                return self._probe(action)
            if name == "fork_ready":
                return self._fork_ready(action)
            if name == "reopen_observation":
                return self._reopen(action)
            if name == "submit":
                return self._submit(action)
            raise ToolError("unknown action")
        except (CandidateError, ToolError, KeyError, TypeError, ValueError) as exc:
            return self._bounded({"accepted": False, "error_code": "tool_rejected", "detail": str(exc)})

    def _tree(self, action: dict[str, Any]) -> dict[str, Any]:
        if set(action) != {"action", "path", "offset", "limit"}:
            raise ToolError("tree action shape differs")
        offset, limit = action["offset"], action["limit"]
        if not isinstance(offset, int) or isinstance(offset, bool) or offset < 0:
            raise ToolError("tree offset invalid")
        if not isinstance(limit, int) or isinstance(limit, bool) or not 1 <= limit <= 16:
            raise ToolError("tree limit invalid")
        rows = self.state.candidate.directories(action["path"])
        page = rows[offset:offset + limit]
        return self._bounded(
            {
                "accepted": True,
                "path": action["path"],
                "offset": offset,
                "limit": limit,
                "total_entries": len(rows),
                "next_offset": offset + len(page) if offset + len(page) < len(rows) else None,
                "entries": [{"path": path, "kind": kind} for path, kind in page],
                "candidate_id": self.state.candidate.candidate_id,
            }
        )

    def _search(self, action: dict[str, Any]) -> dict[str, Any]:
        if set(action) != {"action", "path", "query", "offset", "limit"}:
            raise ToolError("search action shape differs")
        path = action["path"]
        root = "" if path == "." else canonical_path(path)
        query = action["query"]
        offset, limit = action["offset"], action["limit"]
        if not isinstance(query, str) or not query or len(query.encode("utf-8")) > 128:
            raise ToolError("search query invalid")
        if not isinstance(offset, int) or offset < 0 or not isinstance(limit, int) or not 1 <= limit <= 16:
            raise ToolError("search paging invalid")
        matches: list[dict[str, Any]] = []
        prefix = "" if not root else root + "/"
        for file_path, data in self.state.candidate.files:
            if root and file_path != root and not file_path.startswith(prefix):
                continue
            for number, line in enumerate(data.decode("utf-8").splitlines(), 1):
                if query.casefold() in line.casefold():
                    matches.append({"path": file_path, "line": number, "text": line[:320]})
        page = matches[offset:offset + limit]
        return self._bounded(
            {
                "accepted": True,
                "path": path,
                "query": query,
                "offset": offset,
                "total_matches": len(matches),
                "next_offset": offset + len(page) if offset + len(page) < len(matches) else None,
                "matches": page,
                "candidate_id": self.state.candidate.candidate_id,
            }
        )

    def _read(self, action: dict[str, Any]) -> dict[str, Any]:
        if set(action) != {"action", "path", "start_line", "line_count"}:
            raise ToolError("read action shape differs")
        path = canonical_path(action["path"])
        start, count = action["start_line"], action["line_count"]
        if not isinstance(start, int) or isinstance(start, bool) or start < 1:
            raise ToolError("read start_line invalid")
        if not isinstance(count, int) or isinstance(count, bool) or not 1 <= count <= 500:
            raise ToolError("read line_count invalid")
        data = self.state.candidate.file_map.get(path)
        if data is None:
            raise ToolError("read path does not exist")
        text = data.decode("utf-8")
        lines = text.splitlines(keepends=True)
        if not lines and start == 1:
            selected: list[str] = []
        elif start > len(lines):
            selected = []
        else:
            selected = lines[start - 1:start - 1 + count]
        while selected and len("".join(selected).encode("utf-8")) > MAX_READ_CONTENT_BYTES:
            selected.pop()
        if lines and start <= len(lines) and not selected:
            raise ToolError("one source line cannot fit the read result")
        content = "".join(selected)
        returned_end = start + len(selected) - 1 if selected else None
        next_line = returned_end + 1 if returned_end is not None and returned_end < len(lines) else None
        complete = next_line is None
        if not lines and start == 1:
            self.state.complete_reads.add(path)
        elif selected and returned_end is not None:
            ranges = [*self.state.read_coverage.get(path, []), (start, returned_end)]
            merged: list[tuple[int, int]] = []
            for first, last in sorted(ranges):
                if not merged or first > merged[-1][1] + 1:
                    merged.append((first, last))
                else:
                    merged[-1] = (merged[-1][0], max(merged[-1][1], last))
            self.state.read_coverage[path] = merged
            if merged[0][0] == 1 and merged[0][1] >= len(lines):
                self.state.complete_reads.add(path)
        return self._bounded(
            {
                "accepted": True,
                "path": path,
                "requested_start_line": start,
                "requested_line_count": count,
                "returned_start_line": start if selected else None,
                "returned_end_line": returned_end,
                "next_start_line": next_line,
                "complete": complete,
                "content": content,
                "candidate_id": self.state.candidate.candidate_id,
                "file_sha256": sha256_bytes(data),
            }
        )

    def _patch(self, action: dict[str, Any]) -> dict[str, Any]:
        required = {"action", "path", "old", "new", "expected_candidate_id", "expected_file_sha256"}
        if set(action) != required:
            raise ToolError("patch action shape differs")
        if self.state.stage == "prefix" and action["path"] == self.final_target:
            raise ToolError("final target is unavailable until after fork_ready")
        successor, diff = self.state.candidate.patch(
            path=action["path"],
            old=action["old"],
            new=action["new"],
            expected_candidate_id=action["expected_candidate_id"],
            expected_file_sha256=action["expected_file_sha256"],
        )
        previous = self.state.candidate.candidate_id
        self.state.candidate = successor
        # A successful mutation invalidates any check result bound to the
        # predecessor. Historical experiments always checked after their last
        # patch, so this strengthens version integrity without changing their
        # model-visible trajectories.
        self.state.prefork_check_passed = False
        self.state.public_check_passed = False
        return self._bounded(
            {
                "accepted": True,
                "path": action["path"],
                "previous_candidate_id": previous,
                "candidate_id": successor.candidate_id,
                "file_sha256": successor.file_sha256(action["path"]),
                "diff": diff,
            }
        )

    def _check(self, action: dict[str, Any]) -> dict[str, Any]:
        if set(action) != {"action", "check_id", "expected_candidate_id"}:
            raise ToolError("check action shape differs")
        if action["expected_candidate_id"] != self.state.candidate.candidate_id:
            raise ToolError("stale check candidate binding")
        check_id = action["check_id"]
        if check_id == "prefork" and self.state.stage == "prefix":
            result = run_checker(self.state.candidate, self.prefork_checker)
            self.state.prefork_check_passed = result["passed"]
        elif check_id == "public" and self.state.stage in {"continuation", "recurrent"}:
            result = run_checker(self.state.candidate, self.public_checker)
            self.state.public_check_passed = result["passed"]
        else:
            raise ToolError("check ID is unavailable in the current stage")
        return self._bounded(
            {
                "accepted": True,
                "check_id": check_id,
                "checked_candidate_id": self.state.candidate.candidate_id,
                **result,
            }
        )

    def _probe(self, action: dict[str, Any]) -> dict[str, Any]:
        if set(action) != {"action", "probe_id"} or self.state.stage not in {"prefix", "recurrent"}:
            raise ToolError("probe action is unavailable")
        if self.probe_id is None or action["probe_id"] != self.probe_id or self.probe_body is None:
            raise ToolError("probe ID is unavailable")
        self.state.probe_done = True
        return self._bounded(
            {
                "accepted": True,
                "probe_id": self.probe_id,
                "candidate_id": self.state.candidate.candidate_id,
                "observation": self.probe_body,
            }
        )

    def _fork_ready(self, action: dict[str, Any]) -> dict[str, Any]:
        if set(action) != {"action", "expected_candidate_id"} or self.state.stage not in {"prefix", "recurrent"}:
            raise ToolError("fork_ready action is unavailable")
        if action["expected_candidate_id"] != self.state.candidate.candidate_id:
            raise ToolError("stale fork candidate binding")
        missing = sorted(set(self.required_full_reads) - self.state.complete_reads)
        if missing:
            raise ToolError("required complete reads remain: " + ",".join(missing))
        check_passed = self.state.prefork_check_passed if self.state.stage == "prefix" else self.state.public_check_passed
        if not check_passed:
            raise ToolError("current boundary check has not passed")
        if self.probe_id is not None and not self.state.probe_done:
            raise ToolError("required compatibility probe has not run")
        self.state.fork_ready = True
        return self._bounded(
            {
                "accepted": True,
                "fork_ready": True,
                "candidate_id": self.state.candidate.candidate_id,
                "pending_stage": "continuation",
            }
        )

    def _reopen(self, action: dict[str, Any]) -> dict[str, Any]:
        if set(action) != {"action", "handle"} or self.state.stage not in {"continuation", "recurrent"}:
            raise ToolError("reopen_observation is unavailable")
        handle = action["handle"]
        if handle not in self.reopenable:
            raise ToolError("observation handle is unavailable")
        body = self.reopenable[handle]
        return self._bounded(
            {
                "accepted": True,
                "handle": handle,
                "exact_result_utf8": body.decode("utf-8"),
                "exact_result_sha256": sha256_bytes(body),
                "size_bytes": len(body),
            }
        )

    def _submit(self, action: dict[str, Any]) -> dict[str, Any]:
        if set(action) != {"action", "expected_candidate_id"} or self.state.stage != "continuation":
            raise ToolError("submit action is unavailable")
        if action["expected_candidate_id"] != self.state.candidate.candidate_id:
            raise ToolError("stale submission binding")
        self.state.submitted = True
        return self._bounded(
            {
                "accepted": True,
                "submitted_candidate_id": self.state.candidate.candidate_id,
                "public_check_passed_for_candidate": self.state.public_check_passed,
            }
        )


def action_schema(stage: str, *, probe_id: str | None) -> dict[str, Any]:
    def obj(properties: dict[str, Any], required: list[str]) -> dict[str, Any]:
        return {"type": "object", "properties": properties, "required": required, "additionalProperties": False}

    const = lambda value: {"type": "string", "const": value}
    text = {"type": "string", "minLength": 1, "maxLength": 2_000}
    path = {"type": "string", "minLength": 1, "maxLength": 160}
    sha = {"type": "string", "pattern": "^[0-9a-f]{64}$"}
    begin = obj({"action": const("begin")}, ["action"])
    tree = obj({"action": const("tree"), "path": path, "offset": {"type": "integer", "minimum": 0, "maximum": 128}, "limit": {"type": "integer", "minimum": 1, "maximum": 16}}, ["action", "path", "offset", "limit"])
    search = obj({"action": const("search"), "path": path, "query": {"type": "string", "minLength": 1, "maxLength": 128}, "offset": {"type": "integer", "minimum": 0, "maximum": 2_000_000}, "limit": {"type": "integer", "minimum": 1, "maximum": 16}}, ["action", "path", "query", "offset", "limit"])
    read = obj({"action": const("read"), "path": path, "start_line": {"type": "integer", "minimum": 1, "maximum": 2_000_000}, "line_count": {"type": "integer", "minimum": 1, "maximum": 500}}, ["action", "path", "start_line", "line_count"])
    patch_fragment = {"type": "string", "minLength": 0, "maxLength": 512}
    patch = obj({"action": const("patch"), "path": path, "old": patch_fragment, "new": patch_fragment, "expected_candidate_id": sha, "expected_file_sha256": sha}, ["action", "path", "old", "new", "expected_candidate_id", "expected_file_sha256"])
    check = obj({"action": const("check"), "check_id": {"type": "string", "enum": ["prefork", "public"]}, "expected_candidate_id": sha}, ["action", "check_id", "expected_candidate_id"])
    fork = obj({"action": const("fork_ready"), "expected_candidate_id": sha}, ["action", "expected_candidate_id"])
    reopen = obj({"action": const("reopen_observation"), "handle": {"type": "string", "pattern": "^OBS-[0-9]{4}$"}}, ["action", "handle"])
    submit = obj({"action": const("submit"), "expected_candidate_id": sha}, ["action", "expected_candidate_id"])
    if stage == "setup":
        schema = begin
    elif stage == "prefix":
        options = [tree, search, read, patch, check, fork]
        if probe_id is not None:
            options.append(obj({"action": const("probe"), "probe_id": {"type": "string", "const": probe_id}}, ["action", "probe_id"]))
        schema = {"oneOf": options}
    elif stage == "continuation":
        options = [tree, search, read, patch, check, reopen, submit]
        schema = {"oneOf": options}
    elif stage == "recurrent":
        options = [tree, search, read, patch, check, reopen, fork]
        if probe_id is not None:
            options.append(obj({"action": const("probe"), "probe_id": {"type": "string", "const": probe_id}}, ["action", "probe_id"]))
        schema = {"oneOf": options}
    else:
        raise ValueError("invalid response stage")
    return {
        "type": "json_schema",
        "json_schema": {
            "name": f"experiment_002_{stage}_action",
            "strict": True,
            "schema": schema,
        },
    }
