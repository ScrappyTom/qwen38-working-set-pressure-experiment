"""A new coverage contribution on the completed backport; no live coaching."""
from functools import lru_cache
from pathlib import Path

import bounded_parser as base
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_session import ContributionSession
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file
from working_set_exp.working_session import WorkingSession

ROOT = base.ROOT
AREA = ROOT / "development/uncoached_contribution"
SOURCE = base.AREA / "parser-documentation/turn-04"
PACKAGE = AREA / "preparation-001"
RUN = AREA / "run-001"
MANIFEST = AREA / "EXECUTION_MANIFEST.json"
ACTOR, SEED = dict(base.ACTOR), base.SEED
MAX_REQUESTS, MAX_OPERATIONS = 16, 24
STARTING_ID = "fbfc4f7a4edf09b8670fb8b0e8700258f59c22114ab6bdc6915beab9b9b89e75"
SOURCE_SEAL = "f239a6dcc1418ed6770ce062c9525af5f1e25cc70dfb1ba3bba14ba5c2921436"
read, save, require = base.read, base.save, base.require


@lru_cache(maxsize=1)
def starting_work():
    require(sha256_file(SOURCE / "RESPONSE_SEAL.json") == SOURCE_SEAL, "saved contribution seal differs")
    inventory = {r["path"]: r for r in read(SOURCE / "RESPONSE_SEAL.json")["files"]}
    for name in ("final-state.json", "final-candidate.json"):
        require(sha256_file(SOURCE / name) == inventory[name]["sha256"], "saved work differs")
    saved, state = read(SOURCE / "final-candidate.json"), read(SOURCE / "final-state.json")
    candidate = Candidate.create({r["path"]: r["content_utf8"].encode() for r in saved["files"]},
                                 max_file_bytes=saved["max_file_bytes"])
    require(candidate.candidate_id == saved["candidate_id"] == state["candidate_id"] == STARTING_ID,
            "starting version differs")
    return candidate, state


def checker():
    candidate, _ = starting_work()
    prefix = "_BASELINE_FILES = " + repr({p: b.decode() for p, b in candidate.files}) + "\n"
    prefix += "_LEGACY_HARNESS_SOURCE = " + repr(base.task.checker().decode()) + "\n"
    return prefix.encode() + (AREA / "PUBLIC_CHECK.py").read_bytes()


def initial_session(session_type=ContributionSession):
    candidate, prior = starting_work()
    session = session_type(candidate, checker(), (AREA / "TASK.txt").read_text(encoding="utf-8"),
                           pairs=prior["pairs"], call_limit=MAX_OPERATIONS)
    session.diffs = {int(k): v for k, v in prior["diffs"].items()}
    # No selected source, hand-picked result or reviewer dialogue is supplied.
    return session


def source_identities():
    extra = [*sorted(AREA.glob("*.py")), *(AREA / n for n in ("TASK.txt", "SYSTEM.txt", "SPEC.md")),
             ROOT / "tests/test_uncoached_contribution.py", ROOT / "tests/test_roundtrip_task.py",
             *(SOURCE / n for n in ("RESPONSE_SEAL.json", "final-candidate.json", "final-state.json"))]
    return {**base.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in extra}}


verify_sources, runtime_paths = base.verify_sources, base.runtime_paths
expected_native, snapshot, candidate_bytes = base.expected_native, base.snapshot, base.candidate_bytes
