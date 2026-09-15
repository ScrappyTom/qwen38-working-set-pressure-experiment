"""Identified uncoached continuation from actual broad selection and rejection."""
import copy
from pathlib import Path

import task as original
from working_set_exp.jsonutil import sha256_file

ROOT, AREA = original.ROOT, Path(__file__).resolve().parent
ACTOR, SEED = dict(original.ACTOR), original.SEED
MAX_REQUESTS, MAX_OPERATIONS = 20, 60
SOURCE_RUN = original.AREA / "run-001"
SETUP = AREA / "SETUP.json"


def initial_session():
    state = original.read(SETUP)
    session = original.policy.AccountedSession(original.starting_candidate(),
        {scope: original.checker(scope) for scope in original.DESCRIPTIONS},
        (original.AREA / "TASK.txt").read_text(encoding="utf-8"),
        edit_checks={original.TEST: "tests", original.DOC: "public"},
        pairs=state["pairs"], call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS)
    for key in ("ranges", "saved", "last", "delivered_sources"):
        setattr(session, key, copy.deepcopy(state[key]))
    original.require(session.candidate.candidate_id == state["candidate_id"], "checkpoint candidate differs")
    original.require(len(session.pairs) == 4 and session.working_account() is None,
                     "checkpoint contains unapproved work or account")
    return session


def source_identities():
    paths = [*AREA.glob("*.py"), AREA / "PLAN.md", AREA / "SPEC.md", AREA / "SYSTEM.txt",
             ROOT / "tests/test_account_group.py", ROOT / "tests/test_feedback_history.py",
             SOURCE_RUN / "RESPONSE_SEAL.json", SOURCE_RUN / "after/C03-O01-state.json",
             SOURCE_RUN / "calls/C04-reply.json", SOURCE_RUN / "calls/C04-wire-request.json"]
    if SETUP.exists():
        paths.append(SETUP)
    return {**original.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


class Task:
    def __init__(self, scenario="complete"):
        self.scenario, self.condition = scenario, "recorded_recovery"
        self.PACKAGE = AREA / ("preparation-" + scenario + "-001")
        self.RUN, self.MANIFEST = AREA / "run-001", AREA / "EXECUTION_MANIFEST.json"
        self.VERIFICATION_NAME = "VERIFICATION-" + scenario + "-001.json"

    def __getattr__(self, name):
        return globals()[name] if name in globals() else getattr(original, name)


def __getattr__(name):
    return getattr(original, name)
