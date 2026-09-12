"""Offline full-path preparation. No server, HTTP, or completion calls."""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
from types import SimpleNamespace

import qualify_compiler_delivery as delivery
import saved_work_continuation as work
from working_set_exp.ecological_pilot_v2 import build_request
from working_set_exp.interface_consultation import new_state
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count

require, read = work.require, work.read


class Counter:
    def __init__(self, output, tokenizer):
        launch = read(delivery.RUN / "private-runtime/launch.json")
        self.profile = SimpleNamespace(model_path=Path(launch[2]), tokenizer_path=tokenizer)
        require(sha256_file(tokenizer) == delivery.TOKENIZER_SHA, "tokenizer differs")
        require(sha256_file(self.profile.model_path) == work.ACTOR["model_sha256"], "model differs")
        stem = delivery.RUN / "admission/C02-X16000-029-x028"
        self.original = read(Path(str(stem) + "-endpoint-request.json"))
        self.native = Path(str(stem) + "-native.txt").read_bytes().decode()
        self.output, self.counts = output, {}
        self.original_count = len(read(Path(str(stem) + "-tokens.json"))["tokens"])
        require(self.count(self.native.encode()) == self.original_count, "native tokenizer baseline differs")

    def count(self, raw):
        if raw not in self.counts:
            self.counts[raw] = tokenizer_count(self.profile, raw)
        return self.counts[raw]

    def render(self, request, stem):
        anchor = {**self.original, "seed": request["seed"]}
        native = delivery.native_for(request, anchor, self.native)
        count = self.count(native)
        save(self.output, stem + "-request.json", request)
        save(self.output, stem + "-native.txt", native)
        result = dict(prompt_tokens=count, physical_generation_space=work.ACTOR["context"]-count,
            request_sha256=sha256_bytes(canonical_json_bytes(request)), native_sha256=sha256_bytes(native), stem=stem)
        save(self.output, stem + "-count.json", result)
        return result


def save(folder, name, value):
    path = folder / name
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("xb") as stream:
        stream.write(value if isinstance(value, bytes) else canonical_json_bytes(value))


def report_action(value, content):
    return dict(action="patch", path=work.REPORT, old=value.state.candidate.file_map[work.REPORT].decode(),
        new=content, expected_candidate_id=value.state.candidate.candidate_id,
        expected_file_sha256=value.state.candidate.file_sha256(work.REPORT))


def oracle_report():
    # Imported only by the offline preparation, never the live loader/runner.
    from prepare_compiler_incident import expected_report
    return expected_report(read(work.compiler.PACKAGE / "captures.json"))


def report_text(value):
    import json
    return json.dumps(value, separators=(",", ":")) + "\n"


def old_state_reacquisition(counter):
    value = new_state("old-C02-reacquisition-screen", work.compiler.load_fixture())
    pairs = read(delivery.RUN / "segments/C02-X16000-pairs.json")[:28]
    for pair in pairs:
        require(value.execute(pair["response"]) == pair["result"], "old C02 replay differs")
    prefix, rows = 26, []
    actions = [dict(action="read", path=name, start_line=1) for name in ("README.md", work.REPORT)]
    actions += [dict(action="reopen_observation", handle=h) for h in ("OBS-0001", "OBS-0002")]
    for index, action in enumerate(actions, 1):
        result = value.execute(action)
        require(result["accepted"], "old-state reacquisition rejected")
        save(counter.output, f"old-state/{index:02d}-pair.json", value.pairs[-1])
        selected = None
        for cut in range(prefix, len(value.pairs)+1):
            req = copy.deepcopy(counter.original)
            state = work.read_bytes(build_request(value.fixture, candidate=value.state.candidate,
                pairs=value.pairs, externalized_payload_count=cut, calls_used=index, fork_binding=None))
            state["active_user_authored_step"] = delivery.state_of(counter.original)["active_user_authored_step"]
            state["resource_state"].pop(work.pilot.wording.RESOURCE_KEY)
            state["resource_state"].update(call_limit=8, calls_used=index, calls_remaining=8-index)
            state["offline_reacquisition_provenance"] = "Events 1-28 are the closed C02 history; subsequent operations are a separate scripted capacity probe, not additional model actions."
            req["messages"][1]["content"] = canonical_json_bytes(state).decode()
            counted = counter.render(req, f"old-state/{index:02d}-x{cut:03d}")
            if counted["prompt_tokens"] <= work.INPUT_CEILING:
                prefix = cut
                selected = dict(**counted, externalized=cut,
                    acquired_group_delivered=work.delivered(req, value, list(range(29, len(value.pairs)+1))),
                    latest_result_delivered=work.result_delivered(req, value, len(value.pairs)))
                break
        rows.append(dict(step=index, action=action, selected=selected))
        print({"old_state_step":index, "selected":selected}, flush=True)
        if selected is None:
            break
    save(counter.output, "old-state/pairs.json", value.pairs)
    return rows


