"""Behavioral acceptance; expected results are explicit, not donor comparisons."""
from pathlib import Path
from datetime import timezone
import json
import math
import sys

sys.path.insert(0, str(Path("src").resolve()))
from shiftledger.api import daily_minutes
from shiftledger.importing import read_shifts
from shiftledger.windows import day_window

HEADER = "employee,start,end,status\n"
failures = []


def equal(label, actual, expected):
    if isinstance(expected, dict):
        passed = isinstance(actual, dict) and actual.keys() == expected.keys()
        passed = passed and all(math.isclose(actual[k], v, abs_tol=1e-9) for k, v in expected.items())
    else:
        passed = actual == expected
    print(json.dumps({"case": label, "passed": passed, "expected": expected, "actual": actual}, sort_keys=True))
    if not passed:
        failures.append(label)


def report(label, rows, expected, day="2026-07-15", offset="+02:00"):
    try:
        actual = daily_minutes(HEADER + "\n".join(rows) + "\n", day, offset)
        equal(label, actual, expected)
    except Exception as error:
        failures.append(label)
        print(json.dumps({"case": label, "passed": False, "exception": type(error).__name__, "message": str(error)}))


overnight = "ada,2026-07-14T23:30:00+02:00,2026-07-15T01:30:00+02:00,confirmed"
decoded = read_shifts(HEADER + overnight + "\n")
equal("decoded record count", len(decoded), 1)
equal("decoded employee and status", [decoded[0].employee, decoded[0].status], ["ada", "confirmed"])
equal("decoded start instant", decoded[0].start.isoformat(), "2026-07-14T21:30:00+00:00")
equal("decoded end instant", decoded[0].end.isoformat(), "2026-07-14T23:30:00+00:00")
window = day_window("2026-07-15", "+02:00")
equal("report window instants", [window.start.astimezone(timezone.utc).isoformat(), window.end.astimezone(timezone.utc).isoformat()],
      ["2026-07-14T22:00:00+00:00", "2026-07-15T22:00:00+00:00"])
report("overnight contribution", [overnight], {"ada": 90.0})
report("preceding day contribution", [overnight], {"ada": 30.0}, day="2026-07-14")
report("following day outside shift", [overnight], {}, day="2026-07-16")
report("shift spanning both boundaries", ["bo,2026-07-14T10:00:00+02:00,2026-07-16T11:00:00+02:00,confirmed"], {"bo": 1440.0})
report("ordinary shift", ["ada,2026-07-15T08:15:00+02:00,2026-07-15T09:45:00+02:00,confirmed"], {"ada": 90.0})
report("touching boundaries", [
    "ada,2026-07-14T22:00:00+02:00,2026-07-15T00:00:00+02:00,confirmed",
    "bo,2026-07-16T00:00:00+02:00,2026-07-16T01:00:00+02:00,confirmed"], {})
report("exact full day", ["ada,2026-07-15T00:00:00+02:00,2026-07-16T00:00:00+02:00,confirmed"], {"ada": 1440.0})
report("mixed employee contributions", [overnight,
    "ada,2026-07-15T08:15:00+02:00,2026-07-15T09:45:00+02:00,confirmed",
    "bo,2026-07-15T10:00:00+02:00,2026-07-15T11:00:00+02:00,confirmed"], {"ada": 180.0, "bo": 60.0})
report("overlapping rows are additive", [
    "ada,2026-07-15T08:00:00+02:00,2026-07-15T09:00:00+02:00,confirmed",
    "ada,2026-07-15T08:30:00+02:00,2026-07-15T09:30:00+02:00,confirmed"], {"ada": 120.0})
report("void exclusion", ["ada,2026-07-14T23:00:00+02:00,2026-07-16T01:00:00+02:00,void"], {})
report("fractional minutes", ["ada,2026-07-14T23:59:30+02:00,2026-07-15T00:00:30+02:00,confirmed"], {"ada": .5})
report("equivalent UTC representation", ["ada,2026-07-14T21:30:00+00:00,2026-07-14T23:30:00+00:00,confirmed"], {"ada": 90.0})
report("negative reporting offset", ["ada,2026-07-16T02:30:00+00:00,2026-07-16T04:30:00+00:00,confirmed"], {"ada": 30.0}, offset="-03:00")
report("empty input", [], {})

for label, row in [
    ("naive timestamps", "ada,2026-07-15T08:00:00,2026-07-15T09:00:00,confirmed"),
    ("reversed interval", "ada,2026-07-15T09:00:00+00:00,2026-07-15T08:00:00+00:00,confirmed"),
    ("empty interval", "ada,2026-07-15T08:00:00+00:00,2026-07-15T08:00:00+00:00,confirmed"),
    ("unknown status", "ada,2026-07-15T08:00:00+00:00,2026-07-15T09:00:00+00:00,unknown"),
    ("empty employee", ",2026-07-15T08:00:00+00:00,2026-07-15T09:00:00+00:00,confirmed")]:
    try:
        daily_minutes(HEADER + row + "\n", "2026-07-15", "+02:00")
    except ValueError:
        equal(label, "rejected", "rejected")
    else:
        equal(label, "accepted", "rejected")

print(json.dumps({"failed_cases": failures, "passed": not failures}, sort_keys=True))
raise SystemExit(bool(failures))
