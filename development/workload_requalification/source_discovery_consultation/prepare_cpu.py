"""Prepare exact historical input for review; no runtime, tokenizer or inference."""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
sys.path.insert(0, str(ROOT / "src"))

from working_set_exp.candidate import Candidate
from working_set_exp.custody import ArtifactStore, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file

EXECUTION_KEYS = {"grammar", "response_format", "tools", "functions", "tool_choice", "function_call"}
BUDGETS = ("max_tokens", "n_predict", "reasoning_budget_tokens", "thinking_budget_tokens")
SEED = 42


def require(condition, message):
    if not condition:
        raise ValueError(message)


def read(path):
    return load_json_strict(path.read_bytes())


def verify_inventory(folder, rows, aggregate):
    require(sha256_bytes(canonical_json_bytes(rows)) == aggregate, "inventory aggregate differs")
    seen = set()
    for row in rows:
        relative = Path(row["path"])
        path = (folder / relative).resolve()
        require(not relative.is_absolute() and path.is_relative_to(folder.resolve()), "inventory path escaped")
        require(row["path"] not in seen, "duplicate inventory path")
        seen.add(row["path"])
        data = path.read_bytes()
        require(len(data) == row["size_bytes"] and sha256_bytes(data) == row["sha256"],
                "sealed artifact differs: " + row["path"])


def historical_source():
    binding = read(AREA / "SOURCE.json")
    run = ROOT / binding["run"]
    for field in ("seal", "input", "candidate"):
        require(sha256_file(run / binding[field]) == binding[field + "_sha256"], field + " identity differs")
    seal = read(run / binding["seal"])
    verify_inventory(run, seal["files"], seal["aggregate_sha256"])
    inventory = {r["path"]: r for r in seal["files"]}
    for field in ("input", "candidate"):
        require(inventory[binding[field]]["sha256"] == binding[field + "_sha256"],
                field + " is not bound by the source seal")
    records = verify_records(run / "records.jsonl", run)
    require(len(records) == seal["record_count"], "source record count differs")
    require(seal["disposition"] == "request_allowance_exhausted" and
            seal["sent_requests"] == seal["returned_responses"] == 10 and seal["port_free"],
            "source attempt is not the closed ten-response run")
    old = read(run / binding["input"])
    require([m["role"] for m in old["messages"]] == ["system", "user"], "historical message roles differ")
    candidate_record = read(run / binding["candidate"])
    candidate = Candidate.create({r["path"]: r["content_utf8"].encode("utf-8")
                                  for r in candidate_record["files"]},
                                 max_file_bytes=candidate_record["max_file_bytes"])
    require(candidate.candidate_id == candidate_record["candidate_id"] == binding["candidate_id"],
            "candidate identity differs")
    require(candidate.file_sha256(binding["test_path"]) == binding["test_file_sha256"], "test identity differs")
    state = load_json_strict(old["messages"][1]["content"].encode("utf-8"))["workspace"]
    require(state["candidate_id"] == candidate.candidate_id, "C06 candidate differs")
    require(state["presentation"]["mode"] == "ordinary" and
            state["presentation"]["selected_bodies_omitted"] is False, "C06 presentation differs")
    sources = state["working_set"]["sources"]
    for source in sources:
        data = candidate.file_map[source["path"]]
        exact = "".join(data.decode("utf-8").splitlines(keepends=True)
                        [source["returned_start_line"] - 1:source["returned_end_line"]])
        require(source["content"] == exact and source["candidate_id"] == candidate.candidate_id and
                source["file_sha256"] == sha256_bytes(data), "visible source differs from saved candidate")
    return old, seal, dict(source_records=len(records), sealed_files=len(seal["files"]),
                           exact_selected_sources=len(sources), candidate_id=candidate.candidate_id)


def quoted_messages(old):
    messages = old["messages"]
    require([m["role"] for m in messages] == ["system", "user"], "expected both original messages")
    parts = []
    for message in messages:
        role = message["role"].upper()
        start, end = "BEGIN EXACT ARCHIVED " + role + " MESSAGE", "END EXACT ARCHIVED " + role + " MESSAGE"
        require(start not in message["content"] and end not in message["content"], "quotation delimiter collision")
        parts.append(start + "\n" + message["content"] + "\n" + end)
    return "\n\n".join(parts)


