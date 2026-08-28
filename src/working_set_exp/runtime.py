from __future__ import annotations

import os
import re
import socket
import subprocess
import tempfile
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from .request import SYSTEM_PROMPT, render_prompt
from .tools import action_schema


MAX_HTTP_BYTES = 16 * 1024 * 1024
OUTPUT_TOKENS = 2_500
RUNTIME_ALLOWANCE = 512
PHYSICAL_CONTEXT = 50_176
C50_PROMPT_CEILING = 47_000
T25_TOTAL_CEILING = 25_000
PORT = 18_110


@dataclass(frozen=True)
class RuntimeProfile:
    model_alias: str
    model_path: Path
    model_sha256: str
    tokenizer_path: Path
    tokenizer_sha256: str
    server_path: Path
    server_sha256: str
    runtime_root: Path
    build: str


@dataclass(frozen=True)
class CallOutcome:
    endpoint_request: bytes
    rendered_prompt: bytes
    raw_endpoint_response: bytes
    assistant_content: bytes
    offline_prompt_tokens: int
    server_prompt_tokens: int
    completion_tokens: int
    accounting_delta: int
    elapsed_ms: int
    response_id: str


@dataclass(frozen=True)
class PreparedCall:
    call_id: str
    endpoint_request: bytes
    rendered_prompt: bytes
    offline_prompt_tokens: int
    active_total_ceiling: int


class TransportStopped(RuntimeError):
    def __init__(self, message: str, *, response_body: bytes | None = None, http_status: int | None = None):
        super().__init__(message)
        self.response_body = response_body
        self.http_status = http_status


def load_runtime(path: Path) -> RuntimeProfile:
    value = load_json_strict(path.read_bytes())
    profile = RuntimeProfile(
        model_alias=value["model_alias"],
        model_path=Path(value["model_path"]),
        model_sha256=value["model_sha256"],
        tokenizer_path=Path(value["tokenizer_path"]),
        tokenizer_sha256=value["tokenizer_sha256"],
        server_path=Path(value["server_path"]),
        server_sha256=value["server_sha256"],
        runtime_root=Path(value["runtime_root"]),
        build=value["build"],
    )
    for actual, expected, label in (
        (profile.model_path, profile.model_sha256, "model"),
        (profile.tokenizer_path, profile.tokenizer_sha256, "tokenizer"),
        (profile.server_path, profile.server_sha256, "server"),
    ):
        if not actual.is_file() or sha256_file(actual) != expected:
            raise RuntimeError(f"{label} identity differs")
    return profile


def tokenizer_count(profile: RuntimeProfile, rendered: bytes) -> int:
    with tempfile.TemporaryDirectory(prefix="ws-exp-tokenize-") as raw:
        prompt = Path(raw) / "prompt.bin"
        prompt.write_bytes(rendered)
        completed = subprocess.run(
            [
                str(profile.tokenizer_path),
                "--offline",
                "--model",
                str(profile.model_path),
                "--file",
                str(prompt),
                "--show-count",
                "--no-bos",
                "--no-escape",
            ],
            env={**os.environ, "LLAMA_ARG_OFFLINE": "1"},
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    matches = re.findall(r"Total number of tokens:\s*(\d+)", completed.stdout + "\n" + completed.stderr)
    if completed.returncode != 0 or len(matches) != 1:
        raise RuntimeError("offline tokenizer failed")
    return int(matches[0])


def guard(profile: RuntimeProfile, request: bytes, *, active_total_ceiling: int) -> dict[str, Any]:
    rendered = render_prompt(request)
    count = tokenizer_count(profile, rendered)
    adjusted = count + RUNTIME_ALLOWANCE
    if active_total_ceiling == T25_TOTAL_CEILING:
        authorized = adjusted + OUTPUT_TOKENS <= T25_TOTAL_CEILING
    else:
        authorized = adjusted <= C50_PROMPT_CEILING and adjusted + OUTPUT_TOKENS <= PHYSICAL_CONTEXT
    return {
        "authorized": authorized,
        "offline_prompt_tokens": count,
        "runtime_allowance_tokens": RUNTIME_ALLOWANCE,
        "adjusted_prompt_tokens": adjusted,
        "output_allowance_tokens": OUTPUT_TOKENS,
        "active_total_ceiling_tokens": active_total_ceiling,
        "rendered_prompt_sha256": sha256_bytes(rendered),
        "rendered_prompt_bytes": len(rendered),
    }


def endpoint_request(profile: RuntimeProfile, request: bytes, *, stage: str, probe_id: str | None, seed: int) -> bytes:
    body = {
        "model": profile.model_alias,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": request.decode("utf-8")},
        ],
        "response_format": action_schema(stage, probe_id=probe_id),
        "max_tokens": OUTPUT_TOKENS,
        "stream": False,
        "seed": seed,
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "min_p": 0.0,
        "presence_penalty": 1.5,
        "repeat_penalty": 1.0,
        "reasoning_budget": 0,
        "chat_template_kwargs": {"enable_thinking": False, "preserve_thinking": False},
    }
    return canonical_json_bytes(body)


