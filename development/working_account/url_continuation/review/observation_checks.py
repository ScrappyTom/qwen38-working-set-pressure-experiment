"""Narrow reviewer fact checks, not a task run or execution of private drafts."""
import contextlib
import io
import json
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
OUT = Path(__file__).resolve().parent / "OBSERVATION_CHECKS.json"

class ChildValueError(ValueError):
    pass

case = unittest.TestCase()
with case.assertRaises(ValueError) as caught:
    raise ChildValueError("example")
assert type(caught.exception) is ChildValueError

output = io.StringIO()
with contextlib.redirect_stdout(output):
    exec(compile("None", "<review-display-check>", "single"), {})
assert output.getvalue() == ""
lines = (ROOT / "development/working_account/url_ports/world/Lib/test/test_urlparse.py").read_text(encoding="utf-8").splitlines()
anchor = [i for i, line in enumerate(lines, 1) if line == "    def test_attributes_bad_port(self):"]
assert anchor == [716]
result = dict(classification="reviewer fact checks; no model performance or candidate execution evidence",
    assertRaises_ValueError_accepts_subclass=True, bare_None_interactive_output=output.getvalue(),
    current_test_anchor_line=716, actor_discussed_615_to_645_contains_anchor=False,
    model_completion_requests=0, stored_candidate_modified=False)
if OUT.exists():
    raise FileExistsError(OUT)
OUT.write_bytes((json.dumps(result, indent=2) + "\n").encode())
print(json.dumps(result, indent=2))
