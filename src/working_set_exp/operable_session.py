"""Opt-in observation custody and a bounded, reversible recovery presentation."""
from __future__ import annotations

import copy

from . import accounted_contribution as prior, operable_view, working_view
from .candidate import CandidateError
from .jsonutil import canonical_json_bytes, sha256_bytes
from .observations import check_report
from .tools import SessionState, ToolExecutor
from .working_session import CapacityError

MAX_TASK_BYTES = 8192
INVENTORY_PAGE = 8
INSPECTION_SOURCE_BYTES = 8192


class OperableSession(prior.AccountedSession):
    joint_selection_actions = ("work_on", "work_on_exact")
    preserve_executed_observations = True

    def __init__(self, candidate, checkers, task, *, observations, **kwargs):
        if len(task.encode()) > MAX_TASK_BYTES:
            raise ValueError("task exceeds the qualified 8,192-byte control-task allowance")
        if len(checkers) > 8 or any(len(k.encode()) > 32 for k in checkers):
            raise ValueError("check inventory exceeds supported control scope")
        self.observations = observations
        self.recovery = False
        self.recovery_obstacle = None
        self.control_tier = 0
        self._inspect_only = False
        super().__init__(candidate, checkers, task, **kwargs)

    def action_rule(self):
        return dict(oneOf=[*operable_view.action_rule(self.checkers)["oneOf"], prior.account_rule()])

    def reply_schema(self):
        return operable_view.reply_schema(self.checkers)

    @staticmethod
    def region(path, fingerprint, first, last):
        value = dict(path=path, file_sha256=fingerprint, start_line=first, end_line=last)
        return dict(region_ref="SRC-" + sha256_bytes(canonical_json_bytes(value)), **value)

    def source(self, span):
        value = super().source(span)
        value["region_ref"] = self.region(value["path"], value["file_sha256"],
            value["returned_start_line"], value["returned_end_line"])["region_ref"]
        return value

    def add_source(self, source):
        if not self._inspect_only:
            super().add_source(source)

    def selection_inventory(self, offset=0, count=INVENTORY_PAGE):
        rows = [dict(kind="source", **self.region(s["path"], self.candidate.file_sha256(s["path"]),
                                                 s["start_line"], s["end_line"])) for s in self.ranges]
        rows += [dict(kind="saved_record", handle=h, total_bytes=v["total_bytes"],
                      sha256=v["sha256"]) for h, v in sorted(self.saved.items())]
        page = rows[offset:offset + count]
        return dict(accepted=True, entries=page, offset=offset, total_entries=len(rows),
                    next_offset=offset + len(page) if offset + len(page) < len(rows) else None,
                    inventory_is_not_source_content=True)

    def summary(self, sequence):
        row = super().summary(sequence)
        pair = self.pairs[sequence - 1]
        if pair["response"]["action"] == "work_on_exact":
            row["source_paths"] = sorted({s["path"] for s in pair["result"].get("sources", [])})
        return row

    def resolve_region(self, reference):
        known = self.selection_inventory(count=len(self.ranges) + len(self.saved))["entries"]
        for pair in self.pairs:
            result = pair["result"]
            if not result.get("accepted"):
                continue
            known.extend(result.get("regions", []))
            sources = [result["source"]] if "source" in result else result.get("sources", [])
            for s in sources:
                if s.get("kind") == "current_source":
                    known.append(self.region(s["path"], s["file_sha256"],
                                             s["returned_start_line"], s["returned_end_line"]))
        for row in known:
            if row.get("region_ref") == reference:
                if self.candidate.file_sha256(row["path"]) != row["file_sha256"]:
                    raise ValueError("source region is stale; obtain a current source reference")
                return {k: row[k] for k in ("path", "start_line", "end_line")}
        raise ValueError("source region reference has not been provided by this host")

    def enter_recovery(self, reason):
        self.recovery, self.control_tier = True, 0
        self.recovery_obstacle = dict(reason=reason, sequence=len(self.pairs),
            result_handle=f"RES-{len(self.pairs):04d}" if self.pairs else None)

    def view(self, **kwargs):
        if self.recovery:
            kwargs["recent_count"] = 0
        value = super().view(**kwargs)
        value["presentation"] = dict(mode="recovery" if self.recovery else "ordinary",
            selected_bodies_omitted=self.recovery,
            ordinary_resumes="after an admitted selection replacement",
            obstacle=copy.deepcopy(self.recovery_obstacle) if self.recovery else None)
        if not self.recovery:
            return value
        value["working_set"] = dict(sources=[], saved_results=[])
        value["selection"] = self.selection_inventory(count=(8, 2, 0)[self.control_tier])
        value["current_p0"] = dict(path=".", access="p0_page", complete_for_repository=False)
        account = value["working_account"]
        if account:
            raw = account.pop("text").encode()
            prefix = raw[:512 if self.control_tier == 0 else 0].decode("utf-8", errors="ignore")
            account.update(text_prefix=prefix, full_text_bytes=len(raw), text_complete=len(prefix.encode()) == len(raw),
                           exact_text_in=account["action_handle"])
        inspect = bool(self.last and self.last.get("recovery_inspection"))
        value["latest_feedback"] = operable_view.feedback_view(self.last, recovery=True,
            limit=20000 if inspect else (20000, 2048, 1024)[self.control_tier], show_inspection=inspect)
        return value

    def mark_delivered(self, view):
        if view != self.view():
            raise ValueError("delivered recovery presentation differs")
        super().mark_delivered(view)

    def _fits(self, measure, *, margin=1024):
        if self.recovery and self.last and self.last.get("recovery_inspection"):
            sources = self.feedback_sources(self.last)
            if sum(len(s.get("content", "").encode()) for s in sources) > INSPECTION_SOURCE_BYTES:
                return False
            if len(canonical_json_bytes(self.last["result"])) > 16_384:
                return False
        return super()._fits(measure, margin=margin)

    def _fits_feedback(self, measure):
        if not self.recovery and super()._fits_feedback(measure):
            return True
        if not self.recovery:
            self.enter_recovery("ordinary feedback did not fit; selected bodies remain designated")
        for tier in range(self.control_tier, 3):
            self.control_tier = tier
            if self._fits(measure, margin=0):
                return True
        return False

    def _record(self, action, result):
        inspection = self.recovery and action["action"] in ("read", "inspect_observation", "reopen_result", "reopen_event")
        super()._record(action, result)
        if inspection:
            self.last["recovery_inspection"] = True
        error = str(result.get("error", ""))
        if not result.get("accepted") and any(s in error for s in
            ("cannot be placed beside", "cannot fit", "cannot be accepted beside", "not fit ordinary presentation")):
            self.enter_recovery("capacity rejection; previous selected material remains designated")

    def _fit_pages(self, action, spans, handles, measure, replace):
        if replace:
            staged = self.clone()
            staged.recovery, staged.recovery_obstacle, staged.control_tier = False, None, 0
            return super(OperableSession, staged)._fit_pages(action, spans, handles, measure, True)
        if self.recovery:
            staged = self.clone()
            staged._inspect_only = True
            result = super(OperableSession, staged)._fit_pages(action, spans, handles, measure, False)
            result._inspect_only = False
            return result
        return super()._fit_pages(action, spans, handles, measure, replace)

    def _select(self, action, measure):
        if action["action"] == "work_on":
            return super()._select(action, measure)
        spans = [self.resolve_region(ref) for ref in action["regions"]]
        other = self.clone()
        other.recovery, other.recovery_obstacle, other.control_tier = False, None, 0
        other.ranges, other.saved = [], {}
        sources = [other.source(span) for span in spans]
        for source in sources:
            other.add_source(source)
        saved = []
        for handle in action["results"]:
            body = self.payload(handle)
            value = dict(kind="saved_bytes", handle=handle, offset=0, next_offset=None,
                         total_bytes=len(body), sha256=sha256_bytes(body), exact_utf8=body.decode())
            other.saved[handle] = value
            saved.append(value)
        other._record(action, dict(accepted=True, sources=sources, saved_results=saved, complete_requested_group=True))
        # A recovery view cannot qualify a promise of complete ordinary assembly.
        if not prior.AccountedSession._fits_feedback(other, measure):
            raise CapacityError("The complete identified group does not fit ordinary presentation; previous selection retained.")
        return other

    def _ordinary(self, action):
        name = action["action"]
        if name == "check":
            if action["expected_candidate_id"] != self.candidate.candidate_id:
                return dict(accepted=False, executed=False, error="stale check candidate binding")
            scope = action["check_id"]
            record = self.observations.execute(self.candidate, self.checkers[scope], scope,
                                               f"CHK-{len(self.pairs)+1:04d}")
            try:
                return check_report(self.observations, record)
            except Exception as error:
                # Execution and observation custody already happened. A faulty
                # report formatter cannot erase them or claim tool rejection.
                return dict(accepted=record["accepted"], executed=record["executed"],
                    check_id=scope, checked_candidate_id=self.candidate.candidate_id,
                    check_definition_sha256=sha256_bytes(self.checkers[scope]),
                    observation=record["observation"], passed=record.get("passed", False),
                    returncode=record.get("returncode"), capture_complete=record.get("capture_complete", False),
                    report_status="unavailable", report_error=type(error).__name__)
        if name == "inspect_observation":
            return self.observations.inspect(action["observation"], action["stream"], action["offset"])
        if name == "selection_page":
            return self.selection_inventory(action["offset"])
        if name in ("record_account", "history", "submit"):
            return super()._ordinary(action)
        state = SessionState(self.candidate, stage="continuation")
        executor = ToolExecutor(state, required_full_reads=(), prefork_checker=b"", public_checker=b"",
            final_target="", probe_id=None, probe_body=None, hierarchical_p0=True, archive_result_policy=True)
        result = executor.execute(action)
        if result.get("accepted"):
            regions = []
            if name == "search":
                for match in result["matches"]:
                    total = len(self.candidate.file_map[match["path"]].decode().splitlines())
                    region = self.region(match["path"], self.candidate.file_sha256(match["path"]),
                                         max(1, match["line"]-3), min(total, match["line"]+12))
                    regions.append(dict(**region, extent_kind="search context", match_line=match["line"]))
            elif name == "p0_page" and result.get("kind") == "file_outline":
                for row in result["entries"]:
                    regions.append(dict(**self.region(action["path"], self.candidate.file_sha256(action["path"]),
                        row["start_line"], row["end_line"]), extent_kind="outline source", name=row["name"]))
            if regions:
                result["regions"] = regions
        return result
