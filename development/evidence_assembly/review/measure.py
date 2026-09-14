"""Post-closure accounting and exact delivery checks; no completion route."""
import argparse
import difflib
import json

import study
from manage import load_helper
from working_set_exp.jsonutil import sha256_file


def measure(condition):
    module = study.Task(condition)
    folder = module.RUN
    study.require((folder / "RESPONSE_SEAL.json").exists(), "close the condition before aggregate assessment")
    helper = load_helper("assembly_accounting", "development/working_set_continuation/review/summarize.py")
    helper.task = module
    result = helper.summarize(folder)
    result["candidate_unmodified_from_start"] = result.pop("exact_prior_artifact_preserved")
    result["condition"] = condition
    result["initial_selection"] = "researcher_supplied"
    result["response_seal_sha256"] = sha256_file(folder / "RESPONSE_SEAL.json")
    deliveries = []
    for i, row in enumerate(result["calls"]):
        tag = row["id"]
        next_path = folder / f"calls/C{int(tag[1:])+1:02d}-wire-request.json"
        if next_path.exists():
            next_request = study.read(next_path)
            next_input = json.loads(next_request["messages"][1]["content"])
            feedback = [next_input["workspace"]["latest_feedback"], *next_input["preceding_operation_feedback"]]
            host_path = folder / f"calls/{tag}-host-result.json"
            if host_path.exists():
                host = study.read(host_path)
                for n, operation in enumerate(host["operations"], 1):
                    found = any(r and r.get("result") == operation["result"] for r in feedback)
                    study.require(found, "actual immediate feedback missing from next request")
                    deliveries.append(dict(after=tag, operation=n, next_request=next_path.name, complete_result_present=True))
        for operation in row["operations"]:
            action = operation["action"]
            if action["action"] == "patch":
                operation["action"] = {k:v for k,v in action.items() if k not in ("old", "new")}
                operation["patch_utf8_bytes"] = {k:len(action[k].encode()) for k in ("old", "new")}
                operation["exact_action_in_original_operation_receipt"] = True
    result["actual_feedback_deliveries"] = deliveries
    seal = study.read(folder / "RESPONSE_SEAL.json")
    result["memory"] = seal["memory"]
    result["runtime"] = seal["runtime"]
    initial = study.read(folder / "starting-candidate.json")
    final_path = next(folder / n for n in ("final-candidate.json", "stopped-candidate.json") if (folder / n).exists())
    final = study.read(final_path)
    old = {r["path"]:r["content_utf8"] for r in initial["files"]}
    new = {r["path"]:r["content_utf8"] for r in final["files"]}
    changed = [p for p in old if old[p] != new[p]]
    result["changed_files"] = changed
    result["library_unchanged"] = old["Lib/configparser.py"] == new["Lib/configparser.py"]
    patch = ''.join(line for p in changed for line in difflib.unified_diff(old[p].splitlines(keepends=True),
        new[p].splitlines(keepends=True), fromfile="saved-start/"+p, tofile="actual-final/"+p))
    output = study.AREA / "review"
    study.save(output, f"METRICS-{condition}.json", result)
    study.save(output, f"ACTUAL-{condition}.patch", patch.encode())
    print(json.dumps({k:result[k] for k in ("condition", "totals", "outcome", "changed_files", "memory")}, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("condition", choices=("broad", "assembled"))
    args = parser.parse_args()
    measure(args.condition)
