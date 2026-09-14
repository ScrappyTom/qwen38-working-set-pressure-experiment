"""Condition bindings for a single paired evidence-assembly comparison."""
import copy
from functools import lru_cache
from pathlib import Path

import interpolation_contribution as prior
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_session import ContributionSession
from working_set_exp.jsonutil import sha256_file

ROOT, AREA, SOURCE = prior.ROOT, Path(__file__).resolve().parent, prior.RUN
read, save, require = prior.read, prior.save, prior.require
GROUPS = read(AREA / "GROUPS.json")
STARTING_ID = "da233419db36b8dd9e943765a37b2d4fdfab6c17b7e9018ab239a0710eec9577"


@lru_cache(maxsize=1)
def starting_work():
    seal = read(SOURCE / "RESPONSE_SEAL.json")
    require(seal["aggregate_sha256"] == "5893802b52cf3547e323b38f8629453427b1556e57117bccd656087295c0b555",
            "historical attempt differs")
    files = {r["path"]: r for r in seal["files"]}
    names = ["after/C12-O01-candidate.json", "after/C12-O01-state.json"]
    for name in names:
        require(sha256_file(SOURCE / name) == files[name]["sha256"], "saved checkpoint differs")
    data, state = [read(SOURCE / n) for n in names]
    candidate = Candidate.create({r["path"]: r["content_utf8"].encode() for r in data["files"]},
                                 max_file_bytes=data["max_file_bytes"])
    require(candidate.candidate_id == state["candidate_id"] == STARTING_ID, "starting identity differs")
    require(len(state["pairs"]) == 67 and state["ranges"] == GROUPS["broad"], "checkpoint history/ranges differ")
    return candidate, state


class Task:
    ROOT, AREA, SOURCE = ROOT, AREA, SOURCE
    base, pilot, ACTOR, SEED = prior.base, prior.pilot, dict(prior.ACTOR), 961211
    MAX_REQUESTS, MAX_OPERATIONS, STARTING_ID = 8, 12, STARTING_ID
    read, save, require = staticmethod(read), staticmethod(save), staticmethod(require)
    checker, snapshot = staticmethod(prior.checker), staticmethod(prior.snapshot)
    verify_sources = staticmethod(prior.verify_sources)
    runtime_paths, candidate_bytes = staticmethod(prior.runtime_paths), staticmethod(prior.candidate_bytes)

    def __init__(self, condition, scenario="complete"):
        require(condition in GROUPS and scenario in ("complete", "correction"), "undeclared cell")
        self.condition, self.scenario = condition, scenario
        self.PACKAGE = AREA / "preparation-002" / condition / scenario
        self.RUN = AREA / "run-001" / condition
        self.MANIFEST = AREA / f"MANIFEST-{condition}.json"

    def initial_session(self):
        candidate, state = starting_work()
        session = ContributionSession(candidate, self.checker(), (AREA / "TASK.txt").read_text(encoding="utf-8"),
            pairs=state["pairs"], call_limit=self.MAX_OPERATIONS, request_limit=self.MAX_REQUESTS)
        session.ranges = copy.deepcopy(GROUPS[self.condition])
        session.diffs = {int(k): v for k, v in state["diffs"].items()}
        session.last = copy.deepcopy(state["last"])
        require(session.starting_archive_length == 67 and session.calls_used == session.requests_used == 0,
                "new allowance or historical ownership differs")
        return session

    def expected_native(self, request):
        require(request["seed"] == self.SEED and request["chat_template_kwargs"] ==
                dict(enable_thinking=True, reasoning_effort="medium"), "condition settings differ")
        original_seed = copy.deepcopy(request)
        original_seed["seed"] = prior.SEED
        return prior.expected_native(original_seed)

    def source_identities(self):
        paths = [*AREA.glob("*.py"), *AREA.glob("*.txt"), AREA / "SPEC.md", AREA / "GROUPS.json",
                 *(SOURCE / n for n in ("RESPONSE_SEAL.json", "after/C12-O01-state.json", "after/C12-O01-candidate.json")),
                 ROOT / "development/working_set_continuation/manage.py",
                 ROOT / "development/working_set_continuation/review/verify.py"]
        return {**prior.source_identities(), **{p.relative_to(ROOT).as_posix():sha256_file(p) for p in paths}}