def _bounded_read(response: Any) -> bytes:
    data = response.read(MAX_HTTP_BYTES + 1)
    if len(data) > MAX_HTTP_BYTES:
        raise RuntimeError("endpoint response exceeds bound")
    return data


class LiveActor:
    def __init__(self, profile: RuntimeProfile, *, seed: int, port: int = PORT):
        self.profile = profile
        self.seed = seed
        self.url = f"http://127.0.0.1:{port}/v1/chat/completions"
        self.call_ids: set[str] = set()

    def prepare(
        self,
        request: bytes,
        *,
        stage: str,
        probe_id: str | None,
        call_id: str,
        active_total_ceiling: int,
    ) -> PreparedCall:
        if call_id in self.call_ids:
            raise RuntimeError("call ID reused; retries are prohibited")
        self.call_ids.add(call_id)
        rendered = render_prompt(request)
        admission = guard(self.profile, request, active_total_ceiling=active_total_ceiling)
        if not admission["authorized"]:
            raise RuntimeError("capacity guard denied endpoint call")
        body = endpoint_request(self.profile, request, stage=stage, probe_id=probe_id, seed=self.seed)
        return PreparedCall(
            call_id=call_id,
            endpoint_request=body,
            rendered_prompt=rendered,
            offline_prompt_tokens=admission["offline_prompt_tokens"],
            active_total_ceiling=active_total_ceiling,
        )

    def invoke(self, prepared: PreparedCall) -> CallOutcome:
        http_request = urllib.request.Request(
            self.url,
            data=prepared.endpoint_request,
            headers={"Content-Type": "application/json", "Authorization": "Bearer local"},
            method="POST",
        )
        started = time.perf_counter()
        try:
            with urllib.request.urlopen(http_request, timeout=600) as response:
                raw = _bounded_read(response)
                status = response.status
        except urllib.error.HTTPError as exc:
            raw = _bounded_read(exc)
            raise TransportStopped(
                f"endpoint HTTP status {exc.code}",
                response_body=raw,
                http_status=exc.code,
            ) from exc
        except (urllib.error.URLError, OSError, TimeoutError) as exc:
            raise TransportStopped(f"endpoint transport failure: {exc}") from exc
        elapsed = round((time.perf_counter() - started) * 1000)
        if status != 200:
            raise TransportStopped(f"endpoint HTTP status {status}", response_body=raw, http_status=status)
        value = load_json_strict(raw)
        if not isinstance(value, dict) or not isinstance(value.get("choices"), list) or len(value["choices"]) != 1:
            raise RuntimeError("endpoint envelope choices differ")
        choice = value["choices"][0]
        if choice.get("finish_reason") != "stop" or not isinstance(choice.get("message"), dict):
            raise RuntimeError("endpoint did not return one stopped message")
        content = choice["message"].get("content")
        if not isinstance(content, str):
            raise RuntimeError("assistant content is not a string")
        usage = value.get("usage")
        if not isinstance(usage, dict):
            raise RuntimeError("endpoint usage is absent")
        server_prompt = usage.get("prompt_tokens")
        completion = usage.get("completion_tokens")
        if not isinstance(server_prompt, int) or not isinstance(completion, int):
            raise RuntimeError("endpoint token accounting differs")
        delta = server_prompt - prepared.offline_prompt_tokens
        # With --cache-prompt this llama.cpp build reports only newly evaluated
        # prompt tokens in API usage. A negative delta is cache reuse, not lower
        # context occupancy. Positive unexplained growth remains fail-closed.
        if delta > RUNTIME_ALLOWANCE:
            raise TransportStopped(
                "runtime prompt accounting delta exceeds allowance",
                response_body=raw,
                http_status=status,
            )
        return CallOutcome(
            endpoint_request=prepared.endpoint_request,
            rendered_prompt=prepared.rendered_prompt,
            raw_endpoint_response=raw,
            assistant_content=content.encode("utf-8"),
            offline_prompt_tokens=prepared.offline_prompt_tokens,
            server_prompt_tokens=server_prompt,
            completion_tokens=completion,
            accounting_delta=delta,
            elapsed_ms=elapsed,
            response_id=str(value.get("id", "")),
        )


