"""Post-closure, full traces for the two failures in the exact saved test artifact."""
import ast
import json
from pathlib import Path

import pending_task as task
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_session import ContributionSession
from working_set_exp.jsonutil import sha256_bytes, sha256_file

module = task.Task()
task.study.require((module.RUN / "RESPONSE_SEAL.json").exists(), "close the model attempt first")
path = module.RUN / "final-candidate.json"
saved = task.study.read(path)
candidate = Candidate.create({r["path"]: r["content_utf8"].encode() for r in saved["files"]},
                             max_file_bytes=saved["max_file_bytes"])
assignment = ast.parse(module.checker().decode()).body[0]
task.study.require(assignment.targets[0].id == "_BACKPORT_HARNESS", "checker prefix differs")
harness = ast.literal_eval(assignment.value)
diagnostic = ("_BACKPORT_HARNESS = " + repr(harness) + "\n" + '''
import json
from pathlib import Path
import unittest
helper = {"__name__": "frozen_backport_harness"}
exec(compile(_BACKPORT_HARNESS, "frozen_backport_harness.py", "exec"), helper)
target = "Lib/test/test_configparser.py"
tests = helper["module_from_source"]("saved_failure_diagnostic", Path(target).read_text(encoding="utf-8"), target)
kind = tests.InterpolationMissingOptionErrorTests
suite = unittest.TestSuite(kind(name) for name in
    ("test_basic_missing_option", "test_extended_cross_section_missing"))
report = helper["run_suite"](suite)
print(json.dumps(report, ensure_ascii=True, separators=(",", ":")))
raise SystemExit(0 if report["successful"] else 1)
''').encode()
session = ContributionSession(candidate, diagnostic, "Reviewer-only full failure traces; no actor feedback")
result = session.execute(dict(action="check", check_id="public",
    expected_candidate_id=candidate.candidate_id), lambda view: 500)
report = json.loads(result["stdout"])
task.study.require(report["tests"] == report["failures"] == 2 and report["errors"] == 0,
                   "saved failures differ from frozen-checker assessment")
task.study.save(task.AREA / "review", "SAVED_FAILURE_DETAILS.json", dict(
    classification="reviewer-only two-test diagnostic using the frozen harness and exact saved source; not another experimental score",
    model_requests=0, original_run_unmodified=True, candidate_id=candidate.candidate_id,
    diagnostic_checker_sha256=sha256_bytes(diagnostic), report=report, result=result,
    source_sha256={p.relative_to(task.study.ROOT).as_posix(): sha256_file(p) for p in (path, Path(__file__))}))
print(json.dumps(report, indent=2))
