"""Native-tokenized offline qualification; this script has no completion path."""
import argparse
from pathlib import Path
from types import SimpleNamespace

import bounded_parser as task
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count
from working_set_exp.working_session import WorkingSession, INPUT_LIMIT, CONTROL_ROOM


class Counter:
    def __init__(self, output, tokenizer):
        _, model, _ = task.runtime_paths()
        task.require(sha256_file(model) == task.ACTOR["model_sha256"] and
                     sha256_file(tokenizer) == task.delivery.TOKENIZER_SHA, "tokenizer/model identity differs")
        self.profile = SimpleNamespace(model_path=model, tokenizer_path=tokenizer)
        self.output, self.rows, self.cache = output, [], {}
        old_native = (task.OLD/"admission/C01-x000-native.txt").read_bytes()
        expected = len(task.read(task.OLD/"admission/C01-x000-tokens.json")["tokens"])
        task.require(tokenizer_count(self.profile, old_native) == expected, "offline tokenizer baseline differs")

    def measure(self, view):
        req = task.request_for(view)
        native = task.expected_native(req)
        digest = sha256_bytes(native)
        if digest in self.cache:
            return self.cache[digest]["prompt_tokens"]
        count = tokenizer_count(self.profile, native)
        stem = f"inputs/Q{len(self.rows)+1:04d}"
        row = dict(stem=stem, prompt_tokens=count, physical_generation_space=task.ACTOR["context"]-count,
                   native_sha256=digest, request_sha256=sha256_bytes(canonical_json_bytes(req)))
        task.save(self.output, stem+"-request.json", req)
        task.save(self.output, stem+"-native.txt", native)
        task.save(self.output, stem+"-count.json", row)
        self.rows.append(row)
        self.cache[digest] = row
        return count

    def row(self, view):
        self.measure(view)
        return self.cache[sha256_bytes(task.expected_native(task.request_for(view)))]


def run_action(session, action, counter, rows):
    count = counter.measure(session.view())
    task.require(count <= INPUT_LIMIT and not session.delivery_blocked, "pre-action input denied")
    session.mark_delivered(session.view())
    result = session.execute(action, counter.measure)
    after = counter.measure(session.view())
    task.require(after <= INPUT_LIMIT and not session.delivery_blocked, "feedback cannot be delivered")
    rows.append(dict(action=action, result=result, before_tokens=count, after_tokens=after,
                     input=counter.row(session.view()), candidate_id=session.candidate.candidate_id))
    return result


def source_span(candidate, edit, context=3):
    text = candidate.file_map[edit["path"]].decode()
    task.require(text.count(edit["old"]) == 1, "reference anchor differs")
    start = text[:text.index(edit["old"])].count("\n")+1
    return dict(path=edit["path"], start_line=max(1,start-context),
                end_line=min(len(text.splitlines()),start+edit["old"].count("\n")+context))


def patch_action(candidate, edit):
    return dict(action="patch", **edit, expected_candidate_id=candidate.candidate_id,
                expected_file_sha256=candidate.file_sha256(edit["path"]))


