"""After closure: assess exact C02 proposal separately from the actor's saved work."""
import json
from pathlib import Path

import pending_task as task
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_session import ContributionSession
from working_set_exp.jsonutil import sha256_file

module = task.Task()
folder = module.RUN
task.study.require((folder / "RESPONSE_SEAL.json").exists(), "close the attempt before assessment")
before_path = folder / "after/C01-O01-candidate.json"
operation_path = folder / "calls/C02-operation-01.json"
before, operation = task.study.read(before_path), task.study.read(operation_path)
task.study.require(operation["result"]["accepted"] is False, "not a rejected proposal")
action = operation["action"]
files = {r["path"]: r["content_utf8"].encode() for r in before["files"]}
candidate = Candidate.create(files, max_file_bytes=before["max_file_bytes"])
task.study.require(candidate.candidate_id == action["expected_candidate_id"], "wrong candidate")
task.study.require(candidate.file_sha256(action["path"]) == action["expected_file_sha256"], "wrong file")
text = files[action["path"]].decode()
task.study.require(text.count(action["old"]) == 1, "not an exact unique anchor")
files[action["path"]] = text.replace(action["old"], action["new"], 1).encode()
proposed = Candidate.create(files, max_file_bytes=before["max_file_bytes"])
session = ContributionSession(proposed, module.checker(), "Reviewer-only rejected-proposal assessment")
result = session.execute(dict(action="check", check_id="public",
    expected_candidate_id=proposed.candidate_id), lambda view: 500)
task.study.require(bool(result.get("stdout")), "checker returned no report")
report = json.loads(result["stdout"])
assessment = dict(
    classification="reviewer-applied exact rejected C02 proposal in an isolated candidate; not saved or checked by Qwen",
    original_run_unmodified=True, model_requests=0, candidate_id=proposed.candidate_id,
    result=result, report=report,
    source_sha256={p.relative_to(task.study.ROOT).as_posix(): sha256_file(p)
                   for p in (before_path, operation_path, Path(__file__))},
    checker_source_sha256=sha256_file(task.study.ROOT / "development/working_set_continuation/PUBLIC_CHECK.py"))
task.study.save(task.AREA / "review", "REJECTED_C02_ASSESSMENT.json", assessment)
print(json.dumps({k: report[k] for k in ("passed", "edited_suite", "observed_paths",
    "existing_work_preserved", "documentation_added_preserving_existing")}, indent=2))
