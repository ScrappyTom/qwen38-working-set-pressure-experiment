"""Explicit behavioral cases and intermediate observations; no donor comparison."""
from dataclasses import asdict
from pathlib import Path
import json
import sys

sys.path.insert(0, str(Path("src").resolve()))
from dispatchledger.api import latest_receipts, summarize_csv
from dispatchledger.ingest.csv_rows import read_receipts

HEADER = "ticket,revision,depot,item,units,status\n"
failures = []


def csv_text(rows):
    return HEADER + "".join(row + "\n" for row in rows)


def equal(label, operation, expected):
    try:
        actual = operation()
        passed = actual == expected
        print(json.dumps(dict(case=label, passed=passed, actual=actual, expected=expected), sort_keys=True))
    except Exception as error:
        passed = False
        print(json.dumps(dict(case=label, passed=False, exception=type(error).__name__, message=str(error))))
    if not passed:
        failures.append(label)


def report(label, rows, expected):
    equal(label, lambda: summarize_csv(csv_text(rows)),
          [dict(depot=d, item=i, units=n) for d, i, n in expected])


def rejected(label, text):
    def operation():
        try:
            summarize_csv(text)
        except ValueError:
            return "rejected"
        return "accepted"
    equal(label, operation, "rejected")


sequence = ["X,1,alpha,cable,9,active", "Y,1,alpha,cable,4,active", "X,2,beta,sensor,6,active"]
print(json.dumps(dict(observation="input sequence", csv=csv_text(sequence))))
expected_records = [dict(ticket="X", revision=1, depot="ALPHA", item="CABLE", units=9, status="active"),
                    dict(ticket="Y", revision=1, depot="ALPHA", item="CABLE", units=4, status="active"),
                    dict(ticket="X", revision=2, depot="BETA", item="SENSOR", units=6, status="active")]
equal("decoded sequence", lambda: [asdict(r) for r in read_receipts(csv_text(sequence))], expected_records)
equal("selected receipts", lambda: [asdict(r) for r in latest_receipts(csv_text(sequence))],
      [expected_records[2], expected_records[1]])
report("sequence report", sequence, [("ALPHA", "CABLE", 4), ("BETA", "SENSOR", 6)])
report("single receipt", ["A,1,north,widget,10,active"], [("NORTH", "WIDGET", 10)])
report("independent receipts", ["A,1,north,widget,10,active", "B,1,north,widget,10,active"], [("NORTH", "WIDGET", 20)])
report("quantity correction", ["A,1,north,widget,10,active", "A,2,north,widget,6,active"], [("NORTH", "WIDGET", 6)])
report("depot correction", ["A,1,north,widget,10,active", "A,2,south,widget,6,active"], [("SOUTH", "WIDGET", 6)])
report("item correction", ["A,1,north,widget,10,active", "A,2,north,gadget,6,active"], [("NORTH", "GADGET", 6)])
report("correction with another receipt", ["A,1,north,widget,10,active", "B,1,north,widget,7,active", "A,2,south,widget,6,active"], [("NORTH", "WIDGET", 7), ("SOUTH", "WIDGET", 6)])
report("multiple corrections", ["A,1,north,widget,10,active", "A,2,south,gadget,6,active", "A,3,east,widget,8,active"], [("EAST", "WIDGET", 8)])
report("return to earlier group", ["A,1,north,widget,10,active", "A,2,south,widget,6,active", "A,3,north,widget,8,active"], [("NORTH", "WIDGET", 8)])
report("duplicate current revision", ["A,1,north,widget,10,active", "A,1,north,widget,10,active"], [("NORTH", "WIDGET", 10)])
report("duplicate after correction", ["A,1,north,widget,10,active", "A,2,south,widget,6,active", "A,2,south,widget,6,active"], [("SOUTH", "WIDGET", 6)])
report("older arrival", ["A,2,south,widget,6,active", "A,1,north,widget,10,active"], [("SOUTH", "WIDGET", 6)])
report("older arrival after correction", ["A,1,north,widget,10,active", "A,3,south,gadget,6,active", "A,2,east,widget,12,active"], [("SOUTH", "GADGET", 6)])
report("void current receipt", ["A,1,north,widget,10,void"], [])
report("void correction", ["A,1,north,widget,10,active", "A,2,north,widget,10,void"], [])
report("void with changed labels", ["A,1,north,widget,10,active", "A,2,south,gadget,10,void"], [])
report("reactivate receipt", ["A,1,north,widget,10,active", "A,2,north,widget,10,void", "A,3,south,gadget,3,active"], [("SOUTH", "GADGET", 3)])
report("zero units", ["A,1,north,widget,0,active"], [])
report("correct to zero at new group", ["A,1,north,widget,10,active", "A,2,south,gadget,0,active"], [])
report("normalization", [" A , 01 , north , Widget , 010 , ACTIVE ", "A,1,NORTH,WIDGET,10,active"], [("NORTH", "WIDGET", 10)])
report("sorted groups", ["A,1,zeta,z,2,active", "B,1,alpha,z,3,active", "C,1,alpha,a,1,active"], [("ALPHA", "A", 1), ("ALPHA", "Z", 3), ("ZETA", "Z", 2)])
report("empty stream", [], [])
for label, rows in [
    ("conflicting current revision", ["A,1,north,widget,10,active", "A,1,south,widget,10,active"]),
    ("negative units", ["A,1,north,widget,-1,active"]),
    ("fractional units", ["A,1,north,widget,1.5,active"]),
    ("non-ASCII units", ["A,1,north,widget,\u0661,active"]),
    ("zero revision", ["A,0,north,widget,1,active"]),
    ("negative revision", ["A,-1,north,widget,1,active"]),
    ("unknown status", ["A,1,north,widget,1,pending"]),
    ("empty ticket", [",1,north,widget,1,active"]),
    ("empty depot", ["A,1, ,widget,1,active"]),
    ("empty item", ["A,1,north, ,1,active"]),
    ("missing field", ["A,1,north,widget,1"]),
    ("extra field", ["A,1,north,widget,1,active,extra"]),
    ("invalid old revision", ["A,2,south,widget,6,active", "A,1,north,widget,-1,active"]),
]:
    rejected(label, csv_text(rows))
rejected("wrong header", "ticket,revision,depot,item,units,units\n")
print(json.dumps(dict(passed=not failures, failed_cases=failures), sort_keys=True))
raise SystemExit(bool(failures))
