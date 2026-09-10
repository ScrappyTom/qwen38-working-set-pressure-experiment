"""Independently compare prepared wording bytes and recount with the pinned CLI."""
from __future__ import annotations

import argparse
import copy
from pathlib import Path
import subprocess
from types import SimpleNamespace

import prepare_interface_wording as wording
from working_set_exp.custody import verify_records
from working_set_exp.jsonutil import canonical_json_bytes, load_json_strict, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count


TOKENIZER_SHA = "d435fb84f60d6c21dbd2adcb0beb38555f2921894909c98f9236bf0984971b1c"
require = wording.require


def verify(args) -> dict:
    folder = args.package
    manifest = wording.validate_package(folder)
    seal = load_json_strict((folder / "PREPARATION_SEAL.json").read_bytes())
    require(seal["disposition"] == "prepared_without_completion" and seal["completion_calls"] == 0, "preparation incomplete")
    require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "seal aggregate differs")
    for row in seal["files"]:
        path = folder / row["path"]
        require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"], "sealed artifact differs")
    for name, digest in seal["private_runtime_files_local_only"].items():
        require(sha256_file(folder / "private-runtime" / name) == digest, "private runtime differs")
    records = verify_records(folder / "records.jsonl", folder)
    require(len(records) == seal["record_count"], "record count differs")
    prepared = [r for r in records if r["record_type"] == "request_prepared"]
    require(len(prepared) == 12 and all(r["payload"]["completion_sent"] is False
            and r["payload"]["routes"] == ["/apply-template", "/tokenize"] for r in prepared), "preparation routes differ")
    require(records[-1]["record_type"] == "preparation_completed", "preparation not terminal")
    require(sha256_file(args.tokenizer) == TOKENIZER_SHA and sha256_file(args.model) == wording.ACTOR["model_sha256"], "offline artifact identity differs")
    version = subprocess.run([str(args.tokenizer), "--version"], capture_output=True, check=True)
    version_text = (version.stdout + version.stderr).decode("utf-8", errors="replace").strip()
    profile = SimpleNamespace(model_path=args.model, tokenizer_path=args.tokenizer)
    old_folder = wording.previous.PACKAGE
    old_manifest = load_json_strict((old_folder / "PACKAGE_MANIFEST.json").read_bytes())
    reference_rows = {r["state"]: r for r in old_manifest["rows"] if r["condition"] == "visible_reference" and r["seed"] == 42}
    change = load_json_strict((folder / "WORDING_CHANGE.json").read_bytes())
    sentence = change["replace_system_sentence"]
    field = change["remove_user_field"]
    require(field["path"] == "/resource_state/correction_cycle_reserved_by_fixture_design", "changed field scope differs")
    cache, checked = {}, []
    for row in manifest["rows"]:
        request = load_json_strict((folder / row["request_path"]).read_bytes())
        control_row = reference_rows[row["state"]]
        control = load_json_strict((old_folder / control_row["request_path"]).read_bytes())
        control["seed"] = row["seed"]
        restored = copy.deepcopy(request)
        original_render = (old_folder / control_row["rendered_path"]).read_bytes()
        expected_render = original_render
        if row["condition"] == "wording":
            system = restored["messages"][0]["content"]
            require(system.count(sentence["after"]) == 1, "new navigation sentence occurrence differs")
            restored["messages"][0]["content"] = system.replace(sentence["after"], sentence["before"], 1)
            state = load_json_strict(restored["messages"][1]["content"].encode("utf-8"))
            require("correction_cycle_reserved_by_fixture_design" not in state["resource_state"], "example retained")
            state["resource_state"]["correction_cycle_reserved_by_fixture_design"] = field["old_value"]
            restored["messages"][1]["content"] = canonical_json_bytes(state).decode("utf-8")
            require(original_render.count(sentence["before"].encode()) == 1, "old sentence not unique in native input")
            require(original_render.count(control["messages"][1]["content"].encode()) == 1, "old user state not unique in native input")
            expected_render = original_render.replace(sentence["before"].encode(), sentence["after"].encode(), 1)
            expected_render = expected_render.replace(control["messages"][1]["content"].encode(), request["messages"][1]["content"].encode(), 1)
        require(restored == control, "more than the two declared changes or seed differs from reviewed reference")
        rendered = (folder / row["rendered_path"]).read_bytes()
        require(rendered == expected_render, "native input has an undeclared difference")
        if rendered not in cache:
            cache[rendered] = tokenizer_count(profile, rendered)
        count = cache[rendered]
        require(count == row["prompt_tokens"], "offline/native token count differs")
        checked.append({"id": row["id"], "state": row["state"], "condition": row["condition"], "purpose": row["purpose"],
                        "prompt_tokens": count, "delta_from_reviewed_reference": count - control_row["prompt_tokens"],
                        "physical_generation_space": wording.ACTOR["context"] - count,
                        "undeclared_message_or_native_changes": False})
    return {"status": "verified_without_completion", "package_sha256": sha256_file(folder / "PACKAGE_MANIFEST.json"),
            "preparation_seal_sha256": sha256_file(folder / "PREPARATION_SEAL.json"),
            "verifier_sha256": sha256_file(Path(__file__)), "model_sha256": wording.ACTOR["model_sha256"],
            "tokenizer_sha256": TOKENIZER_SHA, "tokenizer_version": version_text,
            "tokenization": "pinned offline CLI; no BOS, no escape processing, special tokens parsed",
            "completion_calls": 0, "proposed_comparison_calls": 8, "offline_input_regressions": 4,
            "sealed_public_files": len(seal["files"]), "private_files_verified_local_only": len(seal["private_runtime_files_local_only"]),
            "source_identities": len(manifest["source_sha256"]), "record_count": len(records), "unique_native_prompts": len(cache),
            "original_execution_closure_still_valid": True, "rows": checked}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--model", type=Path, required=True)
    parser.add_argument("--tokenizer", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args)
    wording.reference.base.write_json(args.output, result)
    print(canonical_json_bytes({k: result[k] for k in ("status", "completion_calls", "proposed_comparison_calls", "unique_native_prompts", "package_sha256")}).decode("utf-8"))


if __name__ == "__main__":
    main()
