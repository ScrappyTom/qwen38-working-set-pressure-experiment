"""Qualify complete task inputs and feedback offline with the pinned native tokenizer."""
from pathlib import Path
import argparse

import configparser_backport as task
import configparser_work as work
from run_compiler_incident import validate_action
from prepare_saved_work_continuation import Counter, save
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.measurement import check_opportunities


def schema_edits(rows):
    """Split offline reference insertions to the actor's unchanged 512-char form."""
    result = []
    for original_index, edit in enumerate(rows):
        if len(edit["new"]) <= 512:
            parts = [edit]
        else:
            assert edit["new"].endswith(edit["old"]) and len(edit["old"]) < 512
            prefix = edit["new"][:-len(edit["old"])]
            chunks, chunk = [], ""
            for line in prefix.splitlines(keepends=True):
                assert len(line) + len(edit["old"]) <= 512
                if len(chunk + line + edit["old"]) > 512:
                    chunks.append(chunk)
                    chunk = ""
                chunk += line
            if chunk:
                chunks.append(chunk)
            parts = [{**edit, "new": part + edit["old"]} for part in chunks]
        result.extend((original_index, index == len(parts)-1, part)
                      for index, part in enumerate(parts))
    return result


def route(counter, kind):
    value = new_state(kind, task.fixture())
    prefix, rows, attempts = 0, [], []
    edits = schema_edits(task.read(task.AREA / "REFERENCE_EDITS.json")["rows"])

    def act(action):
        nonlocal prefix
        index = len(value.pairs) + 1
        stem = f"routes/{kind}/{index:02d}"

        def render(request, cut):
            result = counter.render(request, stem + f"-x{cut:03d}")
            attempts.append(dict(action_index=index, prefix=cut, **result))
            return result

        selected = work.select_input(value, previous=prefix, render=render)
        if selected is None:
            raise ValueError("route exceeds input admission: " + stem)
        prefix = selected["externalized"]
        if not work.latest_result_delivered(selected["request"], value):
            raise ValueError("route cannot deliver its immediate feedback: " + stem)
        validate_action(action, selected["request"])
        result = value.execute(action)
        save(counter.output, stem + "-pair.json", value.pairs[-1])
        rows.append(dict(action_index=index, action=action, accepted=result.get("accepted"),
            prompt_tokens=selected["prompt_tokens"], physical_generation_space=selected["physical_generation_space"],
            prefix=prefix, immediate_feedback_delivered=True,
            candidate_after=value.state.candidate.candidate_id,
            selected_request_sha256=selected["request_sha256"], selected_native_sha256=selected["native_sha256"]))
        print(kind, index, action["action"], selected["prompt_tokens"], "input; prefix", prefix, flush=True)
        return result

    def read(path, start=1):
        result = act(dict(action="read", path=path, start_line=start))
        if not result.get("accepted"):
            raise ValueError("scripted read rejected")
        return result

    def check():
        return act(dict(action="check", check_id="public", expected_candidate_id=value.state.candidate.candidate_id))

    assert act(dict(action="p0_page", path="Lib", offset=0))["accepted"]
    if kind == "full_target_reads":
        # Engineering capacity route only. This list is not supplied to Qwen or
        # claimed necessary for this task; the files are real, unpadded targets.
        for path in ("Lib/configparser.py", "Lib/test/test_configparser.py", "Doc/library/configparser.rst"):
            start = 1
            while start is not None:
                start = read(path, start)["next_start_line"]
    else:
        assert not check()["passed"]
    for part_index, (index, last_part, edit) in enumerate(edits):
        candidate = value.state.candidate
        text = candidate.file_map[edit["path"]].decode()
        assert text.count(edit["old"]) == 1
        line = text[:text.index(edit["old"])].count("\n") + 1
        read_result = read(edit["path"], max(1, line-3))
        assert edit["old"] in read_result["content"]
        action = dict(action="patch", **edit, expected_candidate_id=candidate.candidate_id,
                      expected_file_sha256=candidate.file_sha256(edit["path"]))
        if kind == "rejected_guard" and part_index == 1:
            stale = {**action, "expected_candidate_id": "0" * 64}
            assert not act(stale)["accepted"] and value.state.candidate == candidate
        assert act(action)["accepted"]
        if index == 2 and last_part:
            checked = check()
            assert checked["accepted"] and not checked["passed"]
            # Parse the actual result: the code contribution is checked, while
            # the task remains incomplete because tests/documentation are pending.
            details = load_json_strict(checked["stdout"].encode())
            assert details["contract"]["successful"] and details["upstream"]["successful"]
    final = check()
    assert final["accepted"] and final["passed"]
    assert act(dict(action="submit", expected_candidate_id=value.state.candidate.candidate_id))["accepted"]
    assert value.state.submitted and len(value.pairs) <= work.CALL_LIMIT
    save(counter.output, f"routes/{kind}/pairs.json", value.pairs)
    save(counter.output, f"routes/{kind}/final-candidate.json", work.pilot.reference.candidate_bytes(value.state.candidate))
    return dict(kind=kind, rows=rows, native_attempts=attempts, operations=len(value.pairs),
        peak_input=max(row["prompt_tokens"] for row in rows), final_candidate=value.state.candidate.candidate_id,
        prefix_changed=any(row["prefix"] for row in rows), all_immediate_feedback_delivered=True,
        selected_file_limit=value.state.candidate.max_file_bytes,
        check_opportunities=check_opportunities(value.pairs, call_limit=work.CALL_LIMIT),
        model_completions=0, not_a_minimal_or_required_actor_path=True)


