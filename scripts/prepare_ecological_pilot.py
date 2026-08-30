from __future__ import annotations

import shutil
import sys
from pathlib import Path

from working_set_exp.candidate import Candidate
from working_set_exp.ecological_pilot import CASE_IDS, SUBSET_INIT, schedule
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes
from working_set_exp.large_world import _inventory


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "019_owner_controlled_ecological_pilot"
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


SOURCE_TASK = """Repair two regressions in this owner-controlled exact-reopen pipeline. The contract is unambiguous: `ArtifactUnit.start_line` and `end_line` are inclusive, so exact materialization must include every declared source line. `ReopenReceipt.truncated` is true only when the exact text is strictly longer than `max_chars`; equality is complete. Preserve inline-text behavior, hash-mismatch blocking, exact identifiers, and public APIs. Inspect exact current source in `src/addressable_information_layer/artifact_units.py`, `reopen.py`, `records.py`, and `hashing.py` before mutation. Do not modify tests or add dependencies. Run check `public` on the current candidate and submit."""

OBS_TASK = """A current candidate-bound verifier run reports regressions in summary-graph status. Select the current observation by exact candidate binding and reopen its body. Repair source so `collection_stale` is true when any artifact summary is stale, when the current artifact-summary IDs differ from the graph IDs, or when the collection's input IDs differ. `missing_artifact_ids` must list summary artifacts that lack an address map, in deterministic order. Preserve public APIs and do not modify tests. Inspect exact current source in `src/addressable_information_layer/summary_graph.py`, `summaries.py`, `records.py`, and `policy.py` before mutation. Run check `public` on the current candidate and submit."""


SOURCE_PUBLIC = b'''import sys\nsys.path.insert(0, "src")\nfrom addressable_information_layer.artifact_units import build_address_map, import_artifact\nfrom addressable_information_layer.content_log import ContentLog\nfrom addressable_information_layer.reopen import materialize_reopen\n\nlog = ContentLog()\nartifact = import_artifact(log, kind="python", path_or_name="sample.py", text="def alpha():\\n    value = 3\\n    return value\\n")\namap = build_address_map(artifact)\nunit = amap.units["function:alpha"]\nexpected = "def alpha():\\n    value = 3\\n    return value"\nreceipt = materialize_reopen(unit.exact_ref, artifacts={artifact.artifact_id: artifact}, address_maps={artifact.artifact_id: amap}, max_chars=len(expected))\nassert receipt.materialized_text == expected\nassert receipt.truncated is False\nshort = materialize_reopen(unit.exact_ref, artifacts={artifact.artifact_id: artifact}, address_maps={artifact.artifact_id: amap}, max_chars=len(expected) - 1)\nassert short.truncated is True and short.materialized_text == expected[:-1]\nprint("public passed")\n'''

SOURCE_HIDDEN = SOURCE_PUBLIC + b'''\nartifact2 = import_artifact(log, kind="python", path_or_name="one.py", text="def one(): return 1\\n")\namap2 = build_address_map(artifact2)\nunit2 = amap2.units["function:one"]\nr2 = materialize_reopen(unit2.unit_id, artifacts={artifact2.artifact_id: artifact2}, address_maps={artifact2.artifact_id: amap2}, max_chars=100)\nassert r2.materialized_text == "def one(): return 1" and r2.truncated is False\nprint("hidden passed")\n'''

OBS_PUBLIC = b'''import sys\nsys.path.insert(0, "src")\nfrom addressable_information_layer.content_log import ContentLog\nfrom addressable_information_layer.artifact_units import build_address_map, import_artifact\nfrom addressable_information_layer.summary_graph import build_summary_graph, summary_graph_status\n\nlog = ContentLog()\na = import_artifact(log, kind="python", path_or_name="a.py", text="def a():\\n    return 1\\n")\nb = import_artifact(log, kind="python", path_or_name="b.py", text="def b():\\n    return 2\\n")\nartifacts = {x.artifact_id: x for x in (a, b)}\nmaps = {x.artifact_id: build_address_map(x) for x in (a, b)}\nsummaries, graph = build_summary_graph(artifacts, maps)\nstatus = summary_graph_status(summaries, graph, {a.artifact_id: maps[a.artifact_id]})\nassert status["collection_stale"] is True\nassert status["missing_artifact_ids"] == [b.artifact_id]\nprint("public passed")\n'''

