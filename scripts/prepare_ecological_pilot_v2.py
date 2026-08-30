from __future__ import annotations

import sys
from pathlib import Path

from working_set_exp.candidate import Candidate
from working_set_exp.ecological_pilot_v2 import CASE_IDS, SUBSET_INIT, schedule
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes
from working_set_exp.large_world import _inventory


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "020_owner_controlled_ecological_pilot_v2"
DONOR = Path(r"C:\Users\danmc\Addressable_Information_Layer")
SELECTED = (
    "__init__.py",
    "artifact_units.py",
    "availability.py",
    "content_log.py",
    "decomposition.py",
    "fixture_packs.py",
    "focus.py",
    "hashing.py",
    "importers.py",
    "patching.py",
    "policy.py",
    "project_store.py",
    "readiness.py",
    "records.py",
    "reducers.py",
    "renderer.py",
    "reopen.py",
    "routing.py",
    "saved_runs.py",
    "serialization.py",
    "storage.py",
    "summaries.py",
    "summary_graph.py",
    "verifier_logs.py",
    "verifiers.py",
)


def _path(name: str) -> str:
    return f"src/addressable_information_layer/{name}"


SOURCE_INSPECTION = tuple(
    _path(name)
    for name in (
        "saved_runs.py",
        "importers.py",
        "fixture_packs.py",
        "records.py",
        "content_log.py",
        "artifact_units.py",
        "hashing.py",
        "storage.py",
        "renderer.py",
        "policy.py",
        "readiness.py",
    )
)
OBS_INSPECTION = tuple(
    _path(name)
    for name in (
        "verifiers.py",
        "records.py",
        "hashing.py",
        "readiness.py",
        "policy.py",
        "routing.py",
        "reducers.py",
        "verifier_logs.py",
        "storage.py",
        "artifact_units.py",
    )
)


SOURCE_TASK = """Perform a complete import-boundary audit and repair four regressions in this owner-controlled offline audit package. Before the first mutation, make an exact complete read of every path in this frozen acceptance set: src/addressable_information_layer/saved_runs.py, src/addressable_information_layer/importers.py, src/addressable_information_layer/fixture_packs.py, src/addressable_information_layer/records.py, src/addressable_information_layer/content_log.py, src/addressable_information_layer/artifact_units.py, src/addressable_information_layer/hashing.py, src/addressable_information_layer/storage.py, src/addressable_information_layer/renderer.py, src/addressable_information_layer/policy.py, and src/addressable_information_layer/readiness.py. This full inspection is a required audit deliverable, not an optional hint. The exact boundary contract is: a file whose byte size equals max_file_bytes is eligible; max_files=N admits at most the first N eligible files; JSONL records 1 through MAX_JSONL_LINES are eligible for event conversion; and an embedded artifact on line MAX_JSONL_LINES is eligible. Later files or records remain excluded. Preserve deterministic order, exclusions, schemas, identities, artifact materialization, and public APIs. Do not modify tests or add dependencies. Run check `public` on the current candidate and submit."""

OBS_TASK = """A current candidate-bound verifier observation reports two safety regressions. Select the current observation by exact candidate binding and reopen its body. Before the first mutation, make an exact complete read of every path in this frozen acceptance set: src/addressable_information_layer/verifiers.py, src/addressable_information_layer/records.py, src/addressable_information_layer/hashing.py, src/addressable_information_layer/readiness.py, src/addressable_information_layer/policy.py, src/addressable_information_layer/routing.py, src/addressable_information_layer/reducers.py, src/addressable_information_layer/verifier_logs.py, src/addressable_information_layer/storage.py, and src/addressable_information_layer/artifact_units.py. This full inspection is a required audit deliverable, not an optional hint. Repair the verifier so absolute paths, parent traversal, and empty paths are rejected while canonical relative paths remain accepted; verifier timeouts must clamp to the inclusive range 1..MAX_COMMAND_TIMEOUT_SECONDS, with invalid values defaulting to 20. Preserve command-prefix enforcement, workspace containment, deterministic receipts, and public APIs. Do not modify tests or add dependencies. Run check `public` on the current candidate and submit."""