def qualify(counter):
    session = task.initial_session()
    initial = counter.row(session.view())
    task.save(counter.output, "starting-candidate.json", task.candidate_bytes(session.candidate))
    task.save(counter.output, "starting-archive.json", session.pairs)
    task.save(counter.output, "PUBLIC_CHECK.py", session.checker)
    task.save(counter.output, "initial-request.json", task.request_for(session.view()))
    task.save(counter.output, "initial-native.txt", task.expected_native(task.request_for(session.view())))
    task.save(counter.output, "TASK.txt", (task.AREA/"TASK.txt").read_bytes())
    rows = []
    edits = task.read(task.task.AREA/"REFERENCE_EDITS.json")["rows"]
    library = session.candidate.file_map["Lib/configparser.py"]
    # Actual saved C25/C27/C32 information needs, now assembled together. These
    # ranges are evaluator-side capacity examples and are never actor hints.
    group = [dict(path="Lib/configparser.py",start_line=299,end_line=341),
             dict(path="Lib/test/test_configparser.py",start_line=1,end_line=32),
             source_span(session.candidate, edits[3]), source_span(session.candidate, edits[5])]
    result = run_action(session, dict(action="work_on", sources=group, results=[]), counter, rows)
    task.require(result["accepted"] and len(session.sources()) == 4, "complete source group unavailable")
    complete_group = counter.row(session.view())
    run_action(session, dict(action="search",path="Doc/library/configparser.rst",query="allow_no_value",offset=0,limit=8),counter,rows)
    task.require(len(session.sources()) == 4, "search displaced selected sources")
    for edit in (edits[3], edits[5]):
        result = run_action(session, patch_action(session.candidate, edit), counter, rows)
        task.require(result["accepted"], "natural complete reference edit rejected")
    stale = dict(rows[-1]["action"])
    task.require(not run_action(session, stale, counter, rows)["accepted"], "stale repeat accepted")
    check = run_action(session, dict(action="check",check_id="public",expected_candidate_id=session.candidate.candidate_id),counter,rows)
    task.require(check["accepted"] and check["passed"], "saved test and documentation contribution fails")
    checked_candidate = session.candidate
    task.save(counter.output, "checked-candidate.json", task.candidate_bytes(checked_candidate))
    # Fresh decision state from checked work. No private reasoning, pinned group
    # or hidden reference plan is used to reconstruct it.
    fresh = WorkingSession(session.candidate, session.checker, session.task, pairs=session.pairs, call_limit=task.CALL_LIMIT)
    task.require(fresh.check_state()["passed"] and fresh.check_state()["applies_to_current"] and not fresh.ranges,
                 "checked work did not survive a fresh working context")
    fresh_initial = counter.row(fresh.view())
    task.save(counter.output, "fresh-start.json", task.snapshot(fresh))
    task.require(run_action(fresh, dict(action="work_on",sources=[source_span(fresh.candidate,edits[4])],results=[]),counter,rows)["accepted"],
                 "later documentation source unavailable")
    task.require(run_action(fresh,patch_action(fresh.candidate,edits[4]),counter,rows)["accepted"],"later documentation contribution rejected")
    task.require(fresh.candidate.file_map["Lib/configparser.py"] == library and
                 fresh.candidate.file_map["Lib/test/test_configparser.py"] == checked_candidate.file_map["Lib/test/test_configparser.py"],
                 "later contribution changed checked library/tests")
    task.require(run_action(fresh,dict(action="check",check_id="public",expected_candidate_id=fresh.candidate.candidate_id),counter,rows)["passed"],
                 "later contribution fails check")
    task.require(run_action(fresh,dict(action="submit",expected_candidate_id=fresh.candidate.candidate_id),counter,rows)["accepted"] and fresh.submitted,
                 "checked contribution did not submit")
    task.save(counter.output,"route.json",rows)
    task.save(counter.output,"final-candidate.json",task.candidate_bytes(fresh.candidate))
    # History size must not reproduce the old metadata floor. This is synthetic
    # engineering load, not material supplied to Qwen or a capability experiment.
    growth = []
    for length in (100,1000,10000):
        pair = dict(response=dict(action="tree",path=".",offset=0,limit=8),result=dict(accepted=True,entries=[]))
        large = WorkingSession(session.candidate, session.checker, session.task, pairs=[pair]*length)
        growth.append(dict(archive_actions=length, **counter.row(large.view())))
    task.require(max(r["prompt_tokens"] for r in growth)-min(r["prompt_tokens"] for r in growth) < 100,
                 "administrative input grows with archived history")
    # Oversized acquisition is fitted by the host while the companion remains.
    broad = task.initial_session()
    broad_rows = []
    run_action(broad, dict(action="work_on",sources=[dict(path="Lib/configparser.py",start_line=299,end_line=341)],results=[]),counter,broad_rows)
    body = run_action(broad,dict(action="read",path="Lib/test/test_configparser.py",start_line=467,end_line=0),counter,broad_rows)
    task.require(body["accepted"] and any(s["path"]=="Lib/configparser.py" for s in broad.sources()),"read displaced companion source")
    task.save(counter.output,"broad-read-route.json",broad_rows)
    return dict(status="offline_full_path_qualified",completion_requests=0,initial=initial,
                complete_group=complete_group,fresh_start=fresh_initial,history_growth=growth,
                operations=len(rows),peak_route_input=max(r["after_tokens"] for r in rows),
                selected_generation_reserve=task.ACTOR["generation_reserve"],input_ceiling=INPUT_LIMIT,
                read_control_margin=CONTROL_ROOM,source_library_unchanged=True,
                checked_work_survives_fresh_context=True,not_model_behavior=True)


def main(output):
    task.require(not output.exists(), "preserve prior preparation")
    output.mkdir(parents=True)
    status = "incomplete"
    try:
        _, _, tokenizer = task.runtime_paths()
        counter = Counter(output, tokenizer)
        result = qualify(counter)
        task.save(output,"QUALIFICATION.json",result)
        status = result["status"]
        print(canonical_json_bytes(result).decode(),flush=True)
    except BaseException as error:
        task.save(output,"FAILED.json",dict(error_type=type(error).__name__,error=str(error)))
        raise
    finally:
        files = [dict(path=p.relative_to(output).as_posix(),size_bytes=p.stat().st_size,sha256=sha256_file(p))
                 for p in sorted(output.rglob("*")) if p.is_file()]
        task.save(output,"SEAL.json",dict(status=status,completion_requests=0,files=files,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),source_sha256=task.source_identities()))


if __name__ == "__main__":
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output",type=Path,default=task.PACKAGE)
    main(parser.parse_args().output)
