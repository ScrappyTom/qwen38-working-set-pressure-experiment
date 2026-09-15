"""Offline native input costs and the existing scripted contribution route."""
import argparse
import copy
import json
from pathlib import Path
import subprocess
from types import SimpleNamespace
from unittest.mock import patch

import pending_task
from working_set_exp import working_view
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.custody import ArtifactStore, RecordLog, verify_records
from working_set_exp.jsonutil import canonical_json_bytes, sha256_bytes, sha256_file
from working_set_exp.runtime import tokenizer_count

AREA = Path(__file__).resolve().parent
ROOT, study = pending_task.study.ROOT, pending_task.study
GROUPED = pending_task.grouped
BASE = "3c143bae5ead30024f9e815a8db109c7f3b49035"
SOURCE = pending_task.AREA / "run-001"
PROBE = ROOT / "development/working_set_continuation/review/page-search-probe-001"


def identities():
    paths = [Path(__file__), AREA / "PLAN.md", ROOT / "ARCHITECTURE.md",
             ROOT / "tests/test_decision_state.py"]
    return {**GROUPED_IDENTITIES(), **{p.relative_to(ROOT).as_posix(): sha256_file(p) for p in paths}}


GROUPED_IDENTITIES = GROUPED.identities


def original(path):
    """Read unchanged evidence directly from the published preimplementation tree."""
    relative = path.relative_to(ROOT).as_posix()
    raw = subprocess.run(["git", "show", BASE + ":" + relative], cwd=ROOT,
                         capture_output=True, check=True).stdout
    study.require(raw == path.read_bytes(), "historical bytes changed: " + relative)
    return raw


def native_for(request):
    # Seed does not enter this two-message template. Retain the actual seed in
    # the saved request; normalize only the existing template helper's assertion.
    rendered = copy.deepcopy(request)
    rendered["seed"] = study.prior.SEED
    return study.prior.expected_native(rendered)


def amended(request):
    candidate = copy.deepcopy(request)
    content = candidate["messages"][0]["content"]
    anchor = "p0_page: Returns a scoped directory or file-outline page"
    study.require(content.count(anchor) == 1 and working_view.INPUT_INTERPRETATION not in content,
                  "unexpected original reference")
    candidate["messages"][0]["content"] = content.replace(anchor, working_view.INPUT_INTERPRETATION + "\n\n" + anchor, 1)
    return candidate


def samples():
    records = verify_records(SOURCE / "records.jsonl", SOURCE)
    prepared = {r["payload"]["request_sha256"]: r["payload"] for r in records
                if r["record_type"] == "native_input_prepared"}
    for tag in ("C01", "C02", "C05"):
        path = SOURCE / f"calls/{tag}-wire-request.json"
        request = json.loads(original(path))
        row = prepared[sha256_bytes(canonical_json_bytes(request))]
        native = original(SOURCE / (row["stem"] + "-native.txt"))
        yield tag, request, native, row["prompt_tokens"], path.relative_to(ROOT).as_posix()
    counts = [json.loads(original(p)) for p in sorted(PROBE.glob("admission/*-count.json"))]
    row, = [r for r in counts if r["prompt_tokens"] == 23762]
    path = PROBE / (row["stem"] + "-endpoint-request.json")
    yield "historical-boundary", json.loads(original(path)), original(PROBE / (row["stem"] + "-native.txt")), 23762, path.relative_to(ROOT).as_posix()
    request = json.loads(original(SOURCE / "calls/C05-wire-request.json"))
    value = json.loads(request["messages"][1]["content"])
    value["workspace"]["working_set"] = dict(sources=[], saved_results=[])
    value["workspace"]["latest_feedback"] = None
    request["messages"][1]["content"] = canonical_json_bytes(value).decode()
    yield "constructed-empty-selection", request, native_for(request), None, "constructed from C05; no claimed model exposure"


