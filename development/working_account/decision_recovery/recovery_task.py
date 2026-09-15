"""Paired development presentation at the actual acquisition rejection boundary."""
import copy
from pathlib import Path

import task as original
from working_set_exp.jsonutil import sha256_file

ROOT, AREA = original.ROOT, Path(__file__).resolve().parent
SOURCE = original.PARENT / "url_continuation/run-001"
CHECKPOINT = SOURCE / "after/C01-O01-state.json"
ACTOR, SEED = dict(original.ACTOR), 961220
MAX_REQUESTS, MAX_OPERATIONS = 12, 36
FRAME_PATH = AREA / "FRAME_CANDIDATE.txt"
CAPACITY_ERROR = ("The requested source cannot be placed beside the working set. "
                  "Use work_on to select the material needed together, or inspect a narrower source location.")


class RecoverySession(original.policy.AccountedSession):
    def __init__(self, *args, focused=False, **kwargs):
        self.focused = focused
        super().__init__(*args, **kwargs)

    def view(self, **kwargs):
        state = super().view(**kwargs)
        last = state["latest_feedback"]
        if (self.focused and last and last["action_summary"]["action"] in ("read", "work_on")
                and last["result"].get("accepted") is False
                and last["result"].get("error") == CAPACITY_ERROR):
            state["decision_focus"] = FRAME_PATH.read_text(encoding="utf-8").strip()
        return state

    def mark_delivered(self, view):
        if view.get("decision_focus") != self.view().get("decision_focus"):
            raise ValueError("delivered recovery framing differs")
        super().mark_delivered(view)


def initial_session(condition="ordinary", *, recent=0):
    original.require(condition in ("ordinary", "focused"), "undeclared condition")
    saved = original.read(CHECKPOINT)
    session = RecoverySession(original.starting_candidate(),
        {scope: original.checker(scope) for scope in original.DESCRIPTIONS},
        (original.AREA / "TASK.txt").read_text(encoding="utf-8"),
        edit_checks={original.TEST: "tests", original.DOC: "public"},
        pairs=copy.deepcopy(saved["pairs"]), call_limit=MAX_OPERATIONS,
        request_limit=MAX_REQUESTS, focused=(condition == "focused"))
    for key in ("ranges", "saved", "last", "delivered_sources"):
        setattr(session, key, copy.deepcopy(saved[key]))
    original.require(session.candidate.candidate_id == saved["candidate_id"] and len(session.pairs) == 5,
                     "recorded rejection checkpoint differs")
    original.require(session.working_account() is None and session.last["result"]["error"] == CAPACITY_ERROR,
                     "unexpected work or feedback in checkpoint")
    # A common bounded recent-history presentation keeps paired starting inputs
    # identical apart from the candidate frame. Exact prior operations remain.
    session.last["recent_activity_limit"] = recent
    return session


def expected_native(request):
    original.require(request["seed"] == SEED, "matched seed differs")
    normalized = copy.deepcopy(request)
    normalized["seed"] = original.SEED
    return original.expected_native(normalized)


def source_identities():
    files = [*AREA.glob("*.py"), AREA / "PLAN.md", AREA / "SPEC.md", AREA / "SYSTEM.txt", FRAME_PATH,
             CHECKPOINT, SOURCE / "RESPONSE_SEAL.json", SOURCE / "calls/C02-wire-request.json"]
    return {**original.source_identities(),
            **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in files}}


class Task:
    def __init__(self, condition="ordinary", scenario="complete", version="001"):
        self.condition, self.scenario = condition, scenario
        self.PACKAGE = AREA / f"preparation-{condition}-{scenario}-{version}"
        self.RUN = AREA / f"run-{condition}-001"
        self.MANIFEST = AREA / f"EXECUTION-{condition}.json"
        self.VERIFICATION_NAME = f"VERIFICATION-{condition}-{scenario}-{version}.json"

    def initial_session(self):
        return initial_session(self.condition)

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(original, name)


def __getattr__(name):
    return getattr(original, name)
