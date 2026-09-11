import json
CAPTURE = json.loads('{"captured_execution":{"effective_policy":"statement","job_id":"south-export","minor_units":101,"records":[{"amount":"0.335","entry_id":"a"},{"amount":"0.335","entry_id":"b"},{"amount":"0.335","entry_id":"c"}]},"configuration_sha256":"4c97f3ff34ad012e998a43c28b48839fa7a33a5902bb8bb157820da6f537a9ae","incident_id":"INC-042","input_csv":"entry_id,amount\\na,0.335\\nb,0.335\\nc,0.335\\n","input_sha256":"ac8de1dbd677365dec338f030c9af8b05840b96508213039f2855e429cabed52","job_id":"south-export","normalized_records":[{"amount":"0.335","entry_id":"a"},{"amount":"0.335","entry_id":"b"},{"amount":"0.335","entry_id":"c"}]}')
AGREEMENTS = json.loads('{"jobs":{"north-export":{"calculation":"Sum signed exact amounts, then round the statement once.","examples":[{"expected_minor_units":101,"input_csv":"entry_id,amount\\na,0.335\\nb,0.335\\nc,0.335\\n"},{"expected_minor_units":-101,"input_csv":"entry_id,amount\\na,-0.335\\nb,-0.335\\nc,-0.335\\n"},{"expected_minor_units":1,"input_csv":"entry_id,amount\\na,0.004\\nb,0.004\\n"}],"rounding":"nearest minor unit; exact halves away from zero"},"south-export":{"calculation":"Round each signed line to a minor unit before summing.","examples":[{"expected_minor_units":102,"input_csv":"entry_id,amount\\na,0.335\\nb,0.335\\nc,0.335\\n"},{"expected_minor_units":-102,"input_csv":"entry_id,amount\\na,-0.335\\nb,-0.335\\nc,-0.335\\n"},{"expected_minor_units":0,"input_csv":"entry_id,amount\\na,0.004\\nb,0.004\\n"}],"rounding":"nearest minor unit; exact halves away from zero"}},"record_kind":"receiving-account agreements"}')
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
