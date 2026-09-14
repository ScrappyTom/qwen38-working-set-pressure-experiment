"""One new uncoached attempt from the actual rejected-proposal checkpoint."""
import copy
import importlib.util
from pathlib import Path

import study
from working_set_exp.contribution_session import ContributionSession
from working_set_exp.jsonutil import sha256_file

AREA = Path(__file__).resolve().parent
_spec = importlib.util.spec_from_file_location("grouped_action_qualification",
    AREA.parent / "grouped-actions/qualify.py")
grouped = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(grouped)


class Task(study.Task):
    AREA = AREA
    SEED = 961212
    MAX_REQUESTS, MAX_OPERATIONS = 8, 12

    def __init__(self, scenario="complete"):
        study.require(scenario in ("complete", "correction"), "undeclared scenario")
        self.condition, self.scenario = "pending_work", scenario
        self.PACKAGE = AREA / "preparation-001" / scenario
        self.RUN = AREA / "run-001"
        self.MANIFEST = AREA / "EXECUTION_MANIFEST.json"

    def initial_session(self):
        original, _ = grouped.checkpoint()
        session = ContributionSession(original.candidate, self.checker(),
            (AREA / "TASK.txt").read_text(encoding="utf-8"), pairs=original.pairs,
            call_limit=self.MAX_OPERATIONS, request_limit=self.MAX_REQUESTS)
        for key in ("ranges", "saved", "diffs", "last"):
            setattr(session, key, copy.deepcopy(getattr(original, key)))
        study.require(session.starting_archive_length == 71 and session.calls_used == session.requests_used == 0,
                      "new allowance or historical ownership differs")
        study.require(session.candidate.candidate_id == study.STARTING_ID and
                      session.pairs[-1]["response"]["action"] == "patch" and
                      session.pairs[-1]["result"]["accepted"] is False, "starting rejection differs")
        return session

    def source_identities(self):
        paths = [*AREA.glob("*.py"), *AREA.glob("*.txt"), AREA / "SPEC.md",
                 AREA.parent / "grouped-actions/qualify.py", AREA.parent / "pending-work/qualify.py",
                 AREA.parent / "run-001/assembled/RESPONSE_SEAL.json",
                 AREA.parent / "run-001/assembled/after/C04-O01-state.json",
                 AREA.parent / "run-001/assembled/after/C04-O01-candidate.json",
                 AREA.parent / "manage.py"]
        return {**super().source_identities(),
                **{p.relative_to(study.ROOT).as_posix(): sha256_file(p) for p in paths}}