def route(counter, kind):
    value = work.starting_state()
    original_optimizer = {k:v for k,v in value.state.candidate.file_map.items() if k != work.REPORT}
    group = work.assemble(value, 1)
    ranges = [[1, 3], [4, len(value.pairs)]]
    prefix, phase, phase_used, total_used = 0, 1, 0, 0
    rows = []
    expected = oracle_report()
    partial = {"builds":expected["builds"][:1]}
    full = report_text(expected)

    def observe(label, *, require_group=False):
        nonlocal prefix
        tag = f"routes/{kind}/{len(rows)+1:02d}-{label}"
        selected = work.select_input(value, previous=prefix, phase=phase, phase_used=phase_used,
            total_used=total_used, setup_ranges=ranges,
            render=lambda req, cut: counter.render(req, tag+f"-x{cut:03d}"))
        require(selected is not None, "route exceeds input ceiling: " + tag)
        prefix = selected["externalized"]
        newest = work.result_delivered(selected["request"], value, len(value.pairs))
        group_visible = work.delivered(selected["request"], value, group)
        require(newest and (group_visible or not require_group), "required feedback/group not delivered: " + tag)
        row = {k:v for k,v in selected.items() if k != "request"}
        row.update(label=label, phase=phase, phase_used=phase_used, total_used=total_used,
            candidate_id=value.state.candidate.candidate_id, latest_result_delivered=newest,
            assembled_group_delivered=group_visible, group_required=require_group)
        rows.append(row)
        if kind == "direct" and label == "initial":
            save(counter.output, "initial-request.json", selected["request"])
            save(counter.output, "initial-native.txt", (counter.output / (row["stem"]+"-native.txt")).read_bytes())
            save(counter.output, "initial-pairs.json", value.pairs)
            save(counter.output, "initial-candidate.json", work.pilot.reference.candidate_bytes(value.state.candidate))
        print({"route":kind, "step":label, "tokens":row["prompt_tokens"], "prefix":prefix}, flush=True)

    def act(action):
        nonlocal total_used, phase_used
        work.compiler.validate_action(action, work.request_for(value, phase=phase, phase_used=phase_used,
            total_used=total_used, externalized=prefix, setup_ranges=ranges))
        result = value.execute(action)
        total_used += 1
        phase_used += 1
        return result

    def check():
        return act(dict(action="check", check_id="public", expected_candidate_id=value.state.candidate.candidate_id))

    observe("initial", require_group=True)
    if kind == "rejected_edit":
        wrong = report_action(value, report_text(partial))
        wrong["expected_candidate_id"] = value.fixture.initial.candidate_id
        require(not act(wrong)["accepted"], "stale edit unexpectedly accepted")
        observe("after-rejection", require_group=True)
    first = copy.deepcopy(partial)
    if kind == "correct_later":
        first["builds"][0]["changed_functions"] = []
    require(act(report_action(value, report_text(first)))["accepted"], "partial save rejected")
    saved_partial = value.state.candidate
    observe("after-partial-edit")
    first_check = check()
    require(first_check["accepted"] and not first_check["passed"] and "25/26 contract cases passed" in first_check["stdout"],
            "partial-report public boundary differs")
    save(counter.output, f"routes/{kind}/partial-candidate.json", work.pilot.reference.candidate_bytes(saved_partial))
    # Persist then reconstruct a new host object with exact tools/maps before the
    # forced externalization. This is an offline restart, never hidden rescue.
    before = canonical_json_bytes(work.compiler.snapshot(value))
    restarted = new_state("restart", value.fixture)
    for pair in value.pairs:
        require(restarted.execute(pair["response"]) == pair["result"], "restart replay differs")
    require(canonical_json_bytes(work.compiler.snapshot(restarted)) == before, "restart altered saved state")
    value = restarted
    prefix = len(value.pairs)
    start = prefix+1
    group = work.assemble(value, 2)
    ranges = [*ranges, [start, len(value.pairs)]]
    phase, phase_used = 2, 0
    observe("restart-with-saved-work", require_group=True)
    require(value.state.candidate == saved_partial, "assembly modified contribution")
    if kind == "correct_later":
        require(act(dict(action="reopen_observation", handle="OBS-0002"))["accepted"], "prior-entry evidence recovery rejected")
        group = [*group, len(value.pairs)]
        observe("reacquire-prior-entry-evidence", require_group=True)
    require(act(report_action(value, full))["accepted"], "second report save rejected")
    observe("after-final-edit")
    final_check = check()
    require(final_check["passed"], "full report/optimizer public check failed")
    observe("after-final-check")
    require(act(dict(action="submit", expected_candidate_id=value.state.candidate.candidate_id))["accepted"], "submit rejected")
    require(value.state.public_check_passed and value.state.submitted, "scripted route did not complete")
    require({k:v for k,v in value.state.candidate.file_map.items() if k != work.REPORT} == original_optimizer,
            "optimizer regressed")
    # Exercise exact stored-result and patch-payload retrieval in a separate copy.
    recovery = work.compiler.clone(value)
    recovery.state.submitted = False
    patch_index = next(i for i,p in enumerate(value.pairs,1) if work.report_changed(p["response"],p["result"]))
    for action, expected_raw in ((dict(action="reopen_result", handle=f"RES-{patch_index:04d}"), value.result_payloads[f"RES-{patch_index:04d}"]),
                                 (dict(action="reopen_event", handle=f"EVT-{patch_index:04d}"), value.event_payloads[f"EVT-{patch_index:04d}"])):
        result = recovery.execute(action)
        require(result["accepted"], "historical saved-work access rejected")
        key = "exact_result_utf8" if action["action"] == "reopen_result" else "action_payload"
        actual = result[key].encode() if isinstance(result[key], str) else canonical_json_bytes(result[key])
        require(actual == expected_raw, "historical saved-work bytes differ")
    save(counter.output, f"routes/{kind}/pairs.json", value.pairs)
    save(counter.output, f"routes/{kind}/recovery-pairs.json", recovery.pairs[-2:])
    save(counter.output, f"routes/{kind}/final-candidate.json", work.pilot.reference.candidate_bytes(value.state.candidate))
    return dict(kind=kind, rows=rows, scripted_actor_actions=total_used,
        partial_entry_correct=first == partial, public_partial_check_validates_entry=False,
        first_entry_preserved_at_restart=True, final_public_passed=True, optimizer_unchanged=True,
        final_candidate=value.state.candidate.candidate_id, model_calls=0)


