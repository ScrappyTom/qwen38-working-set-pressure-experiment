from __future__ import annotations

import csv
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
from .request import REASONING_DIAGNOSTIC_SYSTEM_PROMPT, SYSTEM_PROMPT, render_prompt, render_reasoning_prompt
from .tools import action_schema


MAX_HTTP_BYTES = 16 * 1024 * 1024
OUTPUT_TOKENS = 2_500
RUNTIME_ALLOWANCE = 512
PHYSICAL_CONTEXT = 50_176
C50_PROMPT_CEILING = 47_000
T25_TOTAL_CEILING = 25_000
PORT = 18_110
REASONING_BUDGET = 512
# The RTX 3060 reference host evaluates long prompts at roughly 7 tokens/s and
# the frozen actor can generate at roughly 1.1 tokens/s. A physically admitted
# 50k prompt plus the 2,500-token output allowance can therefore legitimately
# exceed two hours. This is a transport-hang bound, not a model time budget.
HTTP_TIMEOUT_SECONDS = 14_400


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
    reasoning_content: bytes = b""


@dataclass(frozen=True)
class PreparedCall:
    call_id: str
    endpoint_request: bytes
    rendered_prompt: bytes
    offline_prompt_tokens: int
    active_total_ceiling: int
    authorized: bool
    admission: dict[str, Any]


class TransportStopped(RuntimeError):
    def __init__(self, message: str, *, response_body: bytes | None = None, http_status: int | None = None):
        super().__init__(message)
        self.response_body = response_body
        self.http_status = http_status


class CapacityStopped(RuntimeError):
    def __init__(self, admission: dict[str, Any]):
        super().__init__("capacity guard denied endpoint call")
        self.admission = admission


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


def guard(
    profile: RuntimeProfile,
    request: bytes,
    *,
    active_total_ceiling: int,
    reasoning_enabled: bool = False,
) -> dict[str, Any]:
    rendered = render_reasoning_prompt(request, enabled=reasoning_enabled) if reasoning_enabled else render_prompt(request)
    count = tokenizer_count(profile, rendered)
    adjusted = count + RUNTIME_ALLOWANCE
    if active_total_ceiling == T25_TOTAL_CEILING:
        authorized = adjusted + OUTPUT_TOKENS <= T25_TOTAL_CEILING
    else:
        authorized = adjusted <= C50_PROMPT_CEILING and adjusted + OUTPUT_TOKENS <= PHYSICAL_CONTEXT
    result = {
        "authorized": authorized,
        "offline_prompt_tokens": count,
        "runtime_allowance_tokens": RUNTIME_ALLOWANCE,
        "adjusted_prompt_tokens": adjusted,
        "output_allowance_tokens": OUTPUT_TOKENS,
        "active_total_ceiling_tokens": active_total_ceiling,
        "rendered_prompt_sha256": sha256_bytes(rendered),
        "rendered_prompt_bytes": len(rendered),
    }
    if reasoning_enabled:
        result.update({"reasoning_enabled": True, "reasoning_budget_tokens": REASONING_BUDGET})
    return result


def endpoint_request(
    profile: RuntimeProfile,
    request: bytes,
    *,
    stage: str,
    probe_id: str | None,
    seed: int,
    reasoning_enabled: bool = False,
    read_mode: str = "actor_selected_count",
    hierarchical_p0: bool = False,
) -> bytes:
    body = {
        "model": profile.model_alias,
        "messages": [
            {
                "role": "system",
                "content": REASONING_DIAGNOSTIC_SYSTEM_PROMPT if reasoning_enabled else SYSTEM_PROMPT,
            },
            {"role": "user", "content": request.decode("utf-8")},
        ],
        "response_format": action_schema(stage, probe_id=probe_id, read_mode=read_mode, hierarchical_p0=hierarchical_p0),
        "max_tokens": OUTPUT_TOKENS,
        "stream": False,
        "seed": seed,
        "temperature": 0.7,
        "top_p": 0.8,
        "top_k": 20,
        "min_p": 0.0,
        "presence_penalty": 1.5,
        "repeat_penalty": 1.0,
        "reasoning_budget": REASONING_BUDGET if reasoning_enabled else 0,
        **({"reasoning_effort": "low"} if reasoning_enabled else {}),
        "chat_template_kwargs": {
            "enable_thinking": reasoning_enabled,
            "preserve_thinking": False,
            **({"reasoning_effort": "low"} if reasoning_enabled else {}),
        },
    }
    return canonical_json_bytes(body)


