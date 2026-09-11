"""The preparation adapter supplies CAPTURE and AGREEMENTS as frozen data.

This checker reports observations and named contract failures, not a patch or
preferred action order. It runs outside the editable candidate, as before.
"""
import json
from decimal import Decimal

from posting.api import export
from posting.decode import decode
from posting.policies import calculate


failures = []
checks = 0


def expect(name, actual, expected):
    global checks
    checks += 1
    if actual != expected:
        failures.append({"case": name, "expected": expected, "actual": actual})


def rejects(name, text):
    global checks
    checks += 1
    try:
        decode(text)
    except (ValueError, ArithmeticError):
        return
    failures.append({"case": name, "expected": "input rejection", "actual": "accepted"})


examples = [
    ([], 0, 0),
    (["0.335", "0.335", "0.335"], 102, 101),
    (["-0.335", "-0.335", "-0.335"], -102, -101),
    (["1.005", "-0.005"], 100, 100),
    (["0.004", "0.004"], 0, 1),
    (["12.50", "-2.50", "0"], 1000, 1000),
    (["1.234567", "-1.234567"], 0, 0),
]
for index, (values, line, statement) in enumerate(examples):
    records = [(str(i), Decimal(value)) for i, value in enumerate(values)]
    for policy, expected in (("line", line), ("statement", statement)):
        expect(f"policy-{index}-{policy}", calculate(records, policy), expected)

for index, invalid in enumerate([
    "amount,entry_id\n1,a\n", "entry_id,amount\na,1\na,2\n",
    "entry_id,amount\na,NaN\n", "entry_id,amount\na,Infinity\n",
    "entry_id,amount\na,1e2\n", "entry_id,amount\na, 1\n",
    "entry_id,amount\na,1.0000001\n", "entry_id,amount\n,1\n",
    "entry_id,amount\na,\n", "entry_id,amount\na,1,extra\n",
]):
    rejects(f"invalid-{index}", invalid)

expect("decoded-capture", [{"entry_id": k, "amount": str(v)} for k, v in decode(CAPTURE["input_csv"])], CAPTURE["normalized_records"])
observed = export(CAPTURE["job_id"], CAPTURE["input_csv"])
print(json.dumps({"incident_id": CAPTURE["incident_id"], "current_execution": observed}, sort_keys=True))
for job_id, agreement in AGREEMENTS["jobs"].items():
    # Expected values are explicit receiving examples; neither the candidate
    # calculation nor a proposed donor repair supplies the expected answer.
    for index, example in enumerate(agreement["examples"]):
        expect(f"agreement-{job_id}-{index}", export(job_id, example["input_csv"])["minor_units"], example["expected_minor_units"])

print(json.dumps({"checks": checks, "failures": failures}, sort_keys=True))
raise SystemExit(bool(failures))
