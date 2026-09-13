"""Separate continuation from saved parser work using the bounded host."""
from functools import lru_cache
from pathlib import Path

import configparser_backport as task
import configparser_work as legacy
import qualify_compiler_delivery as delivery
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.working_session import WorkingSession, INPUT_LIMIT
from working_set_exp.working_view import request

ROOT = task.ROOT
AREA = ROOT / "development/bounded_working_set"
OLD = task.AREA / "run-001"
PACKAGE = AREA / "preparation-002"
RUN = AREA / "run-001"
MANIFEST = AREA / "EXECUTION_MANIFEST.json"
ACTOR = dict(legacy.ACTOR)
CALL_LIMIT = 24
SEED = legacy.SEED
read = task.read
require = legacy.require
base, pilot = legacy.pilot.base, legacy.pilot


def save(folder, name, value):
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(value if isinstance(value, bytes) else canonical_json_bytes(value))


@lru_cache(maxsize=1)
def starting_evidence():
    require(sha256_file(OLD / "RESPONSE_SEAL.json") ==
            "9fb7edfd733c30217b701281abc2e5245c2894f2427f00e81e377e9ed9c7911d", "prior seal differs")
    inventory = {row["path"]: row for row in read(OLD / "RESPONSE_SEAL.json")["files"]}
    names = ["after/C32-candidate.json"] + [f"calls/C{i:02d}-host-result.json" for i in range(1,33)]
    for name in names:
        row, path = inventory[name], OLD / name
        require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"], "prior artifact differs: " + name)
    snapshot = read(OLD / names[0])
    candidate = Candidate.create({f["path"]: f["content_utf8"].encode() for f in snapshot["files"]}, max_file_bytes=task.FILE_LIMIT)
    require(candidate.candidate_id == snapshot["candidate_id"] ==
            "8ac73858f45e89ecb2df138e2accfdb105d0325ffc056e0bad7e9bf7e7c89a2d", "saved repair differs")
    pairs = []
    for name in names[1:]:
        result = read(OLD/name)
        require(result["executed"] and result["result"]["accepted"], "prior action disposition differs")
        pairs.append(dict(response=result["action"], result=result["result"]))
    return candidate, pairs


def initial_session():
    candidate, pairs = starting_evidence()
    return WorkingSession(candidate, task.checker(), (AREA/"TASK.txt").read_text(encoding="utf-8"),
                          pairs=pairs, call_limit=CALL_LIMIT)


@lru_cache(maxsize=1)
def original_request():
    return read(OLD/"admission/C01-x000-endpoint-request.json")


def request_for(view):
    settings = {k: v for k, v in original_request().items() if k not in {"messages", "response_format"}}
    require(settings["seed"] == SEED and settings["chat_template_kwargs"] ==
            dict(enable_thinking=True, reasoning_effort="xhigh"), "selected actor settings differ")
    return request(view, settings)


def expected_native(req):
    original = original_request()
    # The output schema constrains generation, not the native two-message text.
    # This declared schema change is verified against server rendering before
    # any new inference; all runtime/template/sampling fields stay fixed.
    anchor = {**original, "response_format": req["response_format"]}
    return delivery.native_for(req, anchor, (OLD/"admission/C01-x000-native.txt").read_text(encoding="utf-8"))


def candidate_bytes(candidate):
    return canonical_json_bytes(dict(candidate_id=candidate.candidate_id, max_file_bytes=candidate.max_file_bytes,
        files=[dict(path=p, content_utf8=b.decode(), sha256=sha256_bytes(b), size_bytes=len(b)) for p,b in candidate.files]))


def snapshot(session):
    return dict(candidate_id=session.candidate.candidate_id, ranges=session.ranges, saved=session.saved,
                pairs=session.pairs, last=session.last, starting_archive_length=session.starting_archive_length,
                call_limit=session.call_limit, submitted=session.submitted, delivery_blocked=session.delivery_blocked,
                delivered_sources=session.delivered_sources, diffs=session.diffs)


def source_identities():
    paths = [*sorted((ROOT/"src").rglob("*.py")), *sorted((ROOT/"scripts").glob("*.py")),
             ROOT/"tests/test_working_session.py", ROOT/"tests/test_bounded_parser.py",
             AREA/"SPEC.md", AREA/"TASK.txt", task.AREA/"PUBLIC_CHECK.py", OLD/"RESPONSE_SEAL.json"]
    return {p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}


def verify_sources(values):
    for name, expected in values.items():
        require(sha256_file(ROOT/name) == expected, "source changed: " + name)


def runtime_paths():
    launch = read(OLD/"private-runtime/launch.json")
    server, model = Path(launch[0]), Path(launch[2])
    tokenizer = server.with_name("llama-tokenize.exe")
    require(server.is_file() and model.is_file() and tokenizer.is_file(), "local pinned runtime is unavailable")
    return server, model, tokenizer
