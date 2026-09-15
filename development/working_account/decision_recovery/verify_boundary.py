"""Replay native counts, existing coordinate discovery and subsequent selection."""
import argparse
import copy
import json

import recovery_task as study
import qualify
from prepare_pair import ReferenceAdapter
from working_set_exp.accounted_contribution import process_reply
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes


def verify(folder):
    helper = qualify.module_at("prior_boundary_verifier", study.original.PARENT / "url_continuation/verify_boundary.py")
    helper.task = study
    result = helper.verify(folder)
    counts = {}
    for row in verify_records(folder / "records.jsonl", folder):
        if row["record_type"] == "native_input_prepared":
            stem = row["payload"]["stem"]
            request = study.read(folder / (stem + "-endpoint-request.json"))
            counts[sha256_bytes(canonical_json_bytes(request))] = row["payload"]["prompt_tokens"]
    for condition in ("ordinary",):
        session = study.initial_session(condition)
        adapter = ReferenceAdapter(study.Task(condition))
        def measure(view):
            return counts[sha256_bytes(canonical_json_bytes(adapter.request_for(view)))]
        for stage in ("release", "search", "group"):
            expected = study.read(folder / f"{condition}-{stage}-result.json")
            actions = [r["action"] for r in expected["operations"]]
            reply = dict(discussion="Independent replay; no model call.")
            if actions[0]["action"] == "record_account":
                reply["account"] = actions.pop(0)["text"]
            assert len(actions) == 1
            reply["operation"] = actions[0]
            session.mark_delivered(session.view())
            session.begin_request()
            actual = process_reply(session, reply, measure, adapter.preceding_feedback)
            assert actual == expected
            assert study.snapshot(session) == study.read(folder / f"{condition}-{stage}-state.json")
    return {**result, "actual_search_group_paths_replayed": 1}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="001")
    args = parser.parse_args()
    folder = study.AREA / ("boundary-" + args.version)
    result = verify(folder)
    study.save(study.AREA, folder.name + "-VERIFICATION.json", result)
    print(json.dumps(result, indent=2))
