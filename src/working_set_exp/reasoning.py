from __future__ import annotations

from pathlib import Path
from typing import Any

from .candidate import Candidate
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


BANK_SCHEMA = "experiment-004-reasoning-bank-v1"
CASE_IDS = ("E4-SOURCE", "E4-OBSERVATION")
PREFIX_CALL_LIMIT = 18
BRANCH_CALL_LIMIT = 8
CONDITIONS = ("R0", "R1")
SEEDS = {"E4-SOURCE": 57721, "E4-OBSERVATION": 65537}
REASONING_BUDGET = 512


def _ledger(module_name: str, marker: str, *, fact_line: str | None = None) -> bytes:
    lines = [f'"""Exact release ledger {module_name}; preserve every entry."""\n']
    if fact_line:
        lines.append(fact_line.rstrip("\n") + "\n")
    lines.append("RELEASE_ROWS = (\n")
    for index in range(220):
        checksum = sha256_bytes(f"e4:{module_name}:{marker}:{index:04d}".encode("utf-8"))[:24]
        lines.append(f'    ("{marker}-{index:04d}", "{checksum}", "hold-{(index * 23 + 17) % 997:03d}"),\n')
    lines.extend([")\n", "\n", f"def {module_name}_release_size() -> int:\n", "    return len(RELEASE_ROWS)\n"])
    data = "".join(lines).encode("utf-8")
    if not 12_000 <= len(data) <= 18_000:
        raise AssertionError(f"ledger geometry differs: {module_name} {len(data)}")
    return data


def _shared(prefix: str, *, source_fact: bool) -> tuple[dict[str, bytes], tuple[str, ...]]:
    files = {
        "archive/amber.py": _ledger("amber", f"{prefix}A"),
        "archive/cobalt.py": _ledger("cobalt", f"{prefix}C"),
        "archive/ivory.py": _ledger("ivory", f"{prefix}I"),
        "staging/gate.py": (
            b'RELEASE_GROUPS = ("amber", "cobalt", "ivory", "namespace")\n\n\n'
            b"def released_count() -> int:\n"
            b"    return 0\n"
        ),
    }
    required = ["archive/amber.py", "archive/cobalt.py", "archive/ivory.py"]
    if source_fact:
        files["policy/namespace.py"] = _ledger(
            "namespace", f"{prefix}N", fact_line='ACTIVE_NAMESPACE = "orb/"'
        ) + b'\n\ndef active_namespace() -> str:\n    """Return the exact active release namespace."""\n    return ACTIVE_NAMESPACE\n'
        required.append("policy/namespace.py")
    return files, tuple(required)


def _source_case() -> dict[str, Any]:
    files, required = _shared("S", source_fact=True)
    files.update(
        {
            "release/key.py": b"def release_key(name: str) -> str:\n    return name.strip().casefold()\n",
            "release/render.py": b'from release.key import release_key\n\ndef render_key(name: str) -> str:\n    return f"release={release_key(name)}"\n',
        }
    )
    phase_a = (
        "Phase A: read each exact release file completely: "
        + ", ".join(f"`{path}`" for path in required)
        + ". Preserve their contents. Then repair `staging/gate.py` so `released_count()` returns the number of `RELEASE_GROUPS`, "
        "run check `prefork`, and call `fork_ready`. Do not change the Phase B target before `fork_ready`."
    )
    phase_b = (
        "Phase B: repair `release/key.py` so a normalized name is prefixed by the exact active namespace audited in Phase A. "
        "Preserve trimming, case folding, and `release/render.py` behavior. Run check `public` and submit."
    )
    return {
        "fixture_id": "E4-SOURCE",
        "family": "fresh_source_reasoning_transition",
        "files": files,
        "required": required,
        "task": "Perform the two phases in order. " + phase_a + " " + phase_b,
        "phase_b": phase_b,
        "prefork": b"from staging.gate import released_count\nassert released_count() == 4\nprint('prefork check passed')\n",
        "public": (
            b"from release.key import release_key\nfrom release.render import render_key\n"
            b"assert release_key('  Blue  ') == 'orb/blue'\n"
            b"assert render_key('X') == 'release=orb/x'\nprint('public check passed')\n"
        ),
        "hidden": (
            b"from release.key import release_key\nfrom release.render import render_key\n"
            b"assert release_key('  Blue  ') == 'orb/blue'\n"
            b"assert render_key('X') == 'release=orb/x'\n"
            b"assert release_key(' MiXeD ') == 'orb/mixed'\nprint('hidden check passed')\n"
        ),
        "probe_id": None,
        "probe_body": None,
        "final_target": "release/key.py",
        "prefork_patch": {"path": "staging/gate.py", "old": "    return 0", "new": "    return len(RELEASE_GROUPS)"},
        "final_patch": {"path": "release/key.py", "old": "    return name.strip().casefold()", "new": '    return "orb/" + name.strip().casefold()'},
        "governing": {"kind": "current_source", "path": "policy/namespace.py", "fact": 'ACTIVE_NAMESPACE = "orb/"'},
    }


