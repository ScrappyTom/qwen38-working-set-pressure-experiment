"""Native counterfactuals on real C04/C08 and broad-acquisition snapshots."""
import argparse
import copy
import json
from pathlib import Path
from types import SimpleNamespace

import qualify
import task
from working_set_exp.accounted_contribution import AccountedSession, process_reply
from working_set_exp import working_view
from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore, RecordLog
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file

ROOT, AREA = task.ROOT, task.PARENT
RECOVERY = ROOT / "development/evidence_assembly/recovery-run/run-001"
BROAD = ROOT / "development/bounded_working_set/run-001"
CASES = dict(C04=(RECOVERY, "after/C03-O01", "C04"),
             C08=(RECOVERY, "after/C07-O01", "C08"),
             broad=(BROAD, "after/C03", "C04"))


def stored(folder, name):
    seal = task.read(folder / "RESPONSE_SEAL.json")
    task.require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "old inventory differs")
    row, = [r for r in seal["files"] if r["path"] == name]
    p = folder / name
    task.require(p.stat().st_size == row["size_bytes"] and sha256_file(p) == row["sha256"], "old artifact differs: " + name)
    return task.read(p)


def restore(name):
    folder, stem, tag = CASES[name]
    state, work = stored(folder, stem + "-state.json"), stored(folder, stem + "-candidate.json")
    if folder == RECOVERY:
        old = stored(folder, f"calls/{tag}-wire-request.json")
    else:
        records = [json.loads(line) for line in (folder / "records.jsonl").read_text().splitlines()]
        event, = [r["payload"] for r in records if r["record_type"] == "invocation_started" and r["payload"]["id"] == tag]
        old = stored(folder, event["input_stem"] + "-endpoint-request.json")
    value = json.loads(old["messages"][1]["content"])
    view = value.get("workspace", value)
    candidate = Candidate.create({r["path"]: r["content_utf8"].encode() for r in work["files"]}, max_file_bytes=work["max_file_bytes"])
    task.require(candidate.candidate_id == state["candidate_id"], "saved candidate differs")
    checker = task.base.task.checker() if name == "broad" else qualify.manage.study.prior.checker()
    session = AccountedSession(candidate, {"public": checker}, view["task"], pairs=state["pairs"],
        edit_checks={"Lib/test/test_configparser.py": "public", "Doc/library/configparser.rst": "public"},
        call_limit=60, request_limit=20)
    for key in ("ranges", "saved", "last"):
        setattr(session, key, copy.deepcopy(state[key]))
    session.diffs = {int(k): v for k, v in state["diffs"].items()}
    module = SimpleNamespace(**{k: getattr(task, k) for k in ("ROOT", "AREA", "base", "ACTOR", "SEED", "MAX_REQUESTS", "snapshot", "candidate_bytes", "expected_native", "require")})
    module.reply_schema = lambda: task.policy.reply_schema(["public"])
    module.operating_reference = lambda: task.policy.operating_reference({"public": "Historical aggregate task checker; unfinished contributions can fail this scope."})
    adapter = task.runner.Adapter(module)
    return session, adapter, old


def proposals(name, session):
    account = "Researcher-authored qualification account: the saved expectation has not established actual behavior. Obtain an actual check before relying on it."
    if name == "C04":
        yield dict(discussion="Replay the actual saved proposal with declared checking.", account=account,
                   operation=stored(RECOVERY, "calls/C04-reply.json")["operation"])
    elif name == "C08":
        yield dict(discussion="Check the actual saved expectation.", account=account,
                   operation=dict(action="check", check_id="public", expected_candidate_id=session.candidate.candidate_id))
    else:
        yield dict(discussion="Replay the actual broad-state historical retrieval before narrowing.",
                   operation=stored(BROAD, "calls/C04-action.json"))
    yield dict(discussion="Researcher-selected narrowing; no model choice is claimed.",
               operation=dict(action="work_on", sources=[dict(path="Lib/configparser.py", start_line=240, end_line=275),
                   dict(path="Lib/test/test_configparser.py", start_line=1, end_line=35)], results=[]))
    yield dict(discussion="Use the existing aggregate checker on the exact current candidate.", account=account,
               operation=dict(action="check", check_id="public", expected_candidate_id=session.candidate.candidate_id))


