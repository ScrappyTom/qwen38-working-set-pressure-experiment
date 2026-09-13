"""Offline check of the C07 edit gate, excluding next-input admission.

Run from the repository root with PYTHONPATH=src;tests;scripts. This restores
the exact saved state and actual delivered input, then edits only an in-memory
candidate clone. It sends no model, rendering or tokenization requests.
"""
import copy
import json
from pathlib import Path

import bounded_parser as task
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes


area = Path(__file__).resolve().parent
run = area / "run-001"
snapshot = task.read(run / "after/C06-state.json")
request = task.read(run / "admission/I0056-endpoint-request.json")
view = json.loads(request["messages"][1]["content"])
session = task.initial_session()
assert session.candidate.candidate_id == snapshot["candidate_id"]
for key, value in snapshot.items():
    if key != "candidate_id":
        setattr(session, key, copy.deepcopy(value))
assert task.request_for(session.view()) == request
session.mark_delivered(view)
path = "Lib/test/test_configparser.py"
old = "class InlineCommentStrippingTestCase(unittest.TestCase):\n"
action = dict(action="patch", path=path, old=old, new="\n" + old,
              expected_candidate_id=session.candidate.candidate_id,
              expected_file_sha256=session.candidate.file_sha256(path))
before = session.candidate
support = [s for s in session.delivered_sources if s["path"] == path and old in s["content"]]
assert len(support) == 1
file_lines = len(before.file_map[path].decode().splitlines())
assert support[0]["returned_end_line"] < file_lines
accepted = session.clone()._patch(action)
assert accepted["accepted"]
missing = session.clone()
missing.delivered_sources = []
try:
    missing._patch(action)
except ValueError as error:
    absent_error = str(error)
else:
    raise AssertionError("unseen exact source should not qualify")
assert "not visible" in absent_error
assert session.candidate == before
output = dict(
    scope="Exact-source edit eligibility only; no next-input admission or task progress is claimed.",
    model_requests=0, rendering_requests=0, tokenization_requests=0,
    actual_request_sha256=sha256_bytes(canonical_json_bytes(request)),
    restored_candidate_id=before.candidate_id, file_line_count=file_lines,
    supplied_action=action,
    supporting_source={k:v for k,v in support[0].items() if k != "content"},
    full_file_visible=False, guard_result=accepted,
    absent_source_control_error=absent_error,
    repository_candidate_files_modified=False,
)
with (area / "EDIT_ELIGIBILITY_PROBE.json").open("xb") as stream:
    stream.write(canonical_json_bytes(output))
print(json.dumps(output, indent=2))