def _bounded_read(response: Any) -> bytes:
    data = response.read(MAX_HTTP_BYTES + 1)
    if len(data) > MAX_HTTP_BYTES:
        raise RuntimeError("endpoint response exceeds bound")
    return data


class LiveActor:
    def __init__(
        self,
        profile: RuntimeProfile,
        *,
        seed: int,
        port: int = PORT,
        reasoning_enabled: bool = False,
        read_mode: str = "actor_selected_count",
        hierarchical_p0: bool = False,
    ):
        self.profile = profile
        self.seed = seed
        self.url = f"http://127.0.0.1:{port}/v1/chat/completions"
        self.reasoning_enabled = reasoning_enabled
        self.read_mode = read_mode
        self.hierarchical_p0 = hierarchical_p0
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
        rendered = render_reasoning_prompt(request, enabled=True) if self.reasoning_enabled else render_prompt(request)
        admission = guard(
            self.profile,
            request,
            active_total_ceiling=active_total_ceiling,
            reasoning_enabled=self.reasoning_enabled,
        )
        body = endpoint_request(
            self.profile,
            request,
            stage=stage,
            probe_id=probe_id,
            seed=self.seed,
            reasoning_enabled=self.reasoning_enabled,
            read_mode=self.read_mode,
            hierarchical_p0=self.hierarchical_p0,
        )
        return PreparedCall(
            call_id=call_id,
            endpoint_request=body,
            rendered_prompt=rendered,
            offline_prompt_tokens=admission["offline_prompt_tokens"],
            active_total_ceiling=active_total_ceiling,
            authorized=admission["authorized"],
            admission=admission,
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
            with urllib.request.urlopen(http_request, timeout=HTTP_TIMEOUT_SECONDS) as response:
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
        reasoning = choice["message"].get("reasoning_content", "")
        if not isinstance(reasoning, str):
            raise RuntimeError("assistant reasoning content is not a string")
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
            reasoning_content=reasoning.encode("utf-8"),
        )


def port_free(port: int = PORT) -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        try:
            probe.bind(("127.0.0.1", port))
        except OSError:
            return False
    return True


def running_process_ids(image_name: str) -> tuple[int, ...]:
    """Return exact-name process IDs for the dedicated runtime preflight."""
    if os.name == "nt":
        completed = subprocess.run(
            ["tasklist", "/FI", f"IMAGENAME eq {image_name}", "/FO", "CSV", "/NH"],
            capture_output=True,
            check=True,
            text=True,
            errors="replace",
        )
        rows = csv.reader(completed.stdout.splitlines())
        return tuple(
            sorted(
                int(row[1])
                for row in rows
                if len(row) >= 2 and row[0].casefold() == image_name.casefold() and row[1].isdigit()
            )
        )
    completed = subprocess.run(
        ["pgrep", "-x", image_name], capture_output=True, check=False, text=True, errors="replace"
    )
    if completed.returncode not in {0, 1}:
        raise RuntimeError(f"process preflight failed for {image_name}")
    return tuple(sorted(int(line) for line in completed.stdout.splitlines() if line.strip().isdigit()))