def compose(old, system, question):
    require(system.strip() and question.strip(), "empty review question")
    request = copy.deepcopy(old)
    for field in EXECUTION_KEYS:
        request.pop(field, None)
    request["seed"] = SEED
    request["messages"] = [dict(role="system", content=system),
        dict(role="user", content=question + "\n\n" + quoted_messages(old))]
    return request


def validate_request(request, old, system, question):
    require(request == compose(old, system, question), "request differs from exact permitted composition")
    require(not (EXECUTION_KEYS & request.keys()), "live action interface present")
    require(request["chat_template_kwargs"] == dict(enable_thinking=True, reasoning_effort="medium"),
            "medium thinking policy differs")
    require(all(request[field] == -1 for field in BUDGETS), "generation/reasoning cap introduced")
    require(request["cache_prompt"] is False and request["stream"] is False, "cache or transport differs")
    require(request["seed"] == SEED, "consultation seed differs")
    require(len(request["messages"]) == 2, "initial request includes unreviewed follow-up")
    # Exact composition is the inclusion boundary: only the review instructions
    # and original two message strings can enter. No source audit, later response,
    # candidate reconstruction, reference artifact or evaluator group is assembled.
    for message in old["messages"]:
        require(message["content"] in request["messages"][1]["content"], "original message omitted")


def source_identities():
    paths = [AREA / n for n in ("PLAN.md", "SYSTEM.txt", "QUESTION_1.txt", "SOURCE.json", "prepare_cpu.py")]
    paths += sorted((AREA / "tests").glob("*.py"))
    paths += [ROOT / "src/working_set_exp" / n for n in ("candidate.py", "custody.py", "jsonutil.py")]
    return {p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}


def prepare(output):
    require(output.resolve().parent == AREA.resolve(), "preparation directory must stay directly inside this package")
    require(not output.exists(), "preserve previous preparation; choose a new attempt directory")
    output.mkdir()
    store = ArtifactStore(output)
    inputs = source_identities()
    files, error = [], None
    try:
        old, seal, verification = historical_source()
        system = (AREA / "SYSTEM.txt").read_text(encoding="utf-8")
        question = (AREA / "QUESTION_1.txt").read_text(encoding="utf-8")
        request = compose(old, system, question)
        validate_request(request, old, system, question)
        files += [store.put("request.json", canonical_json_bytes(request)),
                  store.put("quoted-input.txt", quoted_messages(old).encode("utf-8"))]
        result = dict(status="prepared_cpu_only_native_pending", actor=seal["actor"], seed=SEED,
            initial_requests_prepared=1, conditional_follow_up_prepared=False,
            maximum_total_consultation_requests=2, automatic_follow_up=False,
            completion_requests=0, native_tokenization_performed=False, runtime_started=False,
            checker_executions=0, execution_enabled=False, prompt_tokens=None,
            request_sha256=sha256_bytes(canonical_json_bytes(request)),
            original_message_sha256=[dict(role=m["role"],sha256=sha256_bytes(m["content"].encode("utf-8")))
                                     for m in old["messages"]],
            original_message_content_preserved=True, only_original_messages_and_review_questions_supplied=True,
            additional_reference_solution_supplied=False, source=read(AREA / "SOURCE.json"), **verification)
        files.append(store.put("VALIDATION.json", canonical_json_bytes(result)))
        require(inputs == source_identities(), "preparation inputs changed")
    except BaseException as exc:
        error = exc
        files.append(store.put("FAILED.json", canonical_json_bytes(dict(type=type(exc).__name__, message=str(exc)))))
    finally:
        store.put("SEAL.json", canonical_json_bytes(dict(
            status="failed_preserved" if error else "prepared_cpu_only_native_pending",
            source_identities=inputs, files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files)),
            completion_requests=0, runtime_started=False, native_tokenization_performed=False)))
    if error:
        raise error
    print("Prepared one exact-input consultation request. CPU only; native fit and live freeze remain pending.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=AREA / "cpu-preparation-001")
    prepare(parser.parse_args().output)
