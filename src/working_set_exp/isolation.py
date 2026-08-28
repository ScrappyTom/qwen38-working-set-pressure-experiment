from __future__ import annotations

import os
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

from .candidate import Candidate
from .jsonutil import sha256_bytes


MAX_CHECK_STREAM_BYTES = 8_192


def run_checker(candidate: Candidate, checker: bytes) -> dict[str, Any]:
    with tempfile.TemporaryDirectory(prefix="ws-exp-check-") as raw:
        stage = Path(raw)
        for relative, data in candidate.files:
            target = stage / Path(*relative.split("/"))
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(data)
        checker_path = stage / "_public_check.py"
        checker_path.write_bytes(checker)
        env = {
            "PATH": os.environ.get("PATH", ""),
            "PYTHONHASHSEED": "0",
            "PYTHONDONTWRITEBYTECODE": "1",
        }
        completed = subprocess.run(
            [
                sys.executable,
                "-I",
                "-S",
                "-c",
                "import runpy,sys;sys.path.insert(0,'.');runpy.run_path('_public_check.py',run_name='__main__')",
            ],
            cwd=stage,
            env=env,
            capture_output=True,
            check=False,
            timeout=30,
        )
    stdout = completed.stdout[:MAX_CHECK_STREAM_BYTES]
    stderr = completed.stderr[:MAX_CHECK_STREAM_BYTES]
    return {
        "passed": completed.returncode == 0,
        "returncode": completed.returncode,
        "stdout": stdout.decode("utf-8", errors="replace"),
        "stderr": stderr.decode("utf-8", errors="replace"),
        "stdout_size_bytes": len(completed.stdout),
        "stderr_size_bytes": len(completed.stderr),
        "stdout_sha256": sha256_bytes(completed.stdout),
        "stderr_sha256": sha256_bytes(completed.stderr),
        "streams_truncated": len(completed.stdout) > len(stdout) or len(completed.stderr) > len(stderr),
    }
