"""Prepare and run only the approved three-qualification/four-design follow-on.

Every model response is nonexecuting. The consumed initial runner and host
semantics remain unchanged. Qualification review is supplied by the reviewer,
never inferred from this script completing.
"""
from __future__ import annotations

import argparse
import copy
import csv
import http.client
import json
import os
import re
import runpy
import subprocess
import time
import urllib.error
import urllib.request
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Callable

from prepare_interface_design import FACTS, QUESTION, neutral_ids
from run_interface_consultation import candidate_bytes, session_bytes
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.interface_consultation import MODEL_SHA256, SERVER_SHA256, RUNTIME_REVISION, development_states, endpoint_request
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.runtime import HTTP_TIMEOUT_SECONDS, MAX_HTTP_BYTES, port_free, running_process_ids
from working_set_exp.tools import action_schema


ROOT = Path(__file__).resolve().parents[1]
PORT = 18124
ALIAS = "qwen38-iq3-interface-follow-on"
PROFILE_REVISION = "b5ee42b47553c6882862665ca5a58dc0a921d8d0"
ACTOR = {
    "model_sha256": MODEL_SHA256, "server_sha256": SERVER_SHA256,
    "runtime_revision": RUNTIME_REVISION, "context": 56576,
    "kv_k": "q4_0", "kv_v": "q4_0", "generation_reserve": 20480,
    "minimum_free_gpu_mib": 350, "mtp": False, "thinking": True,
    "effort": "xhigh", "budget": -1, "parallel": 1, "fit": False,
}
CALIBRATION_IDS = ["Q1", "Q2", "Q3"]
DESIGN_IDS = ["D1", "D2", "D3", "D4"]
PROFILE_FILES = (
    "scripts/new_long_context_fixture.py",
    "benchmarks/fixtures/quality/coding-reasoning-v1.txt",
    "benchmarks/fixtures/quality/expected.json",
)
FACTS_ADDITION = """
Additional complete operation details from the current implementation:
The schema lists exact required keys, value forms and bounds; extra keys are
not accepted. Available action/check IDs in the current state restrict what
is usable even when the common schema lists another stage's check ID.
For tree/search/p0_page, path '.' means the repository root. Offsets count
rows from zero; returned next_offset is the continuation or null. Tree returns
shallow directory entries; search returns literal case-folded current-source
matches with path, line number and bounded line text. Search query has a host
limit of 128 UTF-8 bytes as well as the grammar's 128-character limit.
P0 returns at most 24 structure rows within 12,000 JSON bytes. It returns
directory structure or Python symbol signatures/ranges, never exact source.
Read uses one-based start_line and no line_count in this mode; read coverage
is separate from any single page's EOF flag. Tree/search/P0 do not count as
complete source reads. All operation results have a 22,000-byte JSON bound.
Reopen_result and reopen_observation return an envelope with accepted, handle,
exact_result_utf8, exact_result_sha256, and size_bytes. exact_result_utf8 is
the full saved original result JSON, including original status/version fields
and its original exact body; it is not just the extracted fields whose size
is shown in result_body. The envelope hash and size describe those saved bytes.
Reopen_event instead returns accepted, handle, action_payload containing the
saved old/new fields, action_payload_sha256, and size_bytes. The payload hash
and size describe that saved field JSON. Retrieval requires an available
handle and an allowed stage. Each access creates an ordered event; it does not
mutate source, rerun an operation, validate the current candidate, or change
current-source read coverage. No call-limit, prior-reading, P0-completeness,
or already-submitted-state check is performed inside the patch operation.
Host scheduling and actor instructions are distinct from tool rejection rules.
"""
DESIGN_CONSTRAINT = """
You may retain familiar names and grouping, but complete tool argument
requirements, accepted forms, binding meanings, and effects must remain
visible to the operating model. They cannot be discarded as internal audit
detail or replaced by a server-side output grammar. Recommend their
presentation without changing the implemented operations or protections.
"""
Q3_QUESTION = """Interpret the supplied state and tool requirements, without performing the task.
1. Which source files have been read completely? Distinguish that from which
   exact source bodies are currently included in this input.
2. Which candidate and file version does the saved source addressed by
   RES-0001 concern? Explain its relationship to the current candidate.
3. What would reopen_result with handle RES-0001 return, and what would or
   would not change? Distinguish the full saved result from extracted-field
   metadata. An operationally equivalent explanation is sufficient; do not
   invent absent source text or propose interface changes.
"""


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def write_json(path: Path, value: Any) -> None:
    if path.exists():
        raise FileExistsError(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(canonical_json_bytes(value))


def source_identities() -> dict[str, str]:
    paths = [Path(__file__), ROOT / "scripts/prepare_interface_design.py",
             ROOT / "scripts/run_interface_consultation.py", *sorted((ROOT / "src").rglob("*.py"))]
    return {path.relative_to(ROOT).as_posix(): sha256_file(path) for path in paths}


def file_inventory(folder: Path) -> list[dict[str, Any]]:
    return [{"path": p.relative_to(folder).as_posix(), "size_bytes": p.stat().st_size, "sha256": sha256_file(p)}
            for p in sorted(folder.rglob("*")) if p.is_file() and "private-runtime" not in p.parts]


def validate_request(request: dict[str, Any]) -> None:
    require([m["role"] for m in request["messages"]] == ["system", "user"], "request is not a fresh system/user pair")
    require(request["model"] == ALIAS and request["seed"] == 42, "unfrozen actor or seed")
    require(all(request[key] == -1 for key in ("max_tokens", "n_predict", "thinking_budget_tokens", "reasoning_budget_tokens")), "request caps generation")
    require(request["chat_template_kwargs"] == {"enable_thinking": True, "reasoning_effort": "xhigh"}, "thinking settings differ")
    require(request["cache_prompt"] is False and request["stream"] is False, "cache/transport settings differ")
    require(not any(key in request for key in ("tools", "functions", "response_format")), "nonexecuting follow-on request supplied an action channel")
    for key, value in {"temperature": 1.0, "top_p": .95, "top_k": 20, "min_p": 0.0,
                       "presence_penalty": 0.0, "frequency_penalty": 0.0, "repeat_penalty": 1.0}.items():
        require(request[key] == value, "sampler differs: " + key)


def request_for(base: dict[str, Any], system: str, user: str) -> dict[str, Any]:
    request = copy.deepcopy(base)
    request["model"] = ALIAS
    request["messages"] = [{"role": "system", "content": system}, {"role": "user", "content": user}]
    validate_request(request)
    return request


class ResponseFailure(RuntimeError):
    def __init__(self, message: str, data: bytes = b"", status: int | None = None):
        super().__init__(message)
        self.data, self.status = data, status


def post(base: str, route: str, raw: bytes, timeout: int) -> bytes:
    request = urllib.request.Request(base + route, data=raw, headers={"Content-Type": "application/json"})
    pieces: list[bytes] = []
    size = 0
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            while size <= MAX_HTTP_BYTES:
                chunk = response.read1(min(65536, MAX_HTTP_BYTES + 1 - size))
                if not chunk:
                    break
                pieces.append(chunk)
                size += len(chunk)
    except urllib.error.HTTPError as error:
        raise ResponseFailure("HTTP response error", error.read(MAX_HTTP_BYTES + 1), error.code) from error
    except (OSError, http.client.HTTPException) as error:
        raise ResponseFailure(type(error).__name__, b"".join(pieces)) from error
    return b"".join(pieces)


def native_render(base: str, request: dict[str, Any]) -> tuple[bytes, bytes, int]:
    raw = canonical_json_bytes(request)
    response = post(base, "/apply-template", raw, 60)
    rendered = load_json_strict(response)["prompt"].encode("utf-8")
    token_response = post(base, "/tokenize", canonical_json_bytes({"content": rendered.decode("utf-8"), "add_special": False}), 60)
    return response, rendered, len(load_json_strict(token_response)["tokens"])


def largest_retention(build: Callable[[int], str], base_request: dict[str, Any], native: Callable) -> tuple[dict, tuple, dict]:
    ceiling = ACTOR["context"] - ACTOR["generation_reserve"]
    system = "Follow the supplied fixture instructions and return the requested final answer."
    trials: dict[int, tuple[dict, tuple]] = {}

    def trial(size: int):
        if size not in trials:
            request = request_for(base_request, system, build(size))
            trials[size] = request, native(request)
        return trials[size]

    low, high = 1000, ACTOR["context"]
    require(trial(low)[1][2] <= ceiling < trial(high)[1][2], "retention search does not bracket admission ceiling")
    while high - low > 1:
        middle = (low + high) // 2
        if trial(middle)[1][2] <= ceiling:
            low = middle
        else:
            high = middle
    request, rendered = trial(low)
    return request, rendered, {"build_prompt_argument": low, "next_argument": high,
            "selected_prompt_tokens": rendered[2], "next_prompt_tokens": trial(high)[1][2],
            "input_ceiling": ceiling, "native_tokenization_trials": len(trials)}


def prepare_package(folder: Path, profile_repo: Path, base_url: str) -> dict[str, Any]:
    folder.mkdir(parents=True, exist_ok=False)
    (folder / "SPEC.md").write_bytes((ROOT / "development/qwen_interface_consultation/follow-on/SPEC.md").read_bytes())
    profile_rows = []
    for relative in PROFILE_FILES:
        raw = subprocess.check_output(["git", "-C", str(profile_repo), "show", PROFILE_REVISION + ":" + relative])
        target = folder / "profile-fixtures" / Path(relative).name
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(raw)
        profile_rows.append({"repository_path": relative, "commit": PROFILE_REVISION, "sha256": sha256_bytes(raw)})
    build = runpy.run_path(str(folder / "profile-fixtures/new_long_context_fixture.py"))["build_prompt"]
    states = development_states(ROOT)
    base_request = endpoint_request(states[0], seed=42, mode="diagnostic")
    grammar = action_schema("continuation", probe_id=None, read_mode="maximal_bounded_page",
                            hierarchical_p0=True, result_reopen=True, event_reopen=True)["json_schema"]["schema"]
    facts = FACTS + FACTS_ADDITION
    question = QUESTION + "\n" + DESIGN_CONSTRAINT
    (folder / "IMPLEMENTATION_FACTS.txt").write_text(facts, encoding="utf-8", newline="\n")
    (folder / "DESIGN_QUESTION.txt").write_text(question, encoding="utf-8", newline="\n")
    write_json(folder / "ACTION_SCHEMA.json", grammar)

    def state_text(state, label):
        return ("Current state, with a neutral fixture identifier:\n" + canonical_json_bytes(neutral_ids(load_json_strict(state.request), label)).decode("utf-8") +
                "\n\n" + facts + "\nActual accepted final-action grammar:\n" + canonical_json_bytes(grammar).decode("utf-8"))

    render = lambda request: native_render(base_url, request)
    q1, q1_render, retention = largest_retention(build, base_request, render)
    q2 = request_for(base_request, "Follow the supplied fixture instructions and return the requested final answer.",
                     (folder / "profile-fixtures/coding-reasoning-v1.txt").read_text(encoding="utf-8"))
    q3 = request_for(base_request, "You are reviewing a coding-agent interface. Explain the supplied state and answer the questions. Do not perform the embedded task or emit a tool action.",
                     state_text(states[0], "Q3") + "\n\nQuestions:\n" + Q3_QUESTION)
    requests = [("Q1", q1, q1_render), ("Q2", q2, None), ("Q3", q3, None)]
    for number, state in enumerate(states, 1):
        identifier = f"D{number}"
        request = request_for(base_request,
            "You are advising on a coding agent interface. Review the supplied state and implementation facts, then propose your preferred presentation. Do not perform the embedded task or emit an executable tool action. Distinguish preferences, implementation facts, and uncertainty.",
            state_text(state, identifier) + "\n\nDesign question:\n" + question)
        requests.append((identifier, request, None))
        state_folder = folder / "states" / identifier
        state_folder.mkdir(parents=True)
        (state_folder / "original-request.json").write_bytes(state.request)
        (state_folder / "candidate.json").write_bytes(candidate_bytes(state.state.candidate))
        (state_folder / "session.json").write_bytes(session_bytes(state.state))
        write_json(state_folder / "provenance.json", state.provenance)
    rows = []
    for identifier, request, rendered_bundle in requests:
        validate_request(request)
        template_raw, rendered, count = rendered_bundle or render(request)
        require(count + ACTOR["generation_reserve"] <= ACTOR["context"], identifier + " lacks generation reserve")
        stem = folder / "requests" / identifier
        stem.parent.mkdir(exist_ok=True)
        Path(str(stem) + "-request.json").write_bytes(canonical_json_bytes(request))
        Path(str(stem) + "-rendered-prompt.txt").write_bytes(rendered)
        Path(str(stem) + "-template-response.json").write_bytes(template_raw)
        rows.append({"id": identifier, "stage": "qualification" if identifier.startswith("Q") else "design", "seed": 42,
                     "request_path": "requests/" + identifier + "-request.json", "request_sha256": sha256_bytes(canonical_json_bytes(request)),
                     "rendered_path": "requests/" + identifier + "-rendered-prompt.txt", "rendered_sha256": sha256_bytes(rendered),
                     "prompt_tokens": count, "physical_generation_space": ACTOR["context"] - count,
                     "tool_execution_enabled": False})
        print(f"Prepared {identifier}: {count} input tokens; {ACTOR['context']-count} physical generation tokens", flush=True)
    first = states[0]
    before = session_bytes(first.state)
    recovered = first.execute({"action": "reopen_result", "handle": "RES-0001"})
    require(before == session_bytes(first.state) and recovered["accepted"], "Q3 expected recovery changed working state")
    frame = load_json_strict(first.request)["active_phase_event_frame"]["events"]
    expected = {"Q1": {"opening_code": "AURORA-3107", "middle_code": "KESTREL-8842", "late_code": "HARBOR-5926", "opening_rule": 1073},
                "Q2": load_json_strict((folder / "profile-fixtures/expected.json").read_bytes())["coding_reasoning_v1"],
                "Q3": {"complete_reads": sorted(first.state.complete_reads),
                    "resident_source_paths": [e["action"]["path"] for e in frame if e["result_body"]["residency"] == "resident"],
                    "external_source_paths": [e["action"]["path"] for e in frame if e["result_body"]["residency"] == "external"],
                    "candidate_id": first.state.candidate.candidate_id, "actual_retrieval_result": recovered,
                    "session_before": load_json_strict(before), "session_after": load_json_strict(session_bytes(first.state)),
                    "criteria": ["eleven complete file reads, four external exact bodies and seven visible",
                                 "RES-0001 original candidate/file binding matches the current unedited version",
                                 "retrieval envelope contains full original saved result, not just extracted field JSON",
                                 "historical access creates an event, but no source mutation/new check/new source reading"]}}
    write_json(folder / "EXPECTED_RESULTS.json", expected)
    write_json(folder / "RETENTION_CONSTRUCTION.json", retention)
    manifest = {"purpose": "three qualification calls then four conditional informed-design calls; development only",
                "actor": copy.deepcopy(ACTOR), "maximum_completion_calls": 7, "maximum_stage_calls": {"qualification": 3, "design": 4},
                "attempts_per_request": 1, "retries": 0, "completion_calls_made_during_preparation": 0,
                "rows": rows, "profile_source": profile_rows, "source_sha256": source_identities(), "files": file_inventory(folder)}
    write_json(folder / "PACKAGE_MANIFEST.json", manifest)
    return manifest


def validate_package(folder: Path) -> dict[str, Any]:
    manifest = load_json_strict((folder / "PACKAGE_MANIFEST.json").read_bytes())
    require(manifest["actor"] == ACTOR, "package actor/configuration differs from frozen follow-on")
    require([r["id"] for r in manifest["rows"]] == CALIBRATION_IDS + DESIGN_IDS, "package schedule differs")
    require(manifest["maximum_completion_calls"] == 7 and manifest["attempts_per_request"] == 1 and manifest["retries"] == 0, "attempt bounds differ")
    for row in manifest["files"]:
        path = folder / row["path"]
        require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"], "package artifact differs: " + row["path"])
    for path, digest in manifest["source_sha256"].items():
        require(sha256_file(ROOT / path) == digest, "execution source differs: " + path)
    for row in manifest["rows"]:
        raw = (folder / row["request_path"]).read_bytes()
        require(sha256_bytes(raw) == row["request_sha256"], "scheduled request differs")
        validate_request(load_json_strict(raw))
        require(row["tool_execution_enabled"] is False and row["prompt_tokens"] + ACTOR["generation_reserve"] <= ACTOR["context"], "request admission differs")
    return manifest


def memory_stats(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {"samples": 0, "min_free_mib": None, "max_free_mib": None}
    values = []
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()
    if text and not text.endswith("\n"):
        lines = lines[:-1]  # Never interpret a partially written memory value.
    for row in csv.reader(lines):
        if len(row) == 5:
            try:
                values.append(int(row[-1]))
            except ValueError:
                pass
    return {"samples": len(values), "min_free_mib": min(values) if values else None, "max_free_mib": max(values) if values else None}


def runtime_evidence(path: Path) -> dict[str, Any]:
    text = path.read_text(encoding="utf-8", errors="replace") if path.exists() else ""
    return {"full_offload": "offloaded 66/66 layers to GPU" in text,
            "context_matches": bool(re.search(r"llama_context: n_ctx\s*=\s*56576\b", text)),
            "q4_k_and_v": "K (q4_0)" in text and "V (q4_0)" in text,
            "mtp_disabled": "no implementations specified for speculative decoding" in text,
            "truncation_observed": bool(re.search(r"truncated\s*=\s*[1-9]", text)),
            "cuda_failure_observed": bool(re.search(r"CUDA error|CUDA out of memory|cudaMalloc.*failed", text, re.I))}


def launch_args(server: Path, model: Path) -> list[str]:
    return [str(server), "--model", str(model), "--alias", ALIAS, "--host", "127.0.0.1", "--port", str(PORT),
            "--ctx-size", str(ACTOR["context"]), "--parallel", "1", "--gpu-layers", "all", "--fit", "off",
            "--threads", "6", "--threads-batch", "6", "--batch-size", "256", "--ubatch-size", "128",
            "--flash-attn", "on", "--cache-type-k", ACTOR["kv_k"], "--cache-type-v", ACTOR["kv_v"], "--jinja",
            "--reasoning", "on", "--reasoning-budget", "-1", "--reasoning-effort", "xhigh", "--reasoning-preserve",
            "--reasoning-format", "deepseek", "--n-predict", "-1", "--temp", "1", "--top-p", ".95", "--top-k", "20",
            "--min-p", "0", "--presence-penalty", "0", "--frequency-penalty", "0", "--repeat-penalty", "1", "--seed", "42",
            "--no-context-shift", "--no-mmproj", "--no-webui", "--metrics", "--slots", "-lv", "4"]


@contextmanager
def owned_runtime(args, store: ArtifactStore, log: RecordLog):
    require(port_free(PORT) and not running_process_ids(args.server.name), "dedicated port or inference server is already in use")
    require(sha256_file(args.model) == MODEL_SHA256 and sha256_file(args.server) == SERVER_SHA256, "model/runtime artifact identity differs")
    private = args.output / "private-runtime"
    private.mkdir()
    launch = launch_args(args.server, args.model)
    write_json(private / "launch.json", launch)
    portable = list(launch)
    portable[0], portable[2] = "<pinned llama-server>", "<selected GGUF>"
    log.append("runtime_prepared", {"actor": ACTOR, "public_launch": portable, "memory_sampling_ms": 200}, [])
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    process = monitor = None
    stdout = (private / "server.stdout.log").open("wb")
    stderr = (private / "server.stderr.log").open("wb")
    memory = (args.output / "memory.csv").open("wb")
    try:
        monitor = subprocess.Popen(["nvidia-smi", "-i", "0", "--query-gpu=timestamp,index,memory.total,memory.used,memory.free", "--format=csv,noheader,nounits", "-lms", "200"],
                                   stdout=memory, stderr=subprocess.DEVNULL, creationflags=flags)
        process = subprocess.Popen(launch, cwd=args.server.parent, stdout=stdout, stderr=stderr, creationflags=flags)
        base = f"http://127.0.0.1:{PORT}"
        for _ in range(240):
            require(process.poll() is None, "owned runtime exited during startup")
            try:
                with urllib.request.urlopen(base + "/health", timeout=2) as reply:
                    if json.load(reply).get("status") == "ok":
                        break
            except (OSError, ValueError):
                pass
            time.sleep(1)
        else:
            raise RuntimeError("runtime startup timed out")
        evidence = runtime_evidence(private / "server.stderr.log")
        require(all(evidence[key] for key in ("full_offload", "context_matches", "q4_k_and_v", "mtp_disabled")), "effective runtime differs; inspect startup logs")
        require(monitor.poll() is None, "GPU monitor exited")
        log.append("runtime_ready", {"effective_runtime": evidence, "memory": memory_stats(args.output / "memory.csv")}, [])
        yield base
    finally:
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        if monitor is not None and monitor.poll() is None:
            monitor.terminate()
            monitor.wait(timeout=10)
        memory.close()
        stdout.close()
        stderr.close()
        log.append("runtime_closed", {"owned_server_shutdown_verified": process is None or process.poll() is not None,
                   "dedicated_port_free": port_free(PORT), "memory": memory_stats(args.output / "memory.csv"),
                   "effective_runtime": runtime_evidence(private / "server.stderr.log")}, [])


def receive_nonexecuting(store: ArtifactStore, log: RecordLog, row: dict, raw: bytes, elapsed: float) -> dict:
    stem = "calls/" + row["id"]
    log.append("response_received", {"id": row["id"], "elapsed_seconds": elapsed}, [store.put(stem + "-endpoint-response.json", raw)])
    require(len(raw) <= MAX_HTTP_BYTES, "response exceeds transport bound; saved bytes are a prefix")
    response = load_json_strict(raw)
    require(len(response["choices"]) == 1, "expected one response choice")
    choice, usage = response["choices"][0], response["usage"]
    message = choice["message"]
    reasoning, content = message.get("reasoning_content") or "", message.get("content") or ""
    artifacts = [store.put(stem + "-assistant-reasoning.txt", reasoning.encode("utf-8")),
                 store.put(stem + "-assistant-content.txt", content.encode("utf-8"))]
    host = {"executed": False, "tool_execution_enabled": False, "mode": row["stage"],
            "finish_reason": choice.get("finish_reason"), "candidate_mutated": False,
            "nonexecuting_response_not_a_coding_continuation": True}
    artifacts.append(store.put(stem + "-host-result.json", canonical_json_bytes(host)))
    outcome = {"id": row["id"], "usage": usage, "finish_reason": choice.get("finish_reason"), "elapsed_seconds": elapsed,
               "host_result": host, "physical_tokens_remaining": ACTOR["context"] - usage["prompt_tokens"] - usage["completion_tokens"],
               "within_proposed_generation_reserve": usage["completion_tokens"] <= ACTOR["generation_reserve"]}
    log.append("invocation_completed", outcome, artifacts)
    require(usage["prompt_tokens"] == row["prompt_tokens"], "native/endpoint input accounting mismatch")
    require(usage.get("prompt_tokens_details", {}).get("cached_tokens") == 0, "unexpected prompt-cache reuse")
    require(choice.get("finish_reason") == "stop" and bool(content), "incomplete final response")
    require(not message.get("tool_calls") and not message.get("function_call"), "unexpected tool output channel")
    return outcome


def verify_seal(folder: Path) -> dict:
    seal = load_json_strict((folder / "RESPONSE_SEAL.json").read_bytes())
    for row in seal["files"]:
        path = folder / row["path"]
        require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"], "sealed file differs: " + row["path"])
    require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "seal aggregate differs")
    require(len(verify_records(folder / "records.jsonl", folder)) == seal["record_count"], "seal chain count differs")
    return seal


def require_qualification(package: Path, run: Path, review: Path) -> None:
    seal = verify_seal(run)
    require(seal["stage"] == "qualification" and seal["disposition"] == "completed_nonexecuting_stage", "qualification did not complete")
    require(seal["package_sha256"] == sha256_file(package / "PACKAGE_MANIFEST.json"), "qualification package differs")
    records = verify_records(run / "records.jsonl", run)
    completed = [r["payload"] for r in records if r["record_type"] == "invocation_completed"]
    require([r["id"] for r in completed] == CALIBRATION_IDS, "qualification responses incomplete")
    require(all(r["finish_reason"] == "stop" and r["within_proposed_generation_reserve"] for r in completed), "qualification output bound failed")
    require(seal["memory"]["samples"] > 0 and seal["memory"]["min_free_mib"] >= ACTOR["minimum_free_gpu_mib"], "qualification GPU reserve failed")
    evidence = seal["effective_runtime"]
    require(all(evidence[key] for key in ("full_offload", "context_matches", "q4_k_and_v", "mtp_disabled")), "qualification runtime differs")
    require(not evidence["truncation_observed"] and not evidence["cuda_failure_observed"], "qualification runtime failure")
    closed = records[-1]["payload"]
    require(closed["owned_server_shutdown_verified"] and closed["dedicated_port_free"], "qualification lifecycle incomplete")
    decision = load_json_strict(review.read_bytes())
    require(decision["qualification_seal_sha256"] == sha256_file(run / "RESPONSE_SEAL.json"), "review is not bound to qualification")
    require(decision["package_sha256"] == seal["package_sha256"] and decision["continue_to_design"] is True, "review does not support design stage")
    require(decision["direct_review_completed_by_reviewer"] is True, "direct review is still pending")
    require(decision["q1_correct_fields"] == 4 and decision["q2_correct_fields"] == 8 and decision["q3_operational_criteria_passed"] == 4, "reviewed content criteria failed")
    require(len(decision["audit_files"]) == 5, "the five audit products are required")
    for row in decision["audit_files"]:
        require(sha256_file(review.parent / row["path"]) == row["sha256"], "reviewed audit differs")


def execute_stage(args, manifest: dict, base_url: str, store: ArtifactStore, log: RecordLog) -> None:
    rows = [r for r in manifest["rows"] if r["stage"] == args.stage]
    required_ids = CALIBRATION_IDS if args.stage == "qualification" else DESIGN_IDS
    require([r["id"] for r in rows] == required_ids, "stage schedule differs")
    for row in rows:
        request_raw = (args.package / row["request_path"]).read_bytes()
        template_raw, rendered, count = native_render(base_url, load_json_strict(request_raw))
        require(count == row["prompt_tokens"] and sha256_bytes(rendered) == row["rendered_sha256"], "native request differs from frozen preparation")
        stem = "calls/" + row["id"]
        log.append("invocation_prepared", row, [store.put(stem + "-endpoint-request.json", request_raw),
            store.put(stem + "-rendered-prompt.txt", rendered), store.put(stem + "-template-response.json", template_raw)])
    for row in rows:
        memory = memory_stats(args.output / "memory.csv")
        require(memory["samples"] > 0 and memory["min_free_mib"] >= ACTOR["minimum_free_gpu_mib"], "sampled GPU reserve below frozen target; no next request sent")
        evidence = runtime_evidence(args.output / "private-runtime/server.stderr.log")
        require(not evidence["truncation_observed"] and not evidence["cuda_failure_observed"], "runtime capacity/protocol failure; no next request sent")
        log.append("invocation_started", {"id": row["id"], "memory_before": memory, "completion_sent": True}, [])
        print(f"Starting {row['id']}: {row['prompt_tokens']} input tokens", flush=True)
        started = time.monotonic()
        try:
            raw = post(base_url, "/v1/chat/completions", (args.package / row["request_path"]).read_bytes(), HTTP_TIMEOUT_SECONDS)
        except ResponseFailure as error:
            log.append("transport_stopped", {"id": row["id"], "error": str(error), "http_status": error.status,
                        "received_bytes_are_not_asserted_complete": True}, [store.put("calls/" + row["id"] + "-transport-body.bin", error.data)])
            raise
        result = receive_nonexecuting(store, log, row, raw, time.monotonic() - started)
        print(f"Completed {row['id']}: {result['finish_reason']}; {result['usage']['completion_tokens']} output tokens; {result['elapsed_seconds']:.1f}s", flush=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--stage", choices=("prepare", "qualification", "design"), required=True)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--profile-repo", type=Path)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--qualification-run", type=Path)
    parser.add_argument("--qualification-review", type=Path)
    args = parser.parse_args()
    if args.stage == "prepare":
        require(args.profile_repo is not None and not args.package.exists(), "preparation needs a new package and pinned profile repository")
        manifest = None
    else:
        manifest = validate_package(args.package)
        if args.stage == "design":
            require(args.qualification_run is not None and args.qualification_review is not None, "design requires the reviewed qualification")
            require_qualification(args.package, args.qualification_run, args.qualification_review)
        # These exact stages have one output location under this package's parent.
        existing = args.package.parent / (args.stage + "-001")
        require(args.output.resolve() == existing.resolve() and not existing.exists(), "stage attempt is already present or output location differs")
    args.output.mkdir(parents=True, exist_ok=False)
    store, log = ArtifactStore(args.output), RecordLog(args.output / "records.jsonl", "qwen-interface-follow-on-" + args.stage)
    disposition = "preflight_failed"
    error_text = None
    log.append("stage_prepared", {"stage": args.stage, "maximum_completion_calls": 0 if args.stage == "prepare" else len(CALIBRATION_IDS if args.stage == "qualification" else DESIGN_IDS),
               "owner_instruction": "Proceed with the saved three-qualification/four-conditional-design plan; no live comparison is included.",
               "actor": ACTOR, "execution_code_sha256": source_identities()}, [])
    try:
        with owned_runtime(args, store, log) as base_url:
            if args.stage == "prepare":
                manifest = prepare_package(args.package, args.profile_repo, base_url)
                log.append("package_prepared", {"package_sha256": sha256_file(args.package / "PACKAGE_MANIFEST.json"), "rows": manifest["rows"], "completion_calls": 0}, [])
                disposition = "prepared_without_model_exposure"
            else:
                log.append("package_verified", {"package_sha256": sha256_file(args.package / "PACKAGE_MANIFEST.json")}, [])
                execute_stage(args, manifest, base_url, store, log)
                disposition = "completed_nonexecuting_stage"
    except BaseException as error:
        disposition = "stopped_without_retry"
        error_text = type(error).__name__ + ": " + str(error)
        for private_path in (args.model, args.server, args.output, args.package, args.profile_repo):
            if private_path is not None:
                error_text = error_text.replace(str(private_path), "<local path>")
        log.append("stage_stopped", {"error": error_text, "no_retry": True}, [])
    finally:
        records = verify_records(args.output / "records.jsonl", args.output)
        completed = [r for r in records if r["record_type"] == "invocation_completed"]
        received = [r for r in records if r["record_type"] == "response_received"]
        sent = [r for r in records if r["record_type"] == "invocation_started"]
        log.append("stage_closed", {"disposition": disposition, "sent_requests": len(sent), "received_responses": len(received),
                   "completed_responses": len(completed), "owned_server_shutdown_verified": not running_process_ids(args.server.name),
                   "dedicated_port_free": port_free(PORT)}, [])
        records = verify_records(args.output / "records.jsonl", args.output)
        files = file_inventory(args.output)
        private = args.output / "private-runtime"
        seal = {"stage": args.stage, "disposition": disposition, "sent_requests": len(sent), "received_responses": len(received),
                "completed_responses": len(completed), "record_count": len(records), "files": files,
                "aggregate_sha256": sha256_bytes(canonical_json_bytes(files)),
                "package_sha256": sha256_file(args.package / "PACKAGE_MANIFEST.json") if (args.package / "PACKAGE_MANIFEST.json").exists() else None,
                "memory": memory_stats(args.output / "memory.csv"), "effective_runtime": runtime_evidence(private / "server.stderr.log"),
                "private_runtime_files_local_only": {p.name: sha256_file(p) for p in sorted(private.glob("*")) if p.is_file()}}
        store.put("RESPONSE_SEAL.json", canonical_json_bytes(seal))
        print(json.dumps({k: v for k, v in seal.items() if k not in {"files", "private_runtime_files_local_only"}}, indent=2), flush=True)
    if error_text:
        raise SystemExit(error_text)


if __name__ == "__main__":
    main()
