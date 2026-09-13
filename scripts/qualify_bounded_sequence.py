"""Complete offline contributions from Qwen's actual broad source selections."""
import argparse
from pathlib import Path

import bounded_parser as task
from prepare_bounded_parser import Counter, run_action, source_span, patch_action
from qualify_working_capacity import restored
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file


def qualify(output):
    task.require(not output.exists(), "preserve previous qualification")
    output.mkdir(parents=True)
    status = "incomplete"
    try:
        seal = task.read(task.RUN / "RESPONSE_SEAL.json")
        task.require(sha256_file(task.RUN / "RESPONSE_SEAL.json") ==
            "402cd2e034cec912d09aa1380bff7d222a37a613c269d122505d2bff6ef0f961", "source run differs")
        for row in seal["files"]:
            p = task.RUN / row["path"]
            task.require(p.stat().st_size == row["size_bytes"] and sha256_file(p) == row["sha256"], "source artifact differs")
        _, _, tokenizer = task.runtime_paths()
        counter = Counter(output, tokenizer)
        edits = task.read(task.task.AREA / "REFERENCE_EDITS.json")["rows"]
        routes = []
        for tag in ("C03", "C08"):
            s = restored(task.RUN, tag)
            before = s.candidate
            task.save(output, f"{tag}-starting-state.json", task.snapshot(s))
            task.require(s.ranges == [dict(path="Lib/configparser.py", start_line=1, end_line=1347),
                dict(path="Lib/test/test_configparser.py", start_line=1, end_line=605)], "actual broad sources differ")
            rows = []
            check = run_action(s, dict(action="reopen_result", handle="RES-0030", offset=0), counter, rows)
            task.require(check["accepted"] and check["next_offset"] is None and
                check["exact_utf8"].encode() == s.payload("RES-0030"), "full saved check was not deliverable")
            search = run_action(s, dict(action="search", path="Doc/library/configparser.rst",
                query="MissingSectionHeaderError", offset=0, limit=8), counter, rows)
            task.require(search["accepted"] and search["total_matches"] == 1 and
                "output_scope" not in s.last, "complete search feedback was not deliverable")
            task.require(s.candidate == before and s.ranges[0]["end_line"] == 1347, "feedback altered broad selection")
            group = [dict(path="Lib/configparser.py", start_line=299, end_line=341),
                dict(path="Lib/test/test_configparser.py", start_line=1, end_line=32),
                source_span(s.candidate, edits[3]), source_span(s.candidate, edits[5])]
            grouped = run_action(s, dict(action="work_on", sources=group, results=["RES-0030"]), counter, rows)
            task.require(grouped["accepted"] and len(s.sources()) == 4, "complete group unavailable")
            task.require(s.ranges != task.read(task.RUN / f"after/{tag}-state.json")["ranges"], "broad sources not replaced")
            # Guard enforcement is separate from the scripted useful route.
            rejected = run_action(s, dict(action="submit", expected_candidate_id=s.candidate.candidate_id), counter, rows)
            task.require(not rejected["accepted"] and not s.submitted, "premature submission accepted")
            for edit in (edits[3], edits[5]):
                result = run_action(s, patch_action(s.candidate, edit), counter, rows)
                task.require(result["accepted"], "complete contribution edit rejected")
                # Explicitly exercise delivery of the refreshed successor before
                # another operation; run_action calls mark_delivered on each input.
                current = s.view()
                task.require(current["latest_feedback"]["result"]["candidate_id"] == s.candidate.candidate_id,
                    "successor feedback differs")
            checked = run_action(s, dict(action="check", check_id="public", expected_candidate_id=s.candidate.candidate_id), counter, rows)
            task.require(checked["accepted"] and checked["passed"], "completed contribution fails behavioral checker")
            result = run_action(s, dict(action="submit", expected_candidate_id=s.candidate.candidate_id), counter, rows)
            task.require(result["accepted"] and s.submitted, "checked contribution cannot submit")
            task.require(s.candidate.file_map["Lib/configparser.py"] == before.file_map["Lib/configparser.py"], "library changed")
            task.save(output, f"{tag}-route.json", rows)
            task.save(output, f"{tag}-final-state.json", task.snapshot(s))
            task.save(output, f"{tag}-final-candidate.json", task.candidate_bytes(s.candidate))
            routes.append(dict(start=tag, operations=len(rows), initial_tokens=rows[0]["before_tokens"],
                full_check_feedback_tokens=rows[0]["after_tokens"], full_search_feedback_tokens=rows[1]["after_tokens"],
                group_tokens=rows[2]["after_tokens"], peak_input=max(r["after_tokens"] for r in rows),
                saved_library_unchanged=True, checked_submission=True, group_is_researcher_selected=True))
        status = "broad_state_contributions_qualified_offline"
        task.save(output, "QUALIFICATION.json", dict(status=status, completion_requests=0,
            source_run_seal_sha256=sha256_file(task.RUN / "RESPONSE_SEAL.json"), routes=routes,
            native_inputs=len(counter.rows), limits="Scripted choices and reference edits; not model selection, use or completion evidence."))
        print(status, routes, flush=True)
    except BaseException as error:
        task.save(output, "FAILED.json", dict(error_type=type(error).__name__, error=str(error)))
        raise
    finally:
        files = task.base.file_inventory(output)
        task.save(output, "SEAL.json", dict(status=status, files=files,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(files)), source_sha256=task.source_identities(), completion_requests=0))


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--output", type=Path, required=True)
    qualify(p.parse_args().output)