def prepare(tokenizer, output):
    require(not output.exists(), "preparation exists; no overwrite or retry")
    work.verify_start()
    delivery.verify_originals()
    output.mkdir(parents=True)
    status, result = "incomplete", None
    try:
        counter = Counter(output, tokenizer)
        old = old_state_reacquisition(counter)
        routes = [route(counter, kind) for kind in ("direct", "rejected_edit", "correct_later")]
        result = dict(status="offline_full_path_qualified", actor=work.ACTOR,
            input_ceiling=work.INPUT_CEILING, maximum_completion_requests=work.MAX_CALLS,
            completion_calls=0, original_native_count_reproduced=counter.original_count,
            tokenizer_calls=len(counter.counts), old_state_screen=old, routes=routes,
            representation="existing V3, complete reference and monotonic oldest-prefix rule",
            interpretation="Scripted feasibility and assisted saved-work restart; no behavioral result or generation bound.",
            source_sha256=work.sources())
        save(output, "QUALIFICATION.json", result)
        delivery.verify_originals()
        status = "qualified_without_completion"
    except BaseException as error:
        save(output, "FAILED.json", dict(error_type=type(error).__name__, error=str(error)))
        raise
    finally:
        files = [dict(path=p.relative_to(output).as_posix(), sha256=sha256_file(p), size_bytes=p.stat().st_size)
                 for p in sorted(output.rglob("*")) if p.is_file()]
        save(output, "SEAL.json", dict(status=status, files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, default=work.PACKAGE)
    args = parser.parse_args()
    outcome = prepare(args.tokenizer, args.output)
    print({"status":outcome["status"], "completion_calls":0, "tokenizer_calls":outcome["tokenizer_calls"]})