OBS_HIDDEN = OBS_PUBLIC + b'''\nstatus2 = summary_graph_status(summaries, graph, maps)\nassert status2["collection_stale"] is False and status2["missing_artifact_ids"] == []\ntrimmed = dict(summaries)\ntrimmed.pop(b.artifact_id)\nstatus3 = summary_graph_status(trimmed, graph, maps)\nassert status3["collection_stale"] is True\nprint("hidden passed")\n'''


def donor_files() -> tuple[dict[str, bytes], list[dict]]:
    files: dict[str, bytes] = {}
    rows = []
    for name in SELECTED:
        source = DONOR / "src" / "addressable_information_layer" / name
        body = source.read_bytes()
        path = f"src/addressable_information_layer/{name}"
        files[path] = body
        rows.append({"source_path": str(source), "bank_path": "", "candidate_path": path,
                     "size_bytes": len(body), "sha256": sha256_bytes(body)})
    return files, rows


def inject(files: dict[str, bytes], *, family: str) -> dict[str, bytes]:
    changed = dict(files)
    changed["src/addressable_information_layer/__init__.py"] = SUBSET_INIT
    if family == "source":
        path = "src/addressable_information_layer/artifact_units.py"
        text = changed[path].decode()
        old = 'return "\\n".join(lines[unit.start_line - 1 : unit.end_line])'
        new = 'return "\\n".join(lines[unit.start_line - 1 : max(unit.start_line - 1, unit.end_line - 1)])'
        if text.count(old) != 1:
            raise RuntimeError("source donor exact-text injection target differs")
        changed[path] = text.replace(old, new).encode()
        path = "src/addressable_information_layer/reopen.py"
        text = changed[path].decode()
        old = "truncated = len(exact_text) > max_chars"
        if text.count(old) != 1:
            raise RuntimeError("source donor truncation injection target differs")
        changed[path] = text.replace(old, "truncated = len(exact_text) >= max_chars").encode()
    elif family == "observation":
        path = "src/addressable_information_layer/summary_graph.py"
        text = changed[path].decode()
        old = "collection_stale = bool(stale_artifact_summary_ids) or current_summary_ids != graph_summary_ids"
        if text.count(old) != 1:
            raise RuntimeError("observation donor stale injection target differs")
        text = text.replace(old, "collection_stale = bool(stale_artifact_summary_ids) and current_summary_ids != graph_summary_ids")
        old = "missing_artifact_ids = sorted(artifact_id for artifact_id in summaries if artifact_id not in address_maps)"
        if text.count(old) != 1:
            raise RuntimeError("observation donor missing injection target differs")
        changed[path] = text.replace(
            old,
            "missing_artifact_ids = sorted(artifact_id for artifact_id in address_maps if artifact_id not in summaries)",
        ).encode()
    else:
        raise ValueError(family)
    return changed


def write_case(root: Path, *, fixture_id: str, family: str, task: str, candidate_files: dict[str, bytes],
               public: bytes, hidden: bytes, observations: list[dict], observation_bodies: dict[str, bytes],
               provenance: dict) -> None:
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
        canonical_json_bytes({
            "fixture_id": fixture_id,
            "family": family,
            "candidate_id": candidate.candidate_id,
            "candidate_files": rows,
            "observations": observations,
            "provenance": provenance,
        }),
    )


