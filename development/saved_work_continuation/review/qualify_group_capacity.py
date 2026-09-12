"""Post-run capacity screen of actual report groups; no inference or adoption.

This researcher-selected counterfactual asks whether keeping the current report,
its contract and comparison evidence together is even feasible at the selected
ceiling. It does not show that Qwen would select the group or benefit from it.
"""
from pathlib import Path
import argparse
import sys
from types import SimpleNamespace

ROOT = Path(__file__).resolve().parents[3]
sys.path[:0] = [str(ROOT / "scripts"), str(ROOT / "src")]
import qualify_compiler_delivery as probe
import run_saved_work_continuation as runner
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count

AREA = ROOT / "development/saved_work_continuation"
RUN = AREA / "run-001"
OUTPUT = AREA / "group-capacity-001"
require, read = probe.require, probe.read


def main(tokenizer):
    require(not OUTPUT.exists(), "preserve the existing screen")
    seal = runner.base.verify_seal(RUN)
    require((RUN / "RESPONSE_SEAL.json").exists(), "live attempt has not closed")
    require(sha256_file(tokenizer) == probe.TOKENIZER_SHA, "tokenizer differs")
    model = Path(read(RUN / "private-runtime/launch.json")[2])
    require(sha256_file(model) == seal["actor"]["model_sha256"], "model differs")
    profile = SimpleNamespace(model_path=model, tokenizer_path=tokenizer)
    OUTPUT.mkdir()
    rows, status = [], "incomplete"

    def save(name, raw):
        with (OUTPUT / name).open("xb") as stream:
            stream.write(raw)

    try:
        for tag, previous in (("P2-04-C06", "P2-03-C05"), ("P2-05-C07", "P2-04-C06")):
            candidates = sorted((RUN / "admission").glob(tag + "-*-endpoint-request.json"))
            require(candidates, "sampled input missing")
            # Consecutive prefix attempts are ordered numerically by padded name;
            # the final one is the dispatched input, checked against its token gate.
            path = candidates[-1]
            original = read(path)
            stem = path.name.removesuffix("-endpoint-request.json")
            native = (RUN / "admission" / (stem + "-native.txt")).read_bytes().decode("utf-8")
            recorded_count = tokenizer_count(profile, native.encode())
            require(recorded_count == len(read(RUN / "admission" / (stem + "-tokens.json"))["tokens"])
                    <= runner.work.INPUT_CEILING, "recorded input differs")
            snapshot = read(RUN / "after" / (previous + "-snapshot.json"))
            pairs = snapshot["pairs"]
            current = read(RUN / "after" / (previous + "-candidate.json"))
            files = {f["path"]: f["content_utf8"].encode() for f in current["files"]}
            hashes = {k: sha256_bytes(v) for k, v in files.items()}
            materials = {m: probe.material_sequence(pairs, m, hashes) for m in
                ("README.md", "compiler/unary.py", "OBS-0001", "OBS-0002", "OBS-0003")}
            patch = pairs[16]
            require(patch["response"]["action"] == "patch" and patch["response"]["path"] == "reports/incident.json"
                    and patch["response"]["new"].encode() == files["reports/incident.json"]
                    and patch["result"]["file_sha256"] == hashes["reports/incident.json"],
                    "saved patch does not carry the complete current report")
            core = {17, len(pairs), *[materials[m] for m in ("README.md", "OBS-0001", "OBS-0002", "OBS-0003")]}
            variants = []
            for name, kept in (("report_group", core),
                               ("report_group_and_optimizer", core | {materials["compiler/unary.py"]}),
                               ("all_bodies_external", set())):
                request = probe.grouped_request(original, pairs, kept)
                raw = probe.native_for(request, original, native)
                count = tokenizer_count(profile, raw)
                save(tag + "-" + name + "-request.json", canonical_json_bytes(request))
                save(tag + "-" + name + "-native.txt", raw)
                variants.append(dict(name=name, retained_sequences=sorted(kept), input_tokens=count,
                    fits_23808=count <= runner.work.INPUT_CEILING, physical_generation_space=56576-count,
                    not_a_usable_working_view=name == "all_bodies_external"))
            rows.append(dict(id=tag, recorded_input_tokens=recorded_count, original_request_sha256=sha256_file(path),
                material_sequences=materials, report_carried_exactly_by_patch_sequence=17, variants=variants))
        save("RESULTS.json", canonical_json_bytes(dict(completion_requests=0,
            source_seal_sha256=sha256_file(RUN / "RESPONSE_SEAL.json"), cases=rows,
            live_retention_policy_changed=False, researcher_selected_counterfactual=True,
            limitation="Capacity only; no evidence of actor selection, semantic sufficiency or behavioral benefit.")))
        status = "offline_capacity_screen_completed"
    except BaseException as error:
        save("FAILED.json", canonical_json_bytes(dict(error_type=type(error).__name__, error=str(error))))
        raise
    finally:
        files = runner.base.file_inventory(OUTPUT)
        save("SEAL.json", canonical_json_bytes(dict(status=status, files=files,
            aggregate_sha256=sha256_bytes(canonical_json_bytes(files)), completion_requests=0,
            source_sha256=sha256_file(Path(__file__)), helper_sha256=sha256_file(Path(probe.__file__)))))
    print(rows)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--tokenizer", type=Path, required=True)
    main(parser.parse_args().tokenizer)
