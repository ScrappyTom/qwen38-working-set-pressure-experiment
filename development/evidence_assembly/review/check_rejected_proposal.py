"""After closure, assess the exact unsaved C04 proposal; no inference or admission claim."""
import json

import study
from test_working_continuation import check
from working_set_exp.candidate import Candidate
from working_set_exp.jsonutil import sha256_bytes, sha256_file


def main():
    for condition in ("broad", "assembled"):
        study.require((study.Task(condition).RUN / "RESPONSE_SEAL.json").exists(),
                      "close both model attempts before the isolated assessment")
    folder = study.Task("assembled").RUN
    receipt_path = folder / "calls/C04-operation-01.json"
    receipt = study.read(receipt_path)
    action = receipt["action"]
    study.require(action["action"] == "patch" and receipt["result"]["accepted"] is False,
                  "expected the actual rejected edit")
    candidate, _ = study.starting_work()
    study.require(candidate.candidate_id == action["expected_candidate_id"], "wrong source candidate")
    files = candidate.file_map
    text = files[action["path"]].decode()
    study.require(sha256_bytes(files[action["path"]]) == action["expected_file_sha256"] and
                  text.count(action["old"]) == 1, "proposal preconditions differ")
    files[action["path"]] = text.replace(action["old"], action["new"]).encode()
    proposed = Candidate.create(files, max_file_bytes=candidate.max_file_bytes)
    native_trial = study.read(folder / "admission/I0018-endpoint-request.json")
    trial_view = json.loads(native_trial["messages"][1]["content"])["workspace"]
    study.require(proposed.candidate_id == trial_view["candidate_id"], "not the exact rejected successor")
    result, report = check(files)
    output = dict(
        classification="reviewer-only semantic assessment of the exact rejected C04 proposal",
        not_saved_by_actor=True, not_model_performance_evidence=True,
        no_native_admission_claim=True, completion_requests=0,
        proposal_receipt_sha256=sha256_file(receipt_path),
        checker_sha256=sha256_bytes(study.Task.checker()),
        proposed_candidate_id=proposed.candidate_id,
        scope="Existing checkout checker in an isolated candidate; synthetic measurement only bypasses input admission. No original candidate or model input changes.",
        result=result, report=report)
    study.save(study.AREA / "review", "REJECTED_C04_ASSESSMENT.json", output)
    print(json.dumps(dict(candidate=proposed.candidate_id, overall_passed=result["passed"],
                         edited_suite=report["edited_suite"], observed_paths=report["observed_paths"],
                         existing_work_preserved=report["existing_work_preserved"]), indent=2))


if __name__ == "__main__":
    main()
