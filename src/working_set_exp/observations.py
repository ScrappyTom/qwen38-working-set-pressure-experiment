"""Preserve checker observations before constructing any display report.

Opt-in successor to isolation.run_checker; historical capture remains unchanged.
An observation directory is durable before reporting. Replay reads those exact bytes
instead of rerunning a checker or fabricating a new execution time.
"""
from __future__ import annotations

import base64
import copy
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import threading

from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, utc_now

STREAM_LIMIT = 1_048_576
STORE_LIMIT = 134_217_728
PAGE_BYTES = 4_096


class ObservationStorageError(RuntimeError):
    """Execution may have happened: never translate this into tool rejection."""


def text_tail(data, limit=2048):
    start = max(0, len(data) - limit)
    while start < len(data) and data[start] & 0xC0 == 0x80:
        start += 1
    return dict(text=data[start:].decode("utf-8", errors="replace"),
                start_byte=start, complete=(start == 0))


class ObservationStore:
    def __init__(self, root, *, replay=False, stream_limit=STREAM_LIMIT,
                 storage_limit=STORE_LIMIT, timeout=30, on_preserved=None):
        self.root = Path(root)
        self.replay, self.stream_limit = replay, stream_limit
        self.storage_limit, self.timeout = storage_limit, timeout
        self.on_preserved = on_preserved
        if not 0 < stream_limit <= STREAM_LIMIT or not 0 < storage_limit <= STORE_LIMIT or timeout <= 0:
            raise ValueError("unsupported observation limits")

    def directory(self, handle):
        if not re.fullmatch(r"CHK-[0-9]{4,}", handle):
            raise ValueError("invalid observation reference")
        return self.root / handle

    def read(self, handle):
        folder = self.directory(handle)
        if not (folder / "outcome.json").is_file():
            raise ValueError("observation is unavailable")
        record = load_json_strict((folder / "outcome.json").read_bytes())
        for name, meta in record["streams"].items():
            data = (folder / (name + ".bin")).read_bytes()
            if len(data) != meta["captured_bytes"] or sha256_bytes(data) != meta["sha256"]:
                raise ObservationStorageError("preserved observation bytes differ")
        return record

    def inspect(self, handle, stream, offset):
        record = self.read(handle)
        if stream not in ("stdout", "stderr", "outcome"):
            raise ValueError("unknown observation stream")
        body = ((self.directory(handle) / "outcome.json").read_bytes() if stream == "outcome"
                else (self.directory(handle) / (stream + ".bin")).read_bytes())
        if type(offset) is not int or not 0 <= offset <= len(body):
            raise ValueError("observation offset is outside captured bytes")
        end = min(len(body), offset + PAGE_BYTES)
        try:
            body.decode("utf-8")
        except UnicodeDecodeError:
            encoding, content = "base64", base64.b64encode(body[offset:end]).decode("ascii")
        else:
            if offset < len(body) and body[offset] & 0xC0 == 0x80:
                raise ValueError("use the returned UTF-8 continuation offset")
            while end < len(body) and body[end] & 0xC0 == 0x80:
                end -= 1
            encoding, content = "utf-8", body[offset:end].decode("utf-8")
        return dict(accepted=True, kind="observation_bytes", observation=handle,
                    stream=stream, offset=offset, next_offset=end if end < len(body) else None,
                    captured_bytes=len(body), sha256=sha256_bytes(body), encoding=encoding,
                    content=content, capture_complete=record["capture_complete"],
                    checked_candidate_id=record["candidate_id"],
                    check_definition_sha256=record["checker_sha256"])

    def execute(self, candidate, checker, scope, handle):
        expected = dict(candidate_id=candidate.candidate_id, checker_sha256=sha256_bytes(checker),
                        check_id=scope, observation=handle)
        folder = self.directory(handle)
        if self.replay:
            record = self.read(handle)
            if any(record.get(k) != v for k, v in expected.items()):
                raise ObservationStorageError("replayed observation belongs to another operation")
            return record
        used = sum(p.stat().st_size for p in self.root.rglob("*") if p.is_file()) if self.root.exists() else 0
        if used + 2 * self.stream_limit + 16_384 > self.storage_limit:
            return dict(**{**expected, "observation": None}, executed=False, accepted=False,
                        error="observation storage allowance unavailable; check not started")
        folder.mkdir(parents=True, exist_ok=False)
        started = dict(**expected, started_at_utc=utc_now(), stream_limit_bytes=self.stream_limit,
                       storage_limit_bytes=self.storage_limit, timeout_seconds=self.timeout)
        atomic_write(folder / "started.json", canonical_json_bytes(started))
        limit_hit, errors = threading.Event(), []
        streams = {}
        process = None
        reason = None
        try:
            with tempfile.TemporaryDirectory(prefix="ws-observed-check-") as raw:
                stage = Path(raw)
                for relative, data in candidate.files:
                    target = stage / Path(*relative.split("/"))
                    target.parent.mkdir(parents=True, exist_ok=True)
                    target.write_bytes(data)
                (stage / "_public_check.py").write_bytes(checker)
                env = {"PATH": os.environ.get("PATH", ""), "PYTHONHASHSEED": "0",
                       "PYTHONDONTWRITEBYTECODE": "1"}
                process = subprocess.Popen([sys.executable, "-I", "-S", "-c",
                    "import runpy,sys;sys.path.insert(0,'.');runpy.run_path('_public_check.py',run_name='__main__')"],
                    cwd=stage, env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))

                def capture(name, pipe):
                    observed = kept = 0
                    try:
                        with (folder / (name + ".bin")).open("xb") as output:
                            while chunk := pipe.read(4096):
                                observed += len(chunk)
                                prefix = chunk[:max(0, self.stream_limit - kept)]
                                output.write(prefix)
                                kept += len(prefix)
                                if len(prefix) < len(chunk):
                                    limit_hit.set()
                                    if process.poll() is None:
                                        process.kill()
                            output.flush()
                            os.fsync(output.fileno())
                        body = (folder / (name + ".bin")).read_bytes()
                        streams[name] = dict(captured_bytes=kept, observed_pipe_bytes=observed,
                                             sha256=sha256_bytes(body), capture_limit_bytes=self.stream_limit)
                    except BaseException as error:
                        errors.append(error)
                        if process.poll() is None:
                            process.kill()
                    finally:
                        pipe.close()

                threads = [threading.Thread(target=capture, args=(name, pipe), daemon=True)
                           for name, pipe in (("stdout", process.stdout), ("stderr", process.stderr))]
                for thread in threads:
                    thread.start()
                try:
                    process.wait(timeout=self.timeout)
                except subprocess.TimeoutExpired:
                    reason = "timeout"
                    process.kill()
                    process.wait()
                for thread in threads:
                    thread.join(timeout=5)
                if any(t.is_alive() for t in threads):
                    raise ObservationStorageError("checker pipe did not close; started observation is preserved")
                if errors:
                    raise ObservationStorageError("checker ran but observation storage failed") from errors[0]
        except ObservationStorageError:
            raise
        except BaseException as error:
            raise ObservationStorageError("observation could not be completed; inspect its started record") from error
        reason = reason or ("capture_limit" if limit_hit.is_set() else "completed")
        record = dict(**started, completed_at_utc=utc_now(), executed=True, accepted=True,
                      returncode=process.returncode, termination=reason,
                      capture_complete=(reason == "completed"),
                      passed=(reason == "completed" and process.returncode == 0), streams=streams)
        # No report formatter has run yet. These bytes and their scope already exist.
        atomic_write(folder / "outcome.json", canonical_json_bytes(record))
        if self.on_preserved:
            artifacts = []
            for name in ("started.json", "stdout.bin", "stderr.bin", "outcome.json"):
                data = (folder / name).read_bytes()
                artifacts.append(dict(path=handle + "/" + name, size_bytes=len(data), sha256=sha256_bytes(data)))
            try:
                self.on_preserved(copy.deepcopy(record), artifacts)
            except Exception as error:
                raise ObservationStorageError("observation is saved but its custody callback failed") from error
        return record


