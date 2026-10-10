"""CPU saved-state qualification. No runtime, tokenizer, or completion calls.

Run each case in its own Python process because historical task bootstraps use
shared module names. These are evaluator-selected fixtures, not model actions.
"""
import argparse
import copy
import importlib.util
import json
from pathlib import Path
import runpy
import sys

AREA = Path(__file__).resolve().parent
ROOT = AREA.parents[2]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT / "scripts"))
from working_set_exp.contribution_cycle import ContributionCycleMixin, focus_request
from working_set_exp.contribution_limits import Limits
from working_set_exp.contribution_reply import completion_request_bytes
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file


def read(path):
    return json.loads(Path(path).read_bytes())


def main(case, output):
    if case == "visible_source":
        task_area = AREA.parent / "configparser_unnamed"
        runpy.run_path(str(task_area / "bootstrap.py"))
        import unnamed_task as task
        selected = task.Task()
        run = task_area / "run-001"
        checkpoint, call = "after/C16-O02", "C17"
        objective = "Complete one bounded behavior change and obtain execution evidence."
    else:
        task_area = AREA.parent / "dispatch_continuity"
        runpy.run_path(str(task_area / "bootstrap.py"))
        import dispatch_task as task
        if case == "failed_check":
            selected = task.Task("union", "002")
            run = task_area / "union/run-002"
            checkpoint, call = "after/C11-O01", "C12"
            objective = "Resolve the recorded current failure before extending the contribution."
        else:
            sys.path.insert(0, str(task_area / "dynamic"))
            from run_saved_dispatch import Task as SavedTask
            selected = SavedTask("dynamic", "001", task_area / "union/run-002")
            run = task_area / "dynamic/run-001"
            checkpoint, call = "starting", "C16"
            objective = "Establish the behavior needed for the new job using saved work and fresh evidence."
    import run_contribution_cycle as cycle
    import run_uncoached_contribution as old
    state_path, candidate_path = run / f"{checkpoint}-state.json", run / f"{checkpoint}-candidate.json"
    session = selected.restore(read(state_path), read(candidate_path), run, replay=True)
    before_snapshot = task.snapshot(session)
    before_view = session.view()
    old_adapter = old.Adapter(selected)
    feedback = run / f"{checkpoint}-preceding-feedback.json"
    old_adapter.preceding_feedback = read(feedback)
    original = old_adapter.request_for(before_view)
    historical_wire = run / f"calls/{call}-wire-request.json"
    historical = read(historical_wire)
    exact_original = completion_request_bytes(original) == historical_wire.read_bytes()
    baseline_differences = []
    if not exact_original:
        # Older dispatch work predates two already-committed common-host changes.
        # Preserve that difference explicitly; do not call this exact replay.
        assert case in ("failed_check", "released_source")
        old_payload = read_bytes(historical["messages"][1]["content"])
        current_payload = read_bytes(original["messages"][1]["content"])
        assert current_payload["workspace"]["working_set"].pop("source_extent_scope") == "current_selection_not_one_acquisition"
        assert current_payload == old_payload, "additional historical data changed"
        assert {k:v for k,v in original.items() if k != "messages"} == {k:v for k,v in historical.items() if k != "messages"}
        baseline_differences = ["existing operating-reference revision", "existing source_extent_scope field"]
    # Independently qualify the presentation transform on the actual saved input.
    historical_projection = copy.deepcopy(historical)
    frozen_payload = read_bytes(historical_projection["messages"][1]["content"])
    frozen_payload["workspace"]["current_contribution"] = None
    historical_projection["messages"][1]["content"] = canonical_json_bytes(frozen_payload).decode()
    historical_projection = focus_request(historical_projection)
    check_projection = read_bytes(historical_projection["messages"][1]["content"])
    assert check_projection.pop("current_contribution") is None
    assert check_projection == read_bytes(historical["messages"][1]["content"])

    class CycleSession(ContributionCycleMixin, type(session)):
        pass
    session.__class__ = CycleSession
    path = ROOT / "development/bounded_working_set/parser-documentation/grammar-review/json_schema_to_grammar.py"
    spec = importlib.util.spec_from_file_location("cycle_qualification_converter", path)
    converter = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(converter)
    # CPU demonstration limits only: not a live model budget recommendation.
    limits = Limits(600, 1800, 900)
    adapter = cycle.Adapter(selected, checks=session.checkers, converter_class=converter.SchemaConverter, limits=limits)
    adapter.preceding_feedback = copy.deepcopy(old_adapter.preceding_feedback)
    revised = adapter.request_for(session.view())
    payload = read_bytes(revised["messages"][1]["content"])
    assert payload.pop("current_contribution") is None
    assert payload == read_bytes(original["messages"][1]["content"]), "evidence/history changed"
    assert {k:v for k,v in original.items() if k not in ("grammar", "messages")} == {
        k:v for k,v in revised.items() if k not in ("grammar", "messages")}, "sampler or envelope changed"
    assert task.snapshot(session) == before_snapshot
    assert revised["messages"][0]["content"].startswith(original["messages"][0]["content"])

    # This operation is evaluator-supplied. No diagnosis, coordinates, or patch.
    result = session.execute(dict(action="select_contribution", objective=objective, check_id="public"), lambda v: 1000)
    assert result["accepted"]
    assert session.candidate.candidate_id == before_view["candidate_id"]
    assert session.view()["working_set"] == before_view["working_set"]
    assert session.view()["working_account"] == before_view["working_account"]
    assert session.pairs[:-1] == before_snapshot["pairs"]
    new_snapshot = task.snapshot(session)
    restored = selected.restore(read_bytes(canonical_json_bytes(new_snapshot)), session.candidate, run, replay=True)
    restored.__class__ = CycleSession
    assert restored.view() == session.view(), "selection failed serialized restoration"
    scoped = session.current_contribution()["actual_selected_check"]
    if case == "failed_check":
        assert scoped and scoped["applies_to_current"] and not scoped["passed"]
    if case == "released_source":
        assert not session.sources()
        assert scoped and scoped["candidate_matches"] and not scoped["check_definition_matches"]
        path = "Lib/functools.py"
        before = session.candidate.candidate_id
        rejected = session.execute(dict(action="patch", path=path, old="import types\n", new="import types  # requires current source\n",
            expected_candidate_id=before, expected_file_sha256=session.candidate.file_sha256(path)), lambda v: 1000)
        assert not rejected["accepted"] and session.candidate.candidate_id == before
        # Ordinary reacquisition, not inherited exposure, supplies source authority.
        got = session.execute(dict(action="read", path=path, start_line=1, end_line=70), lambda v: 1000)
        assert got["accepted"]
        session.mark_delivered(session.view())
        assert session.delivered_sources
    if case == "visible_source":
        source = next(s for s in session.sources() if s["path"] == "Lib/configparser.py")
        assert source["returned_start_line"] == 1 and source["returned_end_line"] >= 1407

    output.mkdir(parents=True, exist_ok=False)
    artifacts = {}
    for name, value in (("current-baseline-request.json", original), ("historical-presentation-projection.json", historical_projection),
                         ("revised-request.json", revised), ("selected-request.json", adapter.request_for(session.view())),
                         ("selected-state.json", task.snapshot(session))):
        p = output / name
        p.write_bytes(canonical_json_bytes(value))
        artifacts[name] = sha256_file(p)
    native = adapter.expected_native(revised)
    (output / "expected-native.txt").write_bytes(native)
    artifacts["expected-native.txt"] = sha256_file(output / "expected-native.txt")
    evidence = [state_path, candidate_path, feedback, historical_wire, run / f"calls/{call}-assistant-content.txt",
                run / f"calls/{call}-assistant-reasoning.txt", run / f"calls/{call}-host-result.json"]
    report = dict(case=case, status="cpu_transition_and_exact_input_difference_passed", completion_requests=0,
        native_runtime_tested=False, capacity_meter="constant CPU stub, no token-fit claim", candidate_unchanged=True,
        historical_input_matches_current_baseline=exact_original, baseline_differences=baseline_differences,
        historical_projection_preserves_all_original_user_fields=True, original_sources_account_history_unchanged=True,
        selected_check=scoped, evaluator_authored_objective=objective, revised_request_bytes=len(completion_request_bytes(revised)),
        input_bindings={p.relative_to(ROOT).as_posix(): sha256_file(p) for p in evidence}, outputs=artifacts)
    (output / "RESULT.json").write_bytes(canonical_json_bytes(report))
    print(json.dumps({"case": case, "status": report["status"], "output": str(output)}))


def read_bytes(value):
    return json.loads(value)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("case", choices=("visible_source", "failed_check", "released_source"))
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    main(args.case, args.output)