SOURCE_PUBLIC = b'''import json\nimport sys\nimport tempfile\nfrom pathlib import Path\nsys.path.insert(0, "src")\nfrom addressable_information_layer.importers import fixture_from_directory\nfrom addressable_information_layer.saved_runs import _embedded_artifacts_from_jsonl, _events_from_jsonl\n\nwith tempfile.TemporaryDirectory() as raw:\n    root = Path(raw)\n    (root / "a.txt").write_text("abcde", encoding="utf-8")\n    (root / "b.txt").write_text("vwxyz", encoding="utf-8")\n    lines = [json.dumps({"record_type": "receipts", "payload": {"index": i}}) for i in range(1, 1000)]\n    lines.append(json.dumps({"record_type": "artifacts", "payload": {"artifact_ref": "edge", "artifact_kind": "text", "content": "line-1000"}}))\n    (root / "events.jsonl").write_text("\\n".join(lines) + "\\n", encoding="utf-8")\n    imported = fixture_from_directory(root, max_files=1, max_file_bytes=5)\n    assert imported["artifacts"] == [{"path": "a.txt"}]\n    assert len(_events_from_jsonl(root, "generic")) == 1000\n    embedded = _embedded_artifacts_from_jsonl(root)\n    assert len(embedded) == 1 and embedded[0]["text"] == "line-1000"\nprint("public passed")\n'''

SOURCE_HIDDEN = SOURCE_PUBLIC + b'''\nwith tempfile.TemporaryDirectory() as raw:\n    root = Path(raw)\n    (root / "empty.txt").write_bytes(b"")\n    bounded = fixture_from_directory(root, max_files=1, max_file_bytes=0)\n    assert bounded["artifacts"] == [{"path": "empty.txt"}]\n    lines = [json.dumps({"record_type": "receipts", "payload": {"index": i}}) for i in range(1, 1002)]\n    (root / "run_events.jsonl").write_text("\\n".join(lines) + "\\n", encoding="utf-8")\n    assert len(_events_from_jsonl(root, "generic")) == 1000\nprint("hidden passed")\n'''

OBS_PUBLIC = b'''import sys\nimport tempfile\nfrom pathlib import Path\nsys.path.insert(0, "src")\nfrom addressable_information_layer.verifiers import MAX_COMMAND_TIMEOUT_SECONDS, _bounded_timeout, _resolve_safe_cwd, _safe_relative_path\n\nassert _safe_relative_path("pkg/module.py").as_posix() == "pkg/module.py"\nassert _safe_relative_path("../escape.py") is None\nassert _safe_relative_path("/absolute.py") is None\nassert _safe_relative_path("") is None\nassert _bounded_timeout(0) == 1\nassert _bounded_timeout(20) == 20\nassert _bounded_timeout(MAX_COMMAND_TIMEOUT_SECONDS + 99) == MAX_COMMAND_TIMEOUT_SECONDS\nassert _bounded_timeout("invalid") == 20\nwith tempfile.TemporaryDirectory() as raw:\n    workspace = Path(raw)\n    assert _resolve_safe_cwd(workspace, "sub/dir").is_relative_to(workspace.resolve())\n    assert _resolve_safe_cwd(workspace, "../escape") is None\nprint("public passed")\n'''

OBS_HIDDEN = OBS_PUBLIC + b'''\nassert _safe_relative_path("nested\\\\module.py").as_posix() == "nested/module.py"\nassert _bounded_timeout(-100) == 1\nassert _bounded_timeout(10**9) == MAX_COMMAND_TIMEOUT_SECONDS\nprint("hidden passed")\n'''


def donor_files() -> tuple[dict[str, bytes], list[dict]]:
    files: dict[str, bytes] = {}
    rows = []
    for name in SELECTED:
        source = DONOR / "src" / "addressable_information_layer" / name
        body = source.read_bytes()
        path = _path(name)
        files[path] = body
        rows.append(
            {
                "source_path": str(source),
                "bank_path": f"donor_snapshot/{path}",
                "candidate_path": path,
                "size_bytes": len(body),
                "sha256": sha256_bytes(body),
            }
        )
    return files, rows