def identities():
    paths = [Path(__file__)]
    for folder, stem, tag in CASES.values():
        paths.extend([folder / "RESPONSE_SEAL.json", folder / (stem + "-state.json"), folder / (stem + "-candidate.json")])
    return {**task.source_identities(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


def screen(folder):
    folder.mkdir(parents=True, exist_ok=False)
    store, log = ArtifactStore(folder), RecordLog(folder / "records.jsonl", "accounted-saved-state-counterfactuals")
    bound, summaries, error = identities(), [], None
    server, model, _ = task.runtime_paths()
    try:
        with qualify.RUNTIME.owned_runtime(SimpleNamespace(server=server, model=model, output=folder), store, log) as url:
            for name in CASES:
                session, adapter, old = restore(name)
                sub = folder / name
                sub.mkdir()
                local_log = RecordLog(sub / "records.jsonl", "saved-state-" + name)
                loop = task.runner.Loop(sub, ArtifactStore(sub), local_log, url=url, task_module=adapter,
                                        source_check=lambda: task.verify_sources(bound), health=lambda: task.pilot.health(folder))
                initial = loop.measure(session.view())
                contract = adapter.module.operating_reference
                adapter.module.operating_reference = lambda: working_view.system_prompt().split("\n\n", 1)[1]
                baseline_view = session.view()
                baseline_view.pop("working_account")
                baseline_view.pop("verification")
                baseline_count = loop.measure(baseline_view)
                adapter.module.operating_reference = contract
                account_view = copy.deepcopy(session.view())
                account_view["working_account"] = dict(author="model", text="The saved expectation is provisional. Obtain actual evidence before using it in documentation.",
                    action_handle="EVT-9999", input_candidate_id=session.candidate.candidate_id, written_during_request=1)
                account_count = loop.measure(account_view)
                study_view = session.view()
                task.save(sub, "starting-state.json", task.snapshot(session))
                task.save(sub, "original-request.json", old)
                rows = []
                for index, reply in enumerate(proposals(name, session), 1):
                    # A broad historical group may now exceed the ceiling with
                    # added contracts. This is an offline transition, never a
                    # claim that this unadmitted state was sent to Qwen.
                    if loop.measure(session.view()) <= 23808:
                        session.mark_delivered(session.view())
                    session.begin_request()
                    result = process_reply(session, reply, loop.measure, adapter.preceding_feedback)
                    task.save(sub, f"step-{index:02d}-reply.json", reply)
                    task.save(sub, f"step-{index:02d}-result.json", result)
                    task.save(sub, f"step-{index:02d}-state.json", task.snapshot(session))
                    count = loop.measure(session.view())
                    rows.append(dict(step=index, input_tokens=count, accepted=[o["result"].get("accepted") for o in result["operations"]],
                                     passes=[o["result"].get("passed") for o in result["operations"] if o["action"]["action"] == "check"]))
                    task.require(not session.delivery_blocked and count <= 23808 and all(rows[-1]["accepted"]), "counterfactual failed: " + name)
                task.require(session.working_account()["text"].startswith("Researcher-authored"), "account lost across group change")
                summaries.append(dict(name=name, initial_tokens=initial, initial_admitted=initial <= 23808,
                                      without_new_contract_and_state_tokens=baseline_count,
                                      contract_and_state_marginal_tokens=initial-baseline_count,
                                      constructed_short_account_marginal_tokens=account_count-initial,
                                      original_source_ranges=copy.deepcopy(task.read(CASES[name][0] / (CASES[name][1] + "-state.json"))["ranges"]), steps=rows))
                print(name, initial, "->", [r["input_tokens"] for r in rows], flush=True)
    except BaseException as problem:
        error = problem
        task.save(folder, "FAILED.json", dict(type=type(problem).__name__, message=str(problem)))
    task.save(folder, "RESULTS.json", dict(status="failed_preserved" if error else "qualified_counterfactuals", cases=summaries,
        source_sha256=bound, model_completion_requests=0,
        limitation="Old aggregate checks may fail for missing coverage/docs; scoped fresh-task checks are qualified separately. Researcher-selected actions are not Qwen outcomes.",
        memory=qualify.RUNTIME.memory_stats(folder / "memory.csv"), port_free=qualify.RUNTIME.port_free(qualify.RUNTIME.PORT)))
    files = qualify.RUNTIME.file_inventory(folder)
    task.save(folder, "SEAL.json", dict(files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files))))
    if error:
        raise error


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--version", default="001")
    screen(AREA / ("saved-states-" + parser.parse_args().version))
