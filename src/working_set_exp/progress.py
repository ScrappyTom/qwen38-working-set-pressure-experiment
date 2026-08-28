from __future__ import annotations

from pathlib import Path
from typing import Any

from .candidate import Candidate
from .jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file


BANK_SCHEMA = "experiment-003-progress-pointer-bank-v1"
CASE_IDS = ("E3-SOURCE", "E3-OBSERVATION")
PREFIX_CALL_LIMIT = 18
BRANCH_CALL_LIMIT = 8
CONDITIONS = ("T25-M", "T25-P")
SEEDS = {"E3-SOURCE": 314159, "E3-OBSERVATION": 173205}


def _ledger(module_name: str, marker: str, *, fact_line: str | None = None) -> bytes:
    lines = [f'"""Exact certification ledger {module_name}; preserve every entry."""\n']
    if fact_line:
        lines.append(fact_line.rstrip("\n") + "\n")
    lines.append("CERTIFICATION_ROWS = (\n")
    for index in range(220):
        checksum = sha256_bytes(f"e3:{module_name}:{marker}:{index:04d}".encode("utf-8"))[:24]
        lines.append(f'    ("{marker}-{index:04d}", "{checksum}", "retain-{(index * 19 + 31) % 991:03d}"),\n')
    lines.extend([")\n", "\n", f"def {module_name}_certification_size() -> int:\n", "    return len(CERTIFICATION_ROWS)\n"])
    data = "".join(lines).encode("utf-8")
    if not 12_000 <= len(data) <= 18_000:
        raise AssertionError(f"ledger geometry differs: {module_name} {len(data)}")
    return data


def _shared(prefix: str, *, source_fact: bool) -> tuple[dict[str, bytes], tuple[str, ...]]:
    files = {
        "cert/north.py": _ledger("north", f"{prefix}N"),
        "cert/south.py": _ledger("south", f"{prefix}S"),
        "cert/east.py": _ledger("east", f"{prefix}E"),
        "staging/readiness.py": (
            b'CERT_GROUPS = ("north", "south", "east", "policy")\n\n\n'
            b"def certified_count() -> int:\n"
            b"    return 0\n"
        ),
    }
    required = ["cert/north.py", "cert/south.py", "cert/east.py"]
    if source_fact:
        files["policy/track.py"] = _ledger(
            "track", f"{prefix}P", fact_line='TRACK_PREFIX = "gold-"'
        ) + b'\n\ndef track_prefix() -> str:\n    """Return the exact active track prefix."""\n    return TRACK_PREFIX\n'
        required.append("policy/track.py")
    return files, tuple(required)


def _source_case() -> dict[str, Any]:
    files, required = _shared("G", source_fact=True)
    files.update(
        {
            "publish/slug.py": b"def publish_slug(name: str) -> str:\n    return name.strip().lower()\n",
            "publish/formatting.py": b'def display_slug(slug: str) -> str:\n    return f"publish={slug}"\n',
        }
    )
    phase_a = (
        "Phase A: read each exact certification file completely: "
        + ", ".join(f"`{path}`" for path in required)
        + ". Preserve their contents. Then repair `staging/readiness.py` so `certified_count()` returns the number of `CERT_GROUPS`, "
        "run check `prefork`, and call `fork_ready`. Do not change the Phase B target before `fork_ready`."
    )
    phase_b = (
        "Phase B: repair `publish/slug.py` so a normalized name is prefixed by the exact active track policy audited in Phase A. "
        "Preserve trimming, lowercasing, and `publish/formatting.py` behavior. Run check `public` and submit."
    )
    return {
        "fixture_id": "E3-SOURCE",
        "family": "source_progress_reconstruction",
        "files": files,
        "required": required,
        "task": "Perform the two phases in order. " + phase_a + " " + phase_b,
        "phase_b": phase_b,
        "prefork": b"from staging.readiness import certified_count\nassert certified_count() == 4\nprint('prefork check passed')\n",
        "public": (
            b"from publish.slug import publish_slug\nfrom publish.formatting import display_slug\n"
            b"assert publish_slug('  Blue  ') == 'gold-blue'\n"
            b"assert display_slug(publish_slug('X')) == 'publish=gold-x'\nprint('public check passed')\n"
        ),
        "hidden": (
            b"from publish.slug import publish_slug\nfrom publish.formatting import display_slug\n"
            b"assert publish_slug('  Blue  ') == 'gold-blue'\n"
            b"assert display_slug(publish_slug('X')) == 'publish=gold-x'\n"
            b"assert publish_slug(' MiXeD ') == 'gold-mixed'\nprint('hidden check passed')\n"
        ),
        "probe_id": None,
        "probe_body": None,
        "final_target": "publish/slug.py",
        "prefork_patch": {"path": "staging/readiness.py", "old": "    return 0", "new": "    return len(CERT_GROUPS)"},
        "final_patch": {"path": "publish/slug.py", "old": "    return name.strip().lower()", "new": '    return "gold-" + name.strip().lower()'},
        "governing": {"kind": "current_source", "path": "policy/track.py", "fact": 'TRACK_PREFIX = "gold-"'},
    }


