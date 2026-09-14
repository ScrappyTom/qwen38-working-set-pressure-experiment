"""Source-check D1's example and visible anchors; never execute a task action."""
import json
from pathlib import Path
import re

import consult_selection as consult
from working_set_exp import working_view
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

folder = consult.AREA / "turn-01"
consult.task.base.verify_seal(folder)
answer = (folder / "calls/D1-assistant-content.txt").read_text(encoding="utf-8")
examples = re.findall(r"```json\s*(.*?)\s*```", answer, re.S)
consult.task.require(len(examples) == 1, "expected one proposed operation")
action = json.loads(examples[0])
working_view.validate(action, working_view.schema()["json_schema"]["schema"])
consult.task.require(action == dict(action="reopen_event", handle="EVT-0073", offset=0),
                     "review the actual example before changing this assessment")
state_path = consult.SOURCE / "after/C04-O01-state.json"
candidate_path = consult.SOURCE / "after/C04-O01-candidate.json"
state, candidate = consult.task.read(state_path), consult.task.read(candidate_path)
pair = state["pairs"][72]
proposal = pair["response"]
request = consult.task.read(consult.OLD)
view = json.loads(request["messages"][1]["content"])["workspace"]
sources = view["latest_feedback"]["result"]["sources"]
target = next(r for r in candidate["files"] if r["path"] == proposal["path"])
old_visible = any(r["path"] == proposal["path"] and proposal["old"] in r["content"] for r in sources)
facts = dict(
    action_schema_valid=True, handle_identifies_actual_rejected_patch=proposal["action"] == "patch" and not pair["result"]["accepted"],
    exact_action_bytes=len(canonical_json_bytes(proposal)), exact_action_sha256=sha256_bytes(canonical_json_bytes(proposal)),
    candidate_guard_matches=proposal["expected_candidate_id"] == view["candidate_id"],
    file_guard_matches=proposal["expected_file_sha256"] == sha256_bytes(target["content_utf8"].encode()),
    old_fragment_unique_in_current_file=target["content_utf8"].count(proposal["old"]) == 1,
    old_fragment_present_in_actual_C05_source=old_visible,
    test_class_anchor_visible=any("class MiscTestCase(unittest.TestCase):" in r["content"] for r in sources),
    documentation_heading_visible=any("Mapping Protocol Access\n-----------------------" in r["content"] for r in sources),
    actual_allowance=view["allowance"])
consult.task.require(all(facts[k] for k in ("handle_identifies_actual_rejected_patch", "candidate_guard_matches",
    "file_guard_matches", "old_fragment_unique_in_current_file", "old_fragment_present_in_actual_C05_source",
    "test_class_anchor_visible", "documentation_heading_visible")), "expected source facts differ")
report = dict(classification="reviewer source/argument assessment; no operation, inference or new capacity measurement",
    executed=False, model_requests=0, facts=facts,
    source_sha256={p.relative_to(consult.ROOT).as_posix(): sha256_file(p)
        for p in (Path(__file__), state_path, candidate_path, consult.OLD,
                  folder / "RESPONSE_SEAL.json", folder / "calls/D1-assistant-content.txt")})
consult.task.save(consult.AREA, "D1_OPERATION_ASSESSMENT.json", report)
print(json.dumps(facts, indent=2))
