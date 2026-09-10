"""Run the frozen, owner-requested 16-response interface development package.

The old experiment actor hardcodes its template and output limits. This narrow
adapter uses the selected runtime's native template and uncapped generation;
it retains the existing action parser, tools, artifact store, and record chain.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.interface_consultation import MODEL_SHA256, SERVER_SHA256, development_states
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.runtime import HTTP_TIMEOUT_SECONDS, MAX_HTTP_BYTES, port_free, running_process_ids
from working_set_exp.tools import strict_action


ROOT = Path(__file__).resolve().parents[1]
PORT = 18124
CONTEXT = 32768
DEVELOPMENT_GENERATION_ROOM = 8192


def post(base: str, route: str, body: bytes, timeout: int) -> bytes:
    request = urllib.request.Request(base + route, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read(MAX_HTTP_BYTES + 1)


def candidate_bytes(value: Any) -> bytes:
    return canonical_json_bytes({"candidate_id": value.candidate_id,
                                 "files": [{"path": path, "content_utf8": data.decode("utf-8"), "sha256": sha256_bytes(data)}
                                           for path, data in value.files]})


def session_bytes(value: Any) -> bytes:
    return canonical_json_bytes({"candidate_id": value.candidate.candidate_id,
                                 "complete_reads": sorted(value.complete_reads), "read_coverage": value.read_coverage,
                                 "public_check_passed": value.public_check_passed, "submitted": value.submitted})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--server", type=Path, required=True)
    parser.add_argument("--prepare-only", action="store_true", help="load/tokenize only; make zero completion calls")
    args = parser.parse_args()
    manifest = load_json_strict((args.package / "PACKAGE_MANIFEST.json").read_bytes())
    for row in manifest["files"]:
        path = args.package / row["path"]
        if path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise ValueError(f"prepared package differs: {row['path']}")
    for relative, digest in manifest["preparation_code_sha256"].items():
        if sha256_file(ROOT / relative) != digest:
            raise ValueError(f"prepared state code differs: {relative}")
    schedule = load_json_strict((args.package / "SCHEDULE.json").read_bytes())
    if len(schedule) != 16 or manifest["maximum_completion_calls"] != 16:
        raise ValueError("consultation schedule differs")
    if sha256_file(args.model) != MODEL_SHA256 or sha256_file(args.server) != SERVER_SHA256:
        raise ValueError("selected model/runtime identity differs")
    if not port_free(PORT) or running_process_ids(args.server.name):
        raise RuntimeError("dedicated port or inference runtime is already in use")
    args.output.mkdir(parents=True, exist_ok=False)
    private = args.output / "private-runtime"
    private.mkdir()
    store = ArtifactStore(args.output)
    log = RecordLog(args.output / "records.jsonl", "qwen-interface-consultation-001")
    launch = [str(args.server), "--model", str(args.model), "--alias", "qwen38-iq3-interface",
              "--host", "127.0.0.1", "--port", str(PORT), "--ctx-size", str(CONTEXT), "--parallel", "1",
              "--gpu-layers", "all", "--fit", "off", "--threads", "6", "--threads-batch", "6",
              "--batch-size", "256", "--ubatch-size", "128", "--flash-attn", "on",
              "--cache-type-k", "q8_0", "--cache-type-v", "q8_0", "--jinja",
              "--reasoning", "on", "--reasoning-budget", "-1", "--reasoning-effort", "xhigh",
              "--reasoning-preserve", "--reasoning-format", "deepseek", "--n-predict", "-1",
              "--temp", "1", "--top-p", ".95", "--top-k", "20", "--min-p", "0",
              "--presence-penalty", "0", "--frequency-penalty", "0", "--repeat-penalty", "1", "--seed", "42",
              "--no-context-shift", "--no-mmproj", "--no-webui", "--metrics", "--slots", "-lv", "4"]
    (private / "launch.json").write_bytes(canonical_json_bytes(launch))
    public_launch = list(launch)
    public_launch[0], public_launch[2] = "<pinned llama-server>", "<selected GGUF>"
    log.append("development_prepared", {"package_sha256": sha256_file(args.package / "PACKAGE_MANIFEST.json"),
               "maximum_completion_calls": 0 if args.prepare_only else 16, "model_sha256": MODEL_SHA256,
               "server_sha256": SERVER_SHA256, "public_launch": public_launch,
               "development_generation_room": DEVELOPMENT_GENERATION_ROOM,
               "generation_room_is_not_an_output_cap_or_final_comparison_reserve": True,
               "execution_code_sha256": {path.relative_to(ROOT).as_posix(): sha256_file(path)
                                         for path in [Path(__file__), *sorted((ROOT / "src").rglob("*.py"))]}}, [])
    stdout = (private / "server.stdout.log").open("wb")
    stderr = (private / "server.stderr.log").open("wb")
    process = monitor = None
    memory_stream = None
    completions = 0
    disposition = "preflight_failed"
    base = f"http://127.0.0.1:{PORT}"
    flags = subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0
    try:
        process = subprocess.Popen(launch, cwd=args.server.parent, stdout=stdout, stderr=stderr, creationflags=flags)
        for _ in range(240):
            if process.poll() is not None:
                raise RuntimeError("dedicated server exited during startup; inspect exact runtime logs")
            try:
                with urllib.request.urlopen(base + "/health", timeout=2) as response:
                    if json.load(response).get("status") == "ok":
                        break
            except (OSError, ValueError):
                pass
            time.sleep(1)
        else:
            raise TimeoutError("dedicated server did not become ready")
        memory_stream = (args.output / "memory.csv").open("wb")
        monitor = subprocess.Popen(["nvidia-smi", "--query-gpu=timestamp,memory.used,memory.free", "--format=csv,noheader,nounits", "-lms", "500"],
                                   stdout=memory_stream, stderr=subprocess.DEVNULL, creationflags=flags)
        prepared = []
        for row in schedule:
            raw = (args.package / row["request_path"]).read_bytes()
            if sha256_bytes(raw) != row["request_sha256"]:
                raise ValueError("scheduled request differs")
            request = load_json_strict(raw)
            rendered_raw = post(base, "/apply-template", raw, 60)
            rendered = load_json_strict(rendered_raw)["prompt"]
            tokens = load_json_strict(post(base, "/tokenize", canonical_json_bytes({"content": rendered, "add_special": False}), 60))["tokens"]
            count = len(tokens)
            stem = f"calls/{row['ordinal']:02d}"
            artifacts = [store.put(stem + "-endpoint-request.json", raw), store.put(stem + "-rendered-prompt.txt", rendered.encode("utf-8")),
                         store.put(stem + "-template-response.json", rendered_raw)]
            admitted = count + DEVELOPMENT_GENERATION_ROOM <= CONTEXT
            log.append("invocation_prepared", {**row, "prompt_tokens": count, "physical_generation_space": CONTEXT-count,
                       "admitted": admitted, "completion_sent": False}, artifacts)
            if not admitted:
                raise RuntimeError(f"development request {row['ordinal']} lacks the fixed generation room")
            prepared.append((row, raw, count))
        print(f"Native template/token preflight completed for {len(prepared)} requests; maximum input {max(x[2] for x in prepared)} tokens.", flush=True)
        if args.prepare_only:
            disposition = "prepared_without_model_exposure"
            return
        for row, raw, count in prepared:
            # Rebuild the actual-tool state for each independent invocation.
            value = {item.name: item for item in development_states(ROOT)}[row["state"]]
            request = load_json_strict(raw)
            user = request["messages"][1]["content"]
            if row["mode"] == "action" and user.encode("utf-8") != value.request:
                raise ValueError("execution state differs from its prepared model input")
            stem = f"calls/{row['ordinal']:02d}"
            log.append("invocation_started", row, [store.put(stem + "-candidate-before.json", candidate_bytes(value.state.candidate)),
                                                  store.put(stem + "-state-before.json", session_bytes(value.state))])
            print(f"Starting {row['ordinal']}/16: {row['mode']} {row['state']} seed {row['seed']}", flush=True)
            started = time.monotonic()
            try:
                response_raw = post(base, "/v1/chat/completions", raw, HTTP_TIMEOUT_SECONDS)
            except urllib.error.HTTPError as error:
                failure_raw = error.read(MAX_HTTP_BYTES + 1)
                log.append("transport_stopped", {**row, "http_status": error.code}, [store.put(stem + "-endpoint-error.json", failure_raw)])
                raise
            elapsed = time.monotonic() - started
            # Preserve raw bytes before parsing, scoring, or executing any action.
            raw_artifact = store.put(stem + "-endpoint-response.json", response_raw)
            log.append("response_received", {**row, "elapsed_seconds": elapsed}, [raw_artifact])
            completions += 1
            if len(response_raw) > MAX_HTTP_BYTES:
                raise ValueError("response exceeds transport byte bound; preserved prefix is not a complete response")
            response = load_json_strict(response_raw)
            choice = response["choices"][0]
            message = choice["message"]
            content, reasoning = message.get("content") or "", message.get("reasoning_content") or ""
            artifacts = [store.put(stem + "-assistant-content.txt", content.encode("utf-8")),
                         store.put(stem + "-assistant-reasoning.txt", reasoning.encode("utf-8"))]
            usage = response.get("usage", {})
            if usage.get("prompt_tokens") != count:
                log.append("prompt_accounting_mismatch", {"offline_native_tokens": count, "usage": usage}, artifacts)
                raise ValueError("native rendered prompt and actual usage differ; inspect host path before continuing")
            result: dict[str, Any] = {"executed": False, "mode": row["mode"], "finish_reason": choice.get("finish_reason")}
            if choice.get("finish_reason") == "stop" and content and row["mode"] == "action":
                try:
                    action = strict_action(content.encode("utf-8"))
                    result = {"executed": True, "action": action, "result": value.execute(action)}
                except (ValueError, RuntimeError) as error:
                    result = {"executed": False, "protocol_error": str(error)}
            elif choice.get("finish_reason") != "stop" or not content:
                result["disposition"] = "incomplete_output_no_action_executed"
            artifacts.extend([store.put(stem + "-host-result.json", canonical_json_bytes(result)),
                              store.put(stem + "-state-after.json", session_bytes(value.state)),
                              store.put(stem + "-candidate-after.json", candidate_bytes(value.state.candidate))])
            log.append("invocation_completed", {**row, "usage": usage, "elapsed_seconds": elapsed,
                       "finish_reason": choice.get("finish_reason"), "host_result": result}, artifacts)
            print(f"Completed {row['ordinal']}/16: {choice.get('finish_reason')}, {usage.get('completion_tokens')} output tokens, {elapsed:.1f}s", flush=True)
        disposition = "completed_development_consultation"
    except BaseException as error:
        disposition = "stopped_without_retry"
        log.append("development_stopped", {"error_type": type(error).__name__, "error": str(error), "completed_responses": completions}, [])
        raise
    finally:
        if monitor is not None:
            monitor.terminate()
            monitor.wait(timeout=10)
        if memory_stream is not None:
            memory_stream.close()
        if process is not None and process.poll() is None:
            process.terminate()
            try:
                process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=10)
        stdout.close()
        stderr.close()
        shutdown = process is None or process.poll() is not None
        log.append("development_closed", {"disposition": disposition, "completed_responses": completions,
                   "owned_server_shutdown_verified": shutdown, "dedicated_port_free": port_free(PORT)}, [])
        records = verify_records(args.output / "records.jsonl", args.output)
        files = [{"path": path.relative_to(args.output).as_posix(), "size_bytes": path.stat().st_size, "sha256": sha256_file(path)}
                 for path in sorted(args.output.rglob("*")) if path.is_file() and "private-runtime" not in path.parts]
        store.put("RESPONSE_SEAL.json", canonical_json_bytes({"disposition": disposition, "completed_responses": completions,
                  "record_count": len(records), "files": files, "aggregate_sha256": sha256_bytes(canonical_json_bytes(files)),
                  "private_runtime_files_local_only": {path.name: sha256_file(path) for path in sorted(private.glob("*")) if path.is_file()}}))


if __name__ == "__main__":
    main()
