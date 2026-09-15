"""Frozen fresh URL-port contribution on the opt-in account/check policy."""
import copy
from functools import lru_cache
from pathlib import Path

import interpolation_contribution as prior
import run_uncoached_contribution as runner
from working_set_exp import accounted_contribution as policy
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import sha256_file

ROOT, base, pilot = prior.ROOT, prior.base, prior.pilot
AREA = ROOT / "development/working_account/url_ports"
PARENT = AREA.parent
ACTOR, SEED = dict(prior.ACTOR), 961219
MAX_REQUESTS, MAX_OPERATIONS = 20, 60
read, save, require = prior.read, prior.save, prior.require
verify_sources, runtime_paths = prior.verify_sources, prior.runtime_paths
snapshot, candidate_bytes = prior.snapshot, prior.candidate_bytes
TEST, DOC = "Lib/test/test_urlparse.py", "Doc/library/urllib.parse.rst"
FILES = ("Lib/urllib/__init__.py", "Lib/urllib/parse.py", "Lib/test/__init__.py", TEST, DOC, "LICENSE")
DESCRIPTIONS = dict(tests="Saved and edited tests, required port-access paths, exact-error/boundary fault sensitivity, and preservation.",
                    examples="Execute added documentation examples and assess preservation.",
                    public="All tests and added examples with preservation; prose still needs direct review.")
process_reply = policy.process_reply


def reply_schema():
    return policy.reply_schema(DESCRIPTIONS)


def operating_reference():
    return policy.operating_reference(DESCRIPTIONS)


def expected_native(request):
    require(request["seed"] == SEED, "fresh task seed differs")
    normalized = copy.deepcopy(request)
    normalized["seed"] = prior.SEED
    return prior.expected_native(normalized)


@lru_cache(maxsize=1)
def starting_candidate():
    rows = {r["path"]: r for r in read(AREA / "SOURCE.json")["files"]}
    for p in FILES:
        require(sha256_file(AREA / "world" / p) == rows[p]["sha256"], "upstream source differs: " + p)
    return Candidate.create({p: (AREA / "world" / p).read_bytes() for p in FILES}, max_file_bytes=1048576)


@lru_cache(maxsize=3)
def checker(scope="public"):
    require(scope in DESCRIPTIONS, "unknown scope")
    values = dict(_BASELINE_FILES={p: b.decode() for p, b in starting_candidate().files}, _SCOPE=scope,
                  _EXAMPLES_HELPER=(PARENT / "examples.py").read_text(encoding="utf-8"))
    return ("".join(k + " = " + repr(v) + "\n" for k, v in values.items()).encode()
            + (AREA / "CHECK.py").read_bytes())


def initial_session():
    return policy.AccountedSession(starting_candidate(), {s: checker(s) for s in DESCRIPTIONS},
        (AREA / "TASK.txt").read_text(encoding="utf-8"), edit_checks={TEST: "tests", DOC: "public"},
        call_limit=MAX_OPERATIONS, request_limit=MAX_REQUESTS)


def source_identities():
    own = [*PARENT.glob("*.py"), PARENT / "PLAN.md", *AREA.glob("*.py"),
           *(AREA / n for n in ("TASK.txt", "SYSTEM.txt", "REFERENCE_DOC.txt")),
           AREA / "SPEC.md", AREA / "SOURCE.json", *(AREA / "world" / p for p in FILES),
           ROOT / "development/evidence_assembly/manage.py",
           ROOT / "development/working_set_continuation/review/verify.py",
           ROOT / "development/evidence_assembly/grouped-actions/native.py",
           ROOT / "development/bounded_working_set/parser-documentation/grammar-review/native_order_probe_gbnf.py",
           ROOT / "development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py",
           ROOT / "tests/test_accounted_contribution.py"]
    return {**prior.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in own}}


class Task:
    def __init__(self, scenario="complete", version="003"):
        self.scenario, self.condition = scenario, "fresh"
        self.PACKAGE = AREA / f"preparation-{scenario}-{version}"
        self.RUN, self.MANIFEST = AREA / "run-001", AREA / "EXECUTION_MANIFEST.json"
        self.VERIFICATION_NAME = f"VERIFICATION-{scenario}-{version}.json"

    def __getattr__(self, name):
        try:
            return globals()[name]
        except KeyError:
            raise AttributeError(name) from None
