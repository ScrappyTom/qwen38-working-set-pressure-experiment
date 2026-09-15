"""After closure: actual contribution cost, delivery, saved work and verification."""
import difflib
import json

import recovery_task as task
from manage_recovery import assembly
from working_set_exp.candidate import Candidate
from working_set_exp.contribution_session import ContributionSession
from working_set_exp.jsonutil import sha256_file

module = task.Task()
folder, output = module.RUN, task.AREA / "review"
task.study.require((folder / "RESPONSE_SEAL.json").exists(), "close the attempt before assessment")
helper = assembly.load_helper("recovery_accounting", "development/working_set_continuation/review/summarize.py")
helper.task = module
metrics = helper.summarize(folder)
metrics["candidate_unmodified_from_start"] = metrics.pop("exact_prior_artifact_preserved")
metrics["classification"] = "uncoached development from actual C05 checkpoint with inherited assembly assistance"
metrics["response_seal_sha256"] = sha256_file(folder / "RESPONSE_SEAL.json")

deliveries, opportunities = [], []
for row in metrics["calls"]:
    tag = row["id"]
    next_path = folder / f"calls/C{int(tag[1:])+1:02d}-wire-request.json"
    host_path = folder / f"calls/{tag}-host-result.json"
    host = task.study.read(host_path) if host_path.exists() else dict(operations=[])
    following = json.loads(task.study.read(next_path)["messages"][1]["content"]) if next_path.exists() else None
    feedback = ([following["workspace"]["latest_feedback"], *following["preceding_operation_feedback"]]
                if following else [])
    row["thinking_characters"] = len((folder / f"calls/{tag}-assistant-reasoning.txt").read_text(encoding="utf-8"))
    row["final_characters"] = len((folder / f"calls/{tag}-assistant-content.txt").read_text(encoding="utf-8"))
    for number, operation in enumerate(host["operations"], 1):
        present = any(r and r.get("result") == operation["result"] for r in feedback) if following else None
        deliveries.append(dict(after=tag, operation=number, next_request_exists=following is not None,
                               complete_result_present=present))
        if operation["action"]["action"] == "check":
            opportunities.append(dict(request=tag, accepted=operation["result"].get("accepted"),
                passed=operation["result"].get("passed"),
                requests_remaining_after_reply=row["allowance"]["requests_remaining"] - 1,
                operations_remaining_after_check=row["allowance"]["actions_remaining"] - number))
    for operation in row["operations"]:
        action = operation["action"]
        if action["action"] == "patch":
            operation["patch_utf8_bytes"] = {k:len(action[k].encode()) for k in ("old", "new")}
            operation["action"] = {k:v for k,v in action.items() if k not in ("old", "new")}
metrics["actual_feedback_deliveries"] = deliveries
metrics["check_opportunities_with_both_allowances"] = opportunities
seal = task.study.read(folder / "RESPONSE_SEAL.json")
metrics["memory"], metrics["runtime"] = seal["memory"], seal["runtime"]
final_path = next(folder / n for n in ("final-candidate.json", "stopped-candidate.json") if (folder / n).exists())
state_path = next(folder / n for n in ("final-state.json", "stopped-state.json") if (folder / n).exists())
before, after = task.study.read(folder / "starting-candidate.json"), task.study.read(final_path)
old = {r["path"]:r["content_utf8"] for r in before["files"]}
new = {r["path"]:r["content_utf8"] for r in after["files"]}
changed = [p for p in old if old[p] != new[p]]
metrics["changed_files"] = changed
metrics["library_unchanged"] = old["Lib/configparser.py"] == new["Lib/configparser.py"]
diff = ''.join(line for p in changed for line in difflib.unified_diff(old[p].splitlines(keepends=True),
    new[p].splitlines(keepends=True), fromfile="saved-start/" + p, tofile="actual-final/" + p))
task.study.save(output, "ACTUAL.patch", diff.encode())
task.study.save(output, "METRICS.json", metrics)

candidate = Candidate.create({p:s.encode() for p,s in new.items()}, max_file_bytes=after["max_file_bytes"])
state = task.study.read(state_path)
session = ContributionSession(candidate, module.checker(), "Post-closure assessment; no feedback to actor", pairs=state["pairs"])
if session.check_state()["applies_to_current"]:
    result = next(p["result"] for p in reversed(session.pairs) if p["response"]["action"] == "check" and p["result"].get("accepted"))
    classification = "existing actual actor check applies to final artifact; no redundant check executed"
else:
    result = session.execute(dict(action="check", check_id="public", expected_candidate_id=candidate.candidate_id), lambda view:500)
    classification = "independent check after sealed run; never delivered to actor"
task.study.save(output, "ARTIFACT_CHECK.json", dict(classification=classification,
    model_requests=0, candidate_json_sha256=sha256_file(final_path), script_sha256=sha256_file(task.AREA / "review/analyze.py"),
    result=result))
print(json.dumps({k:metrics[k] for k in ("totals", "outcome", "changed_files", "memory")}, indent=2))
print("Final artifact check passed:", result.get("passed"), classification)
