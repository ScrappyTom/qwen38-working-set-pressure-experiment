from __future__ import annotations

import json
import subprocess
from pathlib import Path

from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_file, utc_now
from working_set_exp.runtime import (
    OwnedServer,
    PORT,
    REASONING_BUDGET,
    load_runtime,
    port_free,
    running_process_ids,
)


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "009_recurrent_observation_validity"
OUTPUT = Path(r"C:\e9-lifecycle-qualification")


def main() -> None:
    if OUTPUT.exists():
        raise FileExistsError(OUTPUT)
    status = subprocess.run(
        ["git", "status", "--porcelain"], cwd=ROOT, capture_output=True, check=True, text=True
    ).stdout
    if status:
        raise RuntimeError("lifecycle qualification requires a clean checkout")
    source_commit = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=ROOT, capture_output=True, check=True, text=True
    ).stdout.strip()
    profile_path = EXPERIMENT / "RUNTIME_PROFILE.json"
    profile = load_runtime(profile_path)
    before = running_process_ids(profile.server_path.name)
    if before or not port_free(PORT):
        raise RuntimeError(f"dirty lifecycle preflight: pids={before}, port_free={port_free(PORT)}")
    OUTPUT.mkdir(parents=True)
    receipt = {
        "schema_version": "experiment-009-owned-server-lifecycle-qualification-v1",
        "started_at_utc": utc_now(),
        "source_commit": source_commit,
        "runtime_profile_sha256": sha256_file(profile_path),
        "completion_calls": 0,
        "endpoint_requests": 0,
        "prelaunch_process_ids": list(before),
        "status": "started",
    }
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    server = OwnedServer(
        profile, OUTPUT, port=PORT, reasoning_mode="auto", reasoning_budget=REASONING_BUDGET
    )
    with server:
        launch = load_json_strict((OUTPUT / "runtime" / "launch.json").read_bytes())
        receipt["owned_pid"] = launch["owned_pid"]
        receipt["readiness_reached"] = True
        atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    after = running_process_ids(profile.server_path.name)
    shutdown = load_json_strict((OUTPUT / "runtime" / "shutdown.json").read_bytes())
    if not server.shutdown_verified or after or not port_free(PORT) or not shutdown["verified"]:
        raise RuntimeError(
            f"lifecycle qualification failed: owned={server.shutdown_verified}, pids={after}, "
            f"port_free={port_free(PORT)}, shutdown={shutdown}"
        )
    receipt.update(
        {
            "status": "passed",
            "completed_at_utc": utc_now(),
            "owned_process_termination_verified": True,
            "port_release_verified": True,
            "postshutdown_process_ids": list(after),
            "shutdown_record_sha256": sha256_file(OUTPUT / "runtime" / "shutdown.json"),
        }
    )
    atomic_write(OUTPUT / "RECEIPT.json", canonical_json_bytes(receipt))
    print(json.dumps(receipt, indent=2))


if __name__ == "__main__":
    main()