def inject(files: dict[str, bytes], *, family: str) -> dict[str, bytes]:
    changed = dict(files)
    changed[_path("__init__.py")] = SUBSET_INIT
    if family == "source":
        path = _path("importers.py")
        text = changed[path].decode()
        for old, new, label in (
            ("if path.stat().st_size > max_file_bytes:", "if path.stat().st_size >= max_file_bytes:", "file byte boundary"),
            ("if len(artifacts) >= max_files:", "if len(artifacts) > max_files:", "file count boundary"),
        ):
            if text.count(old) != 1:
                raise RuntimeError(f"source donor {label} injection target differs")
            text = text.replace(old, new)
        changed[path] = text.encode()
        path = _path("saved_runs.py")
        text = changed[path].decode()
        old = """        for idx, item in enumerate(_read_jsonl_lines(path), start=1):
            if idx > MAX_JSONL_LINES:
                break
            event = _event_from_item(item, path, detected)"""
        new = old.replace("idx > MAX_JSONL_LINES", "idx >= MAX_JSONL_LINES")
        if text.count(old) != 1:
            raise RuntimeError("source donor event line-limit injection target differs")
        text = text.replace(old, new)
        old = "if idx > MAX_JSONL_LINES or len(artifacts) >= MAX_EMBEDDED_ARTIFACTS:"
        if text.count(old) != 1:
            raise RuntimeError("source donor embedded line-limit injection target differs")
        changed[path] = text.replace(old, old.replace("idx >", "idx >=")).encode()
    elif family == "observation":
        path = _path("verifiers.py")
        text = changed[path].decode()
        old = 'if path.is_absolute() or ".." in path.parts or not path.parts:'
        new = 'if path.is_absolute() and ".." in path.parts or not path.parts:'
        if text.count(old) != 1:
            raise RuntimeError("observation donor safe-path injection target differs")
        text = text.replace(old, new)
        old = "return max(1, min(timeout, MAX_COMMAND_TIMEOUT_SECONDS))"
        new = "return max(1, max(timeout, MAX_COMMAND_TIMEOUT_SECONDS))"
        if text.count(old) != 1:
            raise RuntimeError("observation donor timeout injection target differs")
        changed[path] = text.replace(old, new).encode()
    else:
        raise ValueError(family)
    return changed


def write_case(
    root: Path,
    *,
    fixture_id: str,
    family: str,
    task: str,
    candidate_files: dict[str, bytes],
    public: bytes,
    hidden: bytes,
    observations: list[dict],
    observation_bodies: dict[str, bytes],
    required_inspection_paths: tuple[str, ...],
    provenance: dict,
) -> None:
    visible = root / "model_visible" / fixture_id
    execution = root / "execution_only" / fixture_id
    evaluator = root / "evaluator_only" / fixture_id
    candidate = Candidate.create(candidate_files)
    atomic_write(visible / "TASK.txt", task.encode())
    rows = []
    for path, body in candidate.files:
        atomic_write(visible / "candidate" / Path(*path.split("/")), body)
        rows.append({"path": path, "size_bytes": len(body), "sha256": sha256_bytes(body)})
    atomic_write(execution / "public.py", public)
    for handle, body in observation_bodies.items():
        atomic_write(execution / "observations" / f"{handle}.json", body)
    atomic_write(evaluator / "hidden.py", hidden)
    atomic_write(
        execution / "FIXTURE.json",
        canonical_json_bytes(
            {
                "fixture_id": fixture_id,
                "family": family,
                "candidate_id": candidate.candidate_id,
                "candidate_files": rows,
                "observations": observations,
                "required_inspection_paths": list(required_inspection_paths),
                "provenance": provenance,
            }
        ),
    )