def main() -> None:
    bank = EXPERIMENT / "fresh_bank"
    if sys.argv[1:] == ["--reset-preseal-execution-artifacts"]:
        for path in (
            EXPERIMENT / "execution_package",
            EXPERIMENT / "EXECUTABLE_CLOSURE.json",
            EXPERIMENT / "OFFLINE_QUALIFICATION_RECEIPT.json",
        ):
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        print("preseal execution artifacts reset")
        return
    if sys.argv[1:] == ["--finalize-preseal-task-wording"]:
        if not bank.exists():
            raise FileNotFoundError(bank)
        atomic_write(bank / "model_visible" / CASE_IDS[0] / "TASK.txt", SOURCE_TASK.encode())
        atomic_write(bank / "model_visible" / CASE_IDS[1] / "TASK.txt", OBS_TASK.encode())
        manifest = load_json_strict((bank / "BANK_MANIFEST.json").read_bytes())
        manifest["files"] = _inventory(bank, {"BANK_MANIFEST.json"})
        manifest["bank_id"] = "E19BANK-" + sha256_bytes(canonical_json_bytes(manifest["files"]))
        atomic_write(bank / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
        print(manifest["bank_id"])
        return
    if sys.argv[1:] == ["--complete-preseal-donor-custody"]:
        if not bank.exists():
            raise FileNotFoundError(bank)
        files, donor_rows = donor_files()
        for row in donor_rows:
            row["bank_path"] = f"donor_snapshot/{row['candidate_path']}"
            atomic_write(bank / "donor_snapshot" / Path(*row["candidate_path"].split("/")), files[row["candidate_path"]])
        manifest = load_json_strict((bank / "BANK_MANIFEST.json").read_bytes())
        manifest["donor_files"] = donor_rows
        manifest["files"] = _inventory(bank, {"BANK_MANIFEST.json"})
        manifest["bank_id"] = "E19BANK-" + sha256_bytes(canonical_json_bytes(manifest["files"]))
        atomic_write(bank / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
        print(manifest["bank_id"])
        return
    if sys.argv[1:] == ["--complete-preseal-subset-adapter"]:
        if not bank.exists():
            raise FileNotFoundError(bank)
        files, _ = donor_files()
        source_candidate = inject(files, family="source")
        obs_candidate = inject(files, family="observation")
        predecessor_files = dict(files)
        predecessor_files["src/addressable_information_layer/__init__.py"] = SUBSET_INIT
        predecessor = Candidate.create(predecessor_files)
        current = Candidate.create(obs_candidate)
        old_body = canonical_json_bytes({"status": "passed", "candidate_id": predecessor.candidate_id,
                                         "suite": "legacy serializer compatibility", "failures": []})
        current_body = canonical_json_bytes({
            "status": "failed", "candidate_id": current.candidate_id, "suite": "summary graph status",
            "failures": [
                {"test": "collection_stale_when_graph_ids_differ", "expected": True, "observed": False},
                {"test": "missing_artifact_ids_direction", "expected": "summary without map", "observed": "map without summary"},
            ],
        })
        observations = [
            {"handle": "OBS-0001", "sequence": 1, "action": "verifier", "target": "legacy serializer compatibility",
             "candidate_id": predecessor.candidate_id, "size_bytes": len(old_body), "sha256": sha256_bytes(old_body)},
            {"handle": "OBS-0002", "sequence": 2, "action": "verifier", "target": "summary graph status",
             "candidate_id": current.candidate_id, "size_bytes": len(current_body), "sha256": sha256_bytes(current_body)},
        ]
        manifest = load_json_strict((bank / "BANK_MANIFEST.json").read_bytes())
        donor_identity = manifest["donor_identity_sha256"]
        write_case(bank, fixture_id=CASE_IDS[0], family="owner_controlled_exact_reopen_pipeline",
                   task=SOURCE_TASK, candidate_files=source_candidate, public=SOURCE_PUBLIC, hidden=SOURCE_HIDDEN,
                   observations=[], observation_bodies={},
                   provenance={"owner_controlled_donor": str(DONOR), "donor_identity_sha256": donor_identity,
                               "fixture_adapter": "neutral bounded-subset __init__; production initializer retained in donor custody",
                               "injected_regressions": ["inclusive_end_line_omitted", "equal_length_reported_truncated"]})
        write_case(bank, fixture_id=CASE_IDS[1], family="owner_controlled_current_verifier_observation",
                   task=OBS_TASK, candidate_files=obs_candidate, public=OBS_PUBLIC, hidden=OBS_HIDDEN,
                   observations=observations, observation_bodies={"OBS-0001": old_body, "OBS-0002": current_body},
                   provenance={"owner_controlled_donor": str(DONOR), "donor_identity_sha256": donor_identity,
                               "fixture_adapter": "neutral bounded-subset __init__; production initializer retained in donor custody",
                               "injected_regressions": ["collection_stale_uses_and", "missing_artifact_direction_reversed"]})
        manifest["fixture_adapter"] = {
            "path": "src/addressable_information_layer/__init__.py",
            "reason": "production initializer imports runner.py, whose 34 KB size exceeds the frozen 24 KB candidate-file bound",
            "model_visible_semantic_content": False,
            "adapted_sha256": sha256_bytes(SUBSET_INIT),
            "production_bytes_retained_in_donor_snapshot": True,
        }
        manifest["files"] = _inventory(bank, {"BANK_MANIFEST.json"})
        manifest["bank_id"] = "E19BANK-" + sha256_bytes(canonical_json_bytes(manifest["files"]))
        atomic_write(bank / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
        print(manifest["bank_id"])
        return
    if EXPERIMENT.exists():
        raise FileExistsError(EXPERIMENT)
    files, donor_rows = donor_files()
    donor_identity = sha256_bytes(canonical_json_bytes([
        {key: row[key] for key in ("candidate_path", "size_bytes", "sha256")} for row in donor_rows
    ]))
    for row in donor_rows:
        row["bank_path"] = f"donor_snapshot/{row['candidate_path']}"
        atomic_write(bank / "donor_snapshot" / Path(*row["candidate_path"].split("/")), files[row["candidate_path"]])
    source_candidate = inject(files, family="source")
    obs_candidate = inject(files, family="observation")
    source_prov = {"owner_controlled_donor": str(DONOR), "donor_identity_sha256": donor_identity,
                   "injected_regressions": ["inclusive_end_line_omitted", "equal_length_reported_truncated"]}
    obs_prov = {"owner_controlled_donor": str(DONOR), "donor_identity_sha256": donor_identity,
                "injected_regressions": ["collection_stale_uses_and", "missing_artifact_direction_reversed"]}
    predecessor = Candidate.create(files)
    current = Candidate.create(obs_candidate)
    old_body = canonical_json_bytes({"status": "passed", "candidate_id": predecessor.candidate_id,
                                     "suite": "legacy serializer compatibility", "failures": []})
    current_body = canonical_json_bytes({
        "status": "failed",
        "candidate_id": current.candidate_id,
        "suite": "summary graph status",
        "failures": [
            {"test": "collection_stale_when_graph_ids_differ", "expected": True, "observed": False},
            {"test": "missing_artifact_ids_direction", "expected": "summary without map", "observed": "map without summary"},
        ],
    })
    observations = [
        {"handle": "OBS-0001", "sequence": 1, "action": "verifier", "target": "legacy serializer compatibility",
         "candidate_id": predecessor.candidate_id, "size_bytes": len(old_body), "sha256": sha256_bytes(old_body)},
        {"handle": "OBS-0002", "sequence": 2, "action": "verifier", "target": "summary graph status",
         "candidate_id": current.candidate_id, "size_bytes": len(current_body), "sha256": sha256_bytes(current_body)},
    ]
    write_case(bank, fixture_id=CASE_IDS[0], family="owner_controlled_exact_reopen_pipeline",
               task=SOURCE_TASK, candidate_files=source_candidate, public=SOURCE_PUBLIC, hidden=SOURCE_HIDDEN,
               observations=[], observation_bodies={}, provenance=source_prov)
    write_case(bank, fixture_id=CASE_IDS[1], family="owner_controlled_current_verifier_observation",
               task=OBS_TASK, candidate_files=obs_candidate, public=OBS_PUBLIC, hidden=OBS_HIDDEN,
               observations=observations, observation_bodies={"OBS-0001": old_body, "OBS-0002": current_body},
               provenance=obs_prov)
    inventory = _inventory(bank, {"BANK_MANIFEST.json"})
    manifest = {
        "schema_version": "experiment-019-owner-controlled-fresh-bank-v1",
        "case_ids": list(CASE_IDS),
        "donor_identity_sha256": donor_identity,
        "donor_files": donor_rows,
        "freshness": {
            "created_after_experiment_018": True,
            "not_selected_from_actor_behavior": True,
            "not_exposed_to_measured_actor": True,
            "real_owner_controlled_source_snapshot": True,
        },
        "evaluator_bytes_model_visible": False,
        "files": inventory,
        "bank_id": "E19BANK-" + sha256_bytes(canonical_json_bytes(inventory)),
    }
    atomic_write(bank / "BANK_MANIFEST.json", canonical_json_bytes(manifest))
    atomic_write(EXPERIMENT / "SCHEDULE.json", canonical_json_bytes(schedule()))
    print(manifest["bank_id"])


if __name__ == "__main__":
    main()