def _observation_case() -> dict[str, Any]:
    files, required = _shared("O", source_fact=False)
    files.update(
        {
            "packet/code.py": b"def packet_code(name: str) -> str:\n    return name.strip().upper()\n",
            "packet/transport.py": b"from packet.code import packet_code\n\ndef encoded_code(name: str) -> bytes:\n    return packet_code(name).encode('ascii')\n",
        }
    )
    phase_a = (
        "Phase A: call compatibility probe `routing` once, then read each exact release file completely: "
        + ", ".join(f"`{path}`" for path in required)
        + ". Preserve their contents. Then repair `staging/gate.py` so `released_count()` returns the number of `RELEASE_GROUPS`, "
        "run check `prefork`, and call `fork_ready`. Do not change the Phase B target before `fork_ready`."
    )
    phase_b = (
        "Phase B: repair `packet/code.py` so it prepends the exact prefix reported by the Phase A routing probe while preserving trimming, "
        "uppercasing, and ASCII transport. The runtime prefix is absent from candidate source. Reopen the historical observation if needed, "
        "run check `public`, and submit."
    )
    return {
        "fixture_id": "E4-OBSERVATION",
        "family": "fresh_observation_reasoning_transition",
        "files": files,
        "required": required,
        "task": "Perform the two phases in order. " + phase_a + " " + phase_b,
        "phase_b": phase_b,
        "prefork": b"from staging.gate import released_count\nassert released_count() == 4\nprint('prefork check passed')\n",
        "public": (
            b"from packet.code import packet_code\nfrom packet.transport import encoded_code\n"
            b"assert packet_code(' blue ') == 'K3>BLUE'\nassert encoded_code('x') == b'K3>X'\nprint('public check passed')\n"
        ),
        "hidden": (
            b"from packet.code import packet_code\nfrom packet.transport import encoded_code\n"
            b"assert packet_code(' blue ') == 'K3>BLUE'\nassert encoded_code('x') == b'K3>X'\n"
            b"assert packet_code(' MiXeD ') == 'K3>MIXED'\nprint('hidden check passed')\n"
        ),
        "probe_id": "routing",
        "probe_body": "routing compatibility result\nrouting_prefix=K3>\nsource=external_router\n",
        "final_target": "packet/code.py",
        "prefork_patch": {"path": "staging/gate.py", "old": "    return 0", "new": "    return len(RELEASE_GROUPS)"},
        "final_patch": {"path": "packet/code.py", "old": "    return name.strip().upper()", "new": '    return "K3>" + name.strip().upper()'},
        "governing": {"kind": "historical_observation", "probe_id": "routing", "fact": "routing_prefix=K3>"},
    }


def case_definitions() -> tuple[dict[str, Any], ...]:
    return (_source_case(), _observation_case())


def _candidate_after(case: dict[str, Any], *, final: bool) -> Candidate:
    candidate = Candidate.create(case["files"])
    patches = [case["prefork_patch"], *([case["final_patch"]] if final else [])]
    for patch in patches:
        candidate, _ = candidate.patch(
            path=patch["path"], old=patch["old"], new=patch["new"],
            expected_candidate_id=candidate.candidate_id,
            expected_file_sha256=candidate.file_sha256(patch["path"]),
        )
    return candidate