def main() -> None:
    if sys.argv[1:] == ["--refresh-preseal-contract"]:
        if not EXPERIMENT.exists() or (EXPERIMENT / "MEASURED_AUTHORIZATION.json").exists():
            raise RuntimeError("Experiment 020 preseal refresh boundary differs")
        bank = EXPERIMENT / "fresh_bank"
        for fixture_id, task, paths in (
            (CASE_IDS[0], SOURCE_TASK, SOURCE_INSPECTION),
            (CASE_IDS[1], OBS_TASK, OBS_INSPECTION),
        ):
            atomic_write(bank / "model_visible" / fixture_id / "TASK.txt", task.encode())
            fixture_path = bank / "execution_only" / fixture_id / "FIXTURE.json"
            fixture = load_json_strict(fixture_path.read_bytes())
            fixture["required_inspection_paths"] = list(paths)
            atomic_write(fixture_path, canonical_json_bytes(fixture))
        manifest_path = bank / "BANK_MANIFEST.json"
        manifest = load_json_strict(manifest_path.read_bytes())
        manifest["files"] = _inventory(bank, {"BANK_MANIFEST.json"})
        manifest["bank_id"] = "E20BANK-" + sha256_bytes(canonical_json_bytes(manifest["files"]))
        atomic_write(manifest_path, canonical_json_bytes(manifest))
        print(manifest["bank_id"])
        return
    if EXPERIMENT.exists():
        raise FileExistsError(EXPERIMENT)
    bank = EXPERIMENT / "fresh_bank"
    files, donor_rows = donor_files()
    donor_identity = sha256_bytes(
        canonical_json_bytes(
            [{key: row[key] for key in ("candidate_path", "size_bytes", "sha256")} for row in donor_rows]
        )
    )
    for row in donor_rows:
        atomic_write(bank / row["bank_path"], files[row["candidate_path"]])
    source_candidate = inject(files, family="source")
    observation_candidate = inject(files, family="observation")
    predecessor_files = dict(files)
    predecessor_files[_path("__init__.py")] = SUBSET_INIT
    predecessor = Candidate.create(predecessor_files)
    current = Candidate.create(observation_candidate)
    old_body = canonical_json_bytes(
        {"status": "passed", "candidate_id": predecessor.candidate_id, "suite": "legacy verifier smoke", "failures": []}
    )
    current_body = canonical_json_bytes(
        {
            "status": "failed",
            "candidate_id": current.candidate_id,
            "suite": "offline verifier safety",
            "failures": [
                {"test": "reject_absolute_and_parent_paths", "expected": "rejected", "observed": "accepted"},
                {"test": "bounded_timeout", "expected": "inclusive 1..60 clamp", "observed": "minimum 60"},
            ],
        }
    )
    observations = [
        {
            "handle": "OBS-0001",
            "sequence": 1,
            "action": "verifier",
            "target": "legacy verifier smoke",
            "candidate_id": predecessor.candidate_id,
            "size_bytes": len(old_body),
            "sha256": sha256_bytes(old_body),
        },
        {
            "handle": "OBS-0002",
            "sequence": 2,
            "action": "verifier",
            "target": "offline verifier safety",
            "candidate_id": current.candidate_id,
            "size_bytes": len(current_body),
            "sha256": sha256_bytes(current_body),
        },
    ]
    common = {
        "owner_controlled_donor": str(DONOR),
        "donor_identity_sha256": donor_identity,
        "fixture_adapter": "neutral bounded-subset __init__; production initializer retained in donor custody",
        "inspection_contract": "exact complete reads before first mutation",
    }
    write_case(
        bank,
        fixture_id=CASE_IDS[0],
        family="owner_controlled_import_boundary_audit",
        task=SOURCE_TASK,
        candidate_files=source_candidate,
        public=SOURCE_PUBLIC,
        hidden=SOURCE_HIDDEN,
        observations=[],
        observation_bodies={},
        required_inspection_paths=SOURCE_INSPECTION,
        provenance={
            **common,
            "injected_regressions": [
                "equal_size_file_excluded",
                "max_files_allows_one_extra",
                "jsonl_event_line_1000_excluded",
                "embedded_artifact_line_1000_excluded",
            ],
        },
    )
    write_case(
        bank,
        fixture_id=CASE_IDS[1],
        family="owner_controlled_verifier_safety_audit",
        task=OBS_TASK,
        candidate_files=observation_candidate,
        public=OBS_PUBLIC,
        hidden=OBS_HIDDEN,
        observations=observations,
        observation_bodies={"OBS-0001": old_body, "OBS-0002": current_body},
        required_inspection_paths=OBS_INSPECTION,
        provenance={
            **common,
            "injected_regressions": ["absolute_or_parent_path_guard_weakened", "timeout_clamp_uses_maximum"],
        },
    )
    inventory = _inventory(bank, {"BANK_MANIFEST.json"})
    manifest = {
        "schema_version": "experiment-020-owner-controlled-fresh-bank-v1",
        "case_ids": list(CASE_IDS),
        "donor_identity_sha256": donor_identity,
        "donor_files": donor_rows,
        "freshness": {
            "created_after_experiment_019_stop": True,
            "not_selected_from_actor_behavior": True,
            "not_exposed_to_measured_actor": True,
            "real_owner_controlled_source_snapshot": True,
            "fresh_sibling_tasks_not_reused_from_experiment_019": True,
        },
        "fixture_contract": {
            "correct_task_compliance_requires_authentic_25k_boundary_before_first_mutation": True,
            "padding_or_duplicated_filler": False,
            "full_correction_cycle_reserved": True,
        },
        "fixture_adapter": {
            "path": _path("__init__.py"),
            "reason": "production initializer imports runner.py, whose size exceeds the frozen candidate-file bound",
            "model_visible_semantic_content": False,
            "adapted_sha256": sha256_bytes(SUBSET_INIT),
            "production_bytes_retained_in_donor_snapshot": True,
        },
        "evaluator_bytes_model_visible": False,
        "files": inventory,
        "bank_id": "E20BANK-" + sha256_bytes(canonical_json_bytes(inventory)),
    }
    atomic_write(bank / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
    atomic_write(EXPERIMENT / "SCHEDULE.json", canonical_json_bytes(schedule()))
    print(manifest["bank_id"])


if __name__ == "__main__":
    main()