def screen(folder):
    folder.mkdir(parents=True, exist_ok=False)
    store, log = ArtifactStore(folder), RecordLog(folder / "records.jsonl", "decision-state-input-cost")
    bound, rows, failed = identities(), [], None
    try:
        _, model, tokenizer = GROUPED.TASK.runtime_paths()
        runtime = dict(model_sha256=sha256_file(model), tokenizer_sha256=sha256_file(tokenizer))
        study.require(runtime["model_sha256"] == GROUPED.TASK.ACTOR["model_sha256"] and
                      runtime["tokenizer_sha256"] == study.prior.base.delivery.TOKENIZER_SHA, "runtime differs")
        log.append("vocabulary_qualification", dict(**runtime, model_completion_requests=0,
                   no_server_launched=True, native_tokenizer_subprocesses=True), [])
        for name, request, expected_native, expected_count, origin in samples():
            native = native_for(request)
            study.require(native == expected_native, "historical native rendering differs")
            changed = amended(request)
            variants = []
            for label, value in (("baseline", request), ("revised", changed)):
                rendered = native_for(value)
                count = tokenizer_count(SimpleNamespace(model_path=model, tokenizer_path=tokenizer), rendered)
                if label == "baseline" and expected_count is not None:
                    study.require(count == expected_count, "historical native count differs")
                row = dict(sample=name, variant=label, prompt_tokens=count,
                           input_admitted=count <= 23808, physical_generation_space=56576-count,
                           request_sha256=sha256_bytes(canonical_json_bytes(value)),
                           native_sha256=sha256_bytes(rendered), completion_sent=False)
                artifacts = [store.put(f"{name}/{label}-wire-request.json", completion_request_bytes(value)),
                             store.put(f"{name}/{label}-native.txt", rendered),
                             store.put(f"{name}/{label}-count.json", canonical_json_bytes(row))]
                log.append("native_input_counted", row, artifacts)
                variants.append(row)
            rows.append(dict(sample=name, source=origin, baseline=variants[0]["prompt_tokens"],
                             revised=variants[1]["prompt_tokens"], added_tokens=variants[1]["prompt_tokens"]-variants[0]["prompt_tokens"],
                             revised_admitted=variants[1]["input_admitted"]))
            print(name, rows[-1]["baseline"], "->", rows[-1]["revised"], flush=True)
        study.require(bound == identities(), "qualified sources changed")
        store.put("RESULTS.json", canonical_json_bytes(dict(status="qualified_offline", rows=rows,
            source_sha256=bound, model_completion_requests=0, limits=dict(input=23808, physical=56576, prospective_generation=32768),
            limitation="Textual cost only. Historical-boundary retains its older tool contract; no behavioral replay or automatic budget change is claimed.")))
    except BaseException as error:
        failed = error
        store.put("FAILED.json", canonical_json_bytes(dict(type=type(error).__name__, message=str(error))))
    finally:
        files = GROUPED.RUNTIME.file_inventory(folder)
        store.put("SEAL.json", canonical_json_bytes(dict(status="failed_preserved" if failed else "qualified_offline",
            source_sha256=bound, files=files, aggregate_sha256=sha256_bytes(canonical_json_bytes(files)), model_completion_requests=0)))
    if failed:
        raise failed
    verify_screen(folder)


def verify_screen(folder):
    seal = study.read(folder / "SEAL.json")
    study.require(seal["status"] == "qualified_offline" and seal["model_completion_requests"] == 0, "qualification failed")
    study.require(sha256_bytes(canonical_json_bytes(seal["files"])) == seal["aggregate_sha256"], "inventory differs")
    for row in seal["files"]:
        path = folder / row["path"]
        study.require(path.stat().st_size == row["size_bytes"] and sha256_file(path) == row["sha256"], "artifact differs")
    study.prior.verify_sources(seal["source_sha256"])
    records = verify_records(folder / "records.jsonl", folder)
    samples_by_name = {row[0]: row[1] for row in samples()}
    rows = []
    for name, original_request in samples_by_name.items():
        pair = []
        for label in ("baseline", "revised"):
            request = study.read(folder / name / f"{label}-wire-request.json")
            expected = original_request if label == "baseline" else amended(original_request)
            study.require(request == expected and completion_request_bytes(request) ==
                          (folder / name / f"{label}-wire-request.json").read_bytes(), "request differs")
            native = native_for(request)
            count = study.read(folder / name / f"{label}-count.json")
            study.require(native == (folder / name / f"{label}-native.txt").read_bytes() and
                          sha256_bytes(native) == count["native_sha256"] and
                          sha256_bytes(canonical_json_bytes(request)) == count["request_sha256"], "native identity differs")
            pair.append(count)
        rows.append((name, pair[1]["prompt_tokens"]-pair[0]["prompt_tokens"]))
    study.require(all(not r["payload"].get("completion_sent") for r in records), "completion recorded")
    return dict(status="verified", native_inputs=len(rows)*2, custody_records=len(records), added_tokens=rows,
                model_completion_requests=0, no_server_launched=True)


def route(folder, verify=False):
    # Reuse the qualified route and full server-side rendering/custody verifier.
    # The historical prefix is replayed under its original renderer by checkpoint().
    with patch.object(GROUPED, "identities", identities):
        if verify:
            return GROUPED.verify(folder)
        GROUPED.qualify(folder)
        return GROUPED.verify(folder)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("screen", "route", "verify"))
    args = parser.parse_args()
    if args.mode == "screen":
        screen(AREA / "input-cost-001")
    elif args.mode == "route":
        result = route(AREA / "contribution-001")
        study.save(AREA, "CONTRIBUTION_VERIFICATION.json", result)
        print(json.dumps(result, indent=2))
    else:
        print(json.dumps(dict(screen=verify_screen(AREA / "input-cost-001"),
                              contribution=route(AREA / "contribution-001", verify=True)), indent=2))