def construct_bank(target: Path) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    files: dict[str, bytes] = {}
    for case in case_definitions():
        initial = Candidate.create(case["files"])
        prefork = _candidate_after(case, final=False)
        known_good = _candidate_after(case, final=True)
        visible = f"model_visible/{case['fixture_id']}"
        candidate_rows = []
        for path, data in initial.files:
            files[f"{visible}/candidate/{path}"] = data
            candidate_rows.append({"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)})
        files[f"{visible}/TASK.txt"] = case["task"].encode("utf-8")
        files[f"{visible}/PHASE_B.txt"] = case["phase_b"].encode("utf-8")
        execution = f"execution_only/{case['fixture_id']}"
        files[f"{execution}/checks/prefork.py"] = case["prefork"]
        files[f"{execution}/checks/public.py"] = case["public"]
        if case["probe_body"] is not None:
            files[f"{execution}/PROBE.txt"] = case["probe_body"].encode("utf-8")
        files[f"{execution}/FIXTURE.json"] = canonical_json_bytes(
            {
                "schema_version": "experiment-004-reasoning-fixture-v1",
                "fixture_id": case["fixture_id"], "family": case["family"],
                "initial_candidate_id": initial.candidate_id,
                "prefork_candidate_id": prefork.candidate_id,
                "known_good_candidate_id": known_good.candidate_id,
                "candidate_files": candidate_rows,
                "required_full_reads": list(case["required"]), "final_target": case["final_target"],
                "probe_id": case["probe_id"], "probe_body_present": case["probe_body"] is not None,
                "probe_body_sha256": sha256_bytes(case["probe_body"].encode("utf-8")) if case["probe_body"] else None,
                "phase_b_sha256": sha256_bytes(case["phase_b"].encode("utf-8")),
            }
        )
        evaluator = f"evaluator_only/{case['fixture_id']}"
        files[f"{evaluator}/hidden.py"] = case["hidden"]
        for path, data in known_good.files:
            files[f"{evaluator}/known_good/{path}"] = data
        files[f"{evaluator}/TRUTH.json"] = canonical_json_bytes(
            {
                "schema_version": "experiment-004-reasoning-truth-v1",
                "fixture_id": case["fixture_id"], "known_good_candidate_id": known_good.candidate_id,
                "prefork_candidate_id": prefork.candidate_id, "governing_requirement": case["governing"],
                "phase_b_sha256": sha256_bytes(case["phase_b"].encode("utf-8")),
                "prefork_patch": case["prefork_patch"], "final_patch": case["final_patch"],
            }
        )
    for relative, data in files.items():
        atomic_write(target / Path(*relative.split("/")), data)
    inventory = [
        {"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)}
        for path, data in sorted(files.items())
    ]
    manifest = {
        "schema_version": BANK_SCHEMA,
        "bank_id": "E4BANK-" + sha256_bytes(canonical_json_bytes(inventory)),
        "case_ids": list(CASE_IDS), "fresh_before_actor_exposure": True,
        "evaluator_separate": True, "files": inventory,
    }
    atomic_write(target / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_bank(target: Path) -> dict[str, Any]:
    manifest = load_json_strict((target / "BANK_MANIFEST.json").read_bytes())
    if manifest["schema_version"] != BANK_SCHEMA:
        raise ValueError("reasoning bank schema differs")
    expected = {row["path"] for row in manifest["files"]}
    observed = {
        path.relative_to(target).as_posix()
        for path in target.rglob("*")
        if path.is_file() and path.name != "BANK_MANIFEST.json"
    }
    if expected != observed:
        raise ValueError("reasoning bank inventory paths differ")
    for row in manifest["files"]:
        path = target / Path(*row["path"].split("/"))
        if path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise ValueError("reasoning bank inventory bytes differ")
    bank_id = "E4BANK-" + sha256_bytes(canonical_json_bytes(manifest["files"]))
    if manifest["bank_id"] != bank_id:
        raise ValueError("reasoning bank identity differs")
    return {"verified": True, "bank_id": bank_id, "file_count": len(observed)}


def progress_pointer(bank_root: Path, fixture_id: str) -> dict[str, Any]:
    phase_path = bank_root / "model_visible" / fixture_id / "PHASE_B.txt"
    text = phase_path.read_text(encoding="utf-8")
    return {
        "schema_version": "experiment-004-verbatim-progress-pointer-v1",
        "completed_protocol_stage": "phase_a",
        "active_protocol_stage": "phase_b",
        "active_step_verbatim": text,
        "active_step_sha256": sha256_bytes(text.encode("utf-8")),
        "derivation": "verbatim_user_authored_frozen_task_component",
        "semantic_host_summary": False,
    }
