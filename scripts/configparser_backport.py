"""Task assembly for a real larger-source maintenance contribution; no inference."""
from pathlib import Path
import sys

from working_set_exp.candidate import Candidate
from working_set_exp.ecological_pilot_v2 import EcologicalFixture
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file

ROOT = Path(__file__).resolve().parents[1]
AREA = ROOT / "development/configparser_backport"
FILE_LIMIT = 1_048_576


def read(path):
    return load_json_strict(path.read_bytes())


def verified_files():
    result = {}
    donor = AREA / "donor-001"
    screen = read(AREA / "screen-002/SCREEN.json")
    assert sha256_file(donor / "SEAL.json") == screen["donor_seal_sha256"]
    for row in screen["records"]:
        path = donor / row["path"]
        raw = path.read_bytes()
        assert len(raw) == row["size_bytes"] and sha256_bytes(raw) == row["sha256"]
        result[row["path"]] = raw
    support = AREA / "test-support-001"
    for row in read(support / "SEAL.json")["files"]:
        path = support / row["path"]
        raw = path.read_bytes()
        assert len(raw) == row["size_bytes"] and sha256_bytes(raw) == row["sha256"]
        assert row["path"] not in result
        result[row["path"]] = raw
    return result


def checker(*, upstream_only=False):
    prefix = "\n".join((
        "_UPSTREAM_ONLY = " + repr(upstream_only),
        "_UPSTREAM_TEST_SOURCE = " + repr((AREA / "donor-001/Lib/test/test_configparser.py").read_text(encoding="utf-8")),
        "_ORIGINAL_PARSER_SOURCE = " + repr((AREA / "donor-001/Lib/configparser.py").read_text(encoding="utf-8")),
    )) + "\n"
    return prefix.encode() + (AREA / "PUBLIC_CHECK.py").read_bytes()


def fixture():
    return EcologicalFixture("CONFIGPARSER-BACKPORT", "larger_source_maintenance_development",
        (AREA / "TASK.txt").read_text(encoding="utf-8"),
        Candidate.create(verified_files(), max_file_bytes=FILE_LIMIT), checker(), b"", (), (),
        {"development_only": True, "known_historical_backport": True}, ())