def check_report(store, record):
    """Small derived report; complete observations are already durable."""
    if not record.get("executed"):
        return record
    result = dict(accepted=True, executed=True, check_id=record["check_id"],
                  checked_candidate_id=record["candidate_id"], check_definition_sha256=record["checker_sha256"],
                  passed=record["passed"], returncode=record["returncode"],
                  observation=record["observation"], capture_complete=record["capture_complete"],
                  termination=record["termination"], streams=record["streams"])
    stdout = (store.directory(record["observation"]) / "stdout.bin").read_bytes()
    stderr = (store.directory(record["observation"]) / "stderr.bin").read_bytes()
    try:
        structured = load_json_strict(stdout)
    except (ValueError, UnicodeError):
        structured = None
    if isinstance(structured, dict) and structured.get("observation_schema") == "contribution-check-v2":
        summary = {}
        for name in ("saved_suite", "edited_suite", "observed_paths", "examples"):
            value = structured.get(name)
            if isinstance(value, dict):
                summary[name] = {k: value[k] for k in ("tests", "failures", "errors", "skipped", "successful", "complete", "examples") if k in value}
        primary = None
        for name in ("saved_suite", "edited_suite", "observed_paths", "examples"):
            value = structured.get(name, {})
            details = value.get("details", []) if isinstance(value, dict) else []
            if details and not value.get("successful", True):
                if isinstance(details, str):
                    details = [dict(test="documentation examples", trace=details)]
                first = details[0]
                primary = dict(scope=name, test=str(first.get("test", ""))[:300],
                               diagnostic=text_tail(str(first.get("trace", first)).encode(), 3072),
                               additional_failures=max(0, len(details) - 1))
                break
        faults = structured.get("fault_sensitivity", {})
        result["report"] = dict(suites=summary, primary_real_failure=primary,
            expected_fault_checks=dict(tested=len(faults), detected=sum(not r.get("successful", True) for r in faults.values())),
            all_details_in_observation=True,
            existing_work_preserved=structured.get("existing_work_preserved"),
            documentation_preserved=structured.get("documentation_preserved"))
        if structured.get("assessment_error"):
            result["report"]["assessment_error"] = text_tail(str(structured["assessment_error"]).encode())
    else:
        result["report"] = dict(stdout_tail=text_tail(stdout), stderr_tail=text_tail(stderr),
                                full_captured_streams_in_observation=True)
    return result
