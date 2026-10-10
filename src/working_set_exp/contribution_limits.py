"""Declared spending controls; never interpret reasoning or certify progress."""
from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import time

from .jsonutil import sha256_bytes


class SpendingStop(RuntimeError):
    def __init__(self, reason, *, data=b"", status=None):
        super().__init__(reason)
        self.reason, self.data, self.status = reason, data, status


@dataclass(frozen=True)
class Limits:
    request_seconds: float
    total_seconds: float
    unchecked_edit_seconds: float

    def __post_init__(self):
        for value in asdict(self).values():
            if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or value <= 0:
                raise ValueError("every spending limit must be a finite positive number")
        if self.request_seconds > self.total_seconds:
            raise ValueError("request limit cannot exceed the whole attempt")


class SpendingControl:
    def __init__(self, limits, *, qualifying_check_ids=("public",), clock=time.monotonic, wall_clock=time.time):
        self.limits, self.clock = limits, clock
        self.wall_clock = wall_clock
        if not qualifying_check_ids or any(not isinstance(s, str) or not s for s in qualifying_check_ids):
            raise ValueError("declare the check scopes that count as an observation")
        self.qualifying_check_ids = tuple(qualifying_check_ids)
        self.started = clock()
        self.unchecked_since = None
        self.requests_completed = 0
        self.model_seconds = 0.0

    def remaining(self):
        now = self.clock()
        choices = [(self.limits.total_seconds - (now - self.started), "attempt_elapsed_limit")]
        if self.unchecked_since is not None:
            choices.append((self.limits.unchecked_edit_seconds - (now - self.unchecked_since),
                            "unchecked_edit_elapsed_limit"))
        seconds, reason = min(choices)
        if seconds <= 0:
            raise SpendingStop(reason)
        return seconds, reason

    def request_allowance(self):
        remaining, reason = self.remaining()
        return min((remaining, reason), (self.limits.request_seconds, "request_elapsed_limit"))

    def observe_reply(self, session, first_operation, elapsed):
        if not math.isfinite(elapsed) or elapsed < 0:
            raise ValueError("invalid completed request duration")
        self.requests_completed += 1
        self.model_seconds += elapsed
        self.observe_operations(session, first_operation)

    def observe_operations(self, session, first_operation):
        for pair in session.pairs[first_operation:]:
            action, result = pair["response"], pair["result"]
            if not result.get("accepted"):
                continue
            if action["action"] in session.mutation_actions:
                if self.unchecked_since is None:
                    self.unchecked_since = self.clock()
            elif (action["action"] == "check" and "passed" in result
                  and result.get("check_id") in self.qualifying_check_ids
                  and result.get("check_id") in session.checkers
                  and result.get("checked_candidate_id") == session.candidate.candidate_id
                  and result.get("check_definition_sha256") == sha256_bytes(session.checkers[result["check_id"]])
                  and (result.get("executed") is True or "returncode" in result)):
                # A genuine failed check supplies evidence too. A stale/rejected
                # request, retrieved result or account claim does not reset this.
                self.unchecked_since = None

    def snapshot(self):
        now = self.clock()
        return dict(limits=asdict(self.limits), elapsed_seconds=now - self.started,
            recorded_at_unix=self.wall_clock(),
            qualifying_check_ids=list(self.qualifying_check_ids),
            unchecked_edit_elapsed_seconds=None if self.unchecked_since is None else now - self.unchecked_since,
            requests_completed=self.requests_completed, model_seconds=self.model_seconds)

    @classmethod
    def restore(cls, value, *, clock=time.monotonic, wall_clock=time.time):
        control = cls(Limits(**value["limits"]), qualifying_check_ids=value["qualifying_check_ids"], clock=clock, wall_clock=wall_clock)
        elapsed = value["elapsed_seconds"]
        unchecked = value["unchecked_edit_elapsed_seconds"]
        model_seconds = value["model_seconds"]
        recorded_at = value["recorded_at_unix"]
        if any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v < 0
               for v in (elapsed, model_seconds, recorded_at, *([] if unchecked is None else [unchecked]))):
            raise ValueError("invalid saved spending record")
        if unchecked is not None and unchecked > elapsed:
            raise ValueError("unchecked duration exceeds attempt duration")
        if type(value["requests_completed"]) is not int or value["requests_completed"] < 0:
            raise ValueError("invalid saved request count")
        downtime = wall_clock() - recorded_at
        if downtime < 0:
            raise ValueError("saved spending clock is in the future; do not reset the allowance")
        # A restart must not refund time spent after the last saved checkpoint.
        # Restoration alone does not authorize resuming a stopped attempt.
        control.started -= elapsed + downtime
        control.unchecked_since = None if unchecked is None else control.clock() - unchecked - downtime
        control.requests_completed = value["requests_completed"]
        control.model_seconds = model_seconds
        return control