def _observation_case() -> dict[str, Any]:
    files, required = _shared("H", source_fact=False)
    files.update(
        {
            "wire/header.py": b"def wire_header(name: str) -> str:\n    return name.strip().upper()\n",
            "wire/transport.py": b"from wire.header import wire_header\n\ndef encoded_header(name: str) -> bytes:\n    return wire_header(name).encode('ascii')\n",
        }
    )
    phase_a = (
        "Phase A: call compatibility probe `negotiation` once, then read each exact certification file completely: "
        + ", ".join(f"`{path}`" for path in required)
        + ". Preserve their contents. Then repair `staging/readiness.py` so `certified_count()` returns the number of `CERT_GROUPS`, "
        "run check `prefork`, and call `fork_ready`. Do not change the Phase B target before `fork_ready`."
    )
    phase_b = (
        "Phase B: repair `wire/header.py` so it prepends the exact prefix reported by the Phase A compatibility probe while preserving trimming, "
        "uppercasing, and ASCII transport. The runtime prefix is absent from candidate source. Reopen the historical observation if needed, "
        "run check `public`, and submit."
    )
    return {
        "fixture_id": "E3-OBSERVATION",
        "family": "observation_progress_reconstruction",
        "files": files,
        "required": required,
        "task": "Perform the two phases in order. " + phase_a + " " + phase_b,
        "phase_b": phase_b,
        "prefork": b"from staging.readiness import certified_count\nassert certified_count() == 4\nprint('prefork check passed')\n",
        "public": (
            b"from wire.header import wire_header\nfrom wire.transport import encoded_header\n"
            b"assert wire_header(' blue ') == 'R7|BLUE'\nassert encoded_header('x') == b'R7|X'\nprint('public check passed')\n"
        ),
        "hidden": (
            b"from wire.header import wire_header\nfrom wire.transport import encoded_header\n"
            b"assert wire_header(' blue ') == 'R7|BLUE'\nassert encoded_header('x') == b'R7|X'\n"
            b"assert wire_header(' MiXeD ') == 'R7|MIXED'\nprint('hidden check passed')\n"
        ),
        "probe_id": "negotiation",
        "probe_body": "compatibility negotiation result\nnegotiated_prefix=R7|\nsource=external_peer\n",
        "final_target": "wire/header.py",
        "prefork_patch": {"path": "staging/readiness.py", "old": "    return 0", "new": "    return len(CERT_GROUPS)"},
        "final_patch": {"path": "wire/header.py", "old": "    return name.strip().upper()", "new": '    return "R7|" + name.strip().upper()'},
        "governing": {"kind": "historical_observation", "probe_id": "negotiation", "fact": "negotiated_prefix=R7|"},
    }


def case_definitions() -> tuple[dict[str, Any], ...]:
    return (_source_case(), _observation_case())


def _candidate_after(case: dict[str, Any], *, final: bool) -> Candidate:
    candidate = Candidate.create(case["files"])
    for patch in [case["prefork_patch"], *([case["final_patch"]] if final else [])]:
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
                "schema_version": "experiment-003-progress-fixture-v1",
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
                "schema_version": "experiment-003-progress-truth-v1", "fixture_id": case["fixture_id"],
                "known_good_candidate_id": known_good.candidate_id, "prefork_candidate_id": prefork.candidate_id,
                "governing_requirement": case["governing"], "phase_b_sha256": sha256_bytes(case["phase_b"].encode("utf-8")),
                "prefork_patch": case["prefork_patch"], "final_patch": case["final_patch"],
            }
        )
    for relative, data in files.items():
        atomic_write(target / Path(*relative.split("/")), data)
    inventory = [{"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)} for path, data in sorted(files.items())]
    manifest = {
        "schema_version": BANK_SCHEMA, "bank_id": "E3BANK-" + sha256_bytes(canonical_json_bytes(inventory)),
        "case_ids": list(CASE_IDS), "fresh_before_actor_exposure": True, "evaluator_separate": True, "files": inventory,
    }
    atomic_write(target / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_bank(target: Path) -> dict[str, Any]:
    manifest = load_json_strict((target / "BANK_MANIFEST.json").read_bytes())
    if manifest["schema_version"] != BANK_SCHEMA:
        raise ValueError("progress bank schema differs")
    expected = {row["path"] for row in manifest["files"]}
    observed = {path.relative_to(target).as_posix() for path in target.rglob("*") if path.is_file() and path.name != "BANK_MANIFEST.json"}
    if expected != observed:
        raise ValueError("progress bank inventory paths differ")
    for row in manifest["files"]:
        path = target / Path(*row["path"].split("/"))
        if path.stat().st_size != row["size_bytes"] or sha256_file(path) != row["sha256"]:
            raise ValueError("progress bank inventory bytes differ")
    bank_id = "E3BANK-" + sha256_bytes(canonical_json_bytes(manifest["files"]))
    if manifest["bank_id"] != bank_id:
        raise ValueError("progress bank identity differs")
    return {"verified": True, "bank_id": bank_id, "file_count": len(observed)}


def progress_pointer(bank_root: Path, fixture_id: str) -> dict[str, Any]:
    phase_path = bank_root / "model_visible" / fixture_id / "PHASE_B.txt"
    text = phase_path.read_text(encoding="utf-8")
    return {
        "schema_version": "experiment-003-verbatim-progress-pointer-v1",
        "completed_protocol_stage": "phase_a",
        "active_protocol_stage": "phase_b",
        "active_step_verbatim": text,
        "active_step_sha256": sha256_bytes(text.encode("utf-8")),
        "derivation": "verbatim_user_authored_frozen_task_component",
        "semantic_host_summary": False,
    }
