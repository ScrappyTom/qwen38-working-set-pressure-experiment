"""Declared continuation of actual saved work, with corrected host boundaries."""
import copy
from functools import lru_cache
from pathlib import Path

import parser_roundtrip as prior
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_session import ContributionSession
from working_set_exp.jsonutil import sha256_file

ROOT, base = prior.ROOT, prior.base
pilot = base.pilot
AREA = ROOT / "development/working_set_continuation"
SOURCE = ROOT / "development/reasoning_allocation/run-001/A03"
PACKAGE, RUN, MANIFEST = AREA / "preparation-001", AREA / "run-001", AREA / "EXECUTION_MANIFEST.json"
ACTOR, SEED = {**prior.ACTOR, "effort": "medium"}, 961210
MAX_REQUESTS, MAX_OPERATIONS = 16, 24
STARTING_ID = "047eeceb0bc5b21006965a5acec83b6f79e1ddcb4ea8744b30985d3c20c52f78"
read, save, require = prior.read, prior.save, prior.require
verify_sources, runtime_paths, candidate_bytes = prior.verify_sources, prior.runtime_paths, prior.candidate_bytes
XHIGH = ("Reasoning effort is set to xhigh. Please think carefully through the task, "
         "validate key assumptions, consider plausible alternatives, and prioritize "
         "correctness, consistency, and clarity in the final answer.")


@lru_cache(maxsize=1)
def starting_work():
    seal = read(SOURCE / "SEAL.json")
    require(seal["status"] == "checked_submission", "starting contribution was not checked")
    inventory = {r["path"]: r for r in seal["files"]}
    for name in ("final-state.json", "final-candidate.json"):
        require(sha256_file(SOURCE / name) == inventory[name]["sha256"], "saved work differs")
    work, state = read(SOURCE / "final-candidate.json"), read(SOURCE / "final-state.json")
    candidate = Candidate.create({r["path"]: r["content_utf8"].encode() for r in work["files"]},
                                 max_file_bytes=work["max_file_bytes"])
    require(candidate.candidate_id == state["candidate_id"] == STARTING_ID, "starting identity differs")
    return candidate, state


@lru_cache(maxsize=1)
def checker():
    candidate, _ = starting_work()
    prefix = "_BACKPORT_HARNESS = " + repr(prior.base.task.checker().decode()) + "\n"
    prefix += "_SAVED_FILES = " + repr({p: b.decode() for p, b in candidate.files}) + "\n"
    return prefix.encode() + (AREA / "PUBLIC_CHECK.py").read_bytes()


def initial_session():
    candidate, state = starting_work()
    session = ContributionSession(candidate, checker(), (AREA / "TASK.txt").read_text(encoding="utf-8"),
        pairs=state["pairs"], call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS)
    session.ranges, session.saved = copy.deepcopy(state["ranges"]), copy.deepcopy(state["saved"])
    session.diffs = {int(k): v for k, v in state["diffs"].items()}
    session.last = copy.deepcopy(state["last"])
    return session


def snapshot(session):
    return {**prior.snapshot(session), "request_limit": session.request_limit, "requests_used": session.requests_used}


def expected_native(request):
    require(request["seed"] == SEED and request["chat_template_kwargs"] ==
            dict(enable_thinking=True, reasoning_effort="medium"), "actor override differs")
    control = copy.deepcopy(request)
    control["seed"] = prior.SEED
    control["chat_template_kwargs"] = dict(enable_thinking=True, reasoning_effort="xhigh")
    native = prior.expected_native(control)
    head = ("<|im_start|>system\n" + XHIGH + "\n\n").encode()
    require(native.startswith(head), "qualified template instruction differs")
    return b"<|im_start|>system\n" + native[len(head):]


def source_identities():
    extra = [*AREA.glob("*.py"), *AREA.glob("*.txt"), AREA / "SPEC.md",
             ROOT / "tests/test_working_boundaries.py", ROOT / "tests/test_working_continuation.py",
             *(SOURCE / n for n in ("SEAL.json", "final-state.json", "final-candidate.json"))]
    return {**prior.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in extra}}
