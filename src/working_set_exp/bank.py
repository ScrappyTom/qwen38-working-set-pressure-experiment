from __future__ import annotations

from pathlib import Path
from typing import Any

from .candidate import Candidate
from .jsonutil import atomic_write, canonical_json_bytes, sha256_bytes


BANK_SCHEMA = "experiment-002-bank-v1"
MEASURED_CASES = ("E2-SOURCE", "E2-OBSERVATION")
DEVELOPMENT_CASE = "DEV-RECONSTRUCTION"


def _ledger(module_name: str, marker: str, *, fact_line: str | None = None) -> bytes:
    lines = [f'"""Exact audit ledger {module_name}; preserve all entries."""\n']
    if fact_line:
        lines.append(fact_line.rstrip("\n") + "\n")
    lines.append("AUDIT_ROWS = (\n")
    for index in range(220):
        checksum = sha256_bytes(f"{module_name}:{marker}:{index:04d}".encode("utf-8"))[:24]
        lines.append(
            f'    ("{marker}-{index:04d}", "{checksum}", "preserve-{(index * 17 + 23) % 997:03d}"),\n'
        )
    lines.extend(
        [
            ")\n",
            "\n",
            f"def {module_name}_audit_size() -> int:\n",
            "    return len(AUDIT_ROWS)\n",
        ]
    )
    data = "".join(lines).encode("utf-8")
    if not 12_000 <= len(data) <= 18_000:
        raise AssertionError(f"ledger geometry differs: {module_name} {len(data)}")
    return data


def _common_files(prefix: str, *, source_fact: bool) -> tuple[dict[str, bytes], tuple[str, ...]]:
    files: dict[str, bytes] = {
        "audit/alpha.py": _ledger("alpha", f"{prefix}A"),
        "audit/bravo.py": _ledger("bravo", f"{prefix}B"),
        "staging/readiness.py": (
            b'AUDIT_GROUPS = ("alpha", "bravo", "policy")\n\n\n'
            b"def audited_count() -> int:\n"
            b"    return 0\n"
        ),
    }
    if source_fact:
        files["policy/channel.py"] = _ledger(
            "channel",
            f"{prefix}P",
            fact_line='RELEASE_PREFIX = "stable-"',
        ) + b'\n\ndef release_prefix() -> str:\n    """Return the exact current release prefix."""\n    return RELEASE_PREFIX\n'
    else:
        files["audit/echo.py"] = _ledger("echo", f"{prefix}E")
    required = tuple(sorted(path for path in files if path.startswith("audit/") or path == "policy/channel.py"))
    return files, required


def _source_case(case_id: str, *, development: bool = False) -> dict[str, Any]:
    prefix = "D" if development else "S"
    files, required = _common_files(prefix, source_fact=True)
    files.update(
        {
            "release/tag.py": (
                b"def release_tag(name: str) -> str:\n"
                b"    return name.strip().lower()\n"
            ),
            "release/formatting.py": b"def display_tag(tag: str) -> str:\n    return f\"release={tag}\"\n",
        }
    )
    task = (
        "Perform the two phases in order. Phase A: read each of these exact audit files completely: "
        + ", ".join(f"`{path}`" for path in required)
        + ". Preserve their contents. Then read and repair `staging/readiness.py` so `audited_count()` returns "
        "the number of `AUDIT_GROUPS`, run check `prefork`, and call `fork_ready`. Do not change the Phase B target before `fork_ready`. "
        "Phase B: repair the release-tag behavior so a normalized name is prefixed by the exact current channel policy that you audited in Phase A. "
        "Preserve normalization and formatting behavior. Run check `public` and submit."
    )
    prefork = b"from staging.readiness import audited_count\nassert audited_count() == 3\nprint('prefork check passed')\n"
    public = (
        b"from release.tag import release_tag\n"
        b"from release.formatting import display_tag\n"
        b"assert release_tag('  Blue  ') == 'stable-blue'\n"
        b"assert display_tag(release_tag('X')) == 'release=stable-x'\n"
        b"print('public check passed')\n"
    )
    hidden = public + b"assert release_tag(' MiXeD ') == 'stable-mixed'\nprint('hidden check passed')\n"
    return {
        "fixture_id": case_id,
        "family": "source_reacquisition",
        "files": files,
        "required": required,
        "task": task,
        "prefork": prefork,
        "public": public,
        "hidden": hidden,
        "probe_id": None,
        "probe_body": None,
        "final_target": "release/tag.py",
        "prefork_patch": {"path": "staging/readiness.py", "old": "    return 0", "new": "    return len(AUDIT_GROUPS)"},
        "final_patch": {"path": "release/tag.py", "old": "    return name.strip().lower()", "new": '    return "stable-" + name.strip().lower()'},
        "governing": {"kind": "current_source", "path": "policy/channel.py", "fact": 'RELEASE_PREFIX = "stable-"'},
    }