def main(args):
    if args.output.exists():
        raise FileExistsError("preserve the existing preparation")
    args.output.mkdir(parents=True)
    status = "incomplete"
    try:
        counter = Counter(args.output, args.tokenizer)
        value = new_state("initial", task.fixture())
        initial = work.request_for(value)
        counted = counter.render(initial, "initial")
        assert counted["prompt_tokens"] <= work.INPUT_CEILING
        save(args.output, "candidate.json", work.pilot.reference.candidate_bytes(value.state.candidate))
        save(args.output, "PUBLIC_CHECK.py", task.checker())
        save(args.output, "TASK.txt", (task.AREA / "TASK.txt").read_bytes())
        routes = [route(counter, kind) for kind in ("focused", "full_target_reads", "rejected_guard")]
        result = dict(status="offline_inputs_and_feedback_qualified", completion_requests=0,
            every_scripted_action_validated_against_actual_request_schema=True,
            actor=work.ACTOR, seed=work.SEED, input_ceiling=work.INPUT_CEILING, call_limit=work.CALL_LIMIT,
            selected_file_limit=task.FILE_LIMIT, original_native_count_reproduced=counter.original_count,
            tokenizer_calls=len(counter.counts), initial=counted, routes=routes,
            candidate_id=value.state.candidate.candidate_id, candidate_bytes=sum(len(raw) for _, raw in value.state.candidate.files),
            limitations="Scripted capacity and feedback qualification, not model behavior or a generation bound. "
                        "Broad reads and corrective actions are not supplied to the actor or mandatory. "
                        "A runtime-bound execution adapter and safeguards still need qualification before exposure.")
        save(args.output, "QUALIFICATION.json", result)
        status = result["status"]
    except BaseException as error:
        save(args.output, "FAILED.json", dict(error_type=type(error).__name__, message=str(error)))
        raise
    finally:
        files = [dict(path=p.relative_to(args.output).as_posix(), size_bytes=p.stat().st_size, sha256=sha256_file(p))
                 for p in sorted(args.output.rglob("*")) if p.is_file()]
        save(args.output, "SEAL.json", dict(status=status, completion_requests=0, files=files,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),
            source_sha256={p.relative_to(task.ROOT).as_posix():sha256_file(p) for p in
                (Path(__file__), Path(task.__file__), Path(work.__file__),
                 task.ROOT / "scripts/run_compiler_incident.py", task.AREA / "PUBLIC_CHECK.py",
                 task.AREA / "TASK.txt", task.AREA / "REFERENCE_EDITS.json")},
            source_host_sha256={p.relative_to(task.ROOT).as_posix():sha256_file(p) for p in
                sorted((task.ROOT / "src").rglob("*.py"))}))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=task.AREA / "input-qualification-001")
    main(parser.parse_args())