def port_free(port: int = PORT) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


class OwnedServer:
    def __init__(self, profile: RuntimeProfile, run_root: Path, *, port: int = PORT):
        self.profile = profile
        self.run_root = run_root
        self.port = port
        self.process: subprocess.Popen[bytes] | None = None
        self.stdout: Any = None
        self.stderr: Any = None

    def __enter__(self) -> "OwnedServer":
        if not port_free(self.port):
            raise RuntimeError(f"dedicated port {self.port} is occupied")
        runtime = self.run_root / "runtime"
        runtime.mkdir(parents=True, exist_ok=False)
        slots = runtime / "slots"
        slots.mkdir()
        arguments = [
            "-m", str(self.profile.model_path), "--alias", self.profile.model_alias,
            "--host", "127.0.0.1", "--port", str(self.port), "--gpu-layers", "all",
            "--fit", "off", "-c", "50000", "--flash-attn", "on", "-ctk", "q4_0", "-ctv", "q4_0",
            "--kv-unified", "-b", "512", "-ub", "256", "--threads", "7", "--threads-batch", "8",
            "--parallel", "1", "--cache-prompt", "--cache-ram", "0", "--slot-save-path", str(slots),
            "--no-context-shift", "--jinja", "--reasoning", "off", "--reasoning-format", "deepseek",
            "--reasoning-budget", "0", "--no-reasoning-preserve", "--temp", "0.7", "--top-p", "0.8",
            "--top-k", "20", "--min-p", "0.0", "--presence-penalty", "1.5", "--repeat-penalty", "1.0",
            "--metrics", "--slots", "--no-mmproj", "--verbose", "--log-file", str(runtime / "llama-server.log"),
        ]
        (runtime / "launch.json").write_bytes(canonical_json_bytes({"executable": str(self.profile.server_path), "arguments": arguments}))
        self.stdout = (runtime / "server-stdout.bin").open("wb")
        self.stderr = (runtime / "server-stderr.bin").open("wb")
        self.process = subprocess.Popen(
            [str(self.profile.server_path), *arguments],
            cwd=self.profile.runtime_root,
            stdout=self.stdout,
            stderr=self.stderr,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                raise RuntimeError("llama-server exited before readiness")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=2) as response:
                    if response.status == 200:
                        return self
            except Exception:
                time.sleep(0.5)
        raise RuntimeError("llama-server readiness timed out")

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=30)
        if self.stdout is not None:
            self.stdout.close()
        if self.stderr is not None:
            self.stderr.close()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not port_free(self.port):
            time.sleep(0.25)
        if not port_free(self.port):
            raise RuntimeError("server port was not released")