def _observation_case(case_id: str) -> dict[str, Any]:
    files, required = _common_files("O", source_fact=False)
    files.update(
        {
            "protocol/banner.py": (
                b"def wire_banner(name: str) -> str:\n"
                b"    return name.strip().upper()\n"
            ),
            "protocol/transport.py": b"from protocol.banner import wire_banner\n\ndef encoded_banner(name: str) -> bytes:\n    return wire_banner(name).encode('ascii')\n",
        }
    )
    task = (
        "Perform the two phases in order. Phase A: call compatibility probe `wire`, then read each of these exact audit files completely: "
        + ", ".join(f"`{path}`" for path in required)
        + ". Preserve their contents. Then read and repair `staging/readiness.py` so `audited_count()` returns the number of `AUDIT_GROUPS`, "
        "run check `prefork`, and call `fork_ready`. Do not change the Phase B target before `fork_ready`. "
        "Phase B: repair the wire banner so it prepends the exact prefix reported by the earlier compatibility probe while preserving trimming, uppercasing, and ASCII transport. "
        "The runtime prefix is not stored in candidate source. Run check `public` and submit."
    )
    prefork = b"from staging.readiness import audited_count\nassert audited_count() == 3\nprint('prefork check passed')\n"
    public = (
        b"from protocol.banner import wire_banner\n"
        b"from protocol.transport import encoded_banner\n"
        b"assert wire_banner(' blue ') == 'XP9:BLUE'\n"
        b"assert encoded_banner('x') == b'XP9:X'\n"
        b"print('public check passed')\n"
    )
    hidden = public + b"assert wire_banner(' MiXeD ') == 'XP9:MIXED'\nprint('hidden check passed')\n"
    return {
        "fixture_id": case_id,
        "family": "observation_reacquisition",
        "files": files,
        "required": required,
        "task": task,
        "prefork": prefork,
        "public": public,
        "hidden": hidden,
        "probe_id": "wire",
        "probe_body": "compatibility runtime observation\nwire_prefix=XP9:\nsource=external_handshake\n",
        "final_target": "protocol/banner.py",
        "prefork_patch": {"path": "staging/readiness.py", "old": "    return 0", "new": "    return len(AUDIT_GROUPS)"},
        "final_patch": {"path": "protocol/banner.py", "old": "    return name.strip().upper()", "new": '    return "XP9:" + name.strip().upper()'},
        "governing": {"kind": "historical_observation", "probe_id": "wire", "fact": "wire_prefix=XP9:"},
    }


def case_definitions(*, measured: bool) -> tuple[dict[str, Any], ...]:
    if measured:
        return (_source_case("E2-SOURCE"), _observation_case("E2-OBSERVATION"))
    return (_source_case(DEVELOPMENT_CASE, development=True),)


def _candidate_after(case: dict[str, Any], *, final: bool) -> Candidate:
    candidate = Candidate.create(case["files"])
    patches = [case["prefork_patch"]] + ([case["final_patch"]] if final else [])
    for patch in patches:
        candidate, _ = candidate.patch(
            path=patch["path"],
            old=patch["old"],
            new=patch["new"],
            expected_candidate_id=candidate.candidate_id,
            expected_file_sha256=candidate.file_sha256(patch["path"]),
        )
    return candidate