class OwnedServer:
    def __init__(
        self,
        profile: RuntimeProfile,
        run_root: Path,
        *,
        port: int = PORT,
        reasoning_mode: str = "off",
        reasoning_budget: int | None = None,
    ):
        if reasoning_mode not in {"off", "auto"}:
            raise ValueError("invalid server reasoning mode")
        if reasoning_budget is not None and reasoning_budget < -1:
            raise ValueError("invalid server reasoning budget")
        self.profile = profile
        self.run_root = run_root
        self.port = port
        self.reasoning_mode = reasoning_mode
        self.reasoning_budget = reasoning_budget
        self.process: subprocess.Popen[bytes] | None = None
        self.stdout: Any = None
        self.stderr: Any = None
        self.shutdown_verified = False

    def __enter__(self) -> "OwnedServer":
        if not port_free(self.port):
            raise RuntimeError(f"dedicated port {self.port} is occupied")
        competing = running_process_ids(self.profile.server_path.name)
        if competing:
            raise RuntimeError(f"competing {self.profile.server_path.name} process IDs exist: {competing}")
        runtime = self.run_root / "runtime"
        runtime.mkdir(parents=True, exist_ok=False)
        slots = runtime / "slots"
        slots.mkdir()
        server_reasoning_budget = (
            self.reasoning_budget
            if self.reasoning_budget is not None
            else (-1 if self.reasoning_mode == "auto" else 0)
        )
        arguments = [
            "-m", str(self.profile.model_path), "--alias", self.profile.model_alias,
            "--host", "127.0.0.1", "--port", str(self.port), "--gpu-layers", "all",
            "--fit", "off", "-c", "50000", "--flash-attn", "on", "-ctk", "q4_0", "-ctv", "q4_0",
            "--kv-unified", "-b", "512", "-ub", "256", "--threads", "7", "--threads-batch", "8",
            "--parallel", "1", "--cache-prompt", "--cache-ram", "0", "--slot-save-path", str(slots),
            "--no-context-shift", "--jinja", "--reasoning", self.reasoning_mode, "--reasoning-format", "deepseek",
            "--reasoning-budget", str(server_reasoning_budget), "--no-reasoning-preserve", "--temp", "0.7", "--top-p", "0.8",
            "--top-k", "20", "--min-p", "0.0", "--presence-penalty", "1.5", "--repeat-penalty", "1.0",
            "--metrics", "--slots", "--no-mmproj", "--verbose", "--log-file", str(runtime / "llama-server.log"),
        ]
        self.stdout = (runtime / "server-stdout.bin").open("wb")
        self.stderr = (runtime / "server-stderr.bin").open("wb")
        self.process = subprocess.Popen(
            [str(self.profile.server_path), *arguments],
            cwd=self.profile.runtime_root,
            stdout=self.stdout,
            stderr=self.stderr,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
        (runtime / "launch.json").write_bytes(
            canonical_json_bytes(
                {
                    "executable": str(self.profile.server_path),
                    "arguments": arguments,
                    "owned_pid": self.process.pid,
                }
            )
        )
        deadline = time.monotonic() + 180
        while time.monotonic() < deadline:
            if self.process.poll() is not None:
                self._shutdown()
                raise RuntimeError("llama-server exited before readiness")
            try:
                with urllib.request.urlopen(f"http://127.0.0.1:{self.port}/health", timeout=2) as response:
                    if response.status == 200:
                        return self
            except Exception:
                time.sleep(0.5)
        self._shutdown()
        raise RuntimeError("llama-server readiness timed out")

    def _shutdown(self) -> None:
        self.shutdown_verified = False
        if self.process is not None and self.process.poll() is None:
            self.process.terminate()
            try:
                self.process.wait(timeout=30)
            except subprocess.TimeoutExpired:
                self.process.kill()
                try:
                    self.process.wait(timeout=30)
                except subprocess.TimeoutExpired:
                    pass
        if self.stdout is not None:
            self.stdout.close()
        if self.stderr is not None:
            self.stderr.close()
        deadline = time.monotonic() + 30
        while time.monotonic() < deadline and not port_free(self.port):
            time.sleep(0.25)
        process_terminated = self.process is not None and self.process.poll() is not None
        port_released = port_free(self.port)
        self.shutdown_verified = process_terminated and port_released
        runtime = self.run_root / "runtime"
        if runtime.is_dir():
            (runtime / "shutdown.json").write_bytes(
                canonical_json_bytes(
                    {
                        "owned_pid": self.process.pid if self.process is not None else None,
                        "process_returncode": self.process.poll() if self.process is not None else None,
                        "process_terminated": process_terminated,
                        "port": self.port,
                        "port_released": port_released,
                        "verified": self.shutdown_verified,
                    }
                )
            )
        if not self.shutdown_verified:
            raise RuntimeError(
                "owned llama-server shutdown was not verified "
                f"(process_terminated={process_terminated}, port_released={port_released})"
            )

    def __exit__(self, exc_type: Any, exc: Any, traceback: Any) -> None:
        self._shutdown()
