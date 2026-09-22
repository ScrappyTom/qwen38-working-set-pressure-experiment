"""Save source-bound CPU projections of actual inputs; never invoke a runtime."""
from __future__ import annotations

import argparse
import copy
import json
from pathlib import Path
import sys
import traceback

import test_navigation as t


def describe(path):
    data = path.read_bytes()
    return dict(path=path.relative_to(t.ROOT).as_posix(), size_bytes=len(data),
                sha256=t.sha256_bytes(data))


def write(path, value):
    path.write_bytes(t.canonical_json_bytes(value))


def qualify(output):
    # A new directory identifies a new attempt. Never replace prior evidence.
    output.mkdir(parents=False, exist_ok=False)
    try:
        cases = []
        source_inputs = {t.RUN / "starting-candidate.json", t.RUN / "records.jsonl"}
        for tag, checkpoint in t.STATES.items():
            view, pairs, candidate = t.saved_case(tag)
            projected = t.nav.project_navigation(view, pairs, candidate)
            stripped = copy.deepcopy(projected)
            for row in stripped["recent_activity"]:
                row.pop("navigation", None)
            assert t.canonical_json_bytes(stripped) == t.canonical_json_bytes(view)
            write(output / f"{tag}-original-view.json", view)
            write(output / f"{tag}-navigation-view.json", projected)
            source_inputs.update((t.RUN / f"calls/{tag}-wire-request.json",
                                  t.RUN / f"after/{checkpoint}-state.json"))
            cases.append(dict(call=tag, candidate_id=candidate.candidate_id,
                archived_pairs_sha256=t.sha256_bytes(t.canonical_json_bytes(pairs)),
                original_view_bytes=len(t.canonical_json_bytes(view)),
                projected_view_bytes=len(t.canonical_json_bytes(projected)),
                navigation_added_bytes=(len(t.canonical_json_bytes(projected)) -
                                        len(t.canonical_json_bytes(view))),
                navigation_rows=[dict(sequence=r["sequence"],
                    result_handle=r["result_handle"], **r["navigation"])
                    for r in projected["recent_activity"] if "navigation" in r]))
        write(output / "RESULTS.json", dict(
            classification="CPU mechanical projection qualification; no model capability evidence",
            runtime_calls=0, completion_calls=0, checker_executions=0,
            native_tokens_measured=False,
            maximum_optional_navigation_bytes=t.nav.NAVIGATION_BYTES,
            maximum_recent_rows=t.nav.MAX_NAVIGATION_PAGES, cases=cases))
        # Historical C19 is an explicitly derived counterfactual. Its old RES
        # never contained a diff; preserve that fact instead of inventing access.
        wire=t.RUN/"calls/C19-wire-request.json"
        statepath=t.RUN/"after/C18-O01-state.json"
        recorded=[a for line in (t.RUN/"records.jsonl").read_bytes().splitlines()
                  for a in json.loads(line)["artifacts"]]
        for path in (wire,statepath):
            matches=[a for a in recorded if a["path"]==path.relative_to(t.RUN).as_posix()]
            assert matches and all(a["sha256"]==t.sha256_bytes(path.read_bytes()) and
                                   a["size_bytes"]==path.stat().st_size for a in matches)
        source_inputs.update((wire,statepath,t.RUN/"after/C18-O01-candidate.json"))
        original=json.loads(t.read(wire)["messages"][1]["content"])["workspace"]
        state=t.read(statepath)
        candidate=t.candidate_from(t.RUN/"after/C18-O01-candidate.json")
        assert candidate.candidate_id==state["candidate_id"]==original["candidate_id"]
        diffs={int(k):v for k,v in state["diffs"].items()}
        change=t.nav.project_immediate_change(original,historical_diffs=diffs)
        combined=t.nav.project_navigation(change,state["pairs"],candidate)
        write(output/"C19-original-view.json",original)
        write(output/"C19-change-counterfactual-view.json",change)
        write(output/"C19-combined-counterfactual-view.json",combined)
        write(output/"C19-CLASSIFICATION.json",dict(
            classification="Historical presentation counterfactual only; no recreated actor transition",
            exact_diff_source="after/C18-O01-state.json diffs[27]",
            original_RES_contains_applied_diff=False,
            raw_receipts_unchanged=True, native_tokens_measured=False,
            change_added_bytes=len(t.canonical_json_bytes(change))-len(t.canonical_json_bytes(original)),
            combined_added_bytes=len(t.canonical_json_bytes(combined))-len(t.canonical_json_bytes(original))))
        source_files = {Path(__file__).resolve(), t.AREA / "navigation.py",
                        t.AREA / "tests/test_navigation.py", t.AREA / "tests/test_change.py"}
        source_files.update(Path(m.__file__).resolve() for name,m in sys.modules.items()
                            if name.startswith("working_set_exp") and getattr(m,"__file__",None))
        write(output / "SOURCE_INPUTS.json", [describe(p) for p in sorted(source_inputs)])
        write(output / "SOURCE_CODE.json", [describe(p) for p in sorted(source_files)])
        write(output / "OUTPUTS.json", [describe(p) for p in sorted(output.glob("*.json"))])
    except BaseException:
        (output / "FAILURE.txt").write_text(traceback.format_exc(), encoding="utf-8")
        raise


if __name__ == "__main__":
    parser=argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    args=parser.parse_args()
    qualify(args.output.resolve())
    print(json.dumps(dict(status="complete", output=str(args.output)), ensure_ascii=True))
