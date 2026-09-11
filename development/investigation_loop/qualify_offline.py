"""Exercise the proposed small loop with an oracle script, not a model actor."""
from pathlib import Path

from working_set_exp.candidate import Candidate
from working_set_exp.ecological_pilot_v2 import admitted_donor_candidate, _record_pair
from working_set_exp.isolation import run_checker
from working_set_exp.jsonutil import canonical_json_bytes, sha256_file
from working_set_exp.tools import SessionState, ToolExecutor


ROOT = Path(__file__).resolve().parents[2]
AREA = Path(__file__).resolve().parent
PROBE = ROOT / "maintenance/resume_after_020/fresh_investigation_probe.py"
TARGET = "src/addressable_information_layer/patching.py"
GOOD = "    new_map = build_address_map(new_artifact)\n"
BAD = "    new_map = address_map\n"
TASK = ("An accepted edit to a Python artifact is followed by a failed reopen of the edited function. "
        "Investigate and repair this behavior while preserving unrelated source, unchanged-content behavior, "
        "later updates, and rejection of genuinely stale references. Use exact current source before editing, "
        "run check public on the final candidate, and submit.")
CHECK_ASSERTIONS = '''
assert receipt.status.value == "applied"
assert exact_text_for_unit(updated, independent_unit) == replacement
assert current.status.value == "materialized" and current.materialized_text == replacement
assert unchanged.status.value == "materialized" and unchanged.materialized_text == "def untouched():\\n    return 7"
assert stale.status.value == "blocked"
assert second_receipt.status.value == "applied"
assert second_reopen.status.value == "materialized" and second_reopen.materialized_text == "def calculate():\\n    return 3"
assert no_change_reopen.status.value == "materialized" and no_change_reopen.materialized_text == exact_text_for_unit(old, old_unit)
'''


def main():
    output = AREA / "OFFLINE_FEASIBILITY.json"
    if output.exists():
        raise FileExistsError(output)
    checker = PROBE.read_bytes() + CHECK_ASSERTIONS.encode("utf-8")
    # Preserve the exact prospective check, including the authentic diagnostic.
    (AREA / "PUBLIC_CHECK.py").write_bytes(checker)
    (AREA / "TASK.txt").write_text(TASK + "\n", encoding="utf-8", newline="\n")
    donor = admitted_donor_candidate(ROOT / "experiments/020_owner_controlled_ecological_pilot_v2/fresh_bank")
    files = donor.file_map
    assert files[TARGET].count(GOOD.encode()) == 1
    files[TARGET] = files[TARGET].replace(GOOD.encode(), BAD.encode())
    broken = Candidate.create(files)
    baseline = run_checker(broken, checker)
    corrected = run_checker(donor, checker)
    assert not baseline["passed"] and corrected["passed"]
    state = SessionState(broken, stage="continuation")
    pairs, events, saved, transcript = [], {}, {}, []
    host = ToolExecutor(state, required_full_reads=(), prefork_checker=b"", public_checker=checker,
                        final_target="__none__", probe_id=None, probe_body=None, result_reopenable=saved,
                        event_reopenable=events, read_mode="maximal_bounded_page", hierarchical_p0=True)

    def act(action):
        before = state.candidate.candidate_id
        result = host.execute(action)
        assert result["accepted"], result
        handle = _record_pair(pairs, action, result, events, saved)
        transcript.append({"action":action, "result":result, "canonical_result_handle":handle,
                           "candidate_before":before, "candidate_after":state.candidate.candidate_id,
                           "public_check_passed":state.public_check_passed, "submitted":state.submitted})
        return result, handle

    # The oracle knows the repair. These actions qualify access/execution only.
    failed, failed_handle = act({"action":"check", "check_id":"public", "expected_candidate_id":broken.candidate_id})
    assert not failed["passed"]
    for path in (".", "src", "src/addressable_information_layer"):
        page, _ = act({"action":"p0_page", "path":path, "offset":0})
        assert page["entries"], page
    assert TARGET in [row["path"] for row in page["entries"]]
    start, read = 1, None
    while start is not None:
        read, _ = act({"action":"read", "path":TARGET, "start_line":start})
        start = read["next_start_line"]
    retrieved, _ = act({"action":"reopen_result", "handle":failed_handle})
    assert retrieved["exact_result_utf8"].encode() == canonical_json_bytes(failed)
    edit, edit_handle = act({"action":"patch", "path":TARGET, "old":BAD, "new":GOOD,
                            "expected_candidate_id":read["candidate_id"], "expected_file_sha256":read["file_sha256"]})
    assert not state.public_check_passed
    retrieved_edit, _ = act({"action":"reopen_result", "handle":edit_handle})
    assert retrieved_edit["exact_result_utf8"].encode() == canonical_json_bytes(edit)
    checked, _ = act({"action":"check", "check_id":"public", "expected_candidate_id":edit["candidate_id"]})
    assert checked["passed"] and checked["checked_candidate_id"] == edit["candidate_id"]
    submitted, _ = act({"action":"submit", "expected_candidate_id":checked["checked_candidate_id"]})
    assert submitted["public_check_passed_for_candidate"]
    report = {"scope":"offline oracle-driven loop and prospective check feasibility; not model behavior or a frozen live package",
              "model_completions":0, "task_sha256":sha256_file(AREA/"TASK.txt"), "public_check_sha256":sha256_file(AREA/"PUBLIC_CHECK.py"),
              "script_sha256":sha256_file(Path(__file__)), "host_tools_sha256":sha256_file(ROOT/"src/working_set_exp/tools.py"),
              "hierarchical_p0_sha256":sha256_file(ROOT/"src/working_set_exp/hierarchical_p0.py"),
              "source_probe_sha256":sha256_file(PROBE), "initial_candidate_id":broken.candidate_id,
              "final_candidate_id":state.candidate.candidate_id, "candidate_files":len(broken.files),
              "candidate_bytes":sum(len(data) for _,data in broken.files), "baseline_check":baseline,
              "independently_asserted_corrected_check":corrected, "scripted_tool_calls":len(transcript), "transcript":transcript,
              "initial_check_reveals_stale_map_diagnosis":True,
              "interpretation":"Suitable candidate for ordinary loop qualification. The authentic diagnostic already names a stale artifact map; no independent root-cause discovery or pressure-continuity evidence is claimed.",
              "model_navigation_qualified":False,"natural_pressure_qualified":False,
              "native_inputs_or_task_budget_qualified":False,"live_execution_authorized":False}
    output.write_bytes(canonical_json_bytes(report))
    print({key:report[key] for key in ("model_completions","scripted_tool_calls","initial_check_reveals_stale_map_diagnosis","natural_pressure_qualified")})


if __name__ == "__main__":
    main()
