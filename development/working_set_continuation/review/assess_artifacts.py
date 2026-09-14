"""Reviewer-only checks after closure; never amend the model's saved candidate."""
import difflib
from pathlib import Path

import interpolation_contribution as task
from test_working_continuation import check
from working_set_exp.jsonutil import sha256_file


def main():
    task.require((task.RUN / "RESPONSE_SEAL.json").exists(), "close and seal before artifact assessment")
    folder = task.AREA / "review/artifact-assessment-001"
    task.require(not folder.exists(), "preserve prior assessment")
    folder.mkdir()
    origin = task.read(task.RUN / "starting-candidate.json")
    final_path = next(task.RUN / name for name in ("final-candidate.json", "stopped-candidate.json")
                      if (task.RUN / name).exists())
    final = task.read(final_path)
    baseline = {r["path"]:r["content_utf8"].encode() for r in origin["files"]}
    saved = {r["path"]:r["content_utf8"].encode() for r in final["files"]}
    changed = [p for p in saved if saved[p] != baseline[p]]
    patch = "".join(line for p in changed for line in difflib.unified_diff(
        baseline[p].decode().splitlines(keepends=True), saved[p].decode().splitlines(keepends=True),
        fromfile="saved-prior/"+p, tofile="actual-final/"+p))
    task.save(folder, "ACTUAL_SAVED.patch", patch.encode())
    actual_result, actual_report = check(saved)
    task.save(folder, "actual-final-check.json", dict(result=actual_result, report=actual_report,
        classification="reviewer-only check of the actual saved artifact; not an actor operation"))
    operation = task.read(task.RUN / "calls/C15-operation-01.json")
    task.require(operation["result"]["accepted"] is False, "proposal was not rejected")
    action = operation["action"]
    before = task.read(task.RUN / "after/C14-O01-candidate.json")
    proposed = {r["path"]:r["content_utf8"].encode() for r in before["files"]}
    old_text = proposed[action["path"]].decode()
    task.require(old_text.count(action["old"]) == 1, "proposal anchor differs")
    proposed[action["path"]] = old_text.replace(action["old"], action["new"], 1).encode()
    proposal_result, proposal_report = check(proposed)
    task.save(folder, "rejected-proposal-check.json", dict(result=proposal_result, report=proposal_report,
        classification="reviewer-applied exact rejected C15 proposal in an isolated checker; not saved or checked by Qwen"))
    summary = dict(actual_changed_files=changed, actual_passed=actual_result["passed"],
        actual_saved_suite=actual_report.get("saved_suite"), actual_edited_suite=actual_report.get("edited_suite"),
        actual_existing_work_preserved=actual_report.get("existing_work_preserved"),
        actual_new_tests=actual_report.get("added_tests"),
        proposal_passed=proposal_result["passed"], proposal_edited_suite=proposal_report.get("edited_suite"),
        proposal_new_tests=proposal_report.get("added_tests"), proposal_observed_paths=proposal_report.get("observed_paths"),
        proposal_restoration_faults=proposal_report.get("restoration_faults"),
        direct_review="The proposed methods omit diagnostic-text assertions and do not add documentation.",
        no_model_inference=True, original_candidate_unmodified=True,
        checked_sources={str(p.relative_to(task.ROOT)):sha256_file(p) for p in
            (final_path, task.RUN/"calls/C15-operation-01.json", task.AREA/"PUBLIC_CHECK.py", Path(__file__))})
    task.save(folder, "SUMMARY.json", summary)
    print(summary)


if __name__ == "__main__":
    main()
