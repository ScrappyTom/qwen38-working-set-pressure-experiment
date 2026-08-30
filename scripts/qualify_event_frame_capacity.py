from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

from working_set_exp.event_frame_capacity import capacity_proof
from working_set_exp.jsonutil import atomic_write, canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.runtime import load_runtime


ROOT = Path(__file__).resolve().parents[1]
EXPERIMENT = ROOT / "experiments" / "016_event_frame_capacity_stress"
ARTIFACTS = EXPERIMENT / "qualification_artifacts"
RUNTIME = ROOT / "experiments" / "015_event_frame_placement_qualification" / "RUNTIME_PROFILE.json"


def inventory(root: Path, *, exclude: set[str] | None = None) -> list[dict[str, object]]:
    excluded = exclude or set()
    rows = []
    for path in sorted(item for item in root.rglob("*") if item.is_file()):
        relative = path.relative_to(root).as_posix()
        if relative in excluded:
            continue
        rows.append({"path": relative, "size_bytes": path.stat().st_size, "sha256": sha256_file(path)})
    return rows


def construct(target: Path) -> dict[str, object]:
    if target.exists():
        raise FileExistsError(target)
    target.mkdir(parents=True)
    profile = load_runtime(RUNTIME)
    proof, artifacts = capacity_proof(profile)
    for relative, body in artifacts.items():
        atomic_write(target / Path(*relative.split("/")), body)
    atomic_write(target / "CAPACITY_PROOF.json", canonical_json_bytes(proof))
    source_paths = (
        "src/working_set_exp/event_frame.py",
        "src/working_set_exp/event_frame_capacity.py",
        "src/working_set_exp/event_frame_placement.py",
        "src/working_set_exp/tools.py",
        "src/working_set_exp/runtime.py",
        "scripts/qualify_event_frame_capacity.py",
    )
    qualification = {
        "schema_version": "experiment-016-offline-qualification-v1",
        "experiment_id": "016_event_frame_capacity_stress",
        "qualification_base_commit": "60c833a55c115f095790a73841f12fa48276a7eb",
        "runtime_profile_sha256": sha256_file(RUNTIME),
        "source_files": [{"path": path, "sha256": sha256_file(ROOT / path)} for path in source_paths],
        "gpu_or_model_server_launch": False,
        "endpoint_requests": 0,
        "completion_calls": 0,
        "fresh_fixture_construction": False,
        "result": proof["capacity_conclusion"],
    }
    atomic_write(target / "OFFLINE_QUALIFICATION.json", canonical_json_bytes(qualification))
    files = inventory(target, exclude={"ARTIFACT_MANIFEST.json"})
    manifest = {
        "schema_version": "experiment-016-artifact-manifest-v1",
        "experiment_id": "016_event_frame_capacity_stress",
        "files": files,
        "artifact_id": "E16ART-" + sha256_bytes(canonical_json_bytes(files)),
    }
    atomic_write(target / "ARTIFACT_MANIFEST.json", canonical_json_bytes(manifest))
    return manifest


def verify(target: Path) -> dict[str, object]:
    observed = load_json_strict((target / "ARTIFACT_MANIFEST.json").read_bytes())
    if observed["files"] != inventory(target, exclude={"ARTIFACT_MANIFEST.json"}):
        raise RuntimeError("Experiment 016 artifact inventory differs")
    with tempfile.TemporaryDirectory(prefix="e16-offline-") as raw:
        rebuilt_root = Path(raw) / "qualification_artifacts"
        rebuilt = construct(rebuilt_root)
        if canonical_json_bytes(rebuilt) != canonical_json_bytes(observed):
            raise RuntimeError("Experiment 016 manifest reconstruction differs")
        for row in observed["files"]:
            relative = Path(*str(row["path"]).split("/"))
            if (target / relative).read_bytes() != (rebuilt_root / relative).read_bytes():
                raise RuntimeError(f"Experiment 016 artifact differs: {row['path']}")
    return {"verified": True, "artifact_id": observed["artifact_id"], "file_count": len(observed["files"])}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=("write", "verify"))
    args = parser.parse_args()
    result = construct(ARTIFACTS) if args.mode == "write" else verify(ARTIFACTS)
    print(canonical_json_bytes(result).decode("utf-8"))


if __name__ == "__main__":
    main()
