"""One prepared contribution from the original C05 view, with fresh accounting."""
import copy
import json
from pathlib import Path

import study
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_session import ContributionSession
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

AREA = Path(__file__).resolve().parent
ORIGIN = AREA.parent / "pending-contribution/run-001"
ORIGIN_SEAL = "c8d7f16179a81002211b588196a656d7eb2ffb7a96678174e6c4ac8c30908bc4"
STEM = "after/C04-O01"
PROPOSAL = "EVT-0073"


def checkpoint():
    study.require(sha256_file(ORIGIN / "RESPONSE_SEAL.json") == ORIGIN_SEAL, "origin seal differs")
    seal = study.read(ORIGIN / "RESPONSE_SEAL.json")
    study.require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "origin inventory differs")
    records = verify_records(ORIGIN / "records.jsonl", ORIGIN)
    inventory = {row["path"]: row for row in seal["files"]}
    names = [STEM + "-state.json", STEM + "-candidate.json", "calls/C05-wire-request.json",
             "calls/C04-operation-01.json", "records.jsonl"]
    for name in names:
        path, row = ORIGIN / name, inventory[name]
        study.require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"], "origin artifact differs: " + name)
    state, work, request = [study.read(ORIGIN / name) for name in names[:3]]
    candidate = Candidate.create({row["path"]: row["content_utf8"].encode() for row in work["files"]},
                                 max_file_bytes=work["max_file_bytes"])
    study.require(candidate.candidate_id == state["candidate_id"] == work["candidate_id"] == study.STARTING_ID,
                  "origin candidate differs")
    study.require(len(state["pairs"]) == 75 and state["requests_used"] == 4 and
                  state["starting_archive_length"] == 71 and state["last"]["sequence"] == 75,
                  "origin checkpoint differs")
    study.require(state["pairs"][-1]["response"] == study.read(ORIGIN / names[3])["action"], "last operation differs")
    view = json.loads(request["messages"][1]["content"])["workspace"]
    return candidate, state, view, len(records)


class Task(study.Task):
    AREA, SOURCE = AREA, ORIGIN
    SEED = 961213
    MAX_REQUESTS, MAX_OPERATIONS = 8, 12

    def __init__(self, scenario="complete"):
        study.require(scenario in ("complete", "correction"), "undeclared scenario")
        self.condition, self.scenario = "recovery_c05", scenario
        self.PACKAGE = AREA / "preparation-001" / scenario
        self.RUN = AREA / "run-001"
        self.MANIFEST = AREA / "EXECUTION_MANIFEST.json"

    def initial_session(self):
        candidate, state, old_view, _ = checkpoint()
        text = (AREA / "TASK.txt").read_text(encoding="utf-8")
        study.require(text == old_view["task"], "task contract changed")
        current = ContributionSession(candidate, self.checker(), text, pairs=state["pairs"],
                                      call_limit=self.MAX_OPERATIONS, request_limit=self.MAX_REQUESTS)
        for key in ("ranges", "saved", "last"):
            setattr(current, key, copy.deepcopy(state[key]))
        current.diffs = {int(k): value for k, value in state["diffs"].items()}
        historical = current.clone()
        historical.starting_archive_length = state["starting_archive_length"]
        historical.requests_used = state["requests_used"]
        study.require(historical.view() == old_view, "original C05 view does not reconstruct")
        study.require(current.starting_archive_length == 75 and current.calls_used == current.requests_used == 0 and
                      current.delivered_sources == [], "fresh accounting or delivery differs")
        return current

    def source_identities(self):
        paths = [*AREA.glob("*.py"), *(AREA / name for name in ("SPEC.md", "SYSTEM.txt", "TASK.txt")),
                 *(ORIGIN / name for name in ("RESPONSE_SEAL.json", "records.jsonl", STEM + "-state.json",
                    STEM + "-candidate.json", "calls/C05-wire-request.json", "calls/C04-operation-01.json")),
                 AREA.parent / "pending-contribution/TASK.txt", AREA.parent / "pending-contribution/SYSTEM.txt",
                 AREA.parent / "manage.py"]
        return {**super().source_identities(), **{p.relative_to(study.ROOT).as_posix(): sha256_file(p) for p in paths}}