def construct_bank(target: Path, *, measured: bool) -> dict[str, Any]:
    if target.exists():
        raise FileExistsError(target)
    files: dict[str, bytes] = {}
    cases = case_definitions(measured=measured)
    for case in cases:
        initial = Candidate.create(case["files"])
        prefork_candidate = _candidate_after(case, final=False)
        known_good = _candidate_after(case, final=True)
        prefix = f"model_visible/{case['fixture_id']}"
        candidate_rows = []
        for path, data in initial.files:
            files[f"{prefix}/candidate/{path}"] = data
            candidate_rows.append({"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)})
        files[f"{prefix}/TASK.txt"] = case["task"].encode("utf-8")
        execution = f"execution_only/{case['fixture_id']}"
        files[f"{execution}/checks/prefork.py"] = case["prefork"]
        files[f"{execution}/checks/public.py"] = case["public"]
        if case["probe_body"] is not None:
            files[f"{execution}/PROBE.txt"] = case["probe_body"].encode("utf-8")
        fixture = {
            "schema_version": "experiment-002-fixture-v1",
            "fixture_id": case["fixture_id"],
            "family": case["family"],
            "initial_candidate_id": initial.candidate_id,
            "prefork_candidate_id": prefork_candidate.candidate_id,
            "known_good_candidate_id": known_good.candidate_id,
            "candidate_files": candidate_rows,
            "required_full_reads": list(case["required"]),
            "final_target": case["final_target"],
            "probe_id": case["probe_id"],
            "probe_body_present": case["probe_body"] is not None,
            "probe_body_sha256": (
                sha256_bytes(case["probe_body"].encode("utf-8"))
                if case["probe_body"] is not None
                else None
            ),
        }
        files[f"{execution}/FIXTURE.json"] = canonical_json_bytes(fixture)
        evaluator = f"evaluator_only/{case['fixture_id']}"
        files[f"{evaluator}/hidden.py"] = case["hidden"]
        for path, data in known_good.files:
            files[f"{evaluator}/known_good/{path}"] = data
        files[f"{evaluator}/TRUTH.json"] = canonical_json_bytes(
            {
                "schema_version": "experiment-002-truth-v1",
                "fixture_id": case["fixture_id"],
                "family": case["family"],
                "known_good_candidate_id": known_good.candidate_id,
                "prefork_candidate_id": prefork_candidate.candidate_id,
                "governing_requirement": case["governing"],
                "required_full_reads": list(case["required"]),
                "prefork_patch": case["prefork_patch"],
                "final_patch": case["final_patch"],
            }
        )
    for relative, data in files.items():
        atomic_write(target / Path(*relative.split("/")), data)
    inventory = [
        {"path": path, "size_bytes": len(data), "sha256": sha256_bytes(data)}
        for path, data in sorted(files.items())
    ]
    bank_id = "E2BANK-" + sha256_bytes(canonical_json_bytes(inventory))
    manifest = {
        "schema_version": BANK_SCHEMA,
        "bank_id": bank_id,
        "measured": measured,
        "case_ids": [case["fixture_id"] for case in cases],
        "evaluator_separate": True,
        "files": inventory,
    }
    atomic_write(target / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify_bank(target: Path) -> dict[str, Any]:
    manifest_path = target / "BANK_MANIFEST.json"
    manifest = __import__("json").loads(manifest_path.read_text(encoding="utf-8"))
    expected_paths = {row["path"] for row in manifest["files"]}
    observed_paths = {
        path.relative_to(target).as_posix()
        for path in target.rglob("*")
        if path.is_file() and path.name != "BANK_MANIFEST.json"
    }
    if expected_paths != observed_paths:
        raise ValueError("bank inventory paths differ")
    for row in manifest["files"]:
        data = (target / Path(*row["path"].split("/"))).read_bytes()
        if len(data) != row["size_bytes"] or sha256_bytes(data) != row["sha256"]:
            raise ValueError("bank inventory bytes differ")
    expected_id = "E2BANK-" + sha256_bytes(canonical_json_bytes(manifest["files"]))
    if manifest["bank_id"] != expected_id:
        raise ValueError("bank ID differs")
    return {"verified": True, "bank_id": manifest["bank_id"], "file_count": len(observed_paths)}
